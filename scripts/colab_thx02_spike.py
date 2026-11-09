#!/usr/bin/env python3
"""Run THX-02 benchmark on Google Colab with GPU (Tesla T4).

Reuses the exact canonical questions and decoding logic from PR #1687.
Optimized for 14.5 GB T4 VRAM with explicit bfloat16 and memory management.
"""

from __future__ import annotations

import json
import os
import sys
import time

os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

# Reusable question dictionary matching spike_thx02.py exactly
QUESTIONS = {
    "decision_type": {
        "type": "choice",
        "instructions": (
            "Classifique o tipo do ato JUDICIAL efetivamente proferido neste documento, "
            "não as decisões citadas em relatório ou fundamentação."
        ),
        "criteria": {
            "sentenca": "Sentença: juiz decide definitivamente um pedido ou extingue o processo no grau.",
            "acordao": "Acórdão: julgamento colegiado de recurso ou ação originária.",
            "interlocutoria": "Decisão interlocutória: resolve questão incidental, não encerra o mérito da causa.",
            "despacho": "Despacho de mero expediente, sem julgamento de pedido ou recurso.",
            "outro": "Ato diferente, peça incompleta ou documento sem decisão identificável.",
        },
    },
    "outcome": {
        "type": "choice",
        "instructions": (
            "Determine exclusivamente o resultado OPERATIVO deste ato, "
            "não pedidos das partes nem decisões anteriores. "
            "Na sentença, classifique o pedido; no acórdão recursal, classifique o RECURSO. "
            "Se não houver dispositivo suficiente, use unknown."
        ),
        "criteria": {
            "procedente": "Pedido inicial julgado integralmente procedente no dispositivo.",
            "improcedente": "Pedido inicial julgado improcedente no dispositivo.",
            "parcialmente_procedente": "Pedido inicial julgado parcialmente procedente no dispositivo.",
            "acordo": "Acordo ou transação homologados judicialmente.",
            "extinto_sem_merito": "Extinção do processo sem resolução do mérito, por motivo processual.",
            "provido": "Recurso conhecido e integralmente provido no dispositivo.",
            "nao_provido": "Recurso conhecido e não provido (desprovido) no dispositivo.",
            "parcialmente_provido": "Recurso conhecido e parcialmente provido no dispositivo.",
            "nao_conhecido": "Recurso não conhecido (inadmissibilidade).",
            "prejudicado": "Recurso julgado prejudicado ou perda superveniente de objeto.",
            "unknown": "Não há julgamento conclusivo do pedido/recurso, ou é impossível determinar o resultado.",
        },
    },
    "recorrente_polo": {
        "type": "choice",
        "instructions": (
            "Qual polo interpôs o recurso OBJETO do dispositivo? "
            "Autor/requerente do pedido inicial = A; réu/requerido = P. "
            "Não confunda recorrente com parte vencedora."
        ),
        "criteria": {
            "A": "Somente o autor/parte ativa interpôs o recurso analisado.",
            "P": "Somente o réu/parte passiva interpôs o recurso analisado.",
            "ambos": "Ambos os polos interpuseram recursos analisados em conjunto.",
            "nao_aplicavel": "Não há recurso, trata-se de sentença ou outro ato não recursal.",
            "unknown": "Não é possível identificar com segurança o polo recorrente.",
        },
    },
    "winner_direct": {
        "type": "choice",
        "instructions": (
            "Considerando pedido inicial, polo recorrente e dispositivo atual, "
            "qual polo venceu materialmente a controvérsia? "
            "Sem decisão de mérito, vitória parcial ambígua ou dados insuficientes: unknown."
        ),
        "criteria": {
            "A": "Polo ativo/autor venceu integralmente o pedido ou preservou essa vitória em recurso.",
            "P": "Polo passivo/réu venceu integralmente o pedido ou preservou essa vitória em recurso.",
            "draw": "Acordo homologado, sem polo vencedor unilateral.",
            "unknown": "Sem vencedor material unívoco, decisão incidental, resultado parcial ou texto insuficiente.",
        },
    },
}

OUTCOME_MAP = {
    "procedente": "procedente",
    "improcedente": "improcedente",
    "parcialmente_procedente": "parcialmente procedente",
    "acordo": "acordo",
    "extinto_sem_merito": "extinto sem mérito",
    "provido": "provido",
    "nao_provido": "não provido",
    "parcialmente_provido": "parcialmente provido",
    "nao_conhecido": "não conhecido",
    "prejudicado": "prejudicado",
    "unknown": "unknown",
}


def resolve_winner(outcome: str, recorrente_polo: str | None) -> str:
    if outcome == "procedente":
        return "A"
    if outcome == "improcedente":
        return "P"
    if outcome == "acordo":
        return "draw"
    if outcome in {"provido", "não provido"} and recorrente_polo in {"A", "P"}:
        if outcome == "provido":
            return recorrente_polo
        return "P" if recorrente_polo == "A" else "A"
    return "unknown"


def main():
    print("=" * 65)
    print("THX-02 COLAB GPU BENCHMARK (NVIDIA TESLA T4)")
    print("=" * 65)

    import torch

    cuda_avail = torch.cuda.is_available()
    device_name = torch.cuda.get_device_name(0) if cuda_avail else "No GPU"
    vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3) if cuda_avail else 0.0

    print(f"CUDA Available: {cuda_avail}")
    print(f"Device: {device_name}")
    print(f"Total VRAM: {vram_gb:.2f} GB")
    print(f"PyTorch Version: {torch.__version__}")
    print(f"Python Version: {sys.version.split()[0]}")

    # Força default dtype em bfloat16 para evitar OOM de float32
    torch.set_default_dtype(torch.bfloat16)

    # Monkeypatch Qwen3_5Model para garantir torch_dtype=bfloat16 e device_map
    from transformers import Qwen3_5Model

    orig_from_pretrained = Qwen3_5Model.from_pretrained

    @classmethod
    def patched_from_pretrained(cls, *args, **kwargs):
        kwargs["torch_dtype"] = torch.bfloat16
        return orig_from_pretrained(*args, **kwargs)

    Qwen3_5Model.from_pretrained = patched_from_pretrained

    from thx02 import THX02

    # 1. Carregamento do modelo
    print("\n--- [1] Carregando modelo THX-02 em GPU (bfloat16) ---")
    t0_load = time.perf_counter()
    model = THX02.load("HAL-X-AI/THX-02", device="cuda" if cuda_avail else "cpu")
    t_load = time.perf_counter() - t0_load
    print(f"Modelo carregado com sucesso em {t_load:.2f}s!")

    if cuda_avail:
        mem_alloc = torch.cuda.memory_allocated(0) / (1024**3)
        mem_res = torch.cuda.memory_reserved(0) / (1024**3)
        print(f"VRAM alocada: {mem_alloc:.2f} GB | VRAM reservada: {mem_res:.2f} GB")

    # 2. Teste 1: Sentença canônica mínima (Aquecimento da GPU)
    print("\n--- [2] Teste Canônico Mínimo (Warmup) ---")
    sample_text = (
        "SENTENÇA. O autor pediu a restituição de valores. "
        "Ante o exposto, JULGO PROCEDENTE o pedido inicial, integralmente, "
        "com resolução do mérito."
    )
    t0_inf = time.perf_counter()
    warmup_res = model.decide(state=sample_text, questions=QUESTIONS, think=False, tta=1)
    t_warmup = time.perf_counter() - t0_inf
    print(f"Latência do aquecimento: {t_warmup:.3f}s ({t_warmup * 1000:.1f} ms)!")
    print(f"Resposta do aquecimento:\n{json.dumps(warmup_res, indent=2, ensure_ascii=False)}")

    # 3. Teste Fixture (12 Casos do CausaGanha)
    print("\n--- [3] Benchmark Completo da Fixture (12 casos) ---")
    fixture_path = "/content/thx02_spike.jsonl"
    if not os.path.exists(fixture_path):
        fixture_path = "tests/fixtures/thx02_spike.jsonl"

    documents = []
    with open(fixture_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                documents.append(json.loads(line))
    print(f"Carregados {len(documents)} documentos da fixture {fixture_path}.")

    results = []
    latencies = []
    correct_outcome = 0
    correct_winner = 0

    for i, doc in enumerate(documents, start=1):
        doc_id = doc["id"]
        text = doc["text"]
        gold = doc.get("gold", {})
        gold_out = gold.get("outcome")
        gold_win = gold.get("winner")

        t0 = time.perf_counter()
        raw_res = model.decide(state=text, questions=QUESTIONS, think=False, tta=1)
        elapsed_s = time.perf_counter() - t0
        elapsed_ms = elapsed_s * 1000.0
        latencies.append(elapsed_ms)

        # Decodificação
        answers = raw_res.get("answers", {})
        raw_out = answers.get("outcome", {}).get("choice", "unknown")
        outcome = OUTCOME_MAP.get(raw_out, "unknown")
        prob_out = answers.get("outcome", {}).get("probability", 0.0)

        raw_rec = answers.get("recorrente_polo", {}).get("choice")
        winner_direct = answers.get("winner_direct", {}).get("choice")
        resolved_win = resolve_winner(outcome, raw_rec)
        winner = winner_direct if winner_direct in {"A", "P", "draw"} else resolved_win

        match_out = outcome == gold_out
        match_win = winner == gold_win
        if match_out:
            correct_outcome += 1
        if match_win:
            correct_winner += 1

        mark_out = "✓" if match_out else "✗"
        mark_win = "✓" if match_win else "✗"
        print(
            f"[{i:02d}/{len(documents):02d}] {doc_id} ({len(text)} chars) -> Latência: {elapsed_ms:.1f} ms | Resultado: {outcome} ({prob_out:.1%}) [{mark_out}] | Vencedor: {winner} [{mark_win}]"
        )

        results.append(
            {
                "id": doc_id,
                "latency_ms": elapsed_ms,
                "outcome": outcome,
                "outcome_probability": prob_out,
                "gold_outcome": gold_out,
                "match_outcome": match_out,
                "winner": winner,
                "gold_winner": gold_win,
                "match_winner": match_win,
                "raw_response": raw_res,
            }
        )

    # Estatísticas
    latencies.sort()
    n = len(latencies)
    p50 = latencies[int(n * 0.50)]
    p95 = latencies[min(int(n * 0.95), n - 1)]
    p99 = latencies[min(int(n * 0.99), n - 1)]
    avg_ms = sum(latencies) / n

    summary = {
        "hardware": device_name,
        "cuda_available": cuda_avail,
        "vram_gb": vram_gb,
        "total_documents": n,
        "outcome_accuracy": correct_outcome / n if n else 0.0,
        "winner_accuracy": correct_winner / n if n else 0.0,
        "latency_p50_ms": p50,
        "latency_p95_ms": p95,
        "latency_p99_ms": p99,
        "latency_avg_ms": avg_ms,
        "throughput_decisions_per_sec": 1000.0 / avg_ms if avg_ms > 0 else 0.0,
        "model_load_time_seconds": t_load,
    }

    print("\n" + "=" * 65)
    print("RESUMO DO BENCHMARK THX-02 NA GPU (COLAB T4)")
    print("=" * 65)
    for k, v in summary.items():
        print(f"{k}: {v}")

    # Salva arquivos de saída
    os.makedirs("/content/output", exist_ok=True)
    with open("/content/output/colab_thx02_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    with open("/content/output/colab_thx02_results.jsonl", "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("\nResultados gravados em /content/output/colab_thx02_summary.json e results.jsonl!")


if __name__ == "__main__":
    main()
