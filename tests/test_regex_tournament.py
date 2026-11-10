"""Testes unitários para o Torneio Competitivo de Regexes."""

from __future__ import annotations

from causaganha.decisoes.regex_tournament import (
    CompetitiveRegex,
    RegexTournament,
    build_default_tournament,
)


def test_competitive_regex_initialization():
    r = CompetitiveRegex("test_proc", r"\bjulgo\s+procedente\b", "procedente")
    assert r.pattern_id == "test_proc"
    assert r.category == "procedente"
    assert r.status == "CANDIDATE"
    assert r.score == 0.0


def test_competitive_regex_scoring_and_promotion():
    r = CompetitiveRegex("test_proc", r"\bjulgo\s+procedente\b", "procedente", fp_penalty=2.0)
    # 20 TP e 2 FP -> Precision = 20 / 22 = 0.909
    # Net TP = 20 - (2.0 * 2) = 16.0
    # Score = 16.0 * 0.909 * 10 = 145.4
    r.update_metrics(tp=20, fp=2, total_positives_in_dataset=25)
    assert r.tp == 20
    assert r.fp == 2
    assert r.precision > 0.90
    assert r.score > 100.0
    assert r.status == "PROMOTED"


def test_competitive_regex_demotion_on_high_false_positives():
    r = CompetitiveRegex("test_loose", r"\bcondeno\b", "procedente", fp_penalty=2.0)
    # 5 TP e 25 FP (muito frouxo!)
    r.update_metrics(tp=5, fp=25, total_positives_in_dataset=30)
    assert r.precision < 0.20
    assert r.score < 0.0
    assert r.status == "DEMOTED"


def test_regex_tournament_evaluation_and_top_k():
    tournament = RegexTournament(top_k=2, fp_penalty=2.0, min_precision=0.75)
    tournament.register(r"\bjulgo\s+procedente\b", "procedente", "p1")
    tournament.register(r"\bacolho\s+o\s+pedido\b", "procedente", "p2")
    tournament.register(r"\bcondeno\b", "procedente", "p3_loose")

    dataset = [
        {"texto": "Diante disso, julgo procedente a ação.", "desfecho_cpc": "procedente"},
        {"texto": "Portanto, julgo procedente o pedido.", "desfecho_cpc": "procedente"},
        {"texto": "Assim, acolho o pedido autoral.", "desfecho_cpc": "procedente"},
        {
            "texto": "Condeno o réu em custas mas julgo improcedente.",
            "desfecho_cpc": "improcedente",
        },
        {"texto": "Condeno a testemunha por falso testemunho.", "desfecho_cpc": "improcedente"},
        {"texto": "Decisão interlocutória qualquer.", "desfecho_cpc": "unknown"},
    ]

    results = tournament.evaluate_tournament(dataset)
    assert results["total_documents_tested"] == 6

    top = tournament.get_top_k("procedente")
    assert len(top) <= 2
    # p1 deve ter precisão 100% e ser a primeira
    assert top[0].pattern_id == "p1"
    assert top[0].precision == 1.0


def test_tournament_classify_best():
    tournament = build_default_tournament()
    text_proc = "Ante o exposto, julgo procedente o pedido para condenar a empresa."
    winner, conf, reg = tournament.classify_best(text_proc)
    assert winner in {"procedente", "unknown"}


def test_tournament_save_and_load(tmp_path):
    t = build_default_tournament()
    save_path = tmp_path / "leaderboard.json"
    t.save_leaderboard(save_path)
    assert save_path.exists()

    t2 = RegexTournament()
    t2.load_leaderboard(save_path)
    assert len(t2.categories) == len(t.categories)
    assert "procedente" in t2.categories
