#!/usr/bin/env python3
"""Evaluate KeywordClassifier and ML models against the gold benchmark."""

# Safely reconfigure standard output and standard error encoding error handling on Windows
import contextlib
import sys


for stream in (sys.stdout, sys.stderr):
    if stream and stream.encoding and stream.encoding.lower() != "utf-8":
        with contextlib.suppress(AttributeError):
            stream.reconfigure(errors="replace")

import argparse
import asyncio
from collections import defaultdict
from pathlib import Path

import duckdb
from rich.console import Console
from rich.table import Table

from causaganha.analysis.benchmark_metrics import InvariantReport, evaluate_invariant
from causaganha.analysis.keyword_classifier import KeywordClassifier


console = Console()


def show_invariant_report(report: InvariantReport, classifier_name: str) -> None:
    """Render the gate + conditional decomposition of invariant-winner scoring.

    The surface ``outcome`` label is posture-dependent; this scores the
    invariant winning polo (A/P/draw) and separates the "is this ratable?"
    gate from the "who won?" conditional so the ~40% procedural ``unknown``
    mass cannot mask outcome performance.
    """
    g = report.gate
    c = report.conditional
    console.print(f"\n[bold cyan]⚖️  Invariante (Polo Vencedor) — {classifier_name}[/bold cyan]")
    console.print(
        f"[bold]Gate (decisão de mérito ratável?):[/bold] "
        f"acc {g.accuracy * 100:.1f}% · P {g.precision:.2f} · R {g.recall:.2f} · "
        f"F1 {g.f1:.2f} · suporte ratável {g.support_ratable}/{g.total}"
    )
    console.print(
        f"[bold]Condicional (polo vencedor | ratável):[/bold] "
        f"acc {c.accuracy * 100:.1f}% sobre {c.n_scored} casos\n"
    )

    table = Table(title=f"Invariante por Polo — {classifier_name}")
    table.add_column("Polo", style="cyan")
    table.add_column("Precisão", style="yellow", justify="right")
    table.add_column("Recall", style="green", justify="right")
    table.add_column("F1-Score", style="magenta", justify="right")
    table.add_column("Suporte", justify="right")
    for polo in ("A", "P", "draw"):
        m = c.per_polo[polo]
        table.add_row(
            polo,
            f"{m['precision']:.2f}",
            f"{m['recall']:.2f}",
            f"{m['f1']:.2f}",
            str(m["support"]),
        )
    console.print(table)


def compute_metrics(y_true: list[str], y_pred: list[str], labels: list[str]) -> dict:
    """Compute precision, recall, and F1 score for each class."""
    metrics = {}

    # Calculate overall accuracy
    correct = sum(1 for t, p in zip(y_true, y_pred, strict=True) if t == p)
    total = len(y_true)
    accuracy = correct / total if total > 0 else 0.0

    metrics["accuracy"] = accuracy
    metrics["total"] = total

    # Calculate per-class metrics
    for label in labels:
        tp = sum(1 for t, p in zip(y_true, y_pred, strict=True) if t == label and p == label)
        fp = sum(1 for t, p in zip(y_true, y_pred, strict=True) if t != label and p == label)
        fn = sum(1 for t, p in zip(y_true, y_pred, strict=True) if t == label and p != label)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        # Support
        support = sum(1 for t in y_true if t == label)

        metrics[label] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": support,
        }

    return metrics


def show_confusion_matrix(y_true: list[str], y_pred: list[str], labels: list[str]) -> None:
    """Render a confusion matrix using a rich table."""
    matrix = defaultdict(lambda: defaultdict(int))
    for t, p in zip(y_true, y_pred, strict=True):
        matrix[t][p] += 1

    table = Table(title="Matriz de Confusão (Linha: Real/Gold, Coluna: Predito/Heurística)")
    table.add_column("Real \\ Predito", style="bold cyan")
    for label in labels:
        table.add_column(label, justify="right")

    for t_label in labels:
        row_values = [t_label]
        for p_label in labels:
            count = matrix[t_label][p_label]
            style = "green" if t_label == p_label and count > 0 else "white"
            if t_label != p_label and count > 0:
                style = "red"
            row_values.append(f"[{style}]{count}[/{style}]")
        table.add_row(*row_values)

    console.print(table)


async def evaluate_ml_ensemble(
    gold_data: list[tuple],
    labels: list[str],
) -> None:
    """Load ML ensemble, embed benchmark texts, and evaluate."""
    from causaganha.analysis.local_embedder import LocalEmbedder  # noqa: PLC0415
    from causaganha.analysis.ml_ensemble import EmbeddingEnsemble  # noqa: PLC0415

    ensemble_path = Path("data/ml_ensemble.joblib")
    if not ensemble_path.exists():
        console.print(
            "[yellow]Aviso: Modelo de Machine Learning (data/ml_ensemble.joblib) não encontrado. Pulando avaliação do ML.[/yellow]"  # noqa: E501
        )
        return

    console.print(
        "\n[bold yellow]🤖 Avaliando Classificador de Machine Learning (Ensemble + Embeddings)...[/bold yellow]"  # noqa: E501
    )

    try:
        # Load model
        ensemble = EmbeddingEnsemble.load(ensemble_path)

        # Initialize local embedder (pplx-embed-v1: 32K context, no chunking needed)
        embedder = LocalEmbedder()

        texts = [row[7] for row in gold_data]
        console.print(f"Gerando embeddings locais para {len(texts)} textos...")
        embeddings = embedder.embed(texts, is_query=False, batch_size=16, normalize=True)

        y_true = [row[1] for row in gold_data]
        y_pred = []

        for emb in embeddings:
            dist = ensemble.predict_proba(emb)
            pred_outcome = max(dist, key=dist.__getitem__)
            y_pred.append(pred_outcome)

        metrics = compute_metrics(y_true, y_pred, labels)

        console.print(
            f"\n[bold green]Acurácia do ML Ensemble: {metrics['accuracy'] * 100:.1f}%[/bold green]\n"  # noqa: E501
        )

        # Display table
        metrics_table = Table(title="Métricas do ML Ensemble por Classe")
        metrics_table.add_column("Outcome", style="cyan")
        metrics_table.add_column("Precisão", style="yellow", justify="right")
        metrics_table.add_column("Recall", style="green", justify="right")
        metrics_table.add_column("F1-Score", style="magenta", justify="right")
        metrics_table.add_column("Suporte", justify="right")

        for label in labels:
            m = metrics[label]
            metrics_table.add_row(
                label,
                f"{m['precision']:.2f}",
                f"{m['recall']:.2f}",
                f"{m['f1']:.2f}",
                str(m["support"]),
            )
        console.print(metrics_table)
        console.print()
        show_confusion_matrix(y_true, y_pred, labels)

        # Invariant (winning polo) — gate + conditional. Gold recorrente_polo
        # (trailing column) preserves appeal polarity; the ensemble does not
        # predict it, so predicted appeals resolve to unknown.
        gold_polos = [row[8] for row in gold_data]
        gold_pairs = list(zip(y_true, gold_polos, strict=True))
        pred_pairs = [(o, None) for o in y_pred]
        show_invariant_report(evaluate_invariant(gold_pairs, pred_pairs), "ML Ensemble")

    except Exception as e:
        console.print(f"[red]Erro na avaliação do ML: {e}[/red]")


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate heuristics against gold benchmark.")
    parser.add_argument(
        "--show-disagreements",
        action="store_true",
        default=True,
        help="Show detailed list of disagreements (default: True).",
    )
    args = parser.parse_args()

    console.print("\n[bold cyan]📊 Avaliação de Heurísticas contra Benchmark de Ouro[/bold cyan]\n")

    db_path = Path("data/causaganha.duckdb")
    if not db_path.exists():
        console.print(f"[red]Erro: Banco de dados {db_path} não encontrado.[/red]")
        return 1

    # Connect to DuckDB
    conn = duckdb.connect(str(db_path))

    # Verify if table exists
    tables = [r[0] for r in conn.execute("SHOW TABLES").fetchall()]
    if "gold_benchmark" not in tables:
        console.print("[red]Erro: Tabela gold_benchmark não encontrada no DuckDB.[/red]")
        console.print("[yellow]Execute scripts/build_gold_benchmark.py primeiro.[/yellow]")
        conn.close()
        return 1

    # recorrente_polo exists from schema 1.3.0; older (1.2.0) rows lack it.
    # Select it when present so appeal outcomes resolve to the correct winner;
    # otherwise fall back to NULL (treated as first-instance by the resolver).
    gold_cols = {r[1] for r in conn.execute("PRAGMA table_info('gold_benchmark')").fetchall()}
    polo_select = "recorrente_polo" if "recorrente_polo" in gold_cols else "NULL AS recorrente_polo"

    # Load gold benchmark data (recorrente_polo is the trailing column, index 8)
    gold_data = conn.execute(f"""
        SELECT intimation_id, lower(outcome) AS outcome, decision_type, plaintiff_won,
               confidence_score, summary, decision_reasoning, texto, {polo_select}
        FROM gold_benchmark
        ORDER BY outcome, intimation_id
    """).fetchall()

    if not gold_data:
        console.print("[red]Erro: Tabela gold_benchmark está vazia.[/red]")
        conn.close()
        return 1

    console.print(f"✓ Carregadas {len(gold_data)} decisões do Gold Benchmark.\n")

    # Labels to evaluate
    labels = [
        "procedente",
        "improcedente",
        "parcialmente procedente",
        "acordo",
        "extinto sem mérito",
        "unknown",
    ]

    # 1. Evaluate KeywordClassifier (Heuristics)
    kc = KeywordClassifier()

    y_true = []
    y_pred = []
    gold_polos = []
    disagreements = []

    for row in gold_data:
        int_id, gold_outcome, _, _, _, _, _, text, gold_polo = row
        pred_outcome, pred_conf, dispositivo = kc.classify_with_dispositivo(text)

        y_true.append(gold_outcome)
        y_pred.append(pred_outcome)
        gold_polos.append(gold_polo)

        if gold_outcome != pred_outcome:
            disagreements.append(
                {
                    "id": int_id,
                    "gold": gold_outcome,
                    "pred": pred_outcome,
                    "conf": pred_conf,
                    "disp": dispositivo,
                    "text": text,
                }
            )

    # Compute metrics
    metrics = compute_metrics(y_true, y_pred, labels)

    console.print(
        f"[bold green]Acurácia das Heurísticas (KeywordClassifier): {metrics['accuracy'] * 100:.1f}%[/bold green]\n"  # noqa: E501
    )

    # Display metrics table
    metrics_table = Table(title="Métricas das Heurísticas (KeywordClassifier) por Classe")
    metrics_table.add_column("Outcome", style="cyan")
    metrics_table.add_column("Precisão", style="yellow", justify="right")
    metrics_table.add_column("Recall", style="green", justify="right")
    metrics_table.add_column("F1-Score", style="magenta", justify="right")
    metrics_table.add_column("Suporte", justify="right")

    for label in labels:
        m = metrics[label]
        metrics_table.add_row(
            label,
            f"{m['precision']:.2f}",
            f"{m['recall']:.2f}",
            f"{m['f1']:.2f}",
            str(m["support"]),
        )
    console.print(metrics_table)
    console.print()

    # Show confusion matrix
    show_confusion_matrix(y_true, y_pred, labels)
    console.print()

    # Invariant (winning polo) — gate + conditional. Gold carries
    # recorrente_polo for recursal cases (schema 1.3.0), so appeals resolve to
    # the correct winner; absent => None (first-instance). The keyword
    # classifier does not predict recorrente_polo, so predicted appeals resolve
    # to unknown — honest, since it cannot infer who filed the appeal.
    gold_pairs = list(zip(y_true, gold_polos, strict=True))
    pred_pairs = [(o, None) for o in y_pred]
    show_invariant_report(evaluate_invariant(gold_pairs, pred_pairs), "KeywordClassifier")
    console.print()

    # Show disagreements
    if args.show_disagreements and disagreements:
        console.print(
            f"[bold red]❌ Divergências Encontradas ({len(disagreements)} casos):[/bold red]\n"
        )

        for idx, dis in enumerate(disagreements[:15], 1):
            console.print(f"[bold red]{idx}. ID {dis['id']}[/bold red]")
            console.print(f"   [bold]Real/Gold:[/bold] {dis['gold']}")
            console.print(
                f"   [bold]Predito/Heurística:[/bold] {dis['pred']} (conf: {dis['conf']:.2f})"
            )

            # Show dispositivo snippet
            disp_snippet = dis["disp"] or dis["text"][:300]
            disp_clean = disp_snippet.strip().replace("\n", " ")[:200]
            console.print(f"   [bold]Operativo/Texto:[/bold] {disp_clean}...\n")

        if len(disagreements) > 15:
            console.print(f"... e mais {len(disagreements) - 15} divergências não exibidas.")

    # 2. Evaluate ML Ensemble if available
    asyncio.run(evaluate_ml_ensemble(gold_data, labels))

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
