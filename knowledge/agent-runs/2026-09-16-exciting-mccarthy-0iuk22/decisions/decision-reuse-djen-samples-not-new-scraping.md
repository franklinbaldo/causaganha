---
type: AgentDecision
id: "2026-09-16-exciting-mccarthy-0iuk22-decision-reuse-djen-samples-not-new-scraping"
run_id: "2026-09-16-exciting-mccarthy-0iuk22"
goal_id: "2026-09-16-exciting-mccarthy-0iuk22-goal-djen-sample-corpus-growth"
question: "#1050 asks to 'mine real candidate documents for rare categories' and 'include multiple document templates/types and... multiple tribunals/sources'. The only existing new-document ingestor (scripts/ingest_juris_technique1_batch.py) is hardcoded to TJRO JURIS candidates from a specific 'JURIS-pool research step' this round has no fresh output from. Should this round build a new TJRO-JURIS-shaped candidate pool (matching that script's exact input contract), or generalize ingestion for a different, already-available real-document source?"
choice: "Generalize: write scripts/ingest_djen_sample_technique1_batch.py to read data/segmenter_samples/*.jsonl-shaped candidates (already real, already fetched, already tribunal/document-type tagged, already cue-scored for rare categories) instead of reproducing the TJRO JURIS candidate-research pipeline. Reuse ingest_juris_technique1_batch's mechanical/fidelity helpers by import rather than duplicating them."
rationale: "data/segmenter_samples/ already contains ~830 real full judicial texts from ~30 non-TJRO tribunals, with the same cue-based rare-category triage spirit as segmenter_dataset.candidate_mining, sitting completely unused -- it is a strictly better fit for #1050's explicit 'multiple tribunals/sources' acceptance criterion than another TJRO batch would be (61/61 existing documents are already TJRO), and requires no new scraping/research step: the mining work #1050 asks for was already done by an earlier pipeline and just never ingested. Importing the shared helpers from ingest_juris_technique1_batch (dedupe, dangling-inicio detection, category exclusion) instead of copy-pasting them keeps the two scripts' mechanical-validation behavior identical by construction, so a future fix to one doesn't silently diverge from the other."
---

# Decisao: generalizar a ingestao para o pool DJEN multi-tribunal, nao replicar o pipeline JURIS

Decisao arquitetural desta rodada: crescer o corpus usando o material real
ja minerado e parado em `data/segmenter_samples/`, com um script novo que
importa (nao duplica) a logica mecanica ja validada de
`ingest_juris_technique1_batch.py`.
