#!/usr/bin/env python3
"""Benchmark 4 Dispositif Extraction Methods against THX-02 on Colab GPU (Tesla T4).

Compares:
1. canonical_regex
2. tail_window
3. paragraph_scorer
4. block_chunk (OPF baseline)
Across:
- Accuracy (Outcome & Winner)
- Latency (Extraction, Inference, Total)
- Character footprint
- Calibration / Confidence
"""

from __future__ import annotations

import json
import os
import time

os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

# Standard questions
QUESTIONS = {
    "outcome": {
        "type": "choice",
        "instructions": (
            "Determine exclusivamente o resultado OPERATIVO deste ato judicial, "
            "não pedidos das partes nem decisões anteriores citadas. "
            "Na sentença, classifique o pedido; no acórdão recursal, classifique o RECURSO. "
            "Se não houver dispositivo conclusivo de mérito, use unknown."
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
            "nao_conhecido": "Recurso não conhecido (inadmissibilidade recursal).",
            "prejudicado": "Recurso julgado prejudicado ou perda superveniente de objeto.",
            "unknown": "Não há julgamento conclusivo do pedido/recurso, ou é impossível determinar o resultado.",
        },
    },
    "winner_direct": {
        "type": "choice",
        "instructions": (
            "Considerando o dispositivo atual, qual polo venceu materialmente a controvérsia? "
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


def main():
    print("=" * 70)
    print("BENCHMARK COMPARATIVO: 4 MÉTODOS DE EXTRAÇÃO DE DISPOSITIVO + THX-02")
    print("=" * 70)

    import torch

    cuda_avail = torch.cuda.is_available()
    device_name = torch.cuda.get_device_name(0) if cuda_avail else "No GPU"
    vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3) if cuda_avail else 0.0
    print(f"CUDA: {cuda_avail} | Device: {device_name} | VRAM: {vram_gb:.2f} GB")

    torch.set_default_dtype(torch.bfloat16)

    # Monkeypatch Qwen3_5Model para garantir torch_dtype=bfloat16
    from transformers import Qwen3_5Model

    orig_from_pretrained = Qwen3_5Model.from_pretrained

    @classmethod
    def patched_from_pretrained(cls, *args, **kwargs):
        kwargs["torch_dtype"] = torch.bfloat16
        return orig_from_pretrained(*args, **kwargs)

    Qwen3_5Model.from_pretrained = patched_from_pretrained

    from thx02 import THX02

    # 1. Carrega modelo em GPU
    print("\n[1] Carregando modelo THX-02 em GPU...")
    t0_load = time.perf_counter()
    model = THX02.load("HAL-X-AI/THX-02", device="cuda" if cuda_avail else "cpu")
    t_load = time.perf_counter() - t0_load
    print(f"Modelo carregado em {t_load:.2f}s!")

    # 2. Carrega dataset de testes
    dataset_path = "/content/segmentation_methods_test_cases.jsonl"
    if not os.path.exists(dataset_path):
        dataset_path = "data/benchmark/segmentation_methods_test_cases.jsonl"

    documents = []
    with open(dataset_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                documents.append(json.loads(line))

    print(f"\n[2] Processando {len(documents)} decisões reais do TJRO sob 4 métodos...")

    method_keys = ["canonical_regex", "tail_window", "paragraph_scorer", "block_chunk"]
    results = []

    for idx, doc in enumerate(documents, start=1):
        doc_id = doc["text_uuid"]
        gold_out = doc["gold_outcome"]
        gold_win = doc["gold_winner"]
        print(
            f"\n--- Documento [{idx:02d}/{len(documents):02d}] {doc_id} (Gold: {gold_out} | Win: {gold_win}) ---"
        )

        for m_key in method_keys:
            m_data = doc["methods"][m_key]
            snippet = m_data["extracted_text"]
            extract_ms = m_data["extraction_ms"]
            char_count = m_data["char_count"]
            fallback = m_data["fallback_used"]

            # Inferência THX-02
            t0_inf = time.perf_counter()
            raw_res = model.decide(state=snippet, questions=QUESTIONS, think=False, tta=1)
            inf_ms = (time.perf_counter() - t0_inf) * 1000.0
            total_ms = extract_ms + inf_ms

            answers = raw_res.get("answers", {})
            out_choice_raw = answers.get("outcome", {}).get("choice", "unknown")
            pred_outcome = OUTCOME_MAP.get(out_choice_raw, "unknown")
            out_prob = answers.get("outcome", {}).get("probability", 0.0)

            pred_win = answers.get("winner_direct", {}).get("choice", "unknown")
            win_prob = answers.get("winner_direct", {}).get("probability", 0.0)

            match_out = pred_outcome == gold_out
            match_win = (pred_win == gold_win) if gold_win != "unknown" else True

            status_out = "✓" if match_out else "✗"
            print(
                f"  [{m_key:<16}] Out: {pred_outcome:<23} ({out_prob:.1%}) [{status_out}] | Chars: {char_count:<4} | Lat: {inf_ms:6.1f} ms"
            )

            results.append(
                {
                    "text_uuid": doc_id,
                    "doc_type": doc["doc_type"],
                    "method": m_key,
                    "char_count": char_count,
                    "extraction_ms": extract_ms,
                    "inference_ms": inf_ms,
                    "total_ms": total_ms,
                    "fallback_used": fallback,
                    "gold_outcome": gold_out,
                    "pred_outcome": pred_outcome,
                    "outcome_prob": out_prob,
                    "match_outcome": match_out,
                    "gold_winner": gold_win,
                    "pred_winner": pred_win,
                    "winner_prob": win_prob,
                    "match_winner": match_win,
                }
            )

    # 3. Consolidação Estatística por Método
    print("\n" + "=" * 75)
    print("MATRIZ COMPARATIVA DE RESULTADOS: 4 MÉTODOS DE EXTRAÇÃO DE DISPOSITIVO")
    print("=" * 75)

    matrix = {}
    for m_key in method_keys:
        m_results = [r for r in results if r["method"] == m_key]
        n_m = len(m_results)

        correct_out = sum(1 for r in m_results if r["match_outcome"])
        correct_win = sum(1 for r in m_results if r["match_winner"])

        avg_chars = sum(r["char_count"] for r in m_results) / n_m
        avg_extract_ms = sum(r["extraction_ms"] for r in m_results) / n_m
        avg_inf_ms = sum(r["inference_ms"] for r in m_results) / n_m
        avg_total_ms = sum(r["total_ms"] for r in m_results) / n_m
        avg_conf = sum(r["outcome_prob"] for r in m_results) / n_m
        fallback_rate = sum(1 for r in m_results if r["fallback_used"]) / n_m

        matrix[m_key] = {
            "total_documents": n_m,
            "outcome_accuracy": correct_out / n_m,
            "winner_accuracy": correct_win / n_m,
            "avg_chars": avg_chars,
            "avg_extraction_ms": avg_extract_ms,
            "avg_inference_ms": avg_inf_ms,
            "avg_total_ms": avg_total_ms,
            "avg_outcome_confidence": avg_conf,
            "fallback_rate": fallback_rate,
        }

    # Print markdown table
    header = f"{'Método':<18} | {'Outcome Acc':<11} | {'Winner Acc':<10} | {'Chars':<6} | {'Extração':<9} | {'Inferência':<11} | {'Total':<10} | {'Conf Média':<10} | {'Fallback':<8}"
    print(header)
    print("-" * len(header))
    for m_key, m_stats in matrix.items():
        print(
            f"{m_key:<18} | {m_stats['outcome_accuracy']:10.1%} | {m_stats['winner_accuracy']:9.1%} | {m_stats['avg_chars']:6.0f} | {m_stats['avg_extraction_ms']:6.3f} ms | {m_stats['avg_inference_ms']:8.1f} ms | {m_stats['avg_total_ms']:7.1f} ms | {m_stats['avg_outcome_confidence']:9.1%} | {m_stats['fallback_rate']:7.1%}"
        )

    # Salva arquivos de saída
    os.makedirs("/content/output", exist_ok=True)
    with open("/content/output/segmentation_methods_matrix.json", "w", encoding="utf-8") as f:
        json.dump(matrix, f, indent=2, ensure_ascii=False)
    with open("/content/output/segmentation_methods_results.jsonl", "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print("\nResultados completos salvos em /content/output/!")


if __name__ == "__main__":
    main()
