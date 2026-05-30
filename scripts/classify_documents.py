#!/usr/bin/env python3
"""Run DocumentClassifier on the consolidated parquet texts and display statistics.

Purpose:  Apply the heuristic DocumentClassifier over the corpus and report the
          distribution of document types / procedural stages.
Problem:  We need to know how well rule-based classification covers the corpus and
          to emit labels that feed the ML training step.
Strategy: Read textos/comunicacoes parquet, classify each, print stats, and write
          classificacoes_documentos.parquet (consumed by train_ml_document_classifier).
Status:   research/analysis step in the classification R&D track. RFC: keep as a
          manual analysis tool, or fold into a reproducible pipeline?
"""

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path

import ibis
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from causaganha.analysis.document_classifier import DocumentClassifier


console = Console()


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify documents and stages.")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit the number of decisions to classify (for testing/sampling).",
    )
    args = parser.parse_args()

    console.print("\n[bold cyan]📋 Classificação de Documentos e Fases Processuais[/bold cyan]\n")

    textos_file = Path("data/test_parquets/textos.parquet")
    comunic_file = Path("data/test_parquets/comunicacoes.parquet")

    if not textos_file.exists():
        console.print(f"[red]Erro: Arquivo {textos_file} não encontrado.[/red]")
        return 1

    # Load texts
    console.print("[yellow]Carregando textos e comunicações do parquet...[/yellow]")
    textos_t = ibis.read_parquet(textos_file)

    if list(textos_t.columns) != ["id", "texto"]:
        # If columns are named differently, resolve
        pass

    # Merge if possible
    if comunic_file.exists():
        comunic_t = ibis.read_parquet(comunic_file)
        comunic_unique = comunic_t.select("texto_id", "numero_processo").distinct(on="texto_id")
        ready_t = textos_t.join(
            comunic_unique, textos_t.id == comunic_unique.texto_id, how="left"
        ).select(
            textos_t.id,
            textos_t.texto,
            numero_processo=ibis.coalesce(
                comunic_unique.numero_processo, ibis.literal("Sem Processo")
            ),
        )
    else:
        ready_t = textos_t.mutate(numero_processo=ibis.literal("Sem Processo"))

    ready_t = ready_t.filter(ready_t.texto.notnull())
    if args.limit is not None:
        ready_t = ready_t.limit(args.limit)
    ready_df = ready_t.execute()

    console.print(f"[green]✓ Carregados {len(ready_df):,} textos de decisões.[/green]\n")

    # Classify
    console.print("[yellow]Executando classificador de documentos...[/yellow]")
    classifier = DocumentClassifier()

    doc_types = []
    proc_classes = []
    confidences = []

    for _, row in ready_df.iterrows():
        res = classifier.classify(str(row["texto"]))
        doc_types.append(res["document_type"])
        proc_classes.append(res["procedural_class"])
        confidences.append(res["confidence"])

    ready_df["document_type"] = doc_types
    ready_df["procedural_class"] = proc_classes
    ready_df["confidence_doc"] = confidences

    # 1. Document Type Table
    doc_counts = Counter(ready_df["document_type"].tolist())
    table_doc = Table(
        title="Distribuição por Tipo de Documento",
        show_header=True,
        header_style="bold magenta",
    )
    table_doc.add_column("Tipo de Documento", style="cyan")
    table_doc.add_column("Quantidade", style="yellow", justify="right")
    table_doc.add_column("Percentual", style="green", justify="right")

    for dt, cnt in doc_counts.most_common():
        pct = (cnt / len(ready_df)) * 100
        table_doc.add_row(str(dt), f"{cnt:,}", f"{pct:.1f}%")

    console.print(table_doc)
    console.print()

    # 2. Procedural Class Table
    class_counts = Counter(ready_df["procedural_class"].tolist())
    table_class = Table(
        title="Distribuição por Classe Processual / Contexto",
        show_header=True,
        header_style="bold magenta",
    )
    table_class.add_column("Classe / Fase Processual", style="cyan")
    table_class.add_column("Quantidade", style="yellow", justify="right")
    table_class.add_column("Percentual", style="green", justify="right")

    for pc, cnt in class_counts.most_common():
        pct = (cnt / len(ready_df)) * 100
        table_class.add_row(str(pc), f"{cnt:,}", f"{pct:.1f}%")

    console.print(table_class)
    console.print()

    # 3. Cross-tabulation table (Crosstab)
    console.print("[bold]Tabela Cruzada: Tipo de Documento vs Classe Processual[/bold]")
    doc_types_seq = ready_df["document_type"].tolist()
    proc_classes_seq = ready_df["procedural_class"].tolist()
    unique_docs = sorted(set(doc_types_seq))
    unique_classes = sorted(set(proc_classes_seq))

    crosstab_counts = defaultdict(lambda: defaultdict(int))
    for dt, pc in zip(doc_types_seq, proc_classes_seq, strict=True):
        crosstab_counts[dt][pc] += 1

    table_cross = Table(show_header=True, header_style="bold blue")
    table_cross.add_column("Tipo / Classe", style="bold cyan")
    for col in unique_classes:
        table_cross.add_column(str(col), justify="right")

    for dt in unique_docs:
        row_vals = [str(crosstab_counts[dt][pc]) for pc in unique_classes]
        table_cross.add_row(dt, *row_vals)

    console.print(table_cross)
    console.print()

    # 4. Display a few samples of each
    console.print("[bold]Amostras de Classificações:[/bold]\n")

    sample_types = [
        "sentença",
        "acórdão",
        "decisão monocrática",
        "decisão interlocutória",
        "despacho",
    ]
    for st in sample_types:
        subset = ready_df[ready_df["document_type"] == st].head(1)
        if len(subset) > 0:
            row = subset.iloc[0]
            proc = row.get("numero_processo", "Desconhecido")
            text_preview = str(row["texto"])[:250].replace("\n", " ")
            console.print(
                f"[bold cyan]• Tipo: {st.upper()} | Processo: {proc}"
                f" | Classe: {row['procedural_class']}[/bold cyan]"
            )
            console.print(f"  [italic]Preview:[/italic] {text_preview}...\n")

    # Save the classification results back to parquet for future use
    output_file = Path("data/test_parquets/classificacoes_documentos.parquet")
    output_df = ready_df[["id", "document_type", "procedural_class", "confidence_doc"]]

    # Convert to Ibis table and write to parquet
    output_table = ibis.memtable(output_df)
    output_table.to_parquet(output_file)

    console.print(
        Panel(
            f"[bold green]✓ Classificação concluída com sucesso![/bold green]\n"
            f"Resultados salvos em: [bold]{output_file}[/bold]",
            title="✓ Concluído",
        )
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
