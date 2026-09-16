---
type: AgentEvidence
id: "2026-09-16-exciting-mccarthy-uyx7xc-evidence-html-markup-defect-found-and-fixed"
run_id: "2026-09-16-exciting-mccarthy-uyx7xc"
goal_id: "2026-09-16-exciting-mccarthy-uyx7xc-goal-djen-sample-batch3"
kind: "other"
reference: "docs/planning/evidence/segmenter-djen-sample-batch3-clean-html.py, live parse of all 483 Sentenca/Acordao candidates in data/segmenter_samples/*.jsonl"
summary: "5 of the 7 candidates selected this round (TJMG, TJRS, TJTO, TRF2, TST) failed scripts/ingest_djen_sample_technique1_batch.py with 'malformed tagged XML: mismatched tag' -- not an annotation error, but a pre-existing defect in the candidate's own texto_limpo: raw, sometimes malformed HTML markup (unclosed void elements like <br> and <meta>, and for 3 of the 5 a full <html><head>...<body><article> wrapper). Diagnosed live: wrapping each RAW (untagged) candidate text in <text>...</text> and calling ET.fromstring already fails for these -- the defect is independent of anything a subagent tags. A live scan of the full pool (483 Sentenca/Acordao candidates) found 114 with the full <html> wrapper and 63 more with a stray unmatched </br>, together ~37% of the entire remaining candidate pool -- too large a fraction to keep dropping candidate-by-candidate as prior rounds did for smaller, one-off defects. Wrote an HTML-to-plain-text cleaner (docs/planning/evidence/segmenter-djen-sample-batch3-clean-html.py, using stdlib html.parser.HTMLParser) and verified it fixes all 5 affected candidates: each now parses as well-formed bare XML and reproduces cleanly-readable judicial text. First cleaner draft had a bug (treating unclosed <meta> as a depth-incrementing drop tag, which never decremented back to zero and silently emptied TJMG/TJRS/TJTO's output to zero characters) -- caught by verifying non-empty, readable output before re-running annotation, fixed by excluding 'meta' from the drop-depth tracking (it has no text content worth dropping anyway). All 5 candidates were re-annotated by fresh subagents on the corrected, cleaned text and ingested successfully afterward."
---

# Evidencia: defeito de markup HTML embutido encontrado e corrigido ao vivo

5/7 candidatos deste lote falharam por um defeito pre-existente no proprio
`texto_limpo` (markup HTML malformado, nao um erro de anotacao). Scan ao
vivo do pool completo (483 candidatos Sentenca/Acordao) confirma que isso
afeta ~37% dos candidatos restantes (114 com wrapper `<html>` completo, 63
com `</br>` solto). Um limpador HTML->texto puro foi escrito, testado e
corrigido ao vivo (um bug no primeiro rascunho zerava o texto de 3
candidatos por causa de `<meta>` nunca fechado) antes de reanotar e
ingerir os 5 documentos afetados com sucesso.
