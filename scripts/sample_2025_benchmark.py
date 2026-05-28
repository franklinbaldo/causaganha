#!/usr/bin/env python3
"""Sample 2025 decisions from anchor_set.parquet and validate them with LLM for the benchmark."""

import asyncio
import hashlib
import os
import random
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import ibis
import yaml
import numpy as np
from rich.console import Console
from rich.progress import track
from rich.table import Table

from causaganha.analysis.llm_analyzer import LLMAnalyzer
from causaganha.analysis.models import DecisionAnalysis

console = Console()
DEFAULT_BATCH_SIZE = 20


def generate_deterministic_ids(text: str, numero_processo: str) -> tuple[str, int]:
    """Generate a deterministic text_uuid (str) and intimation_id (int) from text and process number."""
    # Use MD5 of text for text_uuid (consistent 32-char hex string)
    text_uuid = hashlib.md5(text.encode("utf-8")).hexdigest()
    # Generate 63-bit signed integer for intimation_id (fits in BIGINT)
    # Using md5 of process number to keep it clean and deterministic
    proc_hash = hashlib.md5(numero_processo.encode("utf-8")).hexdigest()
    intimation_id = int(proc_hash[:15], 16)
    return text_uuid, intimation_id


def main() -> int:
    console.print("\n[bold cyan]🏆 Amostragem e Validação de Casos de 2025 para o Benchmark[/bold cyan]\n")

    # Load environment variables from .env files
    try:
        from dotenv import load_dotenv
        load_dotenv()
        load_dotenv(Path(__file__).resolve().parents[1] / ".env")
        load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    except ImportError:
        pass

    # Ensure API Key is present
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        console.print("[red]Erro: Nenhuma chave de API do Gemini/Google encontrada no ambiente.[/red]")
        return 1

    db_path = Path("data/causaganha.duckdb")
    if not db_path.exists():
        console.print(f"[red]Erro: Banco de dados {db_path} não encontrado.[/red]")
        return 1

    # Connect to DuckDB
    conn = duckdb.connect(str(db_path))

    # Get already indexed text_uuids to avoid re-labeling
    existing_uuids = {
        r[0] for r in conn.execute("SELECT text_uuid FROM gold_benchmark").fetchall()
    }
    console.print(f"[blue]Benchmark atual possui {len(existing_uuids)} decisões anotadas.[/blue]\n")

    # Read from anchor_set.parquet using DuckDB
    parquet_path = Path("data/anchor_set.parquet")
    if not parquet_path.exists():
        console.print(f"[red]Erro: {parquet_path} não encontrado.[/red]")
        conn.close()
        return 1

    console.print(f"[yellow]Lendo e filtrando casos de 2025 de {parquet_path}...[/yellow]")
    all_rows = conn.execute(
        f"""
        SELECT numero_processo, texto_truncado, outcome
        FROM '{parquet_path}'
        WHERE SUBSTR(numero_processo, 10, 4) = '2025'
          AND texto_truncado IS NOT NULL
        """
    ).fetchall()

    console.print(f"✓ Encontrados {len(all_rows)} casos do ano de 2025 no Parquet.")

    # Filter out already existing cases
    candidates = []
    for proc, text, outcome in all_rows:
        text_uuid, intimation_id = generate_deterministic_ids(text, proc)
        if text_uuid not in existing_uuids:
            candidates.append((text_uuid, intimation_id, proc, text, outcome))

    console.print(f"✓ {len(candidates)} casos de 2025 são novos/não rotulados.")
    if not candidates:
        console.print("[green]Todas as decisões de 2025 já foram rotuladas ou adicionadas.[/green]")
        conn.close()
        return 0

    # Stratified balance grouping by the outcome column
    grouped_candidates = defaultdict(list)
    for item in candidates:
        outcome = item[4]
        grouped_candidates[outcome].append(item)

    # Print distribution
    dist_table = Table(title="Distribuição dos Candidatos de 2025 por Outcome")
    dist_table.add_column("Outcome", style="cyan")
    dist_table.add_column("Qtd", style="yellow", justify="right")
    for out, items in grouped_candidates.items():
        dist_table.add_row(out, str(len(items)))
    console.print(dist_table)

    # Target 40 new cases (2 batches of 20)
    target_to_sample = min(40, len(candidates))
    sampled_items = []
    outcomes = list(grouped_candidates.keys())

    # Round robin sampling to keep it balanced
    while len(sampled_items) < target_to_sample and any(grouped_candidates.values()):
        active_outcomes = [o for o in outcomes if grouped_candidates[o]]
        if not active_outcomes:
            break
        for o in active_outcomes:
            if len(sampled_items) >= target_to_sample:
                break
            item = grouped_candidates[o].pop(random.randint(0, len(grouped_candidates[o]) - 1))
            sampled_items.append(item)

    console.print(f"\n[green]Selecionadas {len(sampled_items)} decisões de 2025 para validação com o LLM.[/green]")

    # Run LLM validation in batches
    analyzer = LLMAnalyzer(models=LLMAnalyzer.models_from_env())
    gold_records = []
    batch_size = DEFAULT_BATCH_SIZE

    async def process_all():
        shuffled = sampled_items.copy()
        random.shuffle(shuffled)

        batches = [
            shuffled[i : i + batch_size]
            for i in range(0, len(shuffled), batch_size)
        ]

        for i, batch in enumerate(batches, 1):
            console.print(f"\n[yellow]Processando batch {i}/{len(batches)} (tamanho: {len(batch)})...[/yellow]")
            batch_items = [(int_id, text) for _, int_id, _, text, _ in batch]
            
            try:
                results = await analyzer.analyze_batch(batch_items)
                for text_uuid, int_id, proc, text, _ in batch:
                    if int_id in results:
                        analysis, model_used = results[int_id]
                        gold_records.append((text_uuid, int_id, proc, analysis, text, model_used))
                    else:
                        console.print(f"[red]Sem resultado retornado para ID {int_id}[/red]")
            except Exception as e:
                console.print(f"[red]Erro ao executar batch {i}: {e}[/red]")

            if i < len(batches):
                console.print("[dim]Aguardando 5 segundos para respeitar limites de taxa...[/dim]")
                await asyncio.sleep(5)

    asyncio.run(process_all())

    console.print(f"\n[yellow]Salvando {len(gold_records)} registros validados no banco de dados...[/yellow]")
    inserted_count = 0
    for text_uuid, int_id, proc, analysis, text, model_used in gold_records:
        try:
            # We save court as "TJRO" because the process numbers correspond to Rondônia court structure
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
                    "TJRO",
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
    console.print(f"[green]✓ Inseridos {inserted_count} novos registros de 2025 no DuckDB.[/green]")

    # Export all gold benchmark records to Parquet file
    parquet_dest = Path("data/benchmark/gold_benchmark.parquet")
    gold_df = conn.execute("SELECT * FROM gold_benchmark").df()
    gold_table = ibis.memtable(gold_df)
    gold_table.to_parquet(parquet_dest)
    console.print(f"[green]✓ Benchmark total exportado para {parquet_dest} ({len(gold_df)} registros no total).[/green]")

    # Write Markdown files for ALL decisions to keep decisions/ dir sync'd
    md_dir = Path("data/benchmark/decisions")
    md_dir.mkdir(parents=True, exist_ok=True)

    # Clean existing .md files
    for existing_md in md_dir.glob("*.md"):
        existing_md.unlink()

    console.print("[yellow]Exportando todos os registros do benchmark para arquivos Markdown (.md)...[/yellow]")
    for row in gold_df.to_dict(orient="records"):
        text_uuid = row["text_uuid"]
        int_id = row["intimation_id"]
        court = row["court"]
        texto = row.pop("texto", "")
        
        val_date_str = "2026-05-27"
        if isinstance(row.get("validated_at"), datetime):
            val_date_str = row["validated_at"].strftime("%Y-%m-%d")
            row["validated_at"] = row["validated_at"].isoformat()
        else:
            try:
                dt = datetime.fromisoformat(str(row.get("validated_at")))
                val_date_str = dt.strftime("%Y-%m-%d")
            except ValueError:
                pass

        row["schema_version"] = "1.2.0"

        # Clean numpy types
        for k, v in list(row.items()):
            if isinstance(v, np.ndarray):
                row[k] = v.tolist()
            elif isinstance(v, float) and np.isnan(v):
                row[k] = None
            elif isinstance(v, list):
                row[k] = [x.tolist() if isinstance(x, np.ndarray) else x for x in v]
            elif isinstance(v, dict):
                row[k] = {str(dk): (dv.tolist() if isinstance(dv, np.ndarray) else dv) for dk, dv in v.items()}

        frontmatter = yaml.dump(row, allow_unicode=True, default_flow_style=False).strip()
        md_filename = f"{court}-{val_date_str}-{int_id}.md"
        md_content = f"---\n{frontmatter}\n---\n\n{texto}\n"
        
        with open(md_dir / md_filename, "w", encoding="utf-8") as f:
            f.write(md_content)

    console.print(f"[green]✓ {len(gold_df)} arquivos .md atualizados com sucesso em {md_dir}.[/green]\n")

    # Final stats table
    stats = conn.execute("""
        SELECT outcome, COUNT(*)
        FROM gold_benchmark
        GROUP BY 1
        ORDER BY 2 DESC
    """).fetchall()

    final_table = Table(title="Estatísticas Consolidadas do Benchmark")
    final_table.add_column("Outcome", style="cyan")
    final_table.add_column("Total Labeled", style="green", justify="right")
    for out, count in stats:
        final_table.add_row(out, str(count))
    console.print(final_table)

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
