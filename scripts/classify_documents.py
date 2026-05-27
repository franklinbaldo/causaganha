#!/usr/bin/env python3
"""Run DocumentClassifier on the consolidated parquet texts and display statistics."""

import sys
from pathlib import Path

import pandas as pd
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from causaganha.analysis.document_classifier import DocumentClassifier


console = Console()

def main() -> int:
    console.print("\n[bold cyan]📋 Classificação de Documentos e Fases Processuais[/bold cyan]\n")

    textos_file = Path("data/test_parquets/textos.parquet")
    comunic_file = Path("data/test_parquets/comunicacoes.parquet")

    if not textos_file.exists():
        console.print(f"[red]Erro: Arquivo {textos_file} não encontrado.[/red]")
        return 1

    # Load texts
    console.print("[yellow]Carregando textos e comunicações do parquet...[/yellow]")
    textos_df = pd.read_parquet(textos_file)

    if list(textos_df.columns) != ["id", "texto"]:
        # If columns are named differently, resolve
        pass

    comunic_df = pd.read_parquet(comunic_file) if comunic_file.exists() else None

    # Merge if possible
    if comunic_df is not None:
        comunic_unique = comunic_df.drop_duplicates(subset=["texto_id"])[
            ["texto_id", "numero_processo"]
        ]
        ready_df = textos_df.merge(
            comunic_unique, left_on="id", right_on="texto_id", how="left"
        )
    else:
        ready_df = textos_df.copy()
        ready_df["numero_processo"] = "Sem Processo"

    ready_df = ready_df.dropna(subset=["texto"])

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
    doc_counts = ready_df["document_type"].value_counts()
    table_doc = Table(
        title="Distribuição por Tipo de Documento",
        show_header=True,
        header_style="bold magenta",
    )
    table_doc.add_column("Tipo de Documento", style="cyan")
    table_doc.add_column("Quantidade", style="yellow", justify="right")
    table_doc.add_column("Percentual", style="green", justify="right")

    for dt, cnt in doc_counts.items():
        pct = (cnt / len(ready_df)) * 100
        table_doc.add_row(str(dt), f"{cnt:,}", f"{pct:.1f}%")

    console.print(table_doc)
    console.print()

    # 2. Procedural Class Table
    class_counts = ready_df["procedural_class"].value_counts()
    table_class = Table(
        title="Distribuição por Classe Processual / Contexto",
        show_header=True,
        header_style="bold magenta",
    )
    table_class.add_column("Classe / Fase Processual", style="cyan")
    table_class.add_column("Quantidade", style="yellow", justify="right")
    table_class.add_column("Percentual", style="green", justify="right")

    for pc, cnt in class_counts.items():
        pct = (cnt / len(ready_df)) * 100
        table_class.add_row(str(pc), f"{cnt:,}", f"{pct:.1f}%")

    console.print(table_class)
    console.print()

    # 3. Cross-tabulation table (Crosstab)
    console.print("[bold]Tabela Cruzada: Tipo de Documento vs Classe Processual[/bold]")
    crosstab = pd.crosstab(ready_df["document_type"], ready_df["procedural_class"])

    table_cross = Table(show_header=True, header_style="bold blue")
    table_cross.add_column("Tipo / Classe", style="bold cyan")
    for col in crosstab.columns:
        table_cross.add_column(str(col), justify="right")

    for idx, row in crosstab.iterrows():
        row_vals = [str(row[col]) for col in crosstab.columns]
        table_cross.add_row(str(idx), *row_vals)

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
    ready_df[["id", "document_type", "procedural_class", "confidence_doc"]].to_parquet(
        output_file, index=False
    )
    console.print(Panel(
        f"[bold green]✓ Classificação concluída com sucesso![/bold green]\n"
        f"Resultados salvos em: [bold]{output_file}[/bold]",
        title="✓ Concluído"
    ))

    return 0

if __name__ == "__main__":
    sys.exit(main())
