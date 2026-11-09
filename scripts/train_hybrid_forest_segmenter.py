#!/usr/bin/env python3
"""Treinamento e Avaliação da Random Forest Híbrida de Dispositivo Judicial.

Treina sobre os spans gold anotados de data/segmenter_splits/train.jsonl e
avalia a precisão de fronteira, F1, ROC-AUC e latência de inferência no CPU.
Incorpora metadados do DJEN (juiz, comarca, partes, classe processual, data).
"""

from __future__ import annotations

import json
import time
from pathlib import Path
import numpy as np
from sklearn.metrics import classification_report, roc_auc_score

import sys
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

from causaganha.decisoes.hybrid_segmenter import HybridDispositifSegmenter


def load_dataset(jsonl_path: Path):
    segmenter = HybridDispositifSegmenter()
    X = []
    y = []
    doc_records = []
    doc_profiles = []

    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            doc = json.loads(line)
            text = doc["text"]
            labels = doc.get("label", [])
            info = doc.get("info", {})

            # Limites de dispositivo estruturados
            disp_starts = [
                s["start"]
                for s in labels
                if s["category"] in {"dispositivo_abertura", "acordao_decisorio_inicio"}
            ]
            disp_start = min(disp_starts) if disp_starts else None

            encerr_starts = [
                s["start"]
                for s in labels
                if s["category"] in {"encerramento_inicio", "encerramento_fim"}
            ]
            disp_end = min(encerr_starts) if encerr_starts else len(text)

            # Spans pontuais de resultado / dispositivo
            disp_spans = [
                (s["start"], s["end"])
                for s in labels
                if s["category"] in {
                    "dispositivo_abertura",
                    "resultado",
                    "acordao_decisorio_inicio",
                    "valor_condenacao",
                    "honorarios_inicio",
                    "custas_inicio",
                }
            ]

            units = segmenter.split_document_units(text)
            total_paras = len(units)
            total_chars = len(text)

            meta = {
                "judge_name": info.get("relator") or info.get("judge_name"),
                "court": info.get("tribunal", "TJRO"),
                "doc_type": info.get("doc_type"),
                "classe_processual": info.get("classe"),
                "polo_ativo": info.get("polo_ativo"),
                "polo_passivo": info.get("polo_passivo"),
                "data_decisao": info.get("data_decisao") or info.get("data_disponibilizacao"),
            }

            # Preenche metadados via regex do cabeçalho se faltarem
            extracted = segmenter.extract_header_metadata(text)
            for k, v in extracted.items():
                if not meta.get(k):
                    meta[k] = v

            doc_feats = []
            for idx, u in enumerate(units):
                p_text = u["text"]
                p_start = u["start"]
                p_end = u["end"]

                # Determina se a unidade faz parte do dispositivo
                is_disp = 0
                if disp_start is not None and disp_start <= p_start < disp_end:
                    is_disp = 1
                else:
                    for d_start, d_end in disp_spans:
                        if max(p_start, d_start) < min(p_end, d_end):
                            is_disp = 1
                            break

                feats = segmenter.extract_features(
                    paragraph=p_text,
                    para_idx=idx,
                    total_paras=total_paras,
                    char_offset=p_start,
                    total_chars=total_chars,
                    metadata=meta,
                )
                X.append(feats)
                y.append(is_disp)
                doc_feats.append(feats)

            if doc_feats:
                doc_profiles.append(np.mean(doc_feats, axis=0))

            doc_records.append({"text": text, "metadata": meta, "disp_spans": disp_spans})

    return np.array(X), np.array(y), np.array(doc_profiles), doc_records


def main():
    print("=" * 65)
    print("TREINANDO RANDOM FOREST HÍBRIDA DE DISPOSITIVO JUDICIAL")
    print("=" * 65)

    train_path = ROOT_DIR / "data/segmenter_splits/train.jsonl"
    val_path = ROOT_DIR / "data/segmenter_splits/val.jsonl"
    test_path = ROOT_DIR / "data/segmenter_splits/test.jsonl"

    print(f"Carregando dados de treino: {train_path}...")
    X_train, y_train, prof_train, train_docs = load_dataset(train_path)
    print(f"X_train shape: {X_train.shape} | Dispositivo pos: {sum(y_train)} / neg: {len(y_train) - sum(y_train)}")

    print(f"\nCarregando dados de validação: {val_path}...")
    X_val, y_val, prof_val, val_docs = load_dataset(val_path)
    print(f"X_val shape: {X_val.shape} | Dispositivo pos: {sum(y_val)} / neg: {len(y_val) - sum(y_val)}")

    segmenter = HybridDispositifSegmenter()

    t0_fit = time.perf_counter()
    segmenter.fit(X_train, y_train, doc_profiles=prof_train)
    fit_time = time.perf_counter() - t0_fit
    print(f"\nTreinamento concluído em {fit_time:.3f} segundos no CPU!")

    # Feature Importance
    importances = segmenter.rf_model.feature_importances_
    sorted_idx = np.argsort(importances)[::-1]
    print("\n--- IMPORTÂNCIA DAS FEATURES RANKIADAS ---")
    for idx in sorted_idx:
        name = HybridDispositifSegmenter.FEATURE_NAMES[idx]
        bar = "█" * int(importances[idx] * 50)
        print(f"  {name:<22}: {importances[idx]:.4f} | {bar}")

    # Avaliação no split de validação
    y_pred = segmenter.rf_model.predict(X_val)
    y_prob = segmenter.rf_model.predict_proba(X_val)[:, 1]

    print("\n--- RELATÓRIO DE CLASSIFICAÇÃO (VALIDAÇÃO) ---")
    print(classification_report(y_val, y_pred, target_names=["Outro", "Dispositivo"]))
    if len(np.unique(y_val)) > 1:
        print(f"ROC AUC: {roc_auc_score(y_val, y_prob):.4f}")

    # Avaliação no split de teste se existir
    if test_path.exists():
        print(f"\n--- RELATÓRIO DE CLASSIFICAÇÃO (TESTE: {test_path.name}) ---")
        X_test, y_test, prof_test, test_docs = load_dataset(test_path)
        y_test_pred = segmenter.rf_model.predict(X_test)
        y_test_prob = segmenter.rf_model.predict_proba(X_test)[:, 1]
        print(classification_report(y_test, y_test_pred, target_names=["Outro", "Dispositivo"]))
        if len(np.unique(y_test)) > 1:
            print(f"ROC AUC: {roc_auc_score(y_test, y_test_prob):.4f}")

    # Salva o modelo treinado
    model_dir = ROOT_DIR / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    model_file = model_dir / "hybrid_dispositif_forest.joblib"
    segmenter.save(model_file)
    print(f"\nModelo salvo com sucesso em: {model_file} ({model_file.stat().st_size / 1024:.1f} KB)!")

    # Teste de latência ponta a ponta
    print("\n--- BENCHMARK DE VELOCIDADE EM PRODUÇÃO (CPU) ---")
    all_eval_docs = val_docs + (test_docs if test_path.exists() else [])
    test_latencies = []
    for doc in all_eval_docs:
        t0 = time.perf_counter()
        res = segmenter.predict(doc["text"], doc["metadata"])
        elap_ms = (time.perf_counter() - t0) * 1000.0
        test_latencies.append(elap_ms)

    avg_ms = sum(test_latencies) / len(test_latencies)
    print(f"Documentos avaliados: {len(all_eval_docs)}")
    print(f"Latência média por documento: {avg_ms:.3f} ms ({avg_ms*1000:.1f} µs)!")
    print(f"Throughput em CPU: {1000.0 / avg_ms:.0f} documentos/segundo!")


if __name__ == "__main__":
    main()
