---
type: "RunDecision"
id: "run-decisions/20260920t094145z-do-the-best-useful-work-availab/decision-dismiss-trf3-quoted-precedent-art-findi"
run: "runs/20260920T094145Z-do-the-best-useful-work-available-in-this-reposi"
question: "scripts/segmenter_semantic_audit.py flags doc_2f952744ab8c9e0bafb66cd01a9f4e2d (TRF3/42491442) as fundamentacao_legal_collapsed: only 1 fundamentacao_legal tagged but 'art.' appears >3 times. Is this a real annotation defect to fix, or a false positive?"
decision: "False positive, no fix. Every extra 'art.' occurrence (art. 1.021 CPC/2015, art. 557, art. 195,I) lives inside a long block of third-party precedent text the judge quotes verbatim under 'Confiram-se os precedentes:' (STJ AIRESP excerpts, a TRF3 Agravo Legal excerpt, an EMEN:/DTPB:-tagged jurisprudence-database export) -- not this document's own reasoning. The single tagged fundamentacao_legal ('a teor do art. 487, inc. I, do CPC/2015') is the document's only genuine legal-reasoning citation."
rationale: "Same established exclusion already applied in batch24 to TJMA/42725100's footnote-reproduced precedent citations (decision-dismiss-tjma-footnote-citations-finding): a judge quoting another court's decision verbatim is not this document's own fundamentacao_legal, by analogy to the guideline's ref_processual rule ('leave every other case's number untagged'). Tagging quoted-precedent citations would misrepresent them as this document's own legal grounding."
---

# RunDecision
