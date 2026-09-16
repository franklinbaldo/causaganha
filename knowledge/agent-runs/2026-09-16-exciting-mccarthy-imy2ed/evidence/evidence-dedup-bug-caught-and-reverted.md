---
type: AgentEvidence
id: "2026-09-16-exciting-mccarthy-imy2ed-evidence-dedup-bug-caught-and-reverted"
run_id: "2026-09-16-exciting-mccarthy-imy2ed"
goal_id: "2026-09-16-exciting-mccarthy-imy2ed-goal-djen-sample-batch10"
decision_id: "2026-09-16-exciting-mccarthy-imy2ed-decision-fix-candidate-dedup-hash-space"
kind: "runtime_behavior"
description: "First candidate selection (TJRN/72798564, TJBA/574460090), chosen by comparing pool info.sha256 against store source.source_hash, ingested with `uv run python -m scripts.ingest_djen_sample_technique1_batch ... --output data/segmenter`. Reported 'Ingested 2 document(s)' with new annotation IDs, but `scripts/segmenter_governance_status.py` still showed document_count=109 (unchanged) while annotation_count rose 162->164. `git status --short data/segmenter` showed exactly 2 new files, both under annotations/, none under documents/ -- confirming both source_uris (djen_sample_technique1:batch1:TJRN:72798564, djen_sample_technique1:batch1:TJBA:574460090) already existed pre-batch. Reading both documents' pre-existing annotation XML confirmed the same fixed annotator id (llm_technique1:djen_sample_batch1) as the new one -- a second same-annotator annotation, not an independent one. Reverted (`rm` on the 2 new annotation XML files); `git status --short data/segmenter` returned empty and governance_status.py returned to annotation_count=162 -- store confirmed pristine before any real change. Re-selected candidates (TJBA/574460089, TJRN/72797727) using content_hash(text) + (tribunal, id_documento)-vs-source_uri matching -- see decision record for the full before/after."
---

# Evidencia: bug de dedup pego e revertido antes de qualquer dano real

Nenhum commit, push ou evidencia publicada referenciou os candidatos
errados em nenhum momento -- o erro foi detectado e corrigido
inteiramente em working tree local, antes do primeiro `git add`.
