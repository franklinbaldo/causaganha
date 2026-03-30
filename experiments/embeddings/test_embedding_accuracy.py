#!/usr/bin/env python3

MAGIC_VAL_60 = 60
MAGIC_VAL_80 = 80

"""Test embedding-based analysis vs LLM analysis."""

import asyncio

import duckdb
import structlog
from rich.console import Console
from rich.table import Table

from causaganha.infrastructure.ai.embeddings import EmbeddingAnalyzer


logger = structlog.get_logger()
console = Console()


REFERENCE_PHRASES = {
    "WIN": [
        "a parte autora venceu",
        "procedente o pedido do autor",
        "julgo procedente a ação",
        "dou provimento ao recurso do autor",
        "condeno o réu a pagar",
        "defiro o pedido do requerente",
        "acolho o pedido da parte autora",
        "favorável ao autor",
        "determino que o réu pague",
        "ordem para implementar o benefício",
        "julgo procedentes os pedidos",
    ],
    "LOSS": [
        "a parte autora perdeu",
        "improcedente o pedido",
        "julgo improcedente a ação",
        "nego provimento ao recurso do autor",
        "condeno o autor em custas",
        "indefiro o pedido do autor",
        "rejeito o pedido da parte autora",
        "favorável ao réu",
        "não há direito do autor",
    ],
    "PARTIAL": [
        "parcialmente procedente",
        "procedente em parte",
        "acolho parcialmente",
        "defiro em parte",
        "acordo homologado",
        "conciliação entre as partes",
        "extingo o processo com acordo",
    ],
    "UNKNOWN": [
        "intimo as partes a se manifestarem",
        "determino a citação",
        "abro vista dos autos",
        "apresente documentos",
        "aguarde-se",
        "manifeste-se no prazo",
        "intime-se para comparecer",
    ],
}


async def test_embedding_accuracy() -> None:
    """Test embedding accuracy against LLM results."""
    console.print("\n[bold cyan]🧪 Teste de Acurácia: Embeddings vs LLM[/bold cyan]\n")

    # Connect to database
    conn = duckdb.connect("data/causaganha.duckdb", read_only=True)

    # Get analyzed decisions with known outcomes
    console.print("📊 Buscando decisões já analisadas pela LLM...")
    decisions = conn.execute(
        """
        SELECT
            ar.intimation_id,
            ar.outcome as llm_outcome,
            ar.confidence_score as llm_confidence,
            i.texto
        FROM analysis_results ar
        JOIN intimations i ON ar.intimation_id = i.id
        WHERE ar.outcome IN ('WIN', 'LOSS', 'PARTIAL', 'UNKNOWN')
          AND i.texto IS NOT NULL
          AND LENGTH(i.texto) > 200
        ORDER BY ar.analyzed_at DESC
        LIMIT 30
    """,
    ).fetchall()

    console.print(f"✓ Encontradas {len(decisions)} decisões para teste\n")

    if not decisions:
        console.print("[red]❌ Nenhuma decisão encontrada para teste[/red]")
        return

    # Initialize embedding analyzer
    console.print("🔧 Inicializando analisador de embeddings...")
    analyzer = EmbeddingAnalyzer()
    console.print("✓ Frases de referência carregadas\n")

    # Test each decision
    results = []
    correct = 0
    total = 0

    console.print("[bold]Testando decisões...[/bold]\n")

    for intimation_id, llm_outcome, llm_conf, texto in decisions:
        total += 1

        # Analyze with embeddings
        emb_result = analyzer.analyze_decision_outcome(texto, chunk_size=400)

        emb_outcome = emb_result["outcome"]
        emb_confidence = emb_result["confidence"]

        # Check if outcomes match
        match = emb_outcome == llm_outcome
        if match:
            correct += 1

        results.append(
            {
                "intimation_id": intimation_id,
                "llm_outcome": llm_outcome,
                "llm_confidence": llm_conf,
                "emb_outcome": emb_outcome,
                "emb_confidence": emb_confidence,
                "match": match,
                "all_scores": emb_result["all_scores"],
            },
        )

        # Show progress
        status = "✅" if match else "❌"
        console.print(
            f"{status} [{total:2d}/{len(decisions)}] "
            f"LLM: {llm_outcome:8s} ({llm_conf:.2f}) | "
            f"EMB: {emb_outcome:8s} ({emb_confidence:.2f}) | "
            f"ID: {intimation_id}",
        )

    # Calculate metrics
    accuracy = (correct / total * 100) if total > 0 else 0

    # Display results table
    console.print("\n" + "=" * 80)
    console.print("[bold cyan]📊 RESULTADOS DA COMPARAÇÃO[/bold cyan]")
    console.print("=" * 80 + "\n")

    table = Table(title="Resumo de Acurácia")
    table.add_column("Métrica", style="cyan")
    table.add_column("Valor", style="green")

    table.add_row("Total de Decisões", str(total))
    table.add_row("Matches Corretos", str(correct))
    table.add_row("Acurácia", f"{accuracy:.1f}%")

    console.print(table)

    # Confusion matrix
    console.print("\n[bold]Matriz de Confusão (LLM vs Embeddings):[/bold]\n")

    confusion = {}
    for result in results:
        key = (result["llm_outcome"], result["emb_outcome"])
        confusion[key] = confusion.get(key, 0) + 1

    conf_table = Table()
    conf_table.add_column("LLM Outcome", style="cyan")
    conf_table.add_column("EMB Outcome", style="yellow")
    conf_table.add_column("Count", style="green")

    for (llm, emb), count in sorted(confusion.items(), key=lambda x: -x[1]):
        style = "green" if llm == emb else "red"
        conf_table.add_row(llm, emb, str(count), style=style)

    console.print(conf_table)

    # Show some mismatches
    mismatches = [r for r in results if not r["match"]]
    if mismatches:
        console.print(
            f"\n[bold yellow]⚠️  Análise de {len(mismatches)} Discrepâncias:[/bold yellow]\n",
        )

        for i, result in enumerate(mismatches[:5], 1):
            console.print(f"{i}. Intimation ID: {result['intimation_id']}")
            console.print(f"   LLM: {result['llm_outcome']} ({result['llm_confidence']:.2f})")
            console.print(f"   EMB: {result['emb_outcome']} ({result['emb_confidence']:.2f})")
            console.print(f"   Scores: {result['all_scores']}")
            console.print()

    # Calculate cost savings
    console.print("\n[bold cyan]💰 ECONOMIA ESTIMADA[/bold cyan]\n")

    # Gemini Embedding pricing (text-embedding-004)
    # ~$0.00001 per 1K characters (praticamente grátis)
    avg_text_length = sum(len(d[3]) for d in decisions) / len(decisions)
    embedding_cost_per_decision = (avg_text_length / 1000) * 0.00001

    # LLM pricing (Gemini Flash)
    # ~$0.00015 per 1K tokens (input) + $0.0006 per 1K tokens (output)
    # Estimativa: 2000 tokens input + 200 tokens output
    llm_cost_per_decision = (2000 / 1000 * 0.00015) + (200 / 1000 * 0.0006)

    savings_per_decision = llm_cost_per_decision - embedding_cost_per_decision
    total_savings_5k = savings_per_decision * 5794  # Total de decisões no banco

    cost_table = Table()
    cost_table.add_column("Método", style="cyan")
    cost_table.add_column("Custo/Decisão", style="yellow")
    cost_table.add_column("Custo 5.794 decisões", style="green")

    cost_table.add_row(
        "LLM (Gemini Flash)",
        f"${llm_cost_per_decision:.6f}",
        f"${llm_cost_per_decision * 5794:.2f}",
    )
    cost_table.add_row(
        "Embeddings",
        f"${embedding_cost_per_decision:.6f}",
        f"${embedding_cost_per_decision * 5794:.2f}",
    )
    cost_table.add_row(
        "[bold]Economia[/bold]",
        f"[bold green]${savings_per_decision:.6f}[/bold green]",
        f"[bold green]${total_savings_5k:.2f}[/bold green]",
    )

    console.print(cost_table)

    # Final recommendation
    console.print("\n[bold cyan]🎯 RECOMENDAÇÃO[/bold cyan]\n")

    if accuracy >= MAGIC_VAL_80:
        console.print(
            f"[green]✅ Acurácia de {accuracy:.1f}% é excelente! "
            f"Embeddings podem substituir LLM com economia de ${total_savings_5k:.2f}[/green]",
        )
    elif accuracy >= MAGIC_VAL_60:
        console.print(
            f"[yellow]⚠️  Acurácia de {accuracy:.1f}% é aceitável. "
            f"Considere usar embeddings para triagem e LLM para confirmação.[/yellow]",
        )
    else:
        console.print(
            f"[red]❌ Acurácia de {accuracy:.1f}% é baixa. "
            f"Ajuste as frases de referência ou use abordagem híbrida.[/red]",
        )

    conn.close()


if __name__ == "__main__":
    asyncio.run(test_embedding_accuracy())
