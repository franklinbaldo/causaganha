"""Experimento Empírico de Extração de Entidades e Papéis Judiciais (NER Multi-Algoritmo).

Avalia:
1. Throughput e Latência por Extrator Especializado em CPU (Intel/AMD x86_64).
2. Validação Matemática CNJ Módulo 97 em decisões reais do DJEN.
3. Resolução Anafórica e Distribuição de Diplomas Normativos (CPC, CC, CDC, CF).
4. Tipagem e Papel Semântico de Valores (Condenação Principal vs. Honorários vs. Causa).
5. Cobertura de Grandes Litigantes e Concessionárias.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import time
import numpy as np
import pandas as pd

from causaganha.decisoes.ner.composite import CompositeEntityExtractor
from causaganha.decisoes.ner.models import JudicialMention
from causaganha.decisoes.structural_segmenter import FullDocumentStructuralSegmenter

ROOT_DIR = Path(__file__).resolve().parent.parent


@dataclass
class ExtractorTiming:
    name: str
    total_time_ms: float
    mean_lat_ms: float
    p95_lat_ms: float
    throughput_docs_per_s: float
    total_entities: int


def main():
    parser = argparse.ArgumentParser(description="Judicial NER Empirical Experiment")
    parser.add_argument("--limit", type=int, default=500, help="Quantidade de decisões para teste")
    args = parser.parse_args()

    dataset_path = ROOT_DIR / "data/benchmark/ia_expanded_decisions.parquet"
    print("=" * 80)
    print("EXPERIMENTO DE EXTRAÇÃO DE ENTIDADES E PAPÉIS (JUDICIAL MULTI-ALGORITHM NER)")
    print("=" * 80)
    print(f"Dataset de teste: {dataset_path}")
    print(f"Amostra avaliada: {args.limit} decisões\n")

    df = pd.read_parquet(dataset_path)
    text_col = "texto" if "texto" in df.columns else "text"
    docs = []
    for idx, row in df.head(args.limit).iterrows():
        t = str(row.get(text_col, ""))
        if len(t) < 80:
            continue
        meta = {
            "court": row.get("court") or "TJRO",
            "doc_type": row.get("document_type") or row.get("decision_type") or "sentença",
            "classe_processual": row.get("classe_processual")
            or row.get("procedural_class")
            or "procedimento comum",
            "judge_name": row.get("judge_name"),
            "relator": row.get("relator"),
        }
        docs.append({"text": t, "metadata": meta})

    n_docs = len(docs)
    print(f"Documentos válidos carregados: {n_docs}")

    # 1. Segmentação Estrutural Canônica prévia (Gera os SectionSpans)
    print("Executando segmentação estrutural prévia das decisões...")
    structural_segmenter = FullDocumentStructuralSegmenter()
    segmented_docs = []
    t_start_seg = time.perf_counter()
    for d in docs:
        struct = structural_segmenter.segment(d["text"], metadata=d["metadata"])
        segmented_docs.append(struct)
    elap_seg = time.perf_counter() - t_start_seg
    print(f"Segmentação estrutural concluída em {elap_seg:.2f}s ({n_docs / elap_seg:.1f} doc/s)\n")

    # 2. Execução Isolada de Cada Algoritmo Especializado
    extractor = CompositeEntityExtractor()

    # CNJ
    t0 = time.perf_counter()
    cnj_latencies = []
    all_cnj_mentions: list[JudicialMention] = []
    for d in docs:
        t_sub = time.perf_counter()
        m = extractor.cnj.extract(d["text"], "CABECALHO")
        cnj_latencies.append((time.perf_counter() - t_sub) * 1000.0)
        all_cnj_mentions.extend(m)
    elap_cnj = time.perf_counter() - t0

    # Normas (Parser Léxico)
    t0 = time.perf_counter()
    norma_latencies = []
    all_norma_mentions: list[JudicialMention] = []
    for d in docs:
        t_sub = time.perf_counter()
        m = extractor.norma.extract(d["text"], "FUNDAMENTACAO")
        norma_latencies.append((time.perf_counter() - t_sub) * 1000.0)
        all_norma_mentions.extend(m)
    elap_norma = time.perf_counter() - t0

    # Valores Monetários e Percentuais
    t0 = time.perf_counter()
    money_latencies = []
    all_money_mentions: list[JudicialMention] = []
    for d in docs:
        t_sub = time.perf_counter()
        m = extractor.money.extract(d["text"], "DISPOSITIVO")
        money_latencies.append((time.perf_counter() - t_sub) * 1000.0)
        all_money_mentions.extend(m)
    elap_money = time.perf_counter() - t0

    # Datas e Prazos
    t0 = time.perf_counter()
    date_latencies = []
    all_date_mentions: list[JudicialMention] = []
    for d in docs:
        t_sub = time.perf_counter()
        m = extractor.date.extract(d["text"], "ENCERRAMENTO")
        date_latencies.append((time.perf_counter() - t_sub) * 1000.0)
        all_date_mentions.extend(m)
    elap_date = time.perf_counter() - t0

    # Organizações / Grandes Litigantes
    t0 = time.perf_counter()
    org_latencies = []
    all_org_mentions: list[JudicialMention] = []
    for d in docs:
        t_sub = time.perf_counter()
        m = extractor.org.extract(d["text"], "CABECALHO")
        org_latencies.append((time.perf_counter() - t_sub) * 1000.0)
        all_org_mentions.extend(m)
    elap_org = time.perf_counter() - t0

    # 3. Pipeline Composto Seccional Integrado (CompositeEntityExtractor)
    t0 = time.perf_counter()
    composite_latencies = []
    all_composite_mentions: list[JudicialMention] = []
    for s_doc in segmented_docs:
        t_sub = time.perf_counter()
        m = extractor.extract_from_sections(s_doc.sections)
        composite_latencies.append((time.perf_counter() - t_sub) * 1000.0)
        all_composite_mentions.extend(m)
    elap_comp = time.perf_counter() - t0

    timings = [
        ExtractorTiming(
            "1. CNJ (Regex + Modulo 97)",
            elap_cnj,
            float(np.mean(cnj_latencies)),
            float(np.percentile(cnj_latencies, 95)),
            n_docs / elap_cnj,
            len(all_cnj_mentions),
        ),
        ExtractorTiming(
            "2. Normas (Parser Léxico + Anáfora)",
            elap_norma,
            float(np.mean(norma_latencies)),
            float(np.percentile(norma_latencies, 95)),
            n_docs / elap_norma,
            len(all_norma_mentions),
        ),
        ExtractorTiming(
            "3. Valores (Moeda, % e Papel)",
            elap_money,
            float(np.mean(money_latencies)),
            float(np.percentile(money_latencies, 95)),
            n_docs / elap_money,
            len(all_money_mentions),
        ),
        ExtractorTiming(
            "4. Datas (Prazos e ISO)",
            elap_date,
            float(np.mean(date_latencies)),
            float(np.percentile(date_latencies, 95)),
            n_docs / elap_date,
            len(all_date_mentions),
        ),
        ExtractorTiming(
            "5. Organizações (Grandes Litigantes)",
            elap_org,
            float(np.mean(org_latencies)),
            float(np.percentile(org_latencies, 95)),
            n_docs / elap_org,
            len(all_org_mentions),
        ),
        ExtractorTiming(
            "6. PIPELINE COMPOSTO SECCIONAL",
            elap_comp,
            float(np.mean(composite_latencies)),
            float(np.percentile(composite_latencies, 95)),
            n_docs / elap_comp,
            len(all_composite_mentions),
        ),
    ]

    print("=" * 80)
    print("BENCHMARK DE LATÊNCIA E THROUGHPUT POR ALGORITMO (CPU)")
    print("=" * 80)
    print(
        f"{'Algoritmo Especializado':<36} | {'Throughput':<12} | {'Média (ms)':<10} | {'p95 (ms)':<8} | {'Entidades':<9}"
    )
    print("-" * 85)
    for t in timings:
        print(
            f"{t.name:<36} | {t.throughput_docs_per_s:>8.1f} doc/s | {t.mean_lat_ms:>8.2f} ms | {t.p95_lat_ms:>6.2f} ms | {t.total_entities:>8d}"
        )

    # Estatísticas de Qualidade dos Dados Extraídos
    print("\n" + "=" * 80)
    print("ESTATÍSTICAS QUALITATIVAS DAS ENTIDADES EXTRAÍDAS")
    print("=" * 80)

    # CNJ
    cnj_valid = sum(1 for m in all_cnj_mentions if m.normalized_value.is_valid_mod97)
    cnj_total = len(all_cnj_mentions)
    print(
        f"[CNJ] Processos detectados: {cnj_total} | Validados pelo Módulo 97: {cnj_valid} ({cnj_valid / max(cnj_total, 1) * 100:.1f}%)"
    )

    # Normas
    normas_diplomas = Counter(m.normalized_value.diploma for m in all_norma_mentions)
    normas_total = len(all_norma_mentions)
    print(f"[NORMAS] Citações normativas: {normas_total}")
    for dip, count in normas_diplomas.most_common(6):
        print(f"  • {dip:<20}: {count:>4d} ({count / max(normas_total, 1) * 100:.1f}%)")

    # Valores
    money_roles = Counter(m.role.value for m in all_money_mentions)
    money_total = len(all_money_mentions)
    print(f"\n[VALORES] Menções financeiras: {money_total}")
    for r, count in money_roles.most_common():
        print(f"  • {r:<30}: {count:>4d} ({count / max(money_total, 1) * 100:.1f}%)")

    # Organizações
    org_counts = Counter(m.normalized_value["canonical_name"] for m in all_org_mentions)
    org_total = len(all_org_mentions)
    print(f"\n[ORGANIZAÇÕES] Litigantes identificados: {org_total}")
    for org, count in org_counts.most_common(6):
        print(f"  • {org:<35}: {count:>4d} ({count / max(org_total, 1) * 100:.1f}%)")

    # Salva relatório detalhado em Markdown
    out_md = ROOT_DIR / "docs/spikes/judicial_ner_experiment_report.md"
    out_md.parent.mkdir(parents=True, exist_ok=True)
    with open(out_md, "w", encoding="utf-8") as f:
        f.write("# Relatório de Experimentos: Judicial Multi-Algorithm NER\n\n")
        f.write(
            "Avaliação empírica em CPU na base real do DJEN (`ia_expanded_decisions.parquet`).\n\n"
        )
        f.write("## 1. Latência e Throughput por Algoritmo Especializado (1 Core CPU)\n\n")
        f.write(
            "| Extrator / Algoritmo | Throughput (doc/s) | Média (ms) | p95 (ms) | Entidades Extraídas |\n"
        )
        f.write("| :--- | :--- | :--- | :--- | :--- |\n")
        for t in timings:
            f.write(
                f"| **{t.name}** | {t.throughput_docs_per_s:.1f} | {t.mean_lat_ms:.2f} | {t.p95_lat_ms:.2f} | {t.total_entities} |\n"
            )

        f.write("\n## 2. Indicadores de Precisão Mecânica e Resolução\n\n")
        f.write(
            f"- **Números CNJ**: {cnj_total} detectados, com **{cnj_valid / max(cnj_total, 1) * 100:.1f}% validados com sucesso pelo algoritmo Módulo 97 da Res. 65/2008**.\n"
        )
        f.write(
            f"- **Referências Normativas**: {normas_total} citações identificadas. Top diplomas: "
        )
        f.write(", ".join(f"`{k}` ({v})" for k, v in normas_diplomas.most_common(4)) + ".\n")
        f.write(
            f"- **Valores Financeiros**: {money_total} quantias distribuídas entre condenações de mérito, valor da causa, astreintes e percentuais de sucumbência.\n"
        )
        f.write(
            f"- **Grandes Litigantes**: {org_total} ocorrências mapeadas diretamente aos identificadores canônicos do CNJ.\n"
        )

        f.write("\n## 3. Amostra de Documento Anotado com Grafo Seccional\n\n")
        f.write("```json\n")
        sample_doc = segmented_docs[0]
        sample_mentions = extractor.extract_from_sections(sample_doc.sections)
        f.write(f"// Decisão analisada: {len(sample_mentions)} entidades extraídas nas seções\n")
        import json

        f.write(
            json.dumps([m.to_dict() for m in sample_mentions[:5]], indent=2, ensure_ascii=False)
        )
        f.write("\n```\n")

    print(f"\nRelatório de experimento salvo em: {out_md}")


if __name__ == "__main__":
    main()
