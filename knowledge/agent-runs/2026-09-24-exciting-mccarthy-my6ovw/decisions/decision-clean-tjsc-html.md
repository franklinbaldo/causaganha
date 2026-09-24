---
type: AgentDecision
id: "2026-09-24-exciting-mccarthy-my6ovw-decision-clean-tjsc-html"
run_id: "2026-09-24-exciting-mccarthy-my6ovw"
goal_id: "2026-09-24-exciting-mccarthy-my6ovw-goal-djen-sample-batch26"
question: "The first subagent's tagged output for TJSC/587254831 preserved a full <html><head><style>...<body><article>...</article></body></html> wrapper verbatim around the judicial text -- texto_limpo for this candidate is raw HTML, not plain text, the same defect class documented since batch3/batch18 (TRF4 pool excluded entirely for exactly this). Ingest the document with the HTML wrapper intact (verbatim-fidelity would still pass structurally), or clean it to plain text first and re-annotate?"
choice: "Clean with docs/planning/evidence/segmenter-djen-sample-batch3-clean-html.py before re-annotating, discard the first (HTML-wrapped) tagging attempt entirely."
rationale: "Every other document in the store is plain judicial prose, not markup -- ingesting raw HTML tags/entities (<table>, <tr>, &Ccedil;, &nbsp;, etc.) as part of a DocumentRecord's text would be a genuine quality regression the mechanical/verbatim checks cannot catch (they only verify tag-stripped-text-equals-source, and source itself was the raw HTML in the first attempt). The batch3 cleaner is the project's own established fix for exactly this defect class (used for TJGO/TJTO/TJMG in multiple prior batches, and cited as the reason TRF4's entire pool was excluded when cleaning collapsed every candidate below the length floor). Applying it dropped the text from 2336 to 1037 chars (mostly boilerplate table/header markup with no real content) and produced a document consistent with the rest of the corpus; a live near-duplicate recheck on the cleaned text still confirmed it is not a duplicate of anything in the store (max ratio 0.118)."
---

# Decisão: limpar o HTML embutido do candidato TJSC antes de anotar
