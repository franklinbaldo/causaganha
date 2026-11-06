"""Runner de inferência local e benchmark para THX-02 no CausaGanha.

Executa 100% offline contra os pesos locais baixados no hardware da máquina.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
import psutil
import torch
import pandas as pd

# Assegura configuração de CPU em bfloat16
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["THX02_CPU_DTYPE"] = "bfloat16"
os.environ["THX02_DEVICE"] = "cpu"
sys.modules.setdefault("fla", None)

# Adiciona workspace ao path para importar spike_thx02
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from scripts.spike_thx02 import (
    QUESTIONS,
    OUTCOME_LABELS,
    RECURSAL,
    decode_response,
    resolve_winner,
)
from thx02 import THX02


def get_ram_mb() -> float:
    process = psutil.Process()
    return process.memory_info().rss / (1024 * 1024)


def main():
    parser = argparse.ArgumentParser(description="Executar spike THX-02 com modelo local")
    parser.add_argument(
        "--checkpoint",
        default=r"C:\Users\76450694220\.cache\huggingface\hub\models--HAL-X-AI--THX-02\snapshots\8262da06636501d98a060edf8d81b4c1b1eea46a",
        help="Caminho do snapshot local do THX-02",
    )
    parser.add_argument(
        "--fixture",
        default="tests/fixtures/thx02_spike.jsonl",
        help="Arquivo fixture com os casos de teste",
    )
    parser.add_argument("--limit", type=int, default=12, help="Limite de documentos a processar")
    parser.add_argument("--threshold", type=float, default=0.70, help="Limiar de confiança")
    parser.add_argument(
        "--output-jsonl",
        default="output/thx02_local_spike_results.jsonl",
        help="Arquivo de saída JSONL",
    )
    parser.add_argument(
        "--output-parquet",
        default="output/thx02_local_spike_results.parquet",
        help="Arquivo de saída Parquet",
    )
    args = parser.parse_args()

    os.makedirs("output", exist_ok=True)

    ram_start = get_ram_mb()
    print("=" * 65)
    print("EXECUTANDO INFERÊNCIA LOCAL THX-02 (CPU bfloat16)")
    print("=" * 65)
    print(f"RAM inicial do processo: {ram_start:.1f} MB")
    print(f"CPU threads PyTorch: {torch.get_num_threads()}")
    print(f"Carregando pesos de: {args.checkpoint}...")

    t_load0 = time.time()
    model = THX02.load(args.checkpoint, device="cpu")
    load_time = time.time() - t_load0
    ram_after_load = get_ram_mb()

    print(f"Modelo carregado em {load_time:.2f}s!")
    print(f"RAM após carregamento dos pesos: {ram_after_load:.1f} MB (Delta: +{ram_after_load - ram_start:.1f} MB)")

    # Carregar documentos da fixture
    fixture_path = ROOT_DIR / args.fixture
    documents = []
    with open(fixture_path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                documents.append(json.loads(line))

    docs_to_eval = documents[: args.limit]
    print(f"\nProcessando {len(docs_to_eval)} documentos da fixture...")

    results = []
    latencies = []
    max_ram_observed = ram_after_load

    for i, doc in enumerate(docs_to_eval, start=1):
        doc_id = doc["id"]
        text = doc["text"]
        print(f"[{i}/{len(docs_to_eval)}] Processando {doc_id} ({len(text)} chars)...", end="", flush=True)

        t0 = time.time()
        raw_res = model.decide(state=text, questions=QUESTIONS, think=False, tta=1)
        elapsed_ms = (time.time() - t0) * 1000
        latencies.append(elapsed_ms)

        current_ram = get_ram_mb()
        max_ram_observed = max(max_ram_observed, current_ram)

        # Decodifica usando as regras canônicas do spike
        decoded = decode_response(doc, raw_res, threshold=args.threshold)
        decoded["model_latency_ms"] = raw_res.get("latency_ms", elapsed_ms)
        decoded["wall_latency_ms"] = elapsed_ms
        decoded["ram_mb"] = current_ram
        results.append(decoded)

        outcome = decoded["outcome"]
        outcome_p = decoded["outcome_probability"]
        gold_out = decoded["gold_outcome"]
        winner = decoded["winner"]
        gold_win = decoded["gold_winner"]
        match_out = "✓" if outcome == gold_out else "✗"
        match_win = "✓" if winner == gold_win else "✗"

        print(f" Concluído em {elapsed_ms/1000:.1f}s | Resultado: {outcome} ({outcome_p:.1%}) [{match_out}] | Vencedor: {winner} [{match_win}]")

    # Salva resultados
    out_jsonl = ROOT_DIR / args.output_jsonl
    with open(out_jsonl, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    df = pd.DataFrame(results)
    out_parquet = ROOT_DIR / args.output_parquet
    # Converte tipos complexos se houver
    df_clean = df.copy()
    if "usage" in df_clean.columns:
        df_clean["usage"] = df_clean["usage"].apply(lambda x: json.dumps(x) if isinstance(x, dict) else str(x))
    df_clean.to_parquet(out_parquet, index=False)

    print("\n" + "=" * 65)
    print("RESUMO DO BENCHMARK LOCAL THX-02")
    print("=" * 65)
    n = len(results)
    lat_series = pd.Series(latencies)
    acc_outcome = sum(r["outcome"] == r["gold_outcome"] for r in results) / n
    acc_winner = sum(r["winner"] == r["gold_winner"] for r in results) / n

    summary = {
        "hardware": {
            "device": "cpu",
            "dtype": "bfloat16",
            "threads": torch.get_num_threads(),
            "load_time_s": round(load_time, 2),
            "ram_initial_mb": round(ram_start, 1),
            "ram_loaded_mb": round(ram_after_load, 1),
            "ram_max_mb": round(max_ram_observed, 1),
            "ram_weights_delta_mb": round(ram_after_load - ram_start, 1),
        },
        "performance": {
            "total_documents": n,
            "total_questions": n * len(QUESTIONS),
            "latency_p50_s": round(lat_series.median() / 1000, 2),
            "latency_p95_s": round(lat_series.quantile(0.95) / 1000, 2),
            "latency_mean_s": round(lat_series.mean() / 1000, 2),
            "documents_per_minute": round(60 / (lat_series.mean() / 1000), 2) if lat_series.mean() > 0 else 0,
            "questions_per_minute": round((60 / (lat_series.mean() / 1000)) * len(QUESTIONS), 2) if lat_series.mean() > 0 else 0,
        },
        "quality": {
            "outcome_accuracy": round(acc_outcome, 4),
            "winner_accuracy": round(acc_winner, 4),
            "threshold": args.threshold,
            "abstained_count": sum(r["abstained"] for r in results),
        },
    }

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    summary_path = ROOT_DIR / "output/thx02_local_benchmark_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\nResultados salvos:")
    print(f" - JSONL: {out_jsonl}")
    print(f" - Parquet: {out_parquet}")
    print(f" - Sumário: {summary_path}")


if __name__ == "__main__":
    main()
