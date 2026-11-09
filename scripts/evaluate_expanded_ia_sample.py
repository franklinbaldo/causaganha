#!/usr/bin/env python3
"""Avaliação em Escala do TopologyRouter e Segmentador Estrutural no Acervo Expandido do IA.

Consome as 2.030 decisões judiciais reais de data/ia_parquets/textos.parquet
e classificacoes_documentos.parquet baixadas do Internet Archive.
"""

from __future__ import annotations

import time
from pathlib import Path
import pandas as pd
from collections import Counter

import sys
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

from causaganha.decisoes.topology_router import DecisionTopology, TopologyRouter
from causaganha.decisoes.structural_segmenter import FullDocumentStructuralSegmenter


def main():
    print("=" * 75)
    print("AVALIAÇÃO EM ESCALA NO ACERVO EXPANDIDO DO INTERNET ARCHIVE (2.030 DECISÕES)")
    print("=" * 75)

    txt_path = ROOT_DIR / "data/ia_parquets/textos.parquet"
    cls_path = ROOT_DIR / "data/ia_parquets/classificacoes_documentos.parquet"

    df_txt = pd.read_parquet(txt_path)
    df_cls = pd.read_parquet(cls_path)
    df = pd.merge(df_txt, df_cls, on="id")
    n_total = len(df)
    print(f"Total de decisões carregadas: {n_total}\n")

    # 1. Avaliação do TopologyRouter
    print("--- 1. AVALIAÇÃO DO TOPOLOGY ROUTER ---")
    t0_router = time.perf_counter()
    router_results = []
    for _, row in df.iterrows():
        meta = {
            "doc_type": row["document_type"],
            "classe_processual": row["procedural_class"],
        }
        top = TopologyRouter.route(meta, text=str(row["texto"]))
        router_results.append(top.value)

    elapsed_router = time.perf_counter() - t0_router
    df["predicted_topology"] = router_results
    top_counts = df["predicted_topology"].value_counts().to_dict()

    print(f"Tempo total do roteador: {elapsed_router*1000:.2f} ms ({elapsed_router*1000/n_total:.4f} ms/doc)")
    print(f"Throughput do roteador : {n_total / elapsed_router:.0f} decisões/segundo")
    print("Distribuição de Topologias Roteadas:")
    for top_name, count in top_counts.items():
        print(f"  • {top_name:<16}: {count:>5} ({count/n_total*100:>5.1f}%)")

    # Matriz cruzada: document_type vs predicted_topology
    print("\nCruzamento: document_type original vs predicted_topology:")
    cross_tab = pd.crosstab(df["document_type"], df["predicted_topology"])
    print(cross_tab.to_string())

    # 2. Decomposição Estrutural em Amostra Multitribunal Estratificada
    print("\n" + "-" * 75)
    print("--- 2. BENCHMARK DE DECOMPOSIÇÃO ESTRUTURAL COMPLETA EM AMOSTRA ESTRATIFICADA ---")
    segmenter = FullDocumentStructuralSegmenter()

    # Amostra representativa de 100 decisões cobrindo todas as topologias
    sample_df = df.groupby("predicted_topology", group_keys=False).apply(
        lambda g: g.sample(min(len(g), 25), random_state=42)
    )
    print(f"Processando amostra estratificada de {len(sample_df)} decisões...")

    t0_seg = time.perf_counter()
    section_counts = Counter()
    total_chars_segmented = 0

    for _, row in sample_df.iterrows():
        meta = {
            "doc_type": row["document_type"],
            "classe_processual": row["procedural_class"],
        }
        struct = segmenter.segment(str(row["texto"]), metadata=meta)
        total_chars_segmented += len(str(row["texto"]))
        for sec_name in struct.sections.keys():
            section_counts[sec_name] += 1

    elapsed_seg = time.perf_counter() - t0_seg
    avg_seg_ms = (elapsed_seg / len(sample_df)) * 1000.0

    print(f"Tempo total de segmentação : {elapsed_seg:.3f} s")
    print(f"Latência média por documento: {avg_seg_ms:.2f} ms")
    print(f"Throughput de decomposição  : {len(sample_df) / elapsed_seg:.1f} documentos/segundo em CPU pura")
    print(f"Volume textual processado   : {total_chars_segmented/1024:.1f} KB")

    print("\nTaxa de Detecção de Seções Canônicas na Amostra:")
    for sec_name, count in section_counts.most_common():
        pct = (count / len(sample_df)) * 100.0
        bar = "█" * int(pct / 4)
        print(f"  • {sec_name.upper():<20}: {count:>3}/{len(sample_df)} ({pct:>5.1f}%) | {bar}")

    # Salva dataset expandido consolidado
    consolidated_path = ROOT_DIR / "data/benchmark/ia_expanded_decisions.parquet"
    df.to_parquet(consolidated_path, index=False)
    print(f"\nDataset consolidado salvo em: {consolidated_path} ({consolidated_path.stat().st_size/1024:.1f} KB)")
    print("=" * 75)


if __name__ == "__main__":
    main()
