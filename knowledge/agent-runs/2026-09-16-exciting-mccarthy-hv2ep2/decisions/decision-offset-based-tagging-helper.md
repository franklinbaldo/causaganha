---
type: AgentDecision
id: "2026-09-16-exciting-mccarthy-hv2ep2-decision-offset-based-tagging-helper"
run_id: "2026-09-16-exciting-mccarthy-hv2ep2"
goal_id: "2026-09-16-exciting-mccarthy-hv2ep2-goal-batch9-corpus-growth"
question: "Annotate each candidate's texto_limpo by hand-retyping the tagged reproduction (as the canonical prompt in data/segmenter_splits/technique1_annotation_prompt.md instructs a subagent to do), or build a small offset-based helper that inserts XML tags into the original text via str.find so the tag-stripped reconstruction is byte-identical by construction?"
choice: "Built a scratch, unpublished offset-based helper (tagger.py, kept in the session scratchpad, never committed to the repo) and used it for all 6 documents this batch, instead of hand-retyping."
rationale: "The guideline's own Rule 6 warns that hand-retyping a phrase instead of wrapping the existing occurrence is 'a silent corruption,' and RFC 0012 Sec 9's changelog documents this as the single most common Technique 1 failure mode across prior batches (8/20 subagents in batch1 produced zero tags; several later batches needed --allowed-unmatched-overrides specifically because of subtle verbatim drift, e.g. NBSP substitutions). An offset-based helper (str.find on the ORIGINAL text, insertions applied back-to-front by character offset) makes a verbatim mismatch structurally impossible for any anchor it accepts, and turns a whitespace/control-character surprise into an immediate, loud ValueError instead of a mechanical-validator failure discovered only after the fact. This is a within-session tactic (I am the sole annotator this round, no subagents spawned), not a change to the canonical annotation prompt or the production ingestion script -- the helper stays in the scratchpad and is documented in the batch evidence JSON's annotation_mechanism_note rather than published as a new tool, since it has not been used across an actual multi-subagent batch yet."
---

# Decisão: helper de tagging baseado em offset

Evitou reescrita manual do texto marcado, eliminando por construção a
classe de defeito mais comum documentada em RFC 0012 §9 (mismatch de
fidelidade verbatim por retype). Achou os dois novos defeitos de dados
desta rodada (NBSP e caractere de controle) como `ValueError` imediato em
vez de falha silenciosa.
