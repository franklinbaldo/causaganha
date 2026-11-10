"""Pipeline de Classificação e Extração sobre Amostra de 1.000 Documentos Reais do DJEN.

Executa o pipeline completo (Segmentador + NER + Classificador + Recurso Resolver):
1. Amostra 1.000 decisões reais de múltiplos tribunais.
2. Segmenta seções (Cabeçalho, Fundamentação, Dispositivo, Encerramento).
3. Classifica desfecho e resolve polo vencedor invariante (CPC art. 1.008).
4. Extrai CNJ Módulo 97, Partes, Advogados, OAB, Juiz, Valores e Normas.
5. Computa taxa contínua de êxito econômico (Condenação / Causa).
6. Salva resultados em CSV e Parquet para auditoria pessoal do usuário.
"""

from __future__ import annotations

import argparse
import glob
import html
import json
from pathlib import Path
import re
import time
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from causaganha.decisoes.hybrid_segmenter import HybridDispositifSegmenter
from causaganha.decisoes.multi_axis import MultiAxisJudicialClassifier
from causaganha.decisoes.ner.composite import CompositeEntityExtractor
from causaganha.decisoes.ner.models import EntityRole, EntityType
from causaganha.decisoes.structural_segmenter import FullDocumentStructuralSegmenter

ROOT_DIR = Path(__file__).resolve().parent.parent


def clean_html_if_present(text: str) -> str:
    """Limpa markup HTML se presente preservando quebras de linha essenciais."""
    if not text:
        return ""
    if re.search(
        r"<(?:b|p|div|html|body|table|tr|td|article|section|span|br|header|footer)\b|&[a-z]{2,8};",
        text,
        re.IGNORECASE,
    ):
        text = html.unescape(text)
        text = re.sub(
            r"<(?:br|p|div|header|section|footer|h\d|tr)[^>]*>", "\n", text, flags=re.IGNORECASE
        )
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n+", "\n\n", text)
        return text.strip()
    return text


def load_1000_djen_sample(limit: int = 1000) -> list[dict]:
    """Carrega 1.000 documentos reais distribuídos entre múltiplos tribunais do DJEN."""
    docs: list[dict] = []

    # Fonte A: data/segmenter_samples/*.jsonl (dados com info de tribunal e metadados)
    jsonl_files = sorted(glob.glob(str(ROOT_DIR / "data/segmenter_samples/*.jsonl")))
    for jf in jsonl_files:
        if "annotation" in jf:
            continue
        with open(jf, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                row = json.loads(line)
                info = row.get("info", {})
                raw_text = row.get("text", "")
                clean_text = clean_html_if_present(raw_text)
                if not clean_text:
                    continue
                docs.append(
                    {
                        "doc_id": info.get("id") or f"jsonl_{len(docs)}",
                        "court": info.get("tribunal") or "DJEN",
                        "tipo_documento_hint": info.get("tipoDocumento") or "Sentença",
                        "classe_hint": info.get("nomeClasse") or "",
                        "orgao": info.get("nomeOrgao") or "",
                        "texto": clean_text,
                        "source": Path(jf).name,
                    }
                )
                if len(docs) >= limit:
                    return docs

    # Fonte B: data/benchmark/ia_expanded_decisions.parquet
    expanded_path = ROOT_DIR / "data/benchmark/ia_expanded_decisions.parquet"
    if expanded_path.exists() and len(docs) < limit:
        df_exp = pq.read_table(str(expanded_path)).to_pandas()
        for _, r in df_exp.iterrows():
            if len(docs) >= limit:
                break
            raw_t = str(r.get("texto") or "")
            clean_t = clean_html_if_present(raw_t)
            if not clean_t:
                continue
            docs.append(
                {
                    "doc_id": str(r.get("id")),
                    "court": "TJRO",
                    "tipo_documento_hint": str(r.get("document_type") or "Sentença"),
                    "classe_hint": str(r.get("procedural_class") or ""),
                    "orgao": "",
                    "texto": clean_t,
                    "source": "ia_expanded_decisions.parquet",
                }
            )

    # Se ainda faltar para o limite, complementa de tjba_textos.parquet
    if len(docs) < limit:
        tjba_path = ROOT_DIR / "data/ia_parquets/tjba_textos.parquet"
        if tjba_path.exists():
            df_ba = pq.read_table(str(tjba_path)).to_pandas()
            for _, r in df_ba.iterrows():
                if len(docs) >= limit:
                    break
                raw_t = str(r.get("texto") or "")
                clean_t = clean_html_if_present(raw_t)
                if not clean_t:
                    continue
                docs.append(
                    {
                        "doc_id": str(r.get("id")),
                        "court": "TJBA",
                        "tipo_documento_hint": "Sentença",
                        "classe_hint": "",
                        "orgao": "",
                        "texto": clean_t,
                        "source": "tjba_textos.parquet",
                    }
                )

    return docs[:limit]


def run_pipeline_on_sample(limit: int = 1000):
    print("=" * 80)
    print(f"EXECUTANDO PIPELINE COMPLETO SOBRE AMOSTRA DE {limit} DOCUMENTOS REAIS DO DJEN")
    print("=" * 80)

    t0_load = time.perf_counter()
    sample = load_1000_djen_sample(limit)
    print(f"✓ {len(sample)} documentos carregados em {time.perf_counter() - t0_load:.2f}s.")

    # 1. Inicialização dos componentes de produção do pipeline
    full_segmenter = FullDocumentStructuralSegmenter()
    hybrid_segmenter = HybridDispositifSegmenter()
    prod_model = ROOT_DIR / "models/hybrid_dispositif_forest.joblib"
    if prod_model.exists():
        hybrid_segmenter.load(prod_model)
        print(f"✓ Modelo Random Forest carregado de {prod_model.name}.")

    extractor = CompositeEntityExtractor()
    multi_classifier = MultiAxisJudicialClassifier()

    results: list[dict] = []
    sample_cases: list[dict] = []
    lat_seg_list: list[float] = []
    lat_ner_list: list[float] = []
    lat_clf_list: list[float] = []
    lat_total_list: list[float] = []

    print(
        "\nExecutando inferência completa (Segmentação 5-seções + NER Seccional + Classificação Multi-Eixo)..."
    )
    t0_exec = time.perf_counter()

    for idx, doc in enumerate(sample, start=1):
        st_total = time.perf_counter()
        text = doc["texto"]
        court = doc["court"]
        meta_in = {
            "court": court,
            "tipo_documento": doc["tipo_documento_hint"],
            "classe_processual": doc["classe_hint"],
            "id": doc["doc_id"],
        }

        # --- ETAPA 1: Segmentação Estrutural Completa (5 seções canônicas) ---
        st_seg = time.perf_counter()
        doc_struct = full_segmenter.segment(text, metadata=meta_in)
        # Refinamento de dispositivo com Random Forest
        rf_res = hybrid_segmenter.predict(text, metadata=meta_in)
        lat_seg = (time.perf_counter() - st_seg) * 1000.0
        lat_seg_list.append(lat_seg)

        # Determina texto do dispositivo com máxima acurácia
        disp_span = doc_struct.sections.get("dispositivo")
        if rf_res.snippet and len(rf_res.snippet.strip()) > 20:
            disp_text = rf_res.snippet
        elif rf_res.start < rf_res.end and (rf_res.end - rf_res.start) > 20:
            disp_text = text[rf_res.start : rf_res.end]
        elif disp_span and len(disp_span.text.strip()) > 20:
            disp_text = disp_span.text
        else:
            disp_text = ""

        has_disp = bool(disp_text.strip())

        # Métricas de Seções
        sec_names = [s.upper() for s in doc_struct.sections.keys()]
        sec_str = " | ".join(sec_names)

        # --- ETAPA 2: Classificação Multi-Eixo (Taxonomia + Torneio Ponderado) ---
        st_clf = time.perf_counter()
        sec_dict_text = {k: v.text for k, v in doc_struct.sections.items()}
        if has_disp and "dispositivo" not in sec_dict_text:
            sec_dict_text["dispositivo"] = disp_text

        multi_res = multi_classifier.classify(
            text,
            metadata=meta_in,
            sections=sec_dict_text,
        )
        raw_outcome = multi_res.desfecho_operativo
        outcome_conf = multi_res.confianca_desfecho
        winner_polo = multi_res.polo_vencedor

        lat_clf = (time.perf_counter() - st_clf) * 1000.0
        lat_clf_list.append(lat_clf)

        # --- ETAPA 3: Multi-Algorithm NER Seccional ---
        st_ner = time.perf_counter()
        mentions = extractor.extract_from_sections(doc_struct.sections, metadata=meta_in)
        lat_ner = (time.perf_counter() - st_ner) * 1000.0
        lat_ner_list.append(lat_ner)

        # Resolução de entidades
        cnj_principal = None
        autor_nome = None
        reu_nome = None
        advogado_nome = None
        oab_formatada = None
        juiz_nome = None
        valor_causa = None
        valor_condenacao = None
        honorarios_val = None
        normas_principais = []

        for m in mentions:
            if (
                m.entity_type == EntityType.CNJ
                and m.role == EntityRole.PROCESSO_PRINCIPAL
                and not cnj_principal
            ):
                cnj_principal = (
                    m.normalized_value.numero_formatado
                    if hasattr(m.normalized_value, "numero_formatado")
                    else m.literal
                )
            elif (
                m.entity_type == EntityType.PESSOA
                and m.role == EntityRole.POLO_ATIVO
                and not autor_nome
            ):
                autor_nome = (
                    m.normalized_value.nome if hasattr(m.normalized_value, "nome") else m.literal
                )
            elif (
                m.entity_type == EntityType.PESSOA
                and m.role == EntityRole.POLO_PASSIVO
                and not reu_nome
            ):
                reu_nome = (
                    m.normalized_value.nome if hasattr(m.normalized_value, "nome") else m.literal
                )
            elif (
                m.entity_type == EntityType.OAB
                and m.role == EntityRole.ADVOGADO
                and not oab_formatada
            ):
                oab_formatada = (
                    m.normalized_value.formatado
                    if hasattr(m.normalized_value, "formatado")
                    else m.literal
                )
                if hasattr(m.normalized_value, "nome_advogado") and not advogado_nome:
                    advogado_nome = m.normalized_value.nome_advogado
            elif (
                m.entity_type == EntityType.PESSOA
                and m.role == EntityRole.MAGISTRADO
                and not juiz_nome
            ):
                juiz_nome = (
                    m.normalized_value.nome if hasattr(m.normalized_value, "nome") else m.literal
                )
            elif (
                m.entity_type == EntityType.VALOR
                and m.role == EntityRole.VALOR_DA_CAUSA
                and not valor_causa
            ):
                if (
                    hasattr(m.normalized_value, "is_percentage")
                    and not m.normalized_value.is_percentage
                ):
                    valor_causa = m.normalized_value.amount
            elif (
                m.entity_type == EntityType.VALOR
                and m.role == EntityRole.VALOR_CONDENACAO_PRINCIPAL
                and not valor_condenacao
            ):
                if (
                    hasattr(m.normalized_value, "is_percentage")
                    and not m.normalized_value.is_percentage
                ):
                    valor_condenacao = m.normalized_value.amount
            elif (
                m.entity_type == EntityType.VALOR
                and m.role == EntityRole.VALOR_HONORARIOS
                and not honorarios_val
            ):
                honorarios_val = m.literal
            elif m.entity_type == EntityType.NORMA and len(normas_principais) < 3:
                canonical = (
                    m.normalized_value.canonical_string()
                    if hasattr(m.normalized_value, "canonical_string")
                    else m.literal
                )
                if canonical not in normas_principais:
                    normas_principais.append(canonical)

        # Métrica Econômica Contínua de Sucesso
        taxa_sucesso = None
        if valor_causa and valor_causa > 0 and valor_condenacao is not None:
            taxa_sucesso = round(
                min(1.0, max(0.0, float(valor_condenacao) / float(valor_causa))), 4
            )

        lat_total = (time.perf_counter() - st_total) * 1000.0
        lat_total_list.append(lat_total)

        row_res = {
            "indice": idx,
            "doc_id": doc["doc_id"],
            "tribunal": court,
            "topologia": multi_res.macro_categoria,
            "classe_processual": doc["classe_hint"] or "Não especificada",
            "tipo_documento": multi_res.especie_ato,
            "macro_categoria": multi_res.macro_categoria,
            "especie_ato": multi_res.especie_ato,
            "secoes_detectadas": sec_str,
            "num_secoes": len(doc_struct.sections),
            "has_dispositivo": has_disp,
            "chars_cabecalho": len(doc_struct.sections.get("cabecalho").text)
            if doc_struct.sections.get("cabecalho")
            else 0,
            "chars_fundamentacao": len(doc_struct.sections.get("fundamentacao").text)
            if doc_struct.sections.get("fundamentacao")
            else (
                len(doc_struct.sections.get("voto").text) if doc_struct.sections.get("voto") else 0
            ),
            "chars_dispositivo": len(disp_text),
            "chars_encerramento": len(doc_struct.sections.get("encerramento").text)
            if doc_struct.sections.get("encerramento")
            else 0,
            "dispositivo_snippet": disp_text[:140].replace("\n", " ").strip() + "..."
            if disp_text
            else "N/A",
            "desfecho_cpc": raw_outcome,
            "confianca_desfecho": round(outcome_conf, 2),
            "polo_vencedor": winner_polo,
            "cnj": cnj_principal or "Não detectado",
            "autor": autor_nome or "Não identificado",
            "reu": reu_nome or "Não identificado",
            "advogado": advogado_nome or "Não identificado",
            "oab": oab_formatada or "Não identificada",
            "magistrado": juiz_nome or "Não identificado",
            "valor_causa": valor_causa,
            "valor_condenacao": valor_condenacao,
            "taxa_sucesso_economico": taxa_sucesso,
            "normas_aplicadas": " | ".join(normas_principais) if normas_principais else "N/A",
            "lat_seg_ms": round(lat_seg, 2),
            "lat_ner_ms": round(lat_ner, 2),
            "lat_clf_ms": round(lat_clf, 2),
            "lat_total_ms": round(lat_total, 2),
        }
        results.append(row_res)

        # Salva amostras ricas para inspeção profunda do usuário
        if len(sample_cases) < 50:
            sample_cases.append(
                {
                    "indice": idx,
                    "doc_id": doc["doc_id"],
                    "tribunal": court,
                    "desfecho_cpc": raw_outcome,
                    "polo_vencedor": winner_polo,
                    "cnj": cnj_principal,
                    "autor": autor_nome,
                    "reu": reu_nome,
                    "advogado": advogado_nome,
                    "oab": oab_formatada,
                    "magistrado": juiz_nome,
                    "valor_causa": valor_causa,
                    "valor_condenacao": valor_condenacao,
                    "taxa_sucesso": taxa_sucesso,
                    "secoes": {k: v.text[:300] for k, v in doc_struct.sections.items()},
                    "dispositivo_completo": disp_text[:600],
                }
            )

        if idx % 200 == 0 or idx == limit:
            print(
                f"  .. {idx}/{limit} docs processados ({idx / (time.perf_counter() - t0_exec):.1f} doc/s | latência média: {np.mean(lat_total_list):.1f}ms)"
            )

    elap_total = time.perf_counter() - t0_exec
    throughput = len(sample) / max(elap_total, 0.001)

    df_res = pd.DataFrame(results)

    # -------------------------------------------------------------
    # Salvando em Parquet, CSV e JSON para análise pessoal
    # -------------------------------------------------------------
    out_dir = ROOT_DIR / "data/audit"
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_path = out_dir / "classificacao_1000_djen.csv"
    parquet_path = out_dir / "classificacao_1000_djen.parquet"
    cases_json_path = out_dir / "classificacao_1000_djen_sample_cases.json"

    df_res.to_csv(csv_path, index=False, encoding="utf-8-sig")
    df_res.to_parquet(parquet_path, index=False)
    with open(cases_json_path, "w", encoding="utf-8") as f:
        json.dump(sample_cases, f, ensure_ascii=False, indent=2)

    # -------------------------------------------------------------
    # Métricas de Telemetria e Qualidade
    # -------------------------------------------------------------
    p50 = np.percentile(lat_total_list, 50)
    p90 = np.percentile(lat_total_list, 90)
    p95 = np.percentile(lat_total_list, 95)
    p99 = np.percentile(lat_total_list, 99)

    print("\n" + "=" * 80)
    print("RESUMO EXECUTIVO: AUDITORIA DO PIPELINE COMPLETO (1.000 DOCUMENTOS DJEN)")
    print("=" * 80)
    print(f"Tempo total de execução : {elap_total:.2f} s")
    print(f"Throughput alcançado    : {throughput:.1f} documentos / segundo")
    print(f"Latência P50 (mediana)  : {p50:.2f} ms")
    print(f"Latência P90            : {p90:.2f} ms")
    print(f"Latência P95            : {p95:.2f} ms")
    print(f"Latência P99            : {p99:.2f} ms")
    print(f"Tempo médio Segmentação : {np.mean(lat_seg_list):.2f} ms")
    print(f"Tempo médio NER         : {np.mean(lat_ner_list):.2f} ms")
    print(f"Tempo médio Desfecho    : {np.mean(lat_clf_list):.2f} ms")

    print("\nArquivos de auditoria gravados no disco:")
    print(f"  • Planilha CSV (Excel)  : {csv_path}")
    print(f"  • Tabela Parquet        : {parquet_path}")
    print(f"  • 50 Casos Detalhados   : {cases_json_path}")

    # Distribuição de Desfechos
    print("\n--- 1. DISTRIBUIÇÃO DE DESFECHOS PROCESSUAIS (CPC 2015) ---")
    outcomes_vc = df_res["desfecho_cpc"].value_counts()
    for o, c in outcomes_vc.items():
        print(f"  • {o:<30}: {c:>4d} ({c / len(df_res) * 100:>5.1f}%)")

    # Distribuição de Polo Vencedor
    print("\n--- 2. POLO VENCEDOR INVARIANTE (CPC ART. 1.008) ---")
    winner_vc = df_res["polo_vencedor"].value_counts()
    for w, c in winner_vc.items():
        label = {
            "A": "Polo Ativo (Autor / Exequente)",
            "P": "Polo Passivo (Réu / Executado)",
            "draw": "Empate / Sucumbência Recíproca / Acordo",
            "unknown": "Não Ratificável (Terminativa / Despacho)",
        }.get(w, w)
        print(f"  • Polo {w:<7} ({label:<40}): {c:>4d} ({c / len(df_res) * 100:>5.1f}%)")

    # Cobertura Seccional
    print("\n--- 3. TAXAS DE SEGMENTAÇÃO ESTRUTURAL (5 SEÇÕES) ---")
    has_cab = (df_res["chars_cabecalho"] > 0).sum()
    has_fund = (df_res["chars_fundamentacao"] > 0).sum()
    has_disp = (df_res["chars_dispositivo"] > 0).sum()
    has_enc = (df_res["chars_encerramento"] > 0).sum()
    full_5_sec = (
        (df_res["chars_cabecalho"] > 0)
        & (df_res["chars_fundamentacao"] > 0)
        & (df_res["chars_dispositivo"] > 0)
        & (df_res["chars_encerramento"] > 0)
    ).sum()

    print(f"  • Cabeçalho identificado     : {has_cab:>4d} ({has_cab / len(df_res) * 100:.1f}%)")
    print(f"  • Fundamentação/Voto isolada : {has_fund:>4d} ({has_fund / len(df_res) * 100:.1f}%)")
    print(f"  • Dispositivo isolado        : {has_disp:>4d} ({has_disp / len(df_res) * 100:.1f}%)")
    print(f"  • Encerramento isolado       : {has_enc:>4d} ({has_enc / len(df_res) * 100:.1f}%)")
    print(
        f"  • Estrutura Canônica Completa: {full_5_sec:>4d} ({full_5_sec / len(df_res) * 100:.1f}%)"
    )

    # Cobertura de Entidades
    cnj_found = (df_res["cnj"] != "Não detectado").sum()
    autor_found = (df_res["autor"] != "Não identificado").sum()
    reu_found = (df_res["reu"] != "Não identificado").sum()
    adv_found = (df_res["advogado"] != "Não identificado").sum()
    oab_found = (df_res["oab"] != "Não identificada").sum()
    juiz_found = (df_res["magistrado"] != "Não identificado").sum()
    causa_found = df_res["valor_causa"].notna().sum()
    cond_found = df_res["valor_condenacao"].notna().sum()
    ratio_found = df_res["taxa_sucesso_economico"].notna().sum()

    print("\n--- 4. EXTRAÇÃO DE ENTIDADES E MÉTRICAS ECONÔMICAS ---")
    print(
        f"  • Processo CNJ (Módulo 97)   : {cnj_found:>4d} ({cnj_found / len(df_res) * 100:.1f}%)"
    )
    print(
        f"  • Polo Ativo identificado    : {autor_found:>4d} ({autor_found / len(df_res) * 100:.1f}%)"
    )
    print(
        f"  • Polo Passivo identificado  : {reu_found:>4d} ({reu_found / len(df_res) * 100:.1f}%)"
    )
    print(
        f"  • Advogados identificados    : {adv_found:>4d} ({adv_found / len(df_res) * 100:.1f}%)"
    )
    print(
        f"  • Inscrições OAB identificadas: {oab_found:>4d} ({oab_found / len(df_res) * 100:.1f}%)"
    )
    print(
        f"  • Magistrados identificados  : {juiz_found:>4d} ({juiz_found / len(df_res) * 100:.1f}%)"
    )
    print(
        f"  • Valor da Causa identificado: {causa_found:>4d} ({causa_found / len(df_res) * 100:.1f}%)"
    )
    print(
        f"  • Condenação Principal       : {cond_found:>4d} ({cond_found / len(df_res) * 100:.1f}%)"
    )
    print(
        f"  • Taxa Sucesso Econômico     : {ratio_found:>4d} ({ratio_found / len(df_res) * 100:.1f}%)"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Classifica amostra de 1.000 documentos do DJEN")
    parser.add_argument(
        "--limit", type=int, default=1000, help="Quantidade de documentos (default: 1000)"
    )
    args = parser.parse_args()
    run_pipeline_on_sample(limit=args.limit)
