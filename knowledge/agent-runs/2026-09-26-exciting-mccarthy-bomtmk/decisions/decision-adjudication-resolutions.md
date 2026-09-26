---
type: AgentDecision
id: "2026-09-26-exciting-mccarthy-bomtmk-decision-adjudication-resolutions"
run_id: "2026-09-26-exciting-mccarthy-bomtmk"
goal_id: "2026-09-26-exciting-mccarthy-bomtmk-goal-1051-test-split-adjudication"
question: "For each of the 3 documents, where the two independent annotations disagreed, which spans should the accepted ReviewRecord's final_labels use?"
choice: "TRF2 (doc_8904b2884e6177d2b61fd7462ce7539d): mostly A (5 fundamentacao_legal occurrences incl. one B's subagent missed entirely mid-document, custas/honorarios shared-clause pair, encerramento unmatched) + B's tighter cabecalho_inicio/cabecalho_fim boundaries, B's new standalone ref_processual tag, and one new fundamentacao_legal B found that A missed ('na forma do Manual de Calculos...'). TJES (doc_6b29f96e41baeb5405c87bd09fb38d3d): mostly A (tighter cabecalho_inicio, relatorio_inicio, a third fundamentacao_legal occurrence, custas/honorarios) + B's tighter fundamentacao_legal boundaries (excluding the '(LJE)' acronym gloss) and B's new ref_normativa find. TJSE (doc_de65a409f2156cc18d43f96fa35347fc): B's cabecalho pair (A omitted the category entirely) and B's acordao_decisorio_inicio anchor ('ACORDAM OS JUIZES', the guideline's own canonical cue) + A's tighter acordao_decisorio_fim with resultado tagged separately (guideline's anchor-spans-are-short rule), A's more complete ementa_fim, and A's separate custas_inicio/honorarios_inicio (B had collapsed both into one custas pair, dropping honorarios)."
rationale: "Each choice traces to a guideline rule, not a coin flip: 'anchor spans are short' (Rule 1, ~120 char ceiling, prefer 1-5 words) favored the narrower cabecalho boundaries (TRF2, TJES) and A's tight acordao_decisorio_fim+separate resultado over B's wide fused span (TJSE); the guideline's own acordao_decisorio table entry lists 'ACORDAM os Desembargadores' as the canonical opening cue, favoring B's anchor over A's more generic 'Vistos, relatados e discutidos' preamble (TJSE); 'tag every distinct citation' (fundamentacao_legal's row) favored keeping every genuine citation either annotator found rather than picking one annotation wholesale (TRF2's 494-555 new find, TJES's third occurrence); and the established custas/honorarios shared-clause precedent (kgxf50's decision-preserve-audit-allowlist-precedent, reused verbatim allowed-unmatched wording from the TRF2 doc's own first annotation) favored always tagging both categories separately when a document has one shared clause, never collapsing them into a single wrapped pair that drops one category outright (TJSE, where B had done exactly that). Every adjudicated span is an exact substring offset that one of the two annotators already verified byte-for-byte against the document -- no span was invented or estimated by this round, only selected or recombined."
---

# Decision: how each of the 3 documents was adjudicated

Ran `scripts/adjudicate_segmenter_review.py`'s own `diff_labels`-equivalent
comparison manually (via a scratch script calling
`segmenter_dataset.store._labels_to_text_element` directly to build the
resolution tagged text from the final label list, then round-tripped
through `_text_element_to_labels` + `mechanical.validate_record` to
confirm verbatim fidelity and mechanical validity before submitting each
resolution).

**TRF2** (`doc_8904b2884e6177d2b61fd7462ce7539d`): the second annotation
(B) was noticeably less complete than the first (A) here — B found only
8 anchors to A's 13, missing 4 of A's 7 `fundamentacao_legal` citations
entirely (a real under-reading, not a boundary disagreement) plus the
`custas`/`honorarios` shared clause. Kept A's more complete coverage,
adopted B's two genuine improvements (tighter `cabecalho` boundaries per
Rule 1, a new `fundamentacao_legal` occurrence A missed).

**TJES** (`doc_6b29f96e41baeb5405c87bd09fb38d3d`): closer disagreement —
both annotators omitted at least one category (B dropped `relatorio`
and `custas`/`honorarios` entirely; A missed a `ref_normativa` mention).
Combined the genuine finds from both, and preferred B's tighter
`fundamentacao_legal` spans (excluding the trailing `(LJE)` acronym
gloss, which names the law just cited rather than citing an authority
itself).

**TJSE** (`doc_de65a409f2156cc18d43f96fa35347fc`): A omitted `cabecalho`
entirely (a whole missing category, caught by B). The `acordao_decisorio`
pair had a genuine boundary/keyword disagreement, resolved by combining
B's canonical inicio keyword with A's tighter, guideline-compliant fim
(keeping `resultado` as its own tag rather than fusing it into a long
`acordao_decisorio_fim`, as B's subagent had done).
