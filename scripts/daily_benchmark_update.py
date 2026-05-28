#!/usr/bin/env python3
"""Daily incremental ground truth benchmark updater."""

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
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import ibis
from rich.console import Console
from rich.progress import track

from causaganha.analysis.keyword_classifier import KeywordClassifier
from causaganha.analysis.llm_analyzer import LLMAnalyzer
from causaganha.analysis.models import DecisionAnalysis


console = Console()


async def label_with_llm(
    analyzer: LLMAnalyzer,
    text: str,
    intimation_id: int,
    *,
    use_mock: bool,
    keyword_outcome: str,
) -> tuple[DecisionAnalysis, str]:
    """Obtain gold label from LLM or fallback to mock."""
    if use_mock:
        # Mock LLM analysis using KeywordClassifier base
        outcome = keyword_outcome if keyword_outcome != "unknown" else "extinto sem mérito"
        dec_type = "sentença"
        if "acórdão" in text.lower() or "acordam" in text.lower():
            dec_type = "acórdão"
        elif "interlocutória" in text.lower() or "liminar" in text.lower():
            dec_type = "decisão interlocutória"

        mock_analysis = DecisionAnalysis(
            intimation_id=intimation_id,
            outcome=outcome,
            decision_type=dec_type,
            plaintiff_won=outcome in ["procedente", "parcialmente procedente"],
            confidence_score=0.95 if outcome != "unknown" else 0.5,
            summary=f"Daily Mock summary for decision {intimation_id}",
            decision_reasoning="Daily Mock reasoning based on heuristic fallback.",
            analysis_method="mock_llm",
        )
        return mock_analysis, "mock-claude-3-5"

    return await analyzer.analyze_text(text, intimation_id=intimation_id)


def main() -> int:
    parser = argparse.ArgumentParser(description="Daily incremental benchmark update.")
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Number of new decisions to sample and label today (default: 5).",
    )
    parser.add_argument(
        "--court",
        type=str,
        default="TJRO",
        help="Court to target (default: TJRO).",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock LLM responses if API keys are missing.",
    )
    args = parser.parse_args()

    console.print("\n[bold cyan]🔄 Atualização Diária do Benchmark (Rotina Claude)[/bold cyan]\n")

    # Load environment variables from .env files
    try:
        from dotenv import load_dotenv
        load_dotenv()
        load_dotenv(Path(__file__).resolve().parents[1] / ".env")
        load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    except ImportError:
        pass

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
                "[yellow]Aviso: Nenhuma chave de API configurada. Usando mock-LLM para atualização diária.[/yellow]\n"  # noqa: E501
            )
        else:
            console.print(
                "[red]Erro: Nenhuma chave de API configurada (GEMINI_API_KEY ou GOOGLE_API_KEY).[/red]"  # noqa: E501
            )
            console.print("[yellow]Para executar testes locais, utilize --mock.[/yellow]")
            return 1

    db_path = Path("data/causaganha.duckdb")
    if not db_path.exists():
        console.print(f"[red]Erro: Banco de dados {db_path} não encontrado.[/red]")
        return 1

    conn = duckdb.connect(str(db_path))

    # Verify if gold_benchmark table exists
    tables = [r[0] for r in conn.execute("SHOW TABLES").fetchall()]
    if "gold_benchmark" not in tables:
        console.print(
            "[yellow]Tabela gold_benchmark não existe. Execute scripts/build_gold_benchmark.py primeiro.[/yellow]"  # noqa: E501
        )
        conn.close()
        return 1

    # Get already labeled IDs/hashes
    existing_uuids = {
        r[0] for r in conn.execute("SELECT text_uuid FROM gold_benchmark").fetchall()
    }
    existing_ids = {
        r[0] for r in conn.execute("SELECT intimation_id FROM gold_benchmark").fetchall()
    }

    # Fetch new candidate decisions
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

    new_candidates = [c for c in candidates if c[0] not in existing_uuids and c[1] not in existing_ids]
    if not new_candidates:
        console.print(
            "[green]✓ Não há novas decisões para rotular. Benchmark está 100% atualizado![/green]"
        )
        conn.close()
        return 0

    console.print(f"Encontrados {len(new_candidates)} novos candidatos em intimations.")

    # Classify candidate decisions using KeywordClassifier to identify "hard cases"
    kc = KeywordClassifier()
    hard_cases = []
    normal_cases = []

    for text_uuid, int_id, text in new_candidates:
        outcome, confidence = kc.classify(text)
        if outcome == "unknown" or confidence < 0.80:
            hard_cases.append((text_uuid, int_id, text, outcome, confidence))
        else:
            normal_cases.append((text_uuid, int_id, text, outcome, confidence))

    console.print(
        f"  Casos difíceis (heurística desconhecida ou <80% confiança): {len(hard_cases)}"
    )
    console.print(f"  Casos normais: {len(normal_cases)}")

    # We want to prioritize hard cases for our benchmark so that it focuses on ambiguous decisions
    selected_for_labeling = []

    # 1. Take hard cases first
    hard_to_take = min(args.limit, len(hard_cases))
    selected_for_labeling.extend(hard_cases[:hard_to_take])

    # 2. If we still need more to meet the limit, fill with normal cases
    remaining = args.limit - len(selected_for_labeling)
    if remaining > 0 and normal_cases:
        selected_for_labeling.extend(normal_cases[: min(remaining, len(normal_cases))])

    console.print(
        f"\n[bold yellow]Selecionados {len(selected_for_labeling)} casos para rotulação diária (priorizando casos difíceis)...[/bold yellow]\n"  # noqa: E501
    )

    # Run LLM labeling
    analyzer = LLMAnalyzer(models=LLMAnalyzer.models_from_env())
    gold_records = []

    async def process_all():
        for text_uuid, int_id, text, heur_outcome, heur_conf in track(
            selected_for_labeling, description="Processando"
        ):
            try:
                analysis, model_used = await label_with_llm(
                    analyzer,
                    text,
                    int_id,
                    use_mock=use_mock,
                    keyword_outcome=heur_outcome,
                )
                gold_records.append((text_uuid, int_id, analysis, text, model_used))
                console.print(
                    f"  [cyan]ID {int_id}[/cyan]: LLM={analysis.outcome} | Heurística={heur_outcome} (conf: {heur_conf:.2f})"  # noqa: E501
                )
            except Exception as e:
                console.print(f"[red]Erro ao processar ID {int_id}: {e}[/red]")

    asyncio.run(process_all())

    if not gold_records:
        console.print("[yellow]Nenhum registro foi processado com sucesso.[/yellow]")
        conn.close()
        return 0

    # Insert into gold_benchmark
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
            console.print(f"[red]Erro ao salvar ID {int_id}: {e}[/red]")

    conn.commit()
    console.print(f"\n[green]✓ {inserted_count} novos registros adicionados ao DuckDB.[/green]")

    # Regenerate benchmark.parquet
    benchmark_dir = Path("data/benchmark")
    benchmark_dir.mkdir(parents=True, exist_ok=True)
    parquet_path = benchmark_dir / "gold_benchmark.parquet"

    gold_df = conn.execute("SELECT * FROM gold_benchmark").df()
    gold_table = ibis.memtable(gold_df)
    gold_table.to_parquet(parquet_path)
    console.print(
        f"[green]✓ Benchmark atualizado e exportado para {parquet_path} ({len(gold_df)} registros no total).[/green]\n"  # noqa: E501
    )

    # Export each decision as a .md file with frontmatter metadata
    console.print("[yellow]Exportando decisões para arquivos Markdown (.md)...[/yellow]")
    import yaml
    import numpy as np

    md_dir = Path("data/benchmark/decisions")
    md_dir.mkdir(parents=True, exist_ok=True)

    # Clean existing .md files
    for existing_md in md_dir.glob("*.md"):
        existing_md.unlink()

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
        md_path = md_dir / md_filename
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

    console.print(f"[green]✓ {len(gold_df)} arquivos .md atualizados com sucesso em {md_dir}.[/green]\n")

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
