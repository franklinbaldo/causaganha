"""Exporta dados completos para o visualizador Antes e Depois no site CausaGanha."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "scripts"))

from causaganha.decisoes.structural_segmenter import FullDocumentStructuralSegmenter
from classify_djen_sample_1000 import clean_html_if_present, load_1000_djen_sample


def main():
    print("Gerando dados para o Visualizador Interativo Antes e Depois...")
    df_results = pd.read_csv(ROOT_DIR / "data/audit/classificacao_1000_djen.csv")
    sample_docs = load_1000_djen_sample(1000)
    doc_map = {d["doc_id"]: d for d in sample_docs}

    full_segmenter = FullDocumentStructuralSegmenter()

    selected_rows = []
    # Garante casos de todos os tribunais e desfechos
    for desfecho in [
        "procedente",
        "improcedente",
        "parcialmente procedente",
        "extinto sem mérito",
        "acordo",
        "unknown",
    ]:
        sub = df_results[df_results["desfecho_cpc"] == desfecho]
        selected_rows.extend(sub.head(10).to_dict(orient="records"))

    visualizer_cases = []

    for idx, row in enumerate(selected_rows, start=1):
        doc_id = str(row["doc_id"])
        doc = doc_map.get(doc_id)
        if not doc:
            continue

        raw_text = doc["texto"]
        clean_text = clean_html_if_present(raw_text)

        # Segmenta em 5 seções canônicas
        meta = {"court": row["tribunal"], "id": doc_id}
        struct = full_segmenter.segment(clean_text, meta)

        sections_dict = {}
        for sec_name, span in struct.sections.items():
            sections_dict[sec_name.lower()] = {
                "nome": sec_name.upper(),
                "texto": span.text,
                "caracteres": len(span.text),
                "confianca": round(span.confidence, 2),
            }

        # Formata valores
        val_cond = row.get("valor_condenacao")
        val_cond_str = (
            f"R$ {float(val_cond):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            if pd.notna(val_cond)
            else None
        )

        val_causa = row.get("valor_causa")
        val_causa_str = (
            f"R$ {float(val_causa):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            if pd.notna(val_causa)
            else None
        )

        taxa = row.get("taxa_sucesso_economico")
        taxa_str = f"{float(taxa) * 100:.1f}%" if pd.notna(taxa) else None

        visualizer_cases.append(
            {
                "id": idx,
                "doc_id": doc_id,
                "tribunal": row["tribunal"],
                "classe": row["classe_processual"],
                "tipo_documento": row["tipo_documento"],
                "texto_bruto_djen": raw_text,
                "texto_limpo": clean_text,
                "secoes": sections_dict,
                "desfecho_cpc": row["desfecho_cpc"],
                "confianca_desfecho": row["confianca_desfecho"],
                "polo_vencedor": row["polo_vencedor"],
                "cnj": row["cnj"],
                "autor": row["autor"],
                "reu": row["reu"],
                "advogado": row["advogado"],
                "oab": row["oab"],
                "magistrado": row["magistrado"],
                "valor_condenacao": val_cond_str,
                "valor_causa": val_causa_str,
                "taxa_sucesso_economico": taxa_str,
                "normas_aplicadas": row["normas_aplicadas"],
                "latencia_total_ms": row["lat_total_ms"],
            }
        )

    # Grava JSON
    out_public = ROOT_DIR / "web/public/visualizer_data.json"
    out_audit = ROOT_DIR / "data/audit/visualizer_data.json"
    out_public.parent.mkdir(parents=True, exist_ok=True)
    out_audit.parent.mkdir(parents=True, exist_ok=True)

    with open(out_public, "w", encoding="utf-8") as f:
        json.dump(visualizer_cases, f, ensure_ascii=False, indent=2)

    with open(out_audit, "w", encoding="utf-8") as f:
        json.dump(visualizer_cases, f, ensure_ascii=False, indent=2)

    print(f"✓ {len(visualizer_cases)} casos exportados com sucesso:")
    print(f"  • {out_public}")
    print(f"  • {out_audit}")


if __name__ == "__main__":
    main()
