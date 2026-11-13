---
type: AgentDecision
id: "2026-09-26-exciting-mccarthy-sg2540-decision-adjudication-resolutions"
run_id: "2026-09-26-exciting-mccarthy-sg2540"
goal_id: "2026-09-26-exciting-mccarthy-sg2540-goal-1051-test-split-adjudication"
question: "For each of the 4 documents, how should genuine disagreements between the first (general-purpose) and second (haiku) annotations be resolved?"
choice: "Adjudicated span-by-span against the annotation guideline's own rules rather than picking one annotator wholesale; see per-document breakdown below."
rationale: "See per-document breakdown below. The recurring pattern this round: the FIRST annotation consistently omitted the cabecalho category entirely on all 4 documents (a real coverage gap, not a judgment call), which the SECOND annotation caught every time -- adopted in all 4 reviews. Conversely, where the second annotation widened an inicio/fim anchor beyond a short cue phrase (Rule 1: anchor spans are short), the first annotation's tighter span was kept."
---

# Decision: per-document adjudication resolutions

**TRF4 (doc_6b9ee9d4f525b8442af4cbc20da41269, acordao):** adopted B's
cabecalho pair (A omitted it entirely). Kept A's narrower
`ref_processual` (excludes the `/RS` state suffix, matching corpus
convention), A's `fundamentacao_legal` (includes the trailing period,
immaterial), and A's `ementa_fim` (the tighter "princípio da
proporcionalidade." close). Separately, before adjudication, repaired
a structural defect in B's raw annotation: a `resultado` singleton was
nested inside `acordao_decisorio`'s `fim` anchor at an overlapping
span (the same "singleton nested inside a pair's closing anchor"
defect shape documented by round `p08457`) -- split into two adjacent,
non-overlapping spans matching A's own established structure before
ingesting B as a standalone annotation.

**TJMS (doc_c41321b105269252919a5d4d730800a2, acordao):** adopted B's
cabecalho pair (A omitted it), B's `fundamentacao_legal` citation to
an ANEEL administrative resolution (A missed it), B's tighter
`ementa_fim` (excludes the "IV -" numbering prefix and trailing
period), and B's wider `resultado` span covering both parts of the
actual disposition ("afastaram a preliminar e, no mérito, negaram
provimento ao recurso" -- the decision did two things, not one; A's
narrower span only captured the merits half). Kept A's
`ref_processual` (B's own second-annotation output claimed to tag it
but mechanical verification showed it never actually did -- a
self-report/output mismatch, not a real disagreement). Separately,
before adjudication, repaired a genuine content-loss defect in B's raw
annotation: two literal parenthesis characters around an OAB number
were silently dropped by the subagent despite its own verbatim
self-check passing -- restored at the exact position, tag content
untouched.

**TJPI (doc_7e91843200b79e7467d0ae541ad9c6c8, sentenca):** adopted B's
cabecalho pair and all 3 `valor_condenacao` spans (A omitted both
categories entirely, despite the monetary amounts appearing verbatim
3 times in the text). Kept A's narrower `relatorio_inicio`/
`encerramento_inicio` anchors (B's second annotation had widened
`relatorio_inicio` to the entire 211-character first sentence of the
narrative, which both violates Rule 1 and trips
`scripts/segmenter_semantic_audit.py`'s zero-tolerance `long_anchor`
check -- caught only because the audit was re-run during adjudication,
not only at the end, per round `uq3be8`'s process lesson). Kept A's
`capitulo_merito_inicio`/`custas_inicio`/both `fundamentacao_legal`
spans, all of which B's second annotation missed entirely.

**TJES (doc_52ca8d9d94f86a8426e0e9c3c7ef158b, sentenca):** kept A's
`fundamentacao_legal` span, which is 6 characters longer than B's
because it correctly includes the "(LJE)" statute-abbreviation
suffix as part of the citation. No other genuine disagreement once B
was corrected (during mechanical verification, before adjudication)
to include the `honorarios` pair alongside `custas` -- B's raw output
had tagged `custas` but left the immediately adjacent "honorários"
clause completely untagged, an omission rather than a real
disagreement, matching the precedent (`allowed_unmatched` reasons for
both `custas_fim` and `honorarios_fim`) already established in A's own
annotation.
