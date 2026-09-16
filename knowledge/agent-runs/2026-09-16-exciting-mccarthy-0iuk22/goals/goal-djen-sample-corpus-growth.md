---
type: AgentGoal
id: "2026-09-16-exciting-mccarthy-0iuk22-goal-djen-sample-corpus-growth"
run_id: "2026-09-16-exciting-mccarthy-0iuk22"
goal: "Build and use, via TDD, a generalized Technique 1 ingestion path (scripts/ingest_djen_sample_technique1_batch.py) that turns the already-fetched, unused real multi-tribunal judicial texts in data/segmenter_samples/*.jsonl into genuine train-eligible DocumentRecord/AnnotationRecord pairs in the segmenter_dataset store -- the concrete, still-unchecked #1050 work item ('mine real candidate documents... multiple tribunals/sources') the previous round's next_move redirected this lineage to, and ingest a first real batch to measurably raise document_count and the RFC 0012 Sec 5 item 4 val/test ceiling beyond today's 9/9."
rationale: "The previous round (c4y4rc, merged PR #1535) proved with live evidence that adjudicating more of the existing fixed 61-document TJRO-only pool (#1051) can never cross RFC 0012's per-split floor (>=30 val, >=30 test, both adjudicated) -- the ceiling is a function of total corpus size (val_target/test_target = round(total_eligible * ratio)), not of how much of the existing pool gets reviewed. It explicitly redirected next_move to #1050: grow the total corpus. #1050's own body asks for exactly two things no prior round has done: mine real candidate documents for rare categories, and include multiple tribunals/sources -- today 61/61 documents in the store are TJRO. This round found that data/segmenter_samples/*.jsonl already holds ~830 real, already-fetched documents from ~30 non-TJRO tribunals with pre-computed rare-category cue hits, entirely unused -- the missing piece is purely a generalized ingestion path (the only existing new-document ingestor, ingest_juris_technique1_batch.py, is hardcoded to TJRO JURIS candidates) plus real Technique 1 annotations for a first batch. Building that path and proving it moves document_count/val_ceiling/test_ceiling is the real, natural continuation of this lineage -- not another isolated review inside the same 61-document pool."
success_signal: "scripts/ingest_djen_sample_technique1_batch.py exists with its own test suite (TDD RED before the implementation's bugs were fixed, GREEN after) covering tribunal/document_type derivation from candidate metadata, unsupported-tipoDocumento skip, verbatim-fidelity skip, and unmatched-candidate skip. A real batch of >=1 genuine, non-TJRO document from data/segmenter_samples, annotated by a subagent using the canonical Technique 1 prompt (data/segmenter_splits/technique1_annotation_prompt.md) and passing this script's mechanical/verbatim checks, is ingested into data/segmenter/. scripts/segmenter_governance_status.py run before and after the batch shows document_count strictly increasing and source.tribunal diversity beyond {TJRO} in the store. uv run pytest -q and ruff check/format stay green. A PR is opened documenting the before/after governance numbers."
status: "achieved"
---

# Goal: abrir o caminho de ingestao multi-tribunal para #1050

Nao mais um `ReviewRecord` dentro do pool fixo de 61 documentos TJRO -- o
avanco real desta rodada e o item de trabalho de #1050 ainda nao feito por
nenhuma rodada anterior: minerar e ingerir documentos candidatos reais de
outros tribunais, usando o material ja coletado e parado em
`data/segmenter_samples/`.
