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
import numpy as np
import pandas as pd

import sys
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))
sys.path.insert(0, str(ROOT_DIR / "scripts"))

from causaganha.decisoes.hybrid_segmenter import HybridDispositifSegmenter
from thx02_active_learning_flywheel import run_flywheel_cycle


def run_training_step(pool_path: Path, model_save_path: Path) -> dict[str, float]:
    """Dispara o retreinamento com o pool acumulado e retorna as métricas."""
    from train_hybrid_forest_segmenter import load_dataset
    from sklearn.metrics import classification_report, roc_auc_score

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
                units = segmenter_pool.split_document_units(full_text)
                tot_u = len(units)
                tot_c = len(full_text)
                for idx_u, u in enumerate(units):
                    p_txt = u["text"]
                    pos_r = idx_u / max(tot_u - 1, 1)
                    is_d = 1 if (pos_r > 0.65 and any(w in p_txt.lower() for w in ["julgo", "exposto", "acordam", "provimento", "homologo"])) else 0
                    feats = segmenter_pool.extract_features(p_txt, idx_u, tot_u, u["start"], tot_c, meta)
                    X_p.append(feats)
                    y_p.append(is_d)
        if X_p:
            X_train = np.vstack([X_train, np.array(X_p)])
            y_train = np.concatenate([y_train, np.array(y_p)])

    X_val, y_val, _, _ = load_dataset(val_path)
    X_test, y_test, _, _ = load_dataset(test_path)

    segmenter = HybridDispositifSegmenter()
    segmenter.fit(X_train, y_train, doc_profiles=prof_train)
    segmenter.save(model_save_path)

    y_val_prob = segmenter.rf_model.predict_proba(X_val)[:, 1]
    y_test_prob = segmenter.rf_model.predict_proba(X_test)[:, 1]

    val_auc = float(roc_auc_score(y_val, y_val_prob)) if len(np.unique(y_val)) > 1 else 0.0
    test_auc = float(roc_auc_score(y_test, y_test_prob)) if len(np.unique(y_test)) > 1 else 0.0

    return {
        "train_size": len(X_train),
        "val_auc": val_auc,
        "test_auc": test_auc,
    }


def main():
    parser = argparse.ArgumentParser(description="Active Learning Saturation Runner")
    parser.add_argument("--max-iterations", type=int, default=5, help="Número máximo de ciclos")
    parser.add_argument("--sample-size", type=int, default=25, help="Amostras auditadas por ciclo")
    parser.add_argument("--saturation-error", type=float, default=0.10, help="Taxa de erro para declarar saturação")
    args = parser.parse_args()

    dataset_path = ROOT_DIR / "data/benchmark/ia_expanded_decisions.parquet"
    model_path = ROOT_DIR / "models/hybrid_dispositif_forest.joblib"
    pool_path = ROOT_DIR / "data/audit/active_learning_pool.jsonl"

    print("=" * 75)
    print("INICIANDO LOOP DA FLYWHEEL ATÉ A SATURAÇÃO")
    print(f"Critérios: Máx {args.max_iterations} iterações | Saturação se taxa de erro < {args.saturation_error*100:.0f}%")
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
        print(f"  • Taxa de Erro Atual : {error_rate*100:.1f}%")

        # 2. Retreinamento com novo pool
        print(f"\nDisparando retreinamento da Random Forest com os novos feedbacks...")
        retrain_metrics = run_training_step(pool_path, model_path)
        print(f"  • Novo Tamanho de Treino: {retrain_metrics['train_size']} unidades")
        print(f"  • Validação ROC-AUC     : {retrain_metrics['val_auc']:.4f}")
        print(f"  • Teste ROC-AUC         : {retrain_metrics['test_auc']:.4f}")

        elapsed_it = time.perf_counter() - t0_it
        history.append(
            {
                "iteration": it,
                "error_rate": error_rate,
                "failures": n_failures,
                "train_size": retrain_metrics["train_size"],
                "val_auc": retrain_metrics["val_auc"],
                "test_auc": retrain_metrics["test_auc"],
                "elapsed_s": round(elapsed_it, 2),
            }
        )

        # 3. Critério de Saturação
        if error_rate <= args.saturation_error:
            print("\n" + "*" * 75)
            print(f"🎯 SATURAÇÃO ATINGIDA NA ITERAÇÃO {it}!")
            print(f"A taxa de falhas caiu para {error_rate*100:.1f}% (<= {args.saturation_error*100:.0f}%).")
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
        f.write("| Iteração | Taxa de Erro | Falhas | Tamanho Treino | Val AUC | Test AUC | Tempo (s) |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
        for h in history:
            f.write(f"| {h['iteration']} | {h['error_rate']*100:.1f}% | {h['failures']} | {h['train_size']} | {h['val_auc']:.4f} | {h['test_auc']:.4f} | {h['elapsed_s']} |\n")
        f.write("\n")
    print(f"\nHistórico gravado em: {hist_out}")


if __name__ == "__main__":
    main()
