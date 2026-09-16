---
type: AgentEvidence
id: "2026-09-16-exciting-mccarthy-mg2tp1-evidence-batch4-ingested"
run_id: "2026-09-16-exciting-mccarthy-mg2tp1"
goal_id: "2026-09-16-exciting-mccarthy-mg2tp1-goal-djen-sample-batch4"
kind: "runtime"
reference: "docs/planning/evidence/segmenter-djen-sample-batch4-2026-09-16.json, docs/planning/evidence/segmenter-djen-sample-batch4-overrides.json"
summary: "All 5 selected candidates (TJSC, TRF4 x3, TRF6) ingested successfully via scripts/ingest_djen_sample_technique1_batch.py after (a) cleaning all 5 candidates' raw embedded HTML markup with the unmodified batch3 cleaner (same defect class: unclosed <meta> inside an <html><head>...<body> wrapper), (b) a reviewed --allowed-unmatched-overrides entry per candidate for 3 dangling-ementa cases (same established defect class: a structured, numbered-section ementa export with no separate RELATORIO/VOTO to close it against), and (c) fixing a genuinely new defect found live in one candidate (TJSC 587254906): the ingestion script's verbatim-fidelity check reported reconstructed_len==source_len (3977==3977) yet still flagged a mismatch, meaning a same-length single-character substitution was masking the length check -- a programmatic char-by-char diff (not the length numbers) located exactly one non-breaking space (U+00A0) that the annotating subagent had silently normalized to a regular space during transcription; patched by rewriting that one substring in the tagged file (verified the diff fell in plain text, not near a tag boundary) rather than re-running the subagent. uv run python scripts/segmenter_governance_status.py confirms document_count 81->86, val_ceiling_at_full_adjudication/test_ceiling_at_full_adjudication 12->13, and 3 new tribunals now represented (TJSC, TRF4, TRF6), bringing the store to 24 distinct tribunals total (up from 21). No changes to production code (scripts/ingest_djen_sample_technique1_batch.py and its test suite reused as-is, same as prior batches) -- only candidate preprocessing (HTML cleanup, reused from batch3) and one manual per-document transcription fix, done ad hoc in this round's own scratch tooling."
---

# Evidencia: lote 4 ingerido com sucesso

5/5 candidatos selecionados ingeridos apos: limpar markup HTML bruto (os
5, mesmo defeito da rodada anterior), declarar overrides revisados para 3
pares `ementa` pendentes (mesma classe conhecida), e corrigir ao vivo um
defeito novo -- um espaco nao separavel (U+00A0) normalizado
silenciosamente para espaco comum por um subagente, mascarado por um
comprimento de texto igual (3977==3977), so descoberto via diff
caractere-a-caractere programatico. `document_count` 81->86, teto de
val/test 12->13, 3 tribunais novos (total 24 no store). Nenhum codigo de
producao mudou.
