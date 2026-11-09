#!/usr/bin/env python3
"""Demonstração de Decomposição Estrutural Completa em Decisões Reais do DJEN.

Roda o FullDocumentStructuralSegmenter sobre uma amostra de decisões do TJRO
e exibe a árvore de seções canônicas e entidades jurídicas estruturadas.
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd

import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

from causaganha.decisoes.structural_segmenter import FullDocumentStructuralSegmenter


def main():
    print("=" * 70)
    print("DEMONSTRAÇÃO DE DECOMPOSIÇÃO ESTRUTURAL COMPLETA (CAUSAGANHA)")
    print("=" * 70)

    parquet_path = ROOT_DIR / "data/benchmark/gold_benchmark.parquet"
    if not parquet_path.exists():
        print(f"Arquivo não encontrado: {parquet_path}")
        return

    df = pd.read_parquet(parquet_path)
    sample_rows = df.iloc[:2]

    segmenter = FullDocumentStructuralSegmenter()

    for idx, row in sample_rows.iterrows():
        text = str(row["texto"])
        meta = {
            "court": row.get("court"),
            "judge_name": row.get("judge_name"),
            "classe_processual": row.get("classe_processual"),
            "doc_type": row.get("decision_type"),
            "recorrente_polo": row.get("recorrente_polo"),
        }

        struct = segmenter.segment(text, metadata=meta)
        struct_dict = struct.to_dict()

        print(
            f"\n>>> PROCESSO [{row.get('text_uuid', f'doc_{idx}')}] | TOPOLOGIA: {struct.topology.value}"
        )
        print(f"    Tribunal: {meta.get('court')} | Classe: {meta.get('classe_processual')}")
        print(f"    Juiz/Relator: {meta.get('judge_name')}")
        print(f"    Entidades Extraídas: {struct_dict['entities']}")
        print("    --- SEÇÕES CANÔNICAS DECOMPOSTAS ---")
        for sec_name, sec_info in struct_dict["sections"].items():
            txt_preview = sec_info["text"][:80].replace("\n", " ")
            print(
                f"      • {sec_name.upper():<20} [{sec_info['start']:>5}:{sec_info['end']:>5}] ({sec_info['char_count']:>4} chars | conf: {sec_info['confidence']:.2f}) -> {txt_preview!r}..."
            )

    print("\n" + "=" * 70)
    print("Decomposição estrutural concluída com sucesso em tempo real!")
    print("=" * 70)


if __name__ == "__main__":
    main()
