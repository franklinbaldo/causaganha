#!/usr/bin/env python3
"""Mostra exemplo concreto de como k-NN funciona."""

# Safely reconfigure standard output and standard error encoding error handling on Windows
import contextlib
import sys


for stream in (sys.stdout, sys.stderr):
    if stream and stream.encoding and stream.encoding.lower() != "utf-8":
        with contextlib.suppress(AttributeError):
            stream.reconfigure(errors="replace")

import os
from typing import Any

import duckdb
import lancedb
from google import genai
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


console = Console()


CHUNK_INSTRUCTION = (
    "Analise esta parte de uma decisão judicial brasileira e determine qual polo venceu:\n"
    "- Polo Ativo (autor/requerente/exequente)\n"
    "- Polo Passivo (réu/requerido/executado)\n"
    "Considere termos como: procedente, improcedente, julgo, condeno, defiro, indefiro,"
    " provimento, negado."
)


_state: dict[str, Any] = {"genai_client": None}


def get_embedding(text: str) -> list[float]:
    """Get embedding."""
    result = _state["genai_client"].models.embed_content(
        model="models/text-embedding-004",
        contents=[text],
        config={"task_type": "RETRIEVAL_QUERY"},
    )
    return result.embeddings[0].values


def main() -> None:
    """Demonstrar k-NN na prática."""
    console.print("\n[bold cyan]🔍 Exemplo de k-NN: Como Funciona na Prática[/bold cyan]\n")

    # Configurar
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        console.print("[red]Erro: GEMINI_API_KEY não configurada[/red]")
        return

    _state["genai_client"] = genai.Client(api_key=api_key)

    # Conectar bancos
    conn = duckdb.connect("data/causaganha.duckdb", read_only=True)
    db = lancedb.connect("data/lancedb")
    table = db.open_table("ground_truth_embeddings")

    # Pegar uma decisão do ground truth para demonstrar
    decisao_exemplo = conn.execute("""
        SELECT intimation_id, outcome, texto
        FROM ground_truth
        WHERE outcome = 'WIN'
        LIMIT 1
    """).fetchone()

    if not decisao_exemplo:
        console.print("[red]Nenhuma decisão WIN no ground truth[/red]")
        return

    intimation_id, outcome_real, texto = decisao_exemplo

    console.print(
        Panel(
            f"[cyan]ID:[/cyan] {intimation_id}\n"
            f"[cyan]Outcome Real:[/cyan] {outcome_real}\n"
            f"[cyan]Texto (preview):[/cyan] {texto[:200]}...",
            title="📄 Decisão Exemplo",
        ),
    )

    # Criar chunk com prefixo
    chunk = texto[:500]
    prefixed_chunk = f"{CHUNK_INSTRUCTION}\n\n{chunk}"

    console.print("\n[yellow]Gerando embedding do chunk...[/yellow]")
    embedding = get_embedding(prefixed_chunk)

    console.print(f"[green]✓ Embedding gerado: vetor com {len(embedding)} dimensões[/green]\n")
    console.print(f"[dim]Primeiros 10 valores: {embedding[:10]}[/dim]\n")

    # Buscar vizinhos mais próximos (excluindo própria decisão)
    console.print("[yellow]Buscando k=5 vizinhos mais próximos...[/yellow]\n")

    results = table.search(embedding).limit(20).to_pandas()

    # Filtrar para excluir própria decisão
    results = results[results["intimation_id"] != intimation_id].head(5)

    # Mostrar vizinhos
    vizinhos_table = Table(title="🎯 k=5 Vizinhos Mais Próximos")
    vizinhos_table.add_column("Rank", style="cyan", width=6)
    vizinhos_table.add_column("ID", style="yellow")
    vizinhos_table.add_column("Outcome", style="green")
    vizinhos_table.add_column("Similaridade", style="magenta")
    vizinhos_table.add_column("Match?", style="white")

    votos = {}
    for idx, row in results.iterrows():
        rank = idx + 1
        neighbor_id = row["intimation_id"]
        neighbor_outcome = row["outcome"]
        distance = row["_distance"]
        similarity = 1 - distance  # Converter distância em similaridade

        match = "✓" if neighbor_outcome == outcome_real else "✗"

        vizinhos_table.add_row(
            str(rank),
            str(neighbor_id),
            neighbor_outcome,
            f"{similarity:.4f}",
            match,
        )

        votos[neighbor_outcome] = votos.get(neighbor_outcome, 0) + 1

    console.print(vizinhos_table)

    # Mostrar votação
    console.print("\n[bold]📊 Votação dos Vizinhos:[/bold]\n")

    votos_table = Table()
    votos_table.add_column("Outcome", style="cyan")
    votos_table.add_column("Votos", style="yellow")
    votos_table.add_column("Porcentagem", style="green")

    total_votos = sum(votos.values())
    for outcome, count in sorted(votos.items(), key=lambda x: x[1], reverse=True):
        pct = (count / total_votos) * 100
        votos_table.add_row(outcome, str(count), f"{pct:.1f}%")

    console.print(votos_table)

    # Resultado final
    vencedor = max(votos, key=votos.get)
    confianca = votos[vencedor] / total_votos

    console.print()
    if vencedor == outcome_real:
        console.print("[bold green]✓ Classificação Correta![/bold green]")
    else:
        console.print("[bold red]✗ Classificação Incorreta[/bold red]")

    console.print(f"\n[cyan]Outcome Real:[/cyan] {outcome_real}")
    console.print(f"[cyan]Outcome Previsto:[/cyan] {vencedor}")
    console.print(f"[cyan]Confiança:[/cyan] {confianca:.1%}\n")

    # Explicação
    console.print(
        Panel(
            "[bold]Como funciona:[/bold]\n\n"
            "1. Transformamos o texto da decisão em um vetor numérico (embedding)\n"
            "2. Buscamos as 5 decisões do ground truth com vetores MAIS SIMILARES\n"
            "3. Votamos pela maioria: o outcome mais comum entre os vizinhos\n"
            "4. A confiança é a % de vizinhos que concordam\n\n"
            "[yellow]Hipótese:[/yellow] Decisões com texto similar tendem a ter resultado"
            " similar!\n\n"
            f"Neste exemplo: {votos[vencedor]}/{total_votos} vizinhos eram '{vencedor}', "
            f"então classificamos como '{vencedor}' com {confianca:.0%} de confiança.",
            title="💡 Explicação do k-NN",
        ),
    )

    # Mostrar trechos dos vizinhos
    console.print("\n[bold]📝 Trechos dos Vizinhos (para comparar similaridade):[/bold]\n")

    for idx, row in results.head(3).iterrows():
        neighbor_id = row["intimation_id"]
        neighbor_outcome = row["outcome"]

        neighbor_text = conn.execute(
            "SELECT texto FROM ground_truth WHERE intimation_id = ?",
            [neighbor_id],
        ).fetchone()

        if neighbor_text:
            console.print(
                f"[cyan]Vizinho #{idx + 1} (ID {neighbor_id}, {neighbor_outcome}):[/cyan]",
            )
            console.print(f"[dim]{neighbor_text[0][:300]}...[/dim]\n")

    conn.close()


if __name__ == "__main__":
    main()
