"""Exporta dados completos para o visualizador Antes e Depois no site CausaGanha.

Inclui segmentação estrutural (5 seções) e segmentação granular de entidades (NER):
- CNJs validados por Módulo 97
- Partes (Autor, Réu, Pessoas Físicas e Jurídicas)
- Representação jurídica (Advogados e OABs)
- Magistratura (Juiz / Relator prolator)
- Órgãos julgadores e Varas
- Impacto econômico (Valores da causa, condenação, honorários)
- Dispositivos normativos aplicados (CPC, CC, CDC, etc.)
- Datas processuais relevantes
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "scripts"))

from causaganha.decisoes.ner.composite import CompositeEntityExtractor
from causaganha.decisoes.ner.models import EntityRole, EntityType
from causaganha.decisoes.structural_segmenter import FullDocumentStructuralSegmenter
from classify_djen_sample_1000 import clean_html_if_present, load_1000_djen_sample


def main():
    print("Gerando dados para o Visualizador Interativo Antes e Depois com NER granular...")
    df_results = pd.read_csv(ROOT_DIR / "data/audit/classificacao_1000_djen.csv")
    sample_docs = load_1000_djen_sample(1000)
    doc_map = {d["doc_id"]: d for d in sample_docs}

    full_segmenter = FullDocumentStructuralSegmenter()
    ner_extractor = CompositeEntityExtractor()

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

        # 1. Segmenta em 5 seções canônicas
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

        # 2. Segmentação granular de entidades (Multi-Algorithm NER)
        mentions = ner_extractor.extract_from_sections(struct.sections, meta)
        mentions_payload = [m.to_dict() for m in mentions]

        # Resumo categorizado para consumo rápido da UI
        resumo_partes = []
        resumo_advogados = []
        resumo_magistrados = []
        resumo_valores = []
        resumo_normas = []
        resumo_cnjs = []
        resumo_orgaos = []
        resumo_datas = []

        autor_extraido = None
        reu_extraido = None
        advogado_extraido = None
        oab_extraida = None
        magistrado_extraido = None
        cnj_extraido = None

        for m in mentions:
            lit = m.literal.strip()
            role_val = m.role.value if hasattr(m.role, "value") else str(m.role)
            type_val = (
                m.entity_type.value if hasattr(m.entity_type, "value") else str(m.entity_type)
            )

            if type_val == EntityType.CNJ.value:
                if lit not in resumo_cnjs:
                    resumo_cnjs.append(lit)
                if not cnj_extraido:
                    cnj_extraido = lit
            elif type_val == EntityType.PESSOA.value:
                if role_val in {EntityRole.POLO_ATIVO.value, "POLO_ATIVO"}:
                    if not any(p["nome"] == lit for p in resumo_partes):
                        resumo_partes.append({"nome": lit, "polo": "ATIVO", "tipo": "PESSOA"})
                    if not autor_extraido:
                        autor_extraido = lit
                elif role_val in {EntityRole.POLO_PASSIVO.value, "POLO_PASSIVO"}:
                    if not any(p["nome"] == lit for p in resumo_partes):
                        resumo_partes.append({"nome": lit, "polo": "PASSIVO", "tipo": "PESSOA"})
                    if not reu_extraido:
                        reu_extraido = lit
                elif role_val in {EntityRole.ADVOGADO.value, "ADVOGADO"}:
                    if not any(a["nome"] == lit for a in resumo_advogados):
                        resumo_advogados.append({"nome": lit, "oab": None})
                    if not advogado_extraido:
                        advogado_extraido = lit
                elif role_val in {EntityRole.MAGISTRADO.value, "MAGISTRADO"}:
                    if lit not in resumo_magistrados:
                        resumo_magistrados.append(lit)
                    if not magistrado_extraido:
                        magistrado_extraido = lit
            elif type_val == EntityType.OAB.value:
                oab_fmt = (
                    m.normalized_value.formatado
                    if hasattr(m.normalized_value, "formatado")
                    else lit
                )
                adv_nome = (
                    getattr(m.normalized_value, "nome_advogado", None)
                    if hasattr(m.normalized_value, "nome_advogado")
                    else None
                )
                if not any(a.get("oab") == oab_fmt for a in resumo_advogados):
                    resumo_advogados.append({"nome": adv_nome or "Advogado", "oab": oab_fmt})
                if not oab_extraida:
                    oab_extraida = oab_fmt
                if adv_nome and not advogado_extraido:
                    advogado_extraido = adv_nome
            elif type_val == EntityType.ORGANIZACAO.value:
                if role_val in {
                    EntityRole.INSTITUICAO_FINANCEIRA.value,
                    EntityRole.PARTE_PJ.value,
                    EntityRole.EMPRESA_SERVICO_PUBLICO.value,
                }:
                    if not any(p["nome"] == lit for p in resumo_partes):
                        resumo_partes.append(
                            {"nome": lit, "polo": "PASSIVO/PJ", "tipo": "ORGANIZACAO"}
                        )
                    if not reu_extraido:
                        reu_extraido = lit
                elif role_val == EntityRole.ORGAO_JULGADOR.value:
                    if lit not in resumo_orgaos:
                        resumo_orgaos.append(lit)
            elif type_val == EntityType.VALOR.value:
                resumo_valores.append(
                    {
                        "literal": lit,
                        "papel": role_val,
                        "secao": m.section,
                    }
                )
            elif type_val == EntityType.NORMA.value:
                norm_str = (
                    m.normalized_value.canonical_string()
                    if hasattr(m.normalized_value, "canonical_string")
                    else lit
                )
                if norm_str not in resumo_normas:
                    resumo_normas.append(norm_str)
            elif type_val == EntityType.DATA.value:
                if lit not in resumo_datas:
                    resumo_datas.append(lit)

        resumo_entidades = {
            "total_entidades": len(mentions),
            "cnjs": resumo_cnjs,
            "partes_litigantes": resumo_partes,
            "advogados_oab": resumo_advogados,
            "magistrados": resumo_magistrados,
            "orgaos_julgadores": resumo_orgaos,
            "valores_identificados": resumo_valores,
            "normas_aplicadas": resumo_normas,
            "datas_relevantes": resumo_datas,
        }

        # Formata valores principais
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

        normas = row.get("normas_aplicadas")
        normas_str = (
            str(normas)
            if pd.notna(normas)
            else (", ".join(resumo_normas[:3]) if resumo_normas else None)
        )

        # Enriquecimento dos campos primários
        final_cnj = str(row["cnj"]) if pd.notna(row["cnj"]) else (cnj_extraido or "Não detectado")
        final_autor = (
            str(row["autor"])
            if (pd.notna(row["autor"]) and str(row["autor"]).strip() != "Não identificado")
            else (autor_extraido or "Não identificado")
        )
        final_reu = (
            str(row["reu"])
            if (pd.notna(row["reu"]) and str(row["reu"]).strip() != "Não identificado")
            else (reu_extraido or "Não identificado")
        )
        final_adv = (
            str(row["advogado"])
            if (pd.notna(row["advogado"]) and str(row["advogado"]).strip() != "Não identificado")
            else (advogado_extraido or "Não identificado")
        )
        final_oab = (
            str(row["oab"])
            if (pd.notna(row["oab"]) and str(row["oab"]).strip() != "Não identificada")
            else (oab_extraida or "Não identificada")
        )
        final_mag = (
            str(row["magistrado"])
            if (pd.notna(row["magistrado"]) and str(row["magistrado"]).strip() != "Não identificado")
            else (magistrado_extraido or "Não identificado")
        )

        visualizer_cases.append(
            {
                "id": idx,
                "doc_id": doc_id,
                "tribunal": str(row["tribunal"]) if pd.notna(row["tribunal"]) else "DJEN",
                "classe": str(row["classe_processual"])
                if pd.notna(row["classe_processual"])
                else "Sentença",
                "tipo_documento": str(row["tipo_documento"])
                if pd.notna(row["tipo_documento"])
                else "Sentença",
                "texto_bruto_djen": raw_text,
                "texto_limpo": clean_text,
                "secoes": sections_dict,
                "entidades": mentions_payload,
                "resumo_entidades": resumo_entidades,
                "total_entidades": len(mentions),
                "desfecho_cpc": str(row["desfecho_cpc"])
                if pd.notna(row["desfecho_cpc"])
                else "unknown",
                "confianca_desfecho": float(row["confianca_desfecho"])
                if pd.notna(row["confianca_desfecho"])
                else 0.0,
                "polo_vencedor": str(row["polo_vencedor"])
                if pd.notna(row["polo_vencedor"])
                else "unknown",
                "cnj": final_cnj,
                "autor": final_autor,
                "reu": final_reu,
                "advogado": final_adv,
                "oab": final_oab,
                "magistrado": final_mag,
                "valor_condenacao": val_cond_str,
                "valor_causa": val_causa_str,
                "taxa_sucesso_economico": taxa_str,
                "normas_aplicadas": normas_str,
                "latencia_total_ms": round(float(row["lat_total_ms"]), 2)
                if pd.notna(row.get("lat_total_ms"))
                else 20.0,
            }
        )

    # Grava JSON com validação estrita sem NaN
    out_public = ROOT_DIR / "web/public/visualizer_data.json"
    out_audit = ROOT_DIR / "data/audit/visualizer_data.json"
    out_public.parent.mkdir(parents=True, exist_ok=True)
    out_audit.parent.mkdir(parents=True, exist_ok=True)

    with open(out_public, "w", encoding="utf-8") as f:
        json.dump(visualizer_cases, f, ensure_ascii=False, indent=2, allow_nan=False)

    with open(out_audit, "w", encoding="utf-8") as f:
        json.dump(visualizer_cases, f, ensure_ascii=False, indent=2, allow_nan=False)

    total_mencoes = sum(c["total_entidades"] for c in visualizer_cases)
    print(f"✓ {len(visualizer_cases)} casos exportados com sucesso:")
    print(f"  • Total de entidades extraídas: {total_mencoes} (média {total_mencoes / len(visualizer_cases):.1f}/caso)")
    print(f"  • {out_public}")
    print(f"  • {out_audit}")


if __name__ == "__main__":
    main()
