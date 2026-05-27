#!/usr/bin/env python3
"""Process decisions using Google Batch API for embeddings (50% cost reduction)."""


# Safely reconfigure standard output and standard error encoding error handling on Windows
import contextlib
import sys


for stream in (sys.stdout, sys.stderr):
    if stream and stream.encoding and stream.encoding.lower() != "utf-8":
        with contextlib.suppress(AttributeError):
            stream.reconfigure(errors="replace")

import json
import os
import time
from pathlib import Path

import duckdb
from google import genai
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table


console = Console()


CHUNK_INSTRUCTION = (
    "Analise esta parte de uma decisão judicial brasileira e determine qual polo venceu:\n"
    "- Polo Ativo (autor/requerente/exequente)\n"
    "- Polo Passivo (réu/requerido/executado)\n"
    "Considere termos como: procedente, improcedente, julgo, condeno, defiro, indefiro,"
    " provimento, negado."
)


def chunk_text_with_prefix(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    """Chunking com prefixo de instrução."""
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]

        if end < len(text):
            last_period = chunk.rfind(".")
            if last_period > chunk_size * 0.7:
                end = start + last_period + 1
                chunk = text[start:end]

        prefixed_chunk = f"{CHUNK_INSTRUCTION}\n\n{chunk.strip()}"
        chunks.append(prefixed_chunk)

        start = end - overlap

    return chunks


def prepare_batch_requests(decisions: list[tuple], output_file: str) -> int:
    """Prepare batch embedding requests in JSONL format."""
    console.print("\n[yellow]Preparando batch requests...[/yellow]")

    request_count = 0

    with Path(output_file).open("w") as f:
        for intimation_id, texto in decisions:
            chunks = chunk_text_with_prefix(texto)

            for chunk_idx, chunk in enumerate(chunks):
                request = {
                    "key": f"id-{intimation_id}-chunk-{chunk_idx}",
                    "request": {
                        "model": "models/text-embedding-004",
                        "content": {
                            "parts": [{"text": chunk}],
                        },
                        "config": {
                            "task_type": "RETRIEVAL_QUERY",
                        },
                    },
                }
                f.write(json.dumps(request) + "\n")
                request_count += 1

    console.print(f"[green]✓ Criadas {request_count:,} requisições de embedding[/green]")
    console.print(f"[dim]Arquivo: {output_file}[/dim]\n")

    return request_count


def main() -> None:
    """Process decisions with Batch API."""
    console.print("\n[bold cyan]🚀 Batch Embedding: Google Batch API (50% custo)[/bold cyan]\n")

    # Configurar
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        console.print("[red]Erro: GEMINI_API_KEY não configurada[/red]")
        return

    client = genai.Client(api_key=api_key)

    # Conectar DuckDB
    conn = duckdb.connect("data/causaganha.duckdb")

    # Verificar status
    stats = conn.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(ar.intimation_id) as analyzed,
            COUNT(*) - COUNT(ar.intimation_id) as remaining
        FROM intimations i
        LEFT JOIN analysis_results ar ON i.id = ar.intimation_id
    """).fetchone()

    total, analyzed, remaining = stats

    console.print(
        Panel(
            f"[cyan]Total:[/cyan] {total:,} intimações\n"
            f"[green]Analisadas (LLM):[/green] {analyzed:,}\n"
            f"[yellow]Restantes:[/yellow] {remaining:,}",
            title="Status do Banco",
        ),
    )

    if remaining == 0:
        console.print("\n[green]✓ Todas as decisões já foram analisadas![/green]\n")
        conn.close()
        return

    # Calcular custos
    console.print("\n[bold]Batch API - Economia de Custos:[/bold]")
    console.print("  Custo normal: [yellow]$0.09[/yellow]")
    console.print("  Custo batch (50% off): [green]$0.045[/green]")
    console.print("  Economia: [green]$0.045[/green] (50%)\n")

    # Definir tamanho do batch
    batch_size = min(1000, remaining)  # Processar até 1000 por vez

    console.print(f"[yellow]Processando batch de {batch_size:,} decisões...[/yellow]\n")

    # Buscar decisões não analisadas
    unanalyzed = conn.execute(f"""
        SELECT i.id, i.texto
        FROM intimations i
        LEFT JOIN analysis_results ar ON i.id = ar.intimation_id
        WHERE ar.intimation_id IS NULL
          AND i.texto IS NOT NULL
          AND LENGTH(i.texto) > 100
        ORDER BY i.id
        LIMIT {batch_size}
    """).fetchall()

    console.print(f"✓ Carregadas {len(unanalyzed):,} decisões\n")

    # Preparar arquivo de batch
    batch_file = "data/batch_embed_requests.jsonl"
    request_count = prepare_batch_requests(unanalyzed, batch_file)

    # Estimar chunks por decisão
    avg_chunks = request_count / len(unanalyzed)
    console.print(f"[dim]Média de {avg_chunks:.1f} chunks por decisão[/dim]\n")

    # Upload do arquivo
    console.print("[yellow]Uploading batch file...[/yellow]")

    try:
        uploaded_file = client.files.upload(
            file=batch_file,
            config={
                "display_name": f"causaganha-embeddings-batch-{int(time.time())}",
                "mime_type": "application/jsonl",
            },
        )
        console.print(f"[green]✓ Arquivo enviado: {uploaded_file.name}[/green]\n")
    except Exception as e:
        console.print(f"[red]Erro no upload: {e}[/red]")
        return

    # Criar batch job
    console.print("[yellow]Criando batch job...[/yellow]")

    try:
        job = client.batches.create_embeddings(
            model="models/text-embedding-004",
            src=uploaded_file.name,
            config={
                "display_name": f"causaganha-embeddings-{int(time.time())}",
            },
        )
        console.print(f"[green]✓ Batch job criado: {job.name}[/green]\n")
    except Exception as e:
        console.print(f"[red]Erro ao criar job: {e}[/red]")
        return

    # Monitorar progresso
    console.print("[bold]Monitorando batch job...[/bold]")
    console.print(
        "[dim]Jobs normalmente completam em < 24h (frequentemente muito mais rápido)[/dim]\n",
    )

    completed_states = {
        "JOB_STATE_SUCCEEDED",
        "JOB_STATE_FAILED",
        "JOB_STATE_CANCELLED",
        "JOB_STATE_EXPIRED",
    }

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Aguardando conclusão...", total=None)

        last_state = None
        check_interval = 30  # segundos

        while True:
            try:
                status = client.batches.get(name=job.name)
                current_state = status.state.name

                if current_state != last_state:
                    progress.update(task, description=f"Estado: {current_state}")
                    last_state = current_state

                if current_state in completed_states:
                    break

                time.sleep(check_interval)

            except KeyboardInterrupt:
                console.print("\n[yellow]Interrompido pelo usuário[/yellow]")
                console.print(f"[dim]Job ID: {job.name}[/dim]")
                console.print(
                    f"[dim]Para verificar depois: client.batches.get(name='{job.name}')[/dim]\n",
                )
                return
            except Exception as e:
                console.print(f"\n[red]Erro ao verificar status: {e}[/red]")
                time.sleep(check_interval)

    console.print()

    # Verificar resultado
    if status.state.name == "JOB_STATE_SUCCEEDED":
        console.print("[bold green]✓ Batch job completado com sucesso![/bold green]\n")

        # Estatísticas
        stats_table = Table(title="Estatísticas do Batch")
        stats_table.add_column("Métrica", style="cyan")
        stats_table.add_column("Valor", style="yellow")

        if hasattr(status, "batch_stats"):
            stats_table.add_row("Total Requests", f"{status.batch_stats.total_request_count:,}")
            stats_table.add_row("Successful", f"{status.batch_stats.successful_request_count:,}")
            stats_table.add_row("Failed", f"{status.batch_stats.failed_request_count:,}")

        console.print(stats_table)
        console.print()

        # Baixar resultados
        if hasattr(status.dest, "file_name") and status.dest.file_name:
            console.print("[yellow]Baixando resultados...[/yellow]")

            output_file = "data/batch_embed_results.jsonl"
            content = client.files.download(file=status.dest.file_name)

            with Path(output_file).open("wb") as f:
                f.write(content)

            console.print(f"[green]✓ Resultados salvos em: {output_file}[/green]\n")

            # Parsear resultados
            console.print("[yellow]Processando embeddings...[/yellow]")

            embeddings_by_id = {}

            with Path(output_file).open() as f:
                for line in f:
                    result = json.loads(line)
                    key = result.get("key", "")

                    if key.startswith("id-"):
                        parts = key.split("-")
                        intimation_id = int(parts[1])
                        chunk_idx = int(parts[3])

                        if "response" in result and "embedding" in result["response"]:
                            embedding = result["response"]["embedding"]

                            if intimation_id not in embeddings_by_id:
                                embeddings_by_id[intimation_id] = []

                            embeddings_by_id[intimation_id].append(
                                {
                                    "chunk_idx": chunk_idx,
                                    "embedding": embedding,
                                },
                            )

            n = len(embeddings_by_id)
            console.print(
                f"[green]✓ Processados embeddings para {n:,} decisões[/green]\n",
            )

            # Salvar embeddings estruturados
            structured_output = "data/decision_embeddings.jsonl"
            with Path(structured_output).open("w") as f:
                for intimation_id, chunks in embeddings_by_id.items():
                    # Ordenar chunks
                    chunks.sort(key=lambda x: x["chunk_idx"])

                    record = {
                        "intimation_id": intimation_id,
                        "chunks": chunks,
                    }
                    f.write(json.dumps(record) + "\n")

            console.print(
                f"[green]✓ Embeddings estruturados salvos em: {structured_output}[/green]\n",
            )

            console.print("[bold]Próximos passos:[/bold]")
            console.print("  1. Use os embeddings para classificação k-NN local (grátis)")
            console.print("  2. Compare resultados com ground truth")
            console.print("  3. Processe mais batches se necessário\n")

    elif status.state.name == "JOB_STATE_FAILED":
        console.print("[bold red]✗ Batch job falhou[/bold red]\n")
        if hasattr(status, "error"):
            console.print(f"[red]Erro: {status.error}[/red]\n")

    else:
        console.print(f"[yellow]Estado final: {status.state.name}[/yellow]\n")

    conn.close()


if __name__ == "__main__":
    main()
