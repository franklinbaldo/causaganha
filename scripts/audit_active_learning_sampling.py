#!/usr/bin/env python3
"""Flywheel de Active Learning e Auditoria Estratificada para Segmentador Híbrido.

Executa a amostragem inteligente de lotes de decisões judiciais para validação
via LLM Judge (HAL-X THX-02 ou Gemini) e realimentação contínua da Random Forest.

Critérios de Amostragem:
1. Anomalias estruturais detectadas pela Isolation Forest (is_anomaly == True)
2. Decisões com incerteza / baixa confiança da Random Forest (confidence < 0.60)
3. Decisões onde a regra de fallback foi acionada (fallback_used == True)
4. Amostra estratificada de controle (alta confiança) para aferir falsos positivos
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import numpy as np
import pandas as pd

import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

from causaganha.decisoes.hybrid_segmenter import HybridDispositifSegmenter


def build_llm_judge_prompt(doc_id: str, metadata: dict, snippet: str) -> str:
    """Monta o prompt para a LLM Judge avaliar a precisão do dispositivo recortado."""
    return f"""Você é um auditor judiciário sênior especialista em análise de acórdãos e sentenças no direito brasileiro.
Avalie o recorte do dispositivo extraído pelo classificador para o seguinte processo:

[METADADOS DO DJEN]
- Identificador: {doc_id}
- Tribunal: {metadata.get("court", "N/A")}
- Juiz/Relator: {metadata.get("judge_name", "N/A")}
- Classe: {metadata.get("classe_processual", "N/A")}
- Data: {metadata.get("validated_at") or metadata.get("data_decisao", "N/A")}

[RECORTE EXTRAÍDO DO DISPOSITIVO]
\"\"\"
{snippet}
\"\"\"

Sua tarefa de auditoria:
1. O texto acima contém integralmente a decisão/dispositivo de mérito (procedência, provimento, improcedência, condenação)?
2. Há texto truncado antes da conclusão principal?
3. O texto incluiu citações jurisprudenciais irrelevantes em excesso?
4. Responda em JSON estrito:
{{
  "is_dispositivo_complete": true|false,
  "has_truncation_error": true|false,
  "has_false_positive_jurisprudence": true|false,
  "quality_score": 1_a_5,
  "suggested_cut_adjustment": "nenhum|expandir_inicio|encurtar_assinatura"
}}
"""


def run_audit_sampling(
    input_path: Path,
    model_path: Path,
    output_dir: Path,
    sample_size: int = 30,
    seed: int = 42,
) -> Path:
    random.seed(seed)
    np.random.seed(seed)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Carregando modelo segmentador de: {model_path}...")
    segmenter = HybridDispositifSegmenter(model_path=model_path)

    print(f"Carregando lote de decisões de: {input_path}...")
    if input_path.suffix == ".parquet":
        df = pd.read_parquet(input_path)
    elif input_path.suffix in {".jsonl", ".json"}:
        records = []
        with open(input_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
        df = pd.DataFrame(records)
    else:
        raise ValueError(f"Formato não suportado: {input_path.suffix}")

    print(f"Total de decisões no lote bruto: {len(df)}")

    text_col = "texto" if "texto" in df.columns else "text"
    id_col = "text_uuid" if "text_uuid" in df.columns else "id"

    results = []
    print("Processando decisões com HybridDispositifSegmenter...")
    for idx, row in df.iterrows():
        text = str(row.get(text_col, ""))
        if not text or len(text) < 50:
            continue

        doc_id = str(row.get(id_col, f"doc_{idx}"))
        meta = {
            "court": row.get("court"),
            "judge_name": row.get("judge_name"),
            "classe_processual": row.get("classe_processual"),
            "polo_ativo": row.get("polo_ativo") or row.get("recorrente_polo"),
            "polo_passivo": row.get("polo_passivo"),
            "validated_at": str(row.get("validated_at", "")),
        }

        res = segmenter.predict(text, metadata=meta)
        results.append(
            {
                "doc_id": doc_id,
                "text": text,
                "metadata": res.metadata_used,
                "snippet": res.snippet,
                "start": res.start,
                "end": res.end,
                "char_count": len(res.snippet),
                "confidence": res.confidence,
                "is_anomaly": res.is_anomaly,
                "fallback_used": res.fallback_used,
            }
        )

    res_df = pd.DataFrame(results)
    total_processed = len(res_df)
    n_anomalies = int(res_df["is_anomaly"].sum())
    n_fallbacks = int(res_df["fallback_used"].sum())
    n_low_conf = int((res_df["confidence"] < 0.60).sum())

    print("\n--- RESUMO DE QUALIDADE DO LOTE ---")
    print(f"Decisões processadas    : {total_processed}")
    print(f"Anomalias estruturais   : {n_anomalies} ({n_anomalies / total_processed * 100:.1f}%)")
    print(f"Baixa confiança (<0.60) : {n_low_conf} ({n_low_conf / total_processed * 100:.1f}%)")
    print(f"Fallbacks acionados     : {n_fallbacks} ({n_fallbacks / total_processed * 100:.1f}%)")
    print(f"Comprimento médio cut   : {res_df['char_count'].mean():.0f} caracteres")

    # Estratégia de Amostragem Inteligente para LLM Judge
    audit_samples = []

    # 1. 100% das Anomalias (ou até limite)
    anomalies = res_df[res_df["is_anomaly"]].copy()
    for _, row in anomalies.iterrows():
        audit_samples.append({**row.to_dict(), "audit_reason": "ISOLATION_FOREST_ANOMALY"})

    # 2. Casos de Baixa Confiança / Fallback (evitando duplicar)
    already_ids = {s["doc_id"] for s in audit_samples}
    uncertain = res_df[
        (~res_df["doc_id"].isin(already_ids))
        & ((res_df["confidence"] < 0.60) | res_df["fallback_used"])
    ].copy()
    for _, row in uncertain.iterrows():
        audit_samples.append({**row.to_dict(), "audit_reason": "LOW_CONFIDENCE_OR_FALLBACK"})

    # 3. Amostra de Controle (Alta Confiança) para fechar o tamanho desejado
    already_ids = {s["doc_id"] for s in audit_samples}
    remaining_needed = max(0, sample_size - len(audit_samples))
    high_conf = res_df[
        (~res_df["doc_id"].isin(already_ids)) & (res_df["confidence"] >= 0.70)
    ].copy()

    if remaining_needed > 0 and len(high_conf) > 0:
        ctrl_sample = high_conf.sample(n=min(remaining_needed, len(high_conf)), random_state=seed)
        for _, row in ctrl_sample.iterrows():
            audit_samples.append({**row.to_dict(), "audit_reason": "CONTROL_HIGH_CONFIDENCE"})

    print(f"\nAmostra final selecionada para auditoria LLM: {len(audit_samples)} casos")

    # Monta os registros com prompts formatados para a LLM
    export_records = []
    for s in audit_samples:
        prompt = build_llm_judge_prompt(s["doc_id"], s["metadata"], s["snippet"])
        export_records.append(
            {
                "doc_id": s["doc_id"],
                "audit_reason": s["audit_reason"],
                "confidence": round(float(s["confidence"]), 4),
                "is_anomaly": bool(s["is_anomaly"]),
                "fallback_used": bool(s["fallback_used"]),
                "char_count": int(s["char_count"]),
                "metadata": s["metadata"],
                "snippet": s["snippet"],
                "llm_judge_prompt": prompt,
            }
        )

    # Salva arquivo JSONL para a LLM Judge
    out_jsonl = output_dir / "audit_active_learning_batch.jsonl"
    with open(out_jsonl, "w", encoding="utf-8") as f:
        for r in export_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Salva relatório Markdown executivo
    out_report = output_dir / "audit_active_learning_report.md"
    with open(out_report, "w", encoding="utf-8") as f:
        f.write("# Relatório de Auditoria e Active Learning Flywheel\n\n")
        f.write("- **Data de Geração**: 2026-11-09\n")
        f.write(f"- **Lote Analisado**: `{input_path.name}` ({total_processed} decisões)\n")
        f.write(f"- **Total Selecionado para LLM**: {len(export_records)} casos\n\n")
        f.write("## Distribuição da Amostra\n\n")
        reasons_series = pd.Series([r["audit_reason"] for r in export_records]).value_counts()
        f.write("| Motivo de Auditoria | Contagem |\n")
        f.write("| :--- | :--- |\n")
        for reason, count in reasons_series.items():
            f.write(f"| {reason} | {count} |\n")
        f.write("\n\n## Casos Mais Críticos Selecionados para Auditoria\n\n")
        f.write("| ID | Motivo | Confiança | Anomalia | Fallback | Chars | Juiz / Vara |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
        for r in export_records[:15]:
            judge = r["metadata"].get("judge_name") or "Não identificado"
            f.write(
                f"| `{r['doc_id'][:12]}` | {r['audit_reason']} | {r['confidence']:.2f} | "
                f"{r['is_anomaly']} | {r['fallback_used']} | {r['char_count']} | {judge} |\n"
            )

    print("Auditoria salva com sucesso em:")
    print(f"  JSONL: {out_jsonl}")
    print(f"  Report: {out_report}")
    return out_jsonl


def main():
    parser = argparse.ArgumentParser(description="Active Learning Sampling Flywheel")
    parser.add_argument(
        "--input",
        type=Path,
        default=ROOT_DIR / "data/benchmark/gold_benchmark.parquet",
        help="Caminho do arquivo parquet ou jsonl de decisões",
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=ROOT_DIR / "models/hybrid_dispositif_forest.joblib",
        help="Caminho do modelo segmentador treinado",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT_DIR / "data/audit",
        help="Diretório de saída para amostras e relatórios",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=25,
        help="Quantidade total de amostras para auditoria LLM",
    )
    args = parser.parse_args()

    run_audit_sampling(
        input_path=args.input,
        model_path=args.model,
        output_dir=args.output_dir,
        sample_size=args.sample_size,
    )


if __name__ == "__main__":
    main()
