---
type: AgentDecision
id: "2026-09-16-exciting-mccarthy-mg2tp1-decision-reuse-batch3-html-cleaner"
run_id: "2026-09-16-exciting-mccarthy-mg2tp1"
goal_id: "2026-09-16-exciting-mccarthy-mg2tp1-goal-djen-sample-batch4"
question: "All 5 candidates selected for this batch fail ET.fromstring on their raw texto_limpo with the same 'mismatched tag' defect the previous round (uyx7xc) diagnosed and fixed (an unclosed <meta> inside a raw <html><head>...<body> wrapper). Should this round write a new cleaner, or reuse docs/planning/evidence/segmenter-djen-sample-batch3-clean-html.py as-is?"
choice: "Reuse the batch3 cleaner unmodified. Ran it live on all 5 candidates: every one becomes XML-parseable (<text>...</text> parses cleanly) and HTML-entity-free (0 residual '&[a-zA-Z]+;' matches) with no code changes."
rationale: "The previous round already diagnosed this exact defect class, wrote a stdlib-only cleaner for it, and validated it end-to-end (including recovering a document a prior round had discarded). This round's candidates hit the identical failure mode (same ParseError position, same unclosed <meta> pattern) in a different set of tribunals -- there is no new defect shape here that would justify writing new code, and the cleaner is explicitly documented as reusable scratch tooling for this purpose. Still not promoted to scripts/ this round either: it has no dedicated test suite yet, and this round's batch (5 documents) does not materially change the promotion calculus the previous round already made (worth doing once enough future batches keep needing it to justify the investment)."
---

# Decisao: reusar o limpador HTML da rodada anterior sem alteracao

Os 5 candidatos deste lote falham `ET.fromstring` no mesmo padrao de erro
(`<meta>` nao fechado dentro de wrapper `<html><head>...<body>`) que a
rodada anterior (uyx7xc) ja diagnosticou e corrigiu. Reusar
`docs/planning/evidence/segmenter-djen-sample-batch3-clean-html.py` sem
nenhuma mudanca resolve os 5 candidatos (XML-parseavel, 0 entidades HTML
residuais). Ainda nao promovido para `scripts/` -- sem suite de testes
propria, mesma decisao da rodada anterior.
