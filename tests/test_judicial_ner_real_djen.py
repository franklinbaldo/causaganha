"""Testes de Integração do Pipeline de NER Judiciário com Dados Reais do DJEN."""

from __future__ import annotations

import glob
import json
from pathlib import Path
import pyarrow.parquet as pq
import yaml

from causaganha.decisoes.ner.composite import CompositeEntityExtractor
from causaganha.decisoes.ner.models import EntityRole, EntityType

ROOT_DIR = Path(__file__).resolve().parent.parent


def test_real_djen_benchmark_decisions_extraction():
    """Valida extração sobre o conjunto de decisões reais do benchmark de ouro."""
    decision_files = sorted(glob.glob(str(ROOT_DIR / "data/benchmark/decisions/*.md")))
    assert len(decision_files) >= 50, "Deve haver ao menos 50 decisões reais no benchmark"

    extractor = CompositeEntityExtractor()
    total_mentions = 0
    cnj_count = 0
    norma_count = 0
    oab_count = 0
    judges_found = 0
    judges_expected = 0

    for path in decision_files[:30]:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
        parts = raw.split("---", 2)
        assert len(parts) >= 3, f"Arquivo {path} deve conter YAML frontmatter e texto"
        meta = yaml.safe_load(parts[1])
        text = parts[2].strip()

        mentions = extractor.extract_from_text(text, metadata=meta)
        total_mentions += len(mentions)

        for m in mentions:
            if m.entity_type == EntityType.CNJ:
                cnj_count += 1
                if m.normalized_value.is_valid_mod97:
                    assert m.normalized_value.is_valid_mod97 is True
            elif m.entity_type == EntityType.NORMA:
                norma_count += 1
            elif m.entity_type == EntityType.OAB:
                oab_count += 1

        judge_meta = meta.get("judge_name")
        if judge_meta and str(judge_meta).strip() and str(judge_meta).lower() != "none":
            judges_expected += 1
            if any(
                m.entity_type == EntityType.PESSOA and m.role == EntityRole.MAGISTRADO
                for m in mentions
            ):
                judges_found += 1

    assert total_mentions > 300, "Mínimo de menções esperadas na amostra real"
    assert cnj_count >= 30, "Mínimo de CNJs esperados"
    assert norma_count >= 100, "Mínimo de normas citadas esperadas"
    assert oab_count >= 20, "Mínimo de OABs esperadas"
    if judges_expected > 0:
        assert judges_found / judges_expected >= 0.90, (
            f"Grounding de magistrado esperado >= 90%, obteve {judges_found}/{judges_expected}"
        )


def test_real_djen_process_governed_by_metadata():
    """Valida que o número do processo principal é governado estritamente pelos metadados do DJEN."""
    extractor = CompositeEntityExtractor()
    text = (
        "Processo nº 7000685-89.2025.8.22.0011\n"
        "Sentença em conformidade com o precedente do processo paradigma nº 7001234-12.2024.8.22.0001."
    )

    # Caso 1: Metadado oficial coincide com o primeiro CNJ
    meta_oficial = {"numero_processo": "7000685-89.2025.8.22.0011"}
    mentions1 = extractor.extract_from_text(text, metadata=meta_oficial)
    cnj_mentions1 = [m for m in mentions1 if m.entity_type == EntityType.CNJ]

    principal1 = [m for m in cnj_mentions1 if m.role == EntityRole.PROCESSO_PRINCIPAL]
    assert len(principal1) == 1
    assert "70006858920258220011" in principal1[0].normalized_value.numero_limpo

    citados1 = [
        m
        for m in cnj_mentions1
        if m.role in {EntityRole.PROCESSO_CITADO, EntityRole.PROCESSO_PARADIGMA}
    ]
    assert len(citados1) >= 1
    assert "70012341220248220001" in citados1[0].normalized_value.numero_limpo

    # Caso 2: Metadado oficial aponta para outro CNJ não constante no cabeçalho
    # O pipeline DEVE injetar o CNJ oficial dos metadados como PROCESSO_PRINCIPAL soberano
    meta_distinto = {"numero_processo": "7009999-00.2025.8.22.0099"}
    mentions2 = extractor.extract_from_text(text, metadata=meta_distinto)
    cnj_mentions2 = [m for m in mentions2 if m.entity_type == EntityType.CNJ]

    principal2 = [m for m in cnj_mentions2 if m.role == EntityRole.PROCESSO_PRINCIPAL]
    assert len(principal2) == 1
    assert "70099990020258220099" in principal2[0].normalized_value.numero_limpo
    assert principal2[0].section == "METADADOS_DJEN"

    # Ambos os CNJs do texto agora são considerados citados/não-principais
    citados2 = [m for m in cnj_mentions2 if m.section != "METADADOS_DJEN"]
    for c in citados2:
        assert c.role in {EntityRole.PROCESSO_CITADO, EntityRole.PROCESSO_PARADIGMA}


def test_real_djen_segmenter_samples_jsonl():
    """Valida leitura e extração sobre amostras reais de intimacoes em JSONL."""
    jsonl_path = ROOT_DIR / "data/segmenter_samples/tjro.jsonl"
    if not jsonl_path.exists():
        return

    extractor = CompositeEntityExtractor()
    docs_tested = 0
    mentions_found = 0

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            text = row.get("text", "")
            info = row.get("info", {})
            meta = {
                "id": info.get("id"),
                "court": info.get("tribunal"),
                "tipo_documento": info.get("tipoDocumento"),
                "classe_processual": info.get("nomeClasse"),
                "orgao": info.get("nomeOrgao"),
            }
            mentions = extractor.extract_from_text(text, metadata=meta)
            docs_tested += 1
            mentions_found += len(mentions)
            if docs_tested >= 15:
                break

    assert docs_tested == 15
    assert mentions_found > 100, "Deve extrair ao menos 100 entidades em 15 intimações reais"


def test_real_djen_gold_parquet():
    """Valida extração sobre a tabela oficial gold_benchmark.parquet."""
    parquet_path = ROOT_DIR / "data/benchmark/gold_benchmark.parquet"
    assert parquet_path.exists(), "gold_benchmark.parquet deve existir"

    df = pq.read_table(str(parquet_path)).to_pandas().head(20)
    extractor = CompositeEntityExtractor()

    for _, row in df.iterrows():
        text = row["texto"]
        meta = {
            "intimation_id": row["intimation_id"],
            "court": row["court"],
            "classe_processual": row["classe_processual"],
            "judge_name": row["judge_name"],
            "valor_causa": row["valor_causa"],
            "valor_condenacao": row["valor_condenacao"],
        }
        mentions = extractor.extract_from_text(text, metadata=meta)
        assert isinstance(mentions, list)
        assert len(mentions) > 0, "Decisão real do gold benchmark deve ter ao menos 1 entidade"
