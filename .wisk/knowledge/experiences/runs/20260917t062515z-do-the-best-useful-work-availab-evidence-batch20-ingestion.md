---
type: "RunEvidence"
id: "run-evidence/20260917t062515z-do-the-best-useful-work-availab/batch20-ingestion"
run: "runs/20260917T062515Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "scripts/ingest_djen_sample_technique1_batch.py --candidates docs/planning/evidence/segmenter-djen-sample-batch20-candidates.json --tagged-dir <scratch>/batch20_tagged --output data/segmenter --allowed-unmatched-overrides docs/planning/evidence/segmenter-djen-sample-batch20-overrides.json"
summary: "Ingested 6 documents (doc_6b6ccf67.., doc_af3e9021.., doc_da5165f5.., doc_db852d2a.., doc_ec0160bb.., doc_f0c1302f..) for issue #1050, all TRF2. git status --short data/segmenter shows exactly 6 new documents/*.xml + 6 new annotations/<id>/ dirs, no silent no-op. Every candidate's tagged reconstruction (_parse_tagged) matched its source texto_limpo byte-for-byte before ingestion, after fixing a single NBSP-to-space substitution per document (all 6) with docs/planning/evidence/segmenter-djen-sample-batch17-fix-nbsp.py reused verbatim. 5 ementa + 2 custas/honorarios overrides declared, all verified against raw source text first."
goal: "batch20-trf2"
---

# RunEvidence
