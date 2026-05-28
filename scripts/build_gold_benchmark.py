#!/usr/bin/env python3
"""Build gold-standard ground truth benchmark using LLM validation."""

# Safely reconfigure standard output and standard error encoding error handling on Windows
import contextlib
import sys


for stream in (sys.stdout, sys.stderr):
    if stream and stream.encoding and stream.encoding.lower() != "utf-8":
        with contextlib.suppress(AttributeError):
            stream.reconfigure(errors="replace")

import argparse
import asyncio
import os
import random
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import ibis
from rich.console import Console
from rich.progress import track
from rich.table import Table

from causaganha.analysis.keyword_classifier import KeywordClassifier
from causaganha.analysis.llm_analyzer import LLMAnalyzer
from causaganha.analysis.models import DecisionAnalysis


console = Console()

DEFAULT_BATCH_SIZE = 20  # ~20x throughput vs single calls (1 RPD per batch)


def mock_analysis(intimation_id: int, text: str, keyword_outcome: str) -> tuple[DecisionAnalysis, str]:
    """Return a deterministic mock label based on keyword heuristic."""
    outcome = keyword_outcome if keyword_outcome != "unknown" else "improcedente"
    dec_type = "sentença"
    if "acórdão" in text.lower() or "acordam" in text.lower():
        dec_type = "acórdão"
    elif "interlocutória" in text.lower() or "liminar" in text.lower():
        dec_type = "decisão interlocutória"
    return DecisionAnalysis(
        intimation_id=intimation_id,
        outcome=outcome,
        decision_type=dec_type,
        plaintiff_won=outcome in ["procedente", "parcialmente procedente"],
        confidence_score=0.95 if outcome != "unknown" else 0.5,
        summary=f"Mock summary for decision {intimation_id}",
        decision_reasoning="Mock reasoning based on heuristic fallback.",
        analysis_method="mock_llm",
    ), "mock-gemini-2.5-flash-lite"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build gold benchmark dataset.")
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Target number of gold-labeled decisions to sample (default: 50).",
    )
    parser.add_argument(
        "--court",
        type=str,
        default="TJRO",
        help="Court to sample from (default: TJRO).",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock LLM responses (no API key needed).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=(
            f"Decisions per LLM call (default: {DEFAULT_BATCH_SIZE}). "
            "Higher = fewer RPD used; lower = faster per-batch latency."
        ),
    )
    args = parser.parse_args()

    console.print("\n[bold cyan]🏆 Construção do Benchmark de Ouro (Ground Truth)[/bold cyan]\n")

    # Load environment variables from .env file
    try:
        from dotenv import load_dotenv
        # Try current dir and parent directories
        load_dotenv()
        load_dotenv(Path(__file__).resolve().parents[1] / ".env")
        load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    except ImportError:
        # Fallback to manual parsing if python-dotenv is not installed
        for p in [Path("."), Path(".."), Path(__file__).resolve().parents[1], Path(__file__).resolve().parents[2]]:
            env_file = p / ".env"
            if env_file.exists():
                with open(env_file, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            # Handle export GEMINI_API_KEY="..." or GEMINI_API_KEY="..."
                            if line.startswith("export "):
                                line = line[7:]
                            if "=" in line:
                                k, v = line.split("=", 1)
                                k = k.strip()
                                v = v.strip().strip('"').strip("'")
                                os.environ[k] = v

    # Check API key
    api_key = (
        os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
    )
    if "OPENROUTER_API_KEY" in os.environ:
        del os.environ["OPENROUTER_API_KEY"]
    use_mock = args.mock or not api_key

    if not api_key:
        if args.mock:
            console.print(
                "[yellow]Aviso: Nenhuma chave de API configurada. Usando mock-LLM conforme solicitado.[/yellow]\n"  # noqa: E501
            )
        else:
            console.print(
                "[red]Erro: Nenhuma chave de API configurada (GEMINI_API_KEY, GOOGLE_API_KEY ou OPENROUTER_API_KEY).[/red]"  # noqa: E501
            )
            console.print(
                "[yellow]Para testar localmente sem custos, use o parâmetro --mock.[/yellow]"
            )
            return 1
    else:
        console.print(
            "[green]✓ Chave de API detectada. Utilizando provedores do LLMAnalyzer.[/green]\n"
        )

    db_path = Path("data/causaganha.duckdb")
    if not db_path.exists():
        console.print(f"[red]Erro: Banco de dados {db_path} não encontrado.[/red]")
        return 1

    # Connect to DuckDB
    conn = duckdb.connect(str(db_path))

    # Create gold_benchmark table if not exists
    conn.execute("""
        CREATE TABLE IF NOT EXISTS gold_benchmark (
            text_uuid VARCHAR PRIMARY KEY,
            intimation_id BIGINT,
            outcome VARCHAR NOT NULL,
            decision_type VARCHAR NOT NULL,
            plaintiff_won BOOLEAN,
            confidence_score DOUBLE,
            summary VARCHAR,
            decision_reasoning VARCHAR,
            texto VARCHAR NOT NULL,
            court VARCHAR NOT NULL,
            llm_model VARCHAR,
            validated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_human_verified BOOLEAN DEFAULT FALSE,
            fase_processual VARCHAR,
            classe_processual VARCHAR,
            assunto_principal VARCHAR,
            valor_causa DOUBLE,
            valor_condenacao DOUBLE,
            proposed_regex VARCHAR,
            judge_name VARCHAR,
            keywords VARCHAR[],
            legal_bases VARCHAR[],
            precedents MAP(VARCHAR, VARCHAR)
        )
    """)

    # Get already indexed UUIDs in gold_benchmark to avoid re-labeling
    existing_uuids = {
        r[0] for r in conn.execute("SELECT text_uuid FROM gold_benchmark").fetchall()
    }
    console.print(f"[blue]Benchmark atual possui {len(existing_uuids)} decisões anotadas.[/blue]\n")

    # Fetch candidates from intimations (fetching hash as the text_uuid)
    console.print(f"[yellow]Buscando decisões de {args.court} em intimations...[/yellow]")
    candidates = conn.execute(
        """
        SELECT hash, id, texto
        FROM intimations
        WHERE sigla_tribunal = ?
          AND texto IS NOT NULL
          AND hash IS NOT NULL
          AND LENGTH(texto) BETWEEN 500 AND 8000
    """,
        (args.court,),
    ).fetchall()

    if not candidates:
        console.print(f"[red]Erro: Nenhuma decisão encontrada para o tribunal {args.court}.[/red]")
        conn.close()
        return 1

    console.print(f"✓ Encontradas {len(candidates):,} decisões candidatas.")

    # Exclude already processed ones
    new_candidates = [c for c in candidates if c[0] not in existing_uuids]
    console.print(f"✓ {len(new_candidates):,} são novas decisões.")

    if not new_candidates:
        console.print(
            "[green]Todas as decisões candidatas já foram rotuladas. Benchmark atualizado![/green]"
        )
        conn.close()
        return 0

    # Stratified pre-classification using KeywordClassifier
    console.print("\n[yellow]Pré-classificando com heurísticas para balanceamento...[/yellow]")
    kc = KeywordClassifier()
    grouped_candidates = defaultdict(list)

    for text_uuid, int_id, text in new_candidates:
        outcome, _ = kc.classify(text)
        grouped_candidates[outcome].append((text_uuid, int_id, text, outcome))

    # Print distribution
    dist_table = Table(title="Distribuição das novas candidatas por heurística")
    dist_table.add_column("Outcome", style="cyan")
    dist_table.add_column("Candidatos", style="yellow", justify="right")
    for out, items in grouped_candidates.items():
        dist_table.add_row(out, f"{len(items):,}")
    console.print(dist_table)

    # Sample equally from each bucket up to limit
    outcomes = list(grouped_candidates.keys())
    sampled_items = []

    # Calculate how many we need to sample to reach limit
    remaining_to_sample = min(args.limit, len(new_candidates))

    # Keep sampling in rounds to ensure balance
    while remaining_to_sample > 0 and any(grouped_candidates.values()):
        active_outcomes = [o for o in outcomes if grouped_candidates[o]]
        if not active_outcomes:
            break

        # Take one from each active outcome group
        for o in active_outcomes:
            if remaining_to_sample <= 0:
                break
            item = grouped_candidates[o].pop(random.randint(0, len(grouped_candidates[o]) - 1))
            sampled_items.append(item)
            remaining_to_sample -= 1

    console.print(
        f"\n[green]Selecionadas {len(sampled_items)} decisões para rotulação com LLM.[/green]"
    )

    # Run LLM labeling (batched for RPD efficiency)
    analyzer = LLMAnalyzer(models=LLMAnalyzer.models_from_env())
    gold_records: list[tuple[str, int, DecisionAnalysis, str, str]] = []
    batch_size = args.batch_size

    async def process_all() -> None:
        # Shuffle to avoid consecutive similar decisions biasing the model
        shuffled = sampled_items.copy()
        random.shuffle(shuffled)

        # Split into batches
        batches = [
            shuffled[i : i + batch_size]
            for i in range(0, len(shuffled), batch_size)
        ]
        n_batches = len(batches)
        console.print(
            f"  [dim]Batch size: {batch_size} | "
            f"Batches: {n_batches} | "
            f"RPD used: {n_batches} (de ~1 000 disponíveis)[/dim]"
        )

        for batch in track(batches, description="Rotulando batches com LLM"):
            if use_mock:
                # Mock: process individually (no API call)
                for text_uuid, int_id, text, heur_outcome in batch:
                    analysis, model_used = mock_analysis(int_id, text, heur_outcome)
                    gold_records.append((text_uuid, int_id, analysis, text, model_used))
            else:
                # Real batch call
                batch_items = [(int_id, text) for _, int_id, text, _ in batch]
                try:
                    results = await analyzer.analyze_batch(batch_items)
                    for text_uuid, int_id, text, _ in batch:
                        if int_id in results:
                            analysis, model_used = results[int_id]
                            gold_records.append((text_uuid, int_id, analysis, text, model_used))
                        else:
                            console.print(f"[yellow]  Sem resultado para ID {int_id} no batch[/yellow]")
                except Exception as e:
                    console.print(f"[red]  Falha no batch: {e}[/red]")
                
                # Sleep to avoid hitting Gemini's strict 15 RPM (requests per minute) rate limit
                await asyncio.sleep(5)

    asyncio.run(process_all())

    # Insert into gold_benchmark in DuckDB
    console.print(
        f"\n[yellow]Salvando {len(gold_records)} registros rotulados no banco de dados...[/yellow]"
    )
    inserted_count = 0
    for text_uuid, int_id, analysis, text, model_used in gold_records:
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO gold_benchmark (
                    text_uuid, intimation_id, outcome, decision_type, plaintiff_won,
                    confidence_score, summary, decision_reasoning,
                    texto, court, llm_model, validated_at, is_human_verified,
                    fase_processual, classe_processual, assunto_principal,
                    valor_causa, valor_condenacao,
                    proposed_regex, judge_name, keywords, legal_bases, precedents
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    text_uuid,
                    int_id,
                    analysis.outcome,
                    analysis.decision_type,
                    analysis.plaintiff_won,
                    analysis.confidence_score,
                    analysis.summary,
                    analysis.decision_reasoning,
                    text,
                    args.court,
                    model_used,
                    datetime.now(UTC),
                    False,
                    analysis.fase_processual,
                    analysis.classe_processual,
                    analysis.assunto_principal,
                    analysis.valor_causa,
                    analysis.valor_condenacao,
                    analysis.proposed_regex,
                    analysis.judge_name,
                    analysis.keywords,
                    analysis.legal_bases,
                    analysis.precedents,
                ),
            )
            inserted_count += 1
        except Exception as e:
            console.print(f"[red]Erro ao salvar UUID {text_uuid}: {e}[/red]")

    conn.commit()
    console.print(f"[green]✓ Inseridos {inserted_count} novos registros no DuckDB.[/green]")

    # Compact benchmark into a parquet file for offline caching and fast reads
    benchmark_dir = Path("data/benchmark")
    benchmark_dir.mkdir(parents=True, exist_ok=True)
    parquet_path = benchmark_dir / "gold_benchmark.parquet"

    # Query all gold benchmark records
    gold_df = conn.execute("SELECT * FROM gold_benchmark").df()

    # Write to parquet using Ibis
    gold_table = ibis.memtable(gold_df)
    gold_table.to_parquet(parquet_path)

    console.print(
        f"[green]✓ Benchmark exportado para {parquet_path} ({len(gold_df)} registros no total).[/green]"  # noqa: E501
    )

    # Export each decision as a .md file with frontmatter metadata
    console.print("\n[yellow]Exportando decisões para arquivos Markdown (.md)...[/yellow]")
    import yaml
    
    # Ensure markdown output directory exists in the workspace
    md_dir = Path("data/benchmark/decisions")
    md_dir.mkdir(parents=True, exist_ok=True)

    # Remove any existing .md file in the folder to keep it synchronized
    for existing_md in md_dir.glob("*.md"):
        existing_md.unlink()

    for row in gold_df.to_dict(orient="records"):
        text_uuid = row["text_uuid"]
        int_id = row["intimation_id"]
        court = row["court"]
        texto = row.pop("texto", "")
        # Convert timestamp to string
        val_date_str = ""
        if isinstance(row.get("validated_at"), datetime):
            val_date_str = row["validated_at"].strftime("%Y-%m-%d")
            row["validated_at"] = row["validated_at"].isoformat()
        else:
            try:
                # parsed from ISO-8601 string if it comes as string
                dt = datetime.fromisoformat(str(row.get("validated_at")))
                val_date_str = dt.strftime("%Y-%m-%d")
            except ValueError:
                val_date_str = "2026-05-27"
        
        # Add schema version for dataset versioning tracking
        row["schema_version"] = "1.2.0"
        
        # Clean numpy/pandas data types so they serialize cleanly to standard YAML
        import numpy as np
        for k, v in list(row.items()):
            if isinstance(v, np.ndarray):
                row[k] = v.tolist()
            elif isinstance(v, float) and np.isnan(v):
                row[k] = None
            elif isinstance(v, list):
                row[k] = [x.tolist() if isinstance(x, np.ndarray) else x for x in v]
            elif isinstance(v, dict):
                row[k] = {str(dk): (dv.tolist() if isinstance(dv, np.ndarray) else dv) for dk, dv in v.items()}
        
        # Build YAML frontmatter
        frontmatter = yaml.dump(row, allow_unicode=True, default_flow_style=False).strip()
        
        # filename format: court-date-intimation_id.md
        md_filename = f"{court}-{val_date_str}-{int_id}.md"
        md_content = f"---\n{frontmatter}\n---\n\n{texto}\n"
        md_path = md_dir / md_filename
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

    console.print(f"[green]✓ {len(gold_df)} arquivos .md criados com sucesso em {md_dir}.[/green]\n")

    # Show final distribution stats
    stats = conn.execute("""
        SELECT outcome, COUNT(*), AVG(confidence_score)
        FROM gold_benchmark
        GROUP BY 1
        ORDER BY 2 DESC
    """).fetchall()

    final_table = Table(title="Estatísticas Finais do Benchmark de Ouro")
    final_table.add_column("Outcome", style="cyan")
    final_table.add_column("Qtd", style="yellow", justify="right")
    final_table.add_column("Confiança LLM Média", style="green", justify="right")

    for outcome, count, avg_conf in stats:
        final_table.add_row(outcome, str(count), f"{avg_conf:.2f}")
    console.print(final_table)

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
