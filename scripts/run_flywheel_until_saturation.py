#!/usr/bin/env python3
"""Execução da Flywheel de Active Learning até a Saturação (Convergência do Modelo).

Itera continuamente o ciclo:
  Random Forest (Inferência) -> Amostragem Ativa -> THX-02 (Auditoria) -> Retreinamento
até que a taxa de erro caia abaixo do limiar de saturação ou atinja o platô de aprendizado.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd

import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))
sys.path.insert(0, str(ROOT_DIR / "scripts"))

from causaganha.decisoes.hybrid_segmenter import HybridDispositifSegmenter
from causaganha.decisoes.model_ratchet import ModelRatchetGate, RatchetDecision
from thx02_active_learning_flywheel import run_flywheel_cycle


def run_training_step(
    pool_path: Path, model_save_path: Path
) -> tuple[dict[str, Any], RatchetDecision]:
    """Dispara o retreinamento com o pool acumulado e valida estritamente via Catraca."""
    from train_hybrid_forest_segmenter import load_dataset
    from sklearn.metrics import roc_auc_score

    train_path = ROOT_DIR / "data/segmenter_splits/train.jsonl"
    val_path = ROOT_DIR / "data/segmenter_splits/val.jsonl"
    test_path = ROOT_DIR / "data/segmenter_splits/test.jsonl"

    X_train, y_train, prof_train, _ = load_dataset(train_path)

    if pool_path.exists():
        segmenter_pool = HybridDispositifSegmenter()
        X_p, y_p = [], []
        with open(pool_path, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                rec = json.loads(line)
                full_text = rec["full_text"]
                meta = rec.get("metadata", {})
                meta["taxonomy_classification"] = segmenter_pool.taxonomy_registry.classify(
                    full_text, meta
                )
                units = segmenter_pool.split_document_units(full_text)
                tot_u = len(units)
                tot_c = len(full_text)
                corrected_spans = rec.get("corrected_spans") or []
                for idx_u, u in enumerate(units):
                    p_txt = u["text"]
                    p_start = u["start"]
                    p_end = u["end"]
                    is_d = 0
                    if corrected_spans:
                        for d_start, d_end in corrected_spans:
                            if max(p_start, d_start) < min(p_end, d_end):
                                is_d = 1
                                break
                    else:
                        pos_r = idx_u / max(tot_u - 1, 1)
                        is_d = (
                            1
                            if (
                                pos_r > 0.65
                                and any(
                                    w in p_txt.lower()
                                    for w in [
                                        "julgo",
                                        "exposto",
                                        "acordam",
                                        "provimento",
                                        "homologo",
                                    ]
                                )
                            )
                            else 0
                        )
                    feats = segmenter_pool.extract_features(
                        p_txt, idx_u, tot_u, p_start, tot_c, meta
                    )
                    X_p.append(feats)
                    y_p.append(is_d)
        if X_p:
            X_train = np.vstack([X_train, np.array(X_p)])
            y_train = np.concatenate([y_train, np.array(y_p)])

    X_val, y_val, _, _ = load_dataset(val_path)
    X_test, y_test, _, _ = load_dataset(test_path)

    candidate_segmenter = HybridDispositifSegmenter()
    candidate_segmenter.fit(X_train, y_train, doc_profiles=prof_train)

    temp_cand_path = model_save_path.parent / "candidate_flywheel.joblib"
    candidate_segmenter.save(temp_cand_path)

    ratchet_state_file = model_save_path.parent / "ratchet_state.json"
    canaries = [
        {
            "text": "PODER JUDICIÁRIO. Processo de cobrança. FUNDAMENTAÇÃO: Analisadas as provas. DISPOSITIVO: Ante o exposto, julgo procedente o pedido formulado na inicial. Publique-se. Juiz de Direito.",
            "expected_needle": "julgo procedente",
        },
        {
            "text": "TRIBUNAL DE JUSTIÇA. Apelação Cível. VOTO CONDUTOR: Conforme precedentes. ACÓRDÃO: Acordam os Desembargadores em dar provimento ao recurso, à unanimidade. Porto Velho, 2025. Desembargador Relator.",
            "expected_needle": "dar provimento",
        },
        {
            "text": "Vistos. Defiro a tutela provisória de urgência para determinar a imediata suspensão das cobranças indevidas. Intime-se a requerida com urgência.",
            "expected_needle": "defiro a tutela",
            "metadata": {"doc_type": "decisão interlocutória"},
        },
    ]

    gate = ModelRatchetGate(state_file=ratchet_state_file, canary_cases=canaries)
    decision = gate.evaluate_and_gate(
        candidate_segmenter=candidate_segmenter,
        X_test=X_test,
        y_test=y_test,
        candidate_model_path=temp_cand_path,
        production_model_path=model_save_path,
    )

    if temp_cand_path.exists():
        temp_cand_path.unlink()

    y_val_prob = candidate_segmenter.rf_model.predict_proba(X_val)[:, 1]
    y_test_prob = candidate_segmenter.rf_model.predict_proba(X_test)[:, 1]

    val_auc = float(roc_auc_score(y_val, y_val_prob)) if len(np.unique(y_val)) > 1 else 0.0
    test_auc = float(roc_auc_score(y_test, y_test_prob)) if len(np.unique(y_test)) > 1 else 0.0

    metrics = {
        "train_size": len(X_train),
        "val_auc": val_auc,
        "test_auc": test_auc,
    }
    return metrics, decision


def main():
    parser = argparse.ArgumentParser(description="Active Learning Saturation Runner")
    parser.add_argument("--max-iterations", type=int, default=5, help="Número máximo de ciclos")
    parser.add_argument("--sample-size", type=int, default=25, help="Amostras auditadas por ciclo")
    parser.add_argument(
        "--saturation-error", type=float, default=0.10, help="Taxa de erro para declarar saturação"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default=str(ROOT_DIR / "data/benchmark/ia_expanded_decisions.parquet"),
        help="Caminho do dataset parquet para inferência e amostragem ativa",
    )
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    model_path = ROOT_DIR / "models/hybrid_dispositif_forest.joblib"
    pool_path = ROOT_DIR / "data/audit/active_learning_pool.jsonl"

    print("=" * 75)
    print("INICIANDO LOOP DA FLYWHEEL ATÉ A SATURAÇÃO")
    print(
        f"Critérios: Máx {args.max_iterations} iterações | Saturação se taxa de erro < {args.saturation_error * 100:.0f}%"
    )
    print("=" * 75)

    history = []

    for it in range(1, args.max_iterations + 1):
        print(f"\n{'#' * 30} ITERAÇÃO {it}/{args.max_iterations} {'#' * 30}")
        t0_it = time.perf_counter()

        # 1. Roda ciclo de inferência + amostragem + auditoria
        flywheel_res = run_flywheel_cycle(
            dataset_path=dataset_path,
            model_path=model_path,
            pool_output_path=pool_path,
            sample_size=args.sample_size,
        )

        n_audited = flywheel_res["total_audited"]
        n_failures = flywheel_res["failures_found"]
        error_rate = n_failures / max(n_audited, 1)

        print(f"\n[MÉTRICAS DO CICLO {it}]")
        print(f"  • Auditados pelo THX : {n_audited}")
        print(f"  • Falhas encontradas : {n_failures}")
        print(f"  • Taxa de Erro Atual : {error_rate * 100:.1f}%")

        # 2. Retreinamento com novo pool e passagem pelo Ratchet Gatekeeper (Catraca)
        print("\nDisparando retreinamento da Random Forest com os novos feedbacks...")
        retrain_metrics, ratchet_decision = run_training_step(pool_path, model_path)
        print(f"  • Novo Tamanho de Treino: {retrain_metrics['train_size']} unidades")
        print(f"  • Validação ROC-AUC     : {retrain_metrics['val_auc']:.4f}")
        print(f"  • Teste ROC-AUC         : {retrain_metrics['test_auc']:.4f}")

        print("\n  [VEREDITO DA CATRACA]")
        if ratchet_decision.promoted:
            print(f"  ✅ {ratchet_decision.reason}")
            print(
                f"     Métricas promovidas: AUC={ratchet_decision.current_metrics.roc_auc:.4f} | Recall={ratchet_decision.current_metrics.recall:.4f}"
            )
        else:
            print(f"  ❌ {ratchet_decision.reason}")
            print(
                "     ⚠️ Modelo candidato rejeitado pela Catraca! Baseline anterior preservado em produção."
            )

        elapsed_it = time.perf_counter() - t0_it
        history.append(
            {
                "iteration": it,
                "error_rate": error_rate,
                "failures": n_failures,
                "train_size": retrain_metrics["train_size"],
                "val_auc": retrain_metrics["val_auc"],
                "test_auc": retrain_metrics["test_auc"],
                "promoted": ratchet_decision.promoted,
                "elapsed_s": round(elapsed_it, 2),
            }
        )

        # 3. Critério de Saturação
        if error_rate <= args.saturation_error:
            print("\n" + "*" * 75)
            print(f"🎯 SATURAÇÃO ATINGIDA NA ITERAÇÃO {it}!")
            print(
                f"A taxa de falhas caiu para {error_rate * 100:.1f}% (<= {args.saturation_error * 100:.0f}%)."
            )
            print("O modelo convergiu com estabilidade máxima de corte.")
            print("*" * 75)
            break
        elif it > 1 and abs(history[-1]["error_rate"] - history[-2]["error_rate"]) < 0.02:
            print("\n" + "*" * 75)
            print(f"🎯 PLATÔ DE SATURAÇÃO ALCANÇADO NA ITERAÇÃO {it}!")
            print("Variação marginal de erro inferior a 2%. Aprendizado estabilizado.")
            print("*" * 75)
            break

    # Relatório final de convergência
    print("\n" + "=" * 75)
    print("HISTÓRICO DE CONVERGÊNCIA DA FLYWHEEL (SATURAÇÃO)")
    print("=" * 75)
    hist_df = pd.DataFrame(history)
    print(hist_df.to_string(index=False))

    # Salva histórico
    hist_out = ROOT_DIR / "docs/spikes/flywheel_convergence_history.md"
    with open(hist_out, "w", encoding="utf-8") as f:
        f.write("# Histórico de Convergência da Flywheel (Saturação)\n\n")
        f.write(
            "| Iteração | Taxa de Erro | Falhas | Tamanho Treino | Val AUC | Test AUC | Catraca | Tempo (s) |\n"
        )
        f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
        for h in history:
            catraca_str = "PROMOVIDO" if h.get("promoted", True) else "BLOQUEADO"
            f.write(
                f"| {h['iteration']} | {h['error_rate'] * 100:.1f}% | {h['failures']} | {h['train_size']} | {h['val_auc']:.4f} | {h['test_auc']:.4f} | {catraca_str} | {h['elapsed_s']} |\n"
            )
        f.write("\n")
    print(f"\nHistórico gravado em: {hist_out}")


if __name__ == "__main__":
    main()
