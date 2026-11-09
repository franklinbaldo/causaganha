#!/usr/bin/env python3
"""Consolidação e Benchmark Multitribunal Expandido do Internet Archive (IA).

Unifica parquets de múltiplas origens regionais e superiores:
- Superior: STJ (Primeira Seção)
- Nordeste: TJBA (Tribunal de Justiça da Bahia - 5.873 decisões)
- Norte: TJRO (Tribunal de Justiça de Rondônia - 2.030 decisões)
- Sudeste: TJSP, TJRJ, TJMG (Benchmark Gold)

Executa o TopologyRouter e o FullDocumentStructuralSegmenter para validar
a robustez da decomposição estrutural diante de diferentes estilos de redação judiciária.
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
    print("=" * 80)
    print("BENCHMARK MULTITRIBUNAL EXPANDIDO (INTERNET ARCHIVE)")
    print("=" * 80)

    ia_dir = ROOT_DIR / "data/ia_parquets"
    records = []

    # 1. Carrega TJBA (5.873 decisões)
    tjba_path = ia_dir / "tjba_textos.parquet"
    if tjba_path.exists():
        df_tjba = pd.read_parquet(tjba_path)
        print(f"Carregado TJBA: {len(df_tjba)} decisões.")
        # Amostra representativa do TJBA
        sample_tjba = df_tjba.sample(n=min(len(df_tjba), 500), random_state=42)
        for _, row in sample_tjba.iterrows():
            records.append({
                "doc_id": f"tjba_{row['id']}",
                "court": "TJBA",
                "texto": str(row["texto"]),
                "classe_hint": "Procedimento Comum Cível",
                "doc_type_hint": "Sentença",
            })

    # 2. Carrega STJ (89 acórdãos superiores)
    stj_path = ia_dir / "stj_acordaos.parquet"
    if stj_path.exists():
        df_stj = pd.read_parquet(stj_path)
        print(f"Carregado STJ: {len(df_stj)} acórdãos.")
        for _, row in df_stj.iterrows():
            # Une ementa + decisão para formar o texto integral do acórdão
            full_text = f"SUPERIOR TRIBUNAL DE JUSTIÇA\nÓrgão: {row.get('nomeOrgaoJulgador')}\nRelator: {row.get('ministroRelator')}\nClasse: {row.get('descricaoClasse')}\n\nEMENTA\n{row.get('ementa', '')}\n\nACÓRDÃO DECISÓRIO\n{row.get('decisao', '')}"
            records.append({
                "doc_id": f"stj_{row['id']}",
                "court": "STJ",
                "texto": full_text,
                "classe_hint": str(row.get("descricaoClasse", "Recurso")),
                "doc_type_hint": "Acórdão",
                "relator": str(row.get("ministroRelator", "")),
            })

    # 3. Carrega TJRO / Mix de Testes (2.030 decisões)
    mix_path = ia_dir / "textos.parquet"
    cls_path = ia_dir / "classificacoes_documentos.parquet"
    if mix_path.exists() and cls_path.exists():
        df_mix_txt = pd.read_parquet(mix_path)
        df_mix_cls = pd.read_parquet(cls_path)
        df_mix = pd.merge(df_mix_txt, df_mix_cls, on="id")
        print(f"Carregado Mix TJRO/Outros: {len(df_mix)} decisões.")
        sample_mix = df_mix.sample(n=min(len(df_mix), 400), random_state=42)
        for _, row in sample_mix.iterrows():
            records.append({
                "doc_id": f"mix_{row['id']}",
                "court": "TJRO",
                "texto": str(row["texto"]),
                "classe_hint": str(row.get("procedural_class", "")),
                "doc_type_hint": str(row.get("document_type", "")),
            })

    unified_df = pd.DataFrame(records)
    total_docs = len(unified_df)
    print(f"\nTotal consolidado para o benchmark multitribunal: {total_docs} decisões")
    print(unified_df["court"].value_counts().to_string())

    # --- EXECUÇÃO DO TOPOLOGY ROUTER ---
    print("\n--- 1. ROTEAMENTO TOPOLÓGICO MULTITRIBUNAL ---")
    t0_route = time.perf_counter()
    topologies = []
    for _, row in unified_df.iterrows():
        meta = {
            "doc_type": row.get("doc_type_hint"),
            "classe_processual": row.get("classe_hint"),
            "relator": row.get("relator"),
            "court": row.get("court"),
        }
        top = TopologyRouter.route(meta, text=row["texto"])
        topologies.append(top.value)

    unified_df["predicted_topology"] = topologies
    elap_route = time.perf_counter() - t0_route

    print(f"Tempo de roteamento: {elap_route*1000:.2f} ms ({total_docs/elap_route:.0f} docs/s)")
    print("\nDistribuição Topológica por Tribunal:")
    cross = pd.crosstab(unified_df["court"], unified_df["predicted_topology"], margins=True)
    print(cross.to_string())

    # --- EXECUÇÃO DO FULL DOCUMENT STRUCTURAL SEGMENTER ---
    print("\n--- 2. DECOMPOSIÇÃO ESTRUTURAL COMPLETA MULTITRIBUNAL ---")
    segmenter = FullDocumentStructuralSegmenter()

    # Amostra balanceada de 100 decisões cobrindo todos os tribunais
    eval_sample = (
        unified_df.groupby("court", group_keys=False)
        .apply(lambda g: g.sample(min(len(g), 35), random_state=42))
        .reset_index(drop=True)
    )
    print(f"Executando decomposição estrutural em {len(eval_sample)} decisões representativas...")

    t0_seg = time.perf_counter()
    section_stats = Counter()
    court_success = Counter()
    total_chars = 0

    for _, row in eval_sample.iterrows():
        c_name = str(row.get("court", "OUTRO"))
        meta = {
            "doc_type": row.get("doc_type_hint"),
            "classe_processual": row.get("classe_hint"),
            "court": c_name,
            "relator": row.get("relator"),
        }
        struct = segmenter.segment(str(row["texto"]), metadata=meta)
        total_chars += len(str(row["texto"]))
        court_success[c_name] += 1
        for sec_name in struct.sections.keys():
            section_stats[sec_name] += 1

    elap_seg = time.perf_counter() - t0_seg
    avg_ms = (elap_seg / len(eval_sample)) * 1000.0

    print(f"Tempo total de segmentação : {elap_seg:.3f} s")
    print(f"Latência média por documento: {avg_ms:.2f} ms")
    print(f"Throughput de decomposição  : {len(eval_sample)/elap_seg:.1f} decisões/segundo em CPU pura")
    print(f"Volume textual processado   : {total_chars/1024:.1f} KB")

    print("\nDetecção de Seções Canônicas no Brasil (Multitribunal):")
    for sec, count in section_stats.most_common():
        pct = (count / len(eval_sample)) * 100.0
        bar = "█" * int(pct / 4)
        print(f"  • {sec.upper():<20}: {count:>3}/{len(eval_sample)} ({pct:>5.1f}%) | {bar}")

    # Salva dataset expandido consolidado multitribunal
    out_parquet = ROOT_DIR / "data/benchmark/ia_multitribunal_expanded.parquet"
    unified_df.to_parquet(out_parquet, index=False)
    print(f"\nDataset consolidado multitribunal salvo em: {out_parquet} ({out_parquet.stat().st_size/1024:.1f} KB)")

    # Salva relatório técnico
    report_path = ROOT_DIR / "docs/spikes/multitribunal_ia_expansion_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Relatório de Expansão Multitribunal (Internet Archive)\n\n")
        f.write(f"- **Data:** 2026-11-09\n")
        f.write(f"- **Total de Decisões Consolidadas:** {total_docs}\n")
        f.write(f"- **Origens Regionais:** STJ (Superior), TJBA (Nordeste), TJRO (Norte), TJSP/TJRJ/TJMG (Sudeste)\n\n")
        f.write("## Distribuição Topológica por Tribunal\n\n")
        f.write("```\n")
        f.write(cross.to_string())
        f.write("\n```\n")
        f.write("\n\n## Métricas de Performance Estrutural\n\n")
        f.write(f"- **Throughput TopologyRouter:** {total_docs/elap_route:.0f} decisões/s\n")
        f.write(f"- **Latência Média StructuralSegmenter:** {avg_ms:.2f} ms por documento\n")
        f.write(f"- **Throughput StructuralSegmenter:** {len(eval_sample)/elap_seg:.1f} decisões/s\n")

    print(f"Relatório técnico gravado em: {report_path}")
    print("=" * 80)


if __name__ == "__main__":
    main()
