---
type: AgentEvidence
id: "2026-09-16-exciting-mccarthy-imy2ed-evidence-dedup-bug-caught-and-reverted"
run_id: "2026-09-16-exciting-mccarthy-imy2ed"
goal_id: "2026-09-16-exciting-mccarthy-imy2ed-goal-djen-sample-batch10"
kind: "runtime"
reference: "data/segmenter (git status before/after revert), knowledge/backlog/issue-1050.md risk class 7"
summary: "First candidate selection (TJRN/72798564, TJBA/574460090), chosen by comparing pool info.sha256 against store source.source_hash, ingested with 'Ingested 2 document(s)' reported, but document_count stayed 109 (unchanged) and git status showed exactly 2 new files, both under annotations/, none under documents/ -- confirming both source_uris already existed pre-batch under the fixed annotator id (llm_technique1:djen_sample_batch1), so the new annotation was a redundant same-annotator duplicate, not an independent one. Reverted (rm on the 2 new annotation XML files); git status returned empty and governance_status.py returned to annotation_count=162 before any real change or commit."
---

# Evidencia: bug de dedup pego e revertido antes de qualquer dano real

Nenhum commit, push ou evidencia publicada referenciou os candidatos
errados em nenhum momento -- o erro foi detectado e corrigido
inteiramente em working tree local, antes do primeiro `git add`.
