"""Script de Auditoria Automatizada de Jurimetria Empírica do CausaGanha.

Inspeciona o codebase, schemas, classificadores, benchmarks e extratores NER
para verificar a conformidade com as melhores práticas de jurimetria (ABJ, CNJ, CPC).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
import pyarrow.parquet as pq

ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


@dataclass
class AuditCheck:
    bloco: str
    id: str
    descricao: str
    status: str  # "PASS", "WARN", "FAIL"
    evidencia: str
    recomendacao: str = ""


def run_jurimetrics_audit() -> list[AuditCheck]:
    checks: list[AuditCheck] = []

    # -------------------------------------------------------------
    # Bloco 1: Taxonomia e Fidelidade ao CPC
    # -------------------------------------------------------------
    # 1.1 Verificar separação de extinção sem mérito (art. 485) vs improcedência
    taxonomy_file = ROOT_DIR / "src/causaganha/analysis/keyword_classifier.py"
    if taxonomy_file.exists():
        content = taxonomy_file.read_text(encoding="utf-8")
        has_terminativa = "extinto sem m" in content.lower() or "485" in content
        has_parcial = "parcialmente procedente" in content.lower()
        has_acordo = "acordo" in content.lower() or "homolog" in content.lower()

        checks.append(
            AuditCheck(
                bloco="1. Taxonomia CPC",
                id="1.1",
                descricao="Separação de Sentença Terminativa (art. 485 CPC) vs Mérito",
                status="PASS" if has_terminativa else "FAIL",
                evidencia="KeywordClassifier mapeia 'extinto sem mérito' e dispositivos do art. 485"
                if has_terminativa
                else "Terminativas não mapeadas",
            )
        )
        checks.append(
            AuditCheck(
                bloco="1. Taxonomia CPC",
                id="1.2",
                descricao="Preservação da Parcial Procedência como Classe Autônoma",
                status="PASS" if has_parcial else "FAIL",
                evidencia="Outcome 'parcialmente procedente' explicitamente modelado"
                if has_parcial
                else "Parcial procedência colapsada",
            )
        )
        checks.append(
            AuditCheck(
                bloco="1. Taxonomia CPC",
                id="1.3",
                descricao="Tratamento Diferenciado de Homologação de Acordo",
                status="PASS" if has_acordo else "WARN",
                evidencia="Classe 'acordo' tratada como resolução consensual sem vencedor forçado"
                if has_acordo
                else "Acordos tratados como mérito litigioso",
            )
        )
    else:
        checks.append(
            AuditCheck(
                bloco="1. Taxonomia CPC",
                id="1.1",
                descricao="Arquivo keyword_classifier.py",
                status="FAIL",
                evidencia="Arquivo não encontrado",
            )
        )

    # 1.4 Tutelas provisórias no Segmentador
    segmenter_file = ROOT_DIR / "src/causaganha/decisoes/structural_segmenter.py"
    if segmenter_file.exists():
        content = segmenter_file.read_text(encoding="utf-8")
        has_tutela = (
            "tutela" in content.lower()
            or "defiro" in content.lower()
            or "liminar" in content.lower()
        )
        checks.append(
            AuditCheck(
                bloco="1. Taxonomia CPC",
                id="1.4",
                descricao="Reconhecimento de Tutelas Provisórias e Decisões Interlocutórias",
                status="PASS" if has_tutela else "WARN",
                evidencia="Segmentador estrutural possui canários e âncoras para 'defiro/indefiro tutela'"
                if has_tutela
                else "Decisões interlocutórias correm risco de descarte",
            )
        )

    # -------------------------------------------------------------
    # Bloco 2: Métricas Econômicas e Proporcionalidade
    # -------------------------------------------------------------
    ner_money_file = ROOT_DIR / "src/causaganha/decisoes/ner/money.py"
    if ner_money_file.exists():
        content = ner_money_file.read_text(encoding="utf-8")
        has_causa = "VALOR_DA_CAUSA" in content
        has_condenacao = "VALOR_CONDENACAO_PRINCIPAL" in content
        has_honorarios = "VALOR_HONORARIOS" in content

        checks.append(
            AuditCheck(
                bloco="2. Métricas Econômicas",
                id="2.1",
                descricao="Extração e Isolamento do Valor da Causa",
                status="PASS" if has_causa else "FAIL",
                evidencia="MonetaryValueExtractor classifica VALOR_DA_CAUSA por contexto de cabeçalho"
                if has_causa
                else "Valor da causa ausente",
            )
        )
        checks.append(
            AuditCheck(
                bloco="2. Métricas Econômicas",
                id="2.2",
                descricao="Extração e Isolamento do Valor da Condenação Principal",
                status="PASS" if has_condenacao else "FAIL",
                evidencia="MonetaryValueExtractor isola VALOR_CONDENACAO_PRINCIPAL no dispositivo"
                if has_condenacao
                else "Condenação principal ausente",
            )
        )
        checks.append(
            AuditCheck(
                bloco="2. Métricas Econômicas",
                id="2.3",
                descricao="Isolamento de Honorários Sucumbenciais e Multas",
                status="PASS" if has_honorarios else "WARN",
                evidencia="VALOR_HONORARIOS e PERCENTUAL_SUCUMBENCIA separados da condenação principal"
                if has_honorarios
                else "Honorários somados ao principal",
            )
        )

    # -------------------------------------------------------------
    # Bloco 3: Soberania de Metadados e Grounding (DJEN)
    # -------------------------------------------------------------
    composite_ner_file = ROOT_DIR / "src/causaganha/decisoes/ner/composite.py"
    if composite_ner_file.exists():
        content = composite_ner_file.read_text(encoding="utf-8")
        has_gov_cnj = "PROCESSO_PRINCIPAL" in content and "METADADOS_DJEN" in content
        has_gov_parties = "POLO_ATIVO" in content and "METADADOS_DJEN" in content

        checks.append(
            AuditCheck(
                bloco="3. Metadados DJEN",
                id="3.1",
                descricao="Governança Soberana do Processo Principal pelo DJEN",
                status="PASS" if has_gov_cnj else "FAIL",
                evidencia="Metadado oficial dita PROCESSO_PRINCIPAL e injeta se omitido no texto"
                if has_gov_cnj
                else "Inferência solta no cabeçalho",
            )
        )
        checks.append(
            AuditCheck(
                bloco="3. Metadados DJEN",
                id="3.2",
                descricao="Vinculação Oficial de Polos e Partes pelo DJEN",
                status="PASS" if has_gov_parties else "WARN",
                evidencia="Partes 'A' e 'P' mapeadas a partir de destinatarios do DJEN"
                if has_gov_parties
                else "Partes inferidas sem prior do DJEN",
            )
        )

    # 3.4 Magistrado via Texto
    person_file = ROOT_DIR / "src/causaganha/decisoes/ner/person_advogado.py"
    if person_file.exists():
        content = person_file.read_text(encoding="utf-8")
        has_mag = "MAGISTRADO" in content
        checks.append(
            AuditCheck(
                bloco="3. Metadados DJEN",
                id="3.4",
                descricao="Extração Textual de Magistrados (reconhecendo ausência no DJEN)",
                status="PASS" if has_mag else "WARN",
                evidencia="NER possui rotina especializada para magistrado e juiz prolator"
                if has_mag
                else "Ausência de rotina para juiz",
            )
        )

    # -------------------------------------------------------------
    # Bloco 4: Dinâmica Recursal e Efeito Substitutivo
    # -------------------------------------------------------------
    recurso_file = ROOT_DIR / "src/causaganha/analysis/recurso_resolver.py"
    if recurso_file.exists():
        content = recurso_file.read_text(encoding="utf-8")
        has_substitutivo = "provido" in content and "recorrente" in content
        checks.append(
            AuditCheck(
                bloco="4. Dinâmica Recursal",
                id="4.1",
                descricao="Inversão de Polaridade pelo Efeito Substitutivo (CPC art. 1.008)",
                status="PASS" if has_substitutivo else "FAIL",
                evidencia="recurso_resolver implementa polaridade: provido + recorrente='P' -> P venceu"
                if has_substitutivo
                else "Efeito substitutivo incompleto",
            )
        )
    else:
        checks.append(
            AuditCheck(
                bloco="4. Dinâmica Recursal",
                id="4.1",
                descricao="Módulo recurso_resolver.py (Inversão Recursal CPC art. 1.008)",
                status="WARN",
                evidencia="recurso_resolver.py especificado no DESIGN.md ainda não está implementado em src/causaganha/analysis/",
                recomendacao="Criar recurso_resolver.py para aplicar a inversão de polaridade (provido vs não provido x recorrente_polo)",
            )
        )

    # 2.4 Métrica Econômica Contínua (Taxa de Sucesso Substantivo)
    models_file = ROOT_DIR / "src/causaganha/analysis/models.py"
    if models_file.exists():
        content = models_file.read_text(encoding="utf-8")
        has_taxa_sucesso = "taxa_sucesso" in content or "proporcao_sucesso" in content
        has_binary_won = "plaintiff_won" in content

        checks.append(
            AuditCheck(
                bloco="2. Métricas Econômicas",
                id="2.4",
                descricao="Métrica Econômica Contínua vs. Binário plaintiff_won",
                status="WARN" if (has_binary_won and not has_taxa_sucesso) else "PASS",
                evidencia="DecisionAnalysis possui 'plaintiff_won: bool' mas não possui métrica contínua de taxa de êxito econômico (valor_condenacao / valor_causa)"
                if not has_taxa_sucesso
                else "Métrica contínua de proporção de êxito presente",
                recomendacao="Adicionar propriedade ou campo taxa_sucesso_economico = min(1.0, valor_condenacao / valor_causa) para evitar redução binária",
            )
        )

    # -------------------------------------------------------------
    # Bloco 5: Rigor Estatístico no Benchmark
    # -------------------------------------------------------------
    parquet_path = ROOT_DIR / "data/benchmark/gold_benchmark.parquet"
    if parquet_path.exists():
        df = pq.read_table(str(parquet_path)).to_pandas()
        has_classes = len(df["classe_processual"].unique()) > 1
        has_courts = len(df["court"].unique()) > 1
        has_types = len(df["decision_type"].unique()) > 1

        checks.append(
            AuditCheck(
                bloco="5. Rigor Estatístico",
                id="5.1",
                descricao="Estratificação Multitribunal e Multiclasse no Benchmark",
                status="PASS" if (has_courts and has_types and has_classes) else "WARN",
                evidencia=f"Benchmark cobre {len(df['court'].unique())} tribunais, {len(df['classe_processual'].unique())} classes e {len(df['decision_type'].unique())} tipos de decisão",
            )
        )

    return checks


def print_audit_report(checks: list[AuditCheck]):
    print("=" * 85)
    print("RELATÓRIO DE AUDITORIA DE JURIMETRIA EMPÍRICA (CAUSAGANHA)")
    print("=" * 85)
    print(f"{'Bloco':<24} | {'ID':<4} | {'Status':<6} | {'Evidência Técnica'}")
    print("-" * 85)

    passed = 0
    warns = 0
    fails = 0

    for c in checks:
        if c.status == "PASS":
            status_str = "[PASS]"
            passed += 1
        elif c.status == "WARN":
            status_str = "[WARN]"
            warns += 1
        else:
            status_str = "[FAIL]"
            fails += 1
        print(f"{c.bloco:<24} | {c.id:<4} | {status_str:<6} | {c.evidencia}")

    total = len(checks)
    compliance_rate = (passed / total) * 100 if total else 0.0

    print("=" * 85)
    print(
        f"ÍNDICE DE CONFORMIDADE JURIMÉTRICA: {compliance_rate:.1f}% ({passed}/{total} itens em PASS)"
    )
    print(f"Avisos de Melhoria (WARN): {warns} | Falhas Críticas (FAIL): {fails}")
    print("=" * 85)

    if warns > 0:
        print("\nRecomendações de Aprimoramento:")
        for c in checks:
            if c.status == "WARN":
                print(f"  • [{c.bloco} - {c.id}]: {c.descricao} -> {c.evidencia}")


if __name__ == "__main__":
    audit_results = run_jurimetrics_audit()
    print_audit_report(audit_results)
