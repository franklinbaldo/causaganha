---
type: "RunEvidence"
id: "run-evidence/20260920t094145z-do-the-best-useful-work-availab/evidence-batch25-ingested"
run: "runs/20260920T094145Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "7 subagents (Technique 1 canonical prompt) annotated TJCE/363676235, TJMT/74432048, TJRJ/488920434, TJTO/285641901, TRF3/42491442, TRF5/463264368, TJPI/22537155 -- each self-verified byte-for-byte verbatim reconstruction; scripts/ingest_djen_sample_technique1_batch.py --allowed-unmatched-overrides (6 unmatched-pair overrides, each verified against raw source text before declaring) ingested all 7 into data/segmenter"
summary: "document_count: 184 -> 191 (find data/segmenter/documents -iname '*.xml' | wc -l). Near-duplicate check performed BEFORE annotation this round against the FULL 184-document existing corpus (not just other batch25 candidates), applying the batch24 process lesson -- 152 eligible candidates found across 20 tribunals after filtering out exact/near duplicates (threshold 0.90), of which 7 were selected (TJCE/TJMT/TJRJ/TJTO/TRF3/TRF5 raised from store_count=5->6, TJPI raised from 6->7). Real HTML cleaner used (docs/planning/evidence/segmenter-djen-sample-batch3-clean-html.py), not html.unescape. ruff check/format --check clean. scripts/segmenter_semantic_audit.py: 1 new HIGH finding on doc_2f952744ab8c9e0bafb66cd01a9f4e2d (TRF3/42491442) 'fundamentacao_legal_collapsed' -- verified against raw source: all extra 'art.' mentions are inside third-party quoted precedent blocks (STJ/TRF3 ementas reproduced verbatim under 'Confiram-se os precedentes:'), not this document's own reasoning -- false positive, same established exclusion as batch24's TJMA footnote-citations precedent, no fix needed."
---

# RunEvidence
