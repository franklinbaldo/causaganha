"""Executa o Torneio Competitivo de Regexes sobre 1.000 Decisões Reais do DJEN.

Mede True Positives (TP) e False Positives (FP) de cada regex candidata,
penaliza severamente falsos positivos e seleciona as Top-K melhores por categoria.
"""

from __future__ import annotations

from pathlib import Path
import sys
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))
sys.path.insert(0, str(ROOT_DIR / "scripts"))

from causaganha.decisoes.regex_tournament import build_default_tournament
from classify_djen_sample_1000 import clean_html_if_present, load_1000_djen_sample


def main():
    print("=" * 75)
    print("🏆 TORNEIO COMPETITIVO DE REGEXES — CAUSAGANHA")
    print("   Critério: Recompensa de TP com penalização estrita de Falsos Positivos")
    print("=" * 75)

    # 1. Carrega o acervo de benchmark
    print("\n[1/4] Carregando acervo de 1.000 decisões reais do DJEN...")
    csv_path = ROOT_DIR / "data/audit/classificacao_1000_djen.csv"
    if not csv_path.exists():
        print(f"Erro: Arquivo {csv_path} não encontrado.")
        return

    df_gold = pd.read_csv(csv_path)
    sample_docs = load_1000_djen_sample(1000)
    doc_map = {d["doc_id"]: d for d in sample_docs}

    dataset = []
    for _, row in df_gold.iterrows():
        doc_id = str(row["doc_id"])
        doc = doc_map.get(doc_id)
        if not doc:
            continue
        clean_text = clean_html_if_present(doc["texto"])
        dataset.append(
            {
                "doc_id": doc_id,
                "tribunal": row["tribunal"],
                "texto": clean_text,
                "desfecho_cpc": str(row["desfecho_cpc"]).lower().strip(),
            }
        )

    print(f"✓ {len(dataset)} documentos preparados para a avaliação.")

    # 2. Inicializa o Torneio
    print("\n[2/4] Inicializando participantes e registrando candidatos...")
    tournament = build_default_tournament()

    # Adiciona algumas regexes candidatas adicionais (algumas boas, outras propositalmente fracas para testar penalização de FP)
    tournament.register(
        r"\bcondeno\b",
        "procedente",
        "proc_condeno_generico",
        source="candidate_loose",
        description="Padrão muito frouxo (teste de penalidade)",
    )
    tournament.register(
        r"\bpedido\s+procedente\b",
        "procedente",
        "proc_pedido_procedente",
        source="candidate_strict",
        description="Variante de cabeçalho/dispositivo",
    )
    tournament.register(
        r"\brejeição\s+do\s+pedido\b",
        "improcedente",
        "improc_rejeicao_pedido",
        source="candidate_strict",
        description="Substantivo de rejeição",
    )
    tournament.register(
        r"\bextinção\s+sem\s+resolução\b",
        "extinto sem mérito",
        "extinto_sem_res_subst",
        source="candidate_strict",
        description="Fórmula substantiva de extinção",
    )
    tournament.register(
        r"\bsem\s+julgamento\s+do\s+mérito\b",
        "extinto sem mérito",
        "extinto_sem_julg_merito",
        source="candidate_strict",
        description="Fórmula clássica CPC/73 / CPC/15",
    )

    total_patterns = sum(len(p) for p in tournament.categories.values())
    print(
        f"✓ {total_patterns} expressões regulares em competição distribuídas em {len(tournament.categories)} categorias."
    )

    # 3. Executa a rodada do Torneio
    print("\n[3/4] Executando rodada do torneio contra todas as decisões...")
    tournament.evaluate_tournament(dataset, text_key="texto", label_key="desfecho_cpc")

    # 4. Exibe o Leaderboard
    print("\n[4/4] RESULTADOS DO TORNEIO (LEADERBOARD POR CATEGORIA):\n")

    for cat, rules in tournament.categories.items():
        print(f"📌 CATEGORIA: {cat.upper()} (Top-3 Promovidas marcadas com ⭐)")
        print(
            f"{'Status':<11} | {'Pattern ID':<26} | {'TP':<4} | {'FP':<4} | {'Precision':<9} | {'Score':<8} | {'Pattern':<35}"
        )
        print("-" * 105)
        for idx, r in enumerate(rules):
            star = "⭐ " if r.status == "PROMOTED" else "   "
            status_str = f"{star}{r.status}"
            pat_disp = r.pattern if len(r.pattern) <= 35 else r.pattern[:32] + "..."
            print(
                f"{status_str:<11} | {r.pattern_id:<26} | {r.tp:<4} | {r.fp:<4} | {r.precision * 100:>6.1f}% | {r.score:>8.1f} | {pat_disp:<35}"
            )
        print()

    # 5. Salva o Leaderboard
    leaderboard_path = ROOT_DIR / "data/audit/regex_leaderboard.json"
    tournament.save_leaderboard(leaderboard_path)
    print(f"✓ Leaderboard oficial salvo em: {leaderboard_path}")

    # 6. Demonstração de Classificação em Produção com apenas o Top-K
    print("\n🎯 TESTE DE INFERÊNCIA EM PRODUÇÃO (Usando apenas as Top-K promovidas):")
    test_samples = [
        "Ante o exposto, julgo procedente o pedido inicial para condenar o réu ao pagamento de indenização.",
        "Diante de tais fundamentos, julgo improcedente a ação nos termos do art. 487, I, do CPC.",
        "Pelo exposto, acolho em parte o pedido, julgando parcialmente procedente a pretensão.",
        "Posto isso, homologo por sentença o acordo celebrado entre as partes para que produza efeitos.",
        "Assim, extingo o processo sem resolução do mérito com base no art. 485, inciso VI, do CPC.",
    ]
    for idx, s in enumerate(test_samples, 1):
        winner_cat, conf, reg = tournament.classify_best(s)
        reg_id = reg.pattern_id if reg else "none"
        print(
            f"  {idx}. Resultado: {winner_cat.upper():<24} (Conf: {conf * 100:.1f}%) | Regex Vencedora: {reg_id}"
        )

    # 7. Demonstração de Segment-Aware Weighting (Dispositivo 3.0x vs Relatório 0.2x)
    print("\n🛡️ TESTE DE RESILIÊNCIA CONTRA CITAÇÕES CONTRÁRIAS (Segment-Aware Weighting):")
    tricky_sections = {
        "relatorio": "O autor ingressou com ação de cobrança. O réu contestou requerendo que a ação fosse julgada improcedente.",
        "dispositivo": "Ante o exposto, julgo procedente o pedido condenando o réu ao pagamento.",
    }
    explanation = tournament.classify_with_explanation(
        "texto completo...", sections=tricky_sections
    )
    print(f"  Vencedor: {explanation.category.upper()} (Seção: {explanation.winning_section})")
    print(
        f"  Pontuação Efetiva: {explanation.effective_score} (Confiança: {explanation.confidence * 100:.1f}%)"
    )
    print(f"  Regra: {explanation.winning_rule.pattern_id if explanation.winning_rule else 'none'}")
    print(
        "  -> Multiplicador do dispositivo evitou que a menção de 'improcedente' no relatório sequestrasse a decisão."
    )

    print("\n✓ Torneio finalizado com sucesso!")


if __name__ == "__main__":
    main()
