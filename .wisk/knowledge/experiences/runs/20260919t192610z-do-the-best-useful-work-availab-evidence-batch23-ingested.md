---
type: "RunEvidence"
id: "run-evidence/20260919t192610z-do-the-best-useful-work-availab/batch23-ingested"
run: "runs/20260919T192610Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "PR #1586 (https://github.com/franklinbaldo/causaganha/pull/1586), commits 4315114 (ingestion) + 4c241da (YAML fix); data/segmenter/documents/doc_{453771fb,6129fdd7,8937b774,9316eb81,c5d6e5a9,e2986082}*.xml + matching annotations/"
summary: "Six real TRF2 acordaos ingested via scripts/ingest_djen_sample_technique1_batch.py: 301222629, 301222677, 301222685, 301222713, 301222792, 301228222. document_count 167->173, annotation_count 220->226, val/test ceiling 25/25->26/26, confirmed live via scripts/segmenter_governance_status.py. Found and fixed a new structural bug (nesting a single-anchor tag inside a pair's inicio/fim is silently dropped by _text_element_to_labels) in 3 of the 6 documents during independent verbatim-fidelity verification, plus one unverified 'no closing cue' override caught and fixed by comparing against sibling documents in the same batch. knowledge/backlog/issue-1050.md documents the new risk class 17."
goal: "goal-batch23-no-collision"
---

# RunEvidence
