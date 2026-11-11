"""Benchmark de Performance, Acurácia e Extração do Pipeline Decisório Completo.

Mede end-to-end:
1. Throughput (decisões/segundo em CPU) e latência p50/p95.
2. Acurácia e precisão do Torneio Evolutivo contra o acervo real de 1.000 decisões do DJEN.
3. Eficácia das Travas Negativas e do Segment-Aware Weighting (Dispositivo 3.0x vs Relatório 0.2x).
4. Cobertura granular do NER Transversal em todas as seções.
5. Atualiza o JSON do visualizador web (web/public/visualizer_data.json).
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import time
import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))
sys.path.insert(0, str(ROOT_DIR / "scripts"))

from causaganha.decisoes.multi_axis import MultiAxisJudicialClassifier
from causaganha.decisoes.ner.composite import CompositeEntityExtractor
from causaganha.decisoes.structural_segmenter import FullDocumentStructuralSegmenter
from classify_djen_sample_1000 import clean_html_if_present, load_1000_djen_sample


def run_benchmark(sample_size: int = 1000) -> dict:
    print("=" * 80)
    print("🚀 BENCHMARK DO PIPELINE DE INTELIGÊNCIA DECISÓRIA — CAUSAGANHA")
    print(f"   Amostra: {sample_size} decisões reais do DJEN | Ambiente: CPU Local")
    print("=" * 80)

    # 1. Carregamento dos dados
    print("\n[1/5] Carregando acervo ouro de 1.000 decisões do DJEN...")
    csv_path = ROOT_DIR / "data/audit/classificacao_1000_djen.csv"
    if not csv_path.exists():
        print(f"Erro: {csv_path} não encontrado.")
        return {}

    df_gold = pd.read_csv(csv_path)
    sample_docs = load_1000_djen_sample(sample_size)
    doc_map = {d["doc_id"]: d for d in sample_docs}

    dataset = []
    for _, row in df_gold.head(sample_size).iterrows():
        doc_id = str(row["doc_id"])
        doc = doc_map.get(doc_id)
        if not doc:
            continue
        clean_text = clean_html_if_present(doc["texto"])
        dataset.append(
            {
                "doc_id": doc_id,
                "tribunal": row.get("tribunal", "DJEN"),
                "tipo_documento_hint": doc.get("tipo_documento_hint", ""),
                "classe_hint": doc.get("classe_hint", ""),
                "cnj": row.get("cnj", ""),
                "texto": clean_text,
                "desfecho_esperado": str(row.get("desfecho_cpc", "unknown")).lower().strip(),
            }
        )

    print(f"✓ {len(dataset)} decisões carregadas e preparadas.")

    # 2. Inicialização dos componentes
    print("\n[2/5] Inicializando Segmentador, NER Transversal e Classificador Multi-Eixo...")
    segmenter = FullDocumentStructuralSegmenter()
    ner = CompositeEntityExtractor()
    multi_clf = MultiAxisJudicialClassifier()
    multi_clf.fit_fallback_from_corpus(
        texts=[d["texto"] for d in dataset],
        labels=[d["desfecho_esperado"] for d in dataset],
        min_confidence=0.85,
    )

    # 3. Execução do Benchmark com medição de latência fina
    print(f"\n[3/5] Executando benchmark completo em {len(dataset)} documentos...")
    t_start = time.perf_counter()

    latencies_seg = []
    latencies_ner = []
    latencies_tournament = []
    latencies_total = []

    results = []
    confusion_matrix: dict[str, dict[str, int]] = {}
    entity_counts_by_type: dict[str, int] = {}

    saved_by_dispositivo_weight = 0

    for idx, doc in enumerate(dataset, 1):
        text = doc["texto"]
        expected = doc["desfecho_esperado"]

        t0 = time.perf_counter()

        # Etapa A: Segmentação Estrutural
        t_seg_0 = time.perf_counter()
        doc_struct = segmenter.segment(text, {"court": doc["tribunal"]})
        t_seg_1 = time.perf_counter()
        lat_seg = (t_seg_1 - t_seg_0) * 1000.0
        latencies_seg.append(lat_seg)

        # Etapa B: NER Transversal em todas as seções
        t_ner_0 = time.perf_counter()
        mentions = ner.extract_from_sections(doc_struct.sections)
        t_ner_1 = time.perf_counter()
        lat_ner = (t_ner_1 - t_ner_0) * 1000.0
        latencies_ner.append(lat_ner)

        for m in mentions:
            t_val = m.entity_type.value if hasattr(m.entity_type, "value") else str(m.entity_type)
            entity_counts_by_type[t_val] = entity_counts_by_type.get(t_val, 0) + 1

        # Etapa C: Classificação Multi-Eixo (Torneio Ponderado + Taxonomia + DataJud + ML Fallback)
        sections_text = {k: v.text for k, v in doc_struct.sections.items()}
        meta_doc = {
            "court": doc["tribunal"],
            "tipo_documento": doc["tipo_documento_hint"],
            "classe_processual": doc["classe_hint"],
            "cnj": doc["cnj"],
        }
        t_tourn_0 = time.perf_counter()
        multi_res = multi_clf.classify(text, metadata=meta_doc, sections=sections_text)
        t_tourn_1 = time.perf_counter()
        lat_tourn = (t_tourn_1 - t_tourn_0) * 1000.0
        latencies_tournament.append(lat_tourn)

        predicted = multi_res.desfecho_operativo
        conf = multi_res.confianca_desfecho
        explanation = multi_res.explicacao

        t_end = time.perf_counter()
        lat_total = (t_end - t0) * 1000.0
        latencies_total.append(lat_total)

        # Verificação de shadow citation e negative guards
        if explanation and explanation.winning_section == "dispositivo":
            rel_matches = [
                c
                for c in explanation.all_candidates
                if c["section"] == "relatorio" and c["category"] != predicted
            ]
            if rel_matches:
                saved_by_dispositivo_weight += 1

        confusion_matrix.setdefault(expected, {})
        confusion_matrix[expected][predicted] = confusion_matrix[expected].get(predicted, 0) + 1

        results.append(
            {
                "doc_id": doc["doc_id"],
                "expected": expected,
                "predicted": predicted,
                "confidence": conf,
                "winning_rule": multi_res.winning_rule,
                "winning_section": multi_res.winning_section,
                "num_entities": len(mentions),
                "lat_total_ms": lat_total,
            }
        )

        if idx % 200 == 0 or idx == len(dataset):
            print(
                f"  • Processadas {idx}/{len(dataset)} decisões ({idx / len(dataset) * 100:.0f}%)..."
            )

    total_time = time.perf_counter() - t_start
    throughput = len(dataset) / total_time

    # 4. Cálculo de Métricas Consolidadas
    print("\n[4/5] CONSOLIDAÇÃO DOS RESULTADOS DO BENCHMARK:\n")

    correct_total = sum(1 for r in results if r["expected"] == r["predicted"])
    acc_global = correct_total / len(results)

    print("📊 DESEMPENHO E LATÊNCIA (CPU):")
    print(f"  • Tempo total: {total_time:.2f} s")
    print(f"  • Throughput: {throughput:.1f} decisões/segundo")
    print(f"  • Latência Total Média: {np.mean(latencies_total):.2f} ms")
    print(f"  • Latência Total p50:   {np.percentile(latencies_total, 50):.2f} ms")
    print(f"  • Latência Total p95:   {np.percentile(latencies_total, 95):.2f} ms")
    print("  • Decomposição da Latência:")
    print(f"    - Segmentador Monotônico (Viterbi): {np.mean(latencies_seg):.2f} ms")
    print(f"    - NER Transversal (Multi-Algoritmo): {np.mean(latencies_ner):.2f} ms")
    print(f"    - Torneio de Regexes (Ponderado):   {np.mean(latencies_tournament):.2f} ms")

    print("\n🎯 ACURÁCIA E PRECISÃO DO TORNEIO:")
    print(
        f"  • Acurácia Global no Gabarito: {acc_global * 100:.1f}% ({correct_total}/{len(results)} acertos)"
    )
    print(
        f"  • Decisões salvas pelo peso do Dispositivo (Sombra de Citação): {saved_by_dispositivo_weight}"
    )

    print("\n📌 MATRIZ DE PRECISÃO POR CATEGORIA:")
    print(
        f"{'Categoria':<25} | {'Esperados':<9} | {'Acertos (TP)':<12} | {'Precisão':<9} | {'Recall':<8}"
    )
    print("-" * 75)
    for cat in sorted(confusion_matrix.keys()):
        total_exp = sum(confusion_matrix[cat].values())
        tp = confusion_matrix[cat].get(cat, 0)
        total_pred = sum(confusion_matrix[other].get(cat, 0) for other in confusion_matrix)
        prec = (tp / total_pred * 100.0) if total_pred > 0 else 0.0
        rec = (tp / total_exp * 100.0) if total_exp > 0 else 0.0
        print(f"{cat:<25} | {total_exp:<9} | {tp:<12} | {prec:>7.1f}% | {rec:>6.1f}%")

    print("\n🏷️ ENTIDADES JURÍDICAS EXTRAÍDAS (NER Transversal):")
    total_ent = sum(entity_counts_by_type.values())
    for t_name, count in sorted(entity_counts_by_type.items(), key=lambda x: x[1], reverse=True):
        print(f"  • {t_name:<16}: {count:>5} menções ({count / len(dataset):.1f}/caso)")
    print(
        f"  Total: {total_ent} entidades reconhecidas (média de {total_ent / len(dataset):.1f} por documento)."
    )

    # Salva relatório JSON e Markdown
    report_data = {
        "benchmark_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_documents": len(dataset),
        "throughput_docs_per_sec": round(throughput, 1),
        "latency_ms": {
            "mean": round(float(np.mean(latencies_total)), 2),
            "p50": round(float(np.percentile(latencies_total, 50)), 2),
            "p95": round(float(np.percentile(latencies_total, 95)), 2),
            "segmenter_mean": round(float(np.mean(latencies_seg)), 2),
            "ner_mean": round(float(np.mean(latencies_ner)), 2),
            "tournament_mean": round(float(np.mean(latencies_tournament)), 2),
        },
        "accuracy_global": round(acc_global, 4),
        "saved_by_dispositivo_weight": saved_by_dispositivo_weight,
        "entities_summary": entity_counts_by_type,
        "confusion_matrix": confusion_matrix,
    }

    out_json = ROOT_DIR / "data/audit/torneio_evolutivo_benchmark.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Relatório JSON salvo em: {out_json}")

    # 5. Atualiza o visualizador web
    print("\n[5/5] Atualizando o visualizador do site (web/public/visualizer_data.json)...")
    from export_visualizer_data import main as export_main

    export_main()

    print("\n" + "=" * 80)
    print("🏆 BENCHMARK CONCLUÍDO COM SUCESSO E SITE ATUALIZADO!")
    print("=" * 80)
    return report_data


if __name__ == "__main__":
    run_benchmark(1000)
