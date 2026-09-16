---
type: AgentDecision
id: "2026-09-16-exciting-mccarthy-la7bsl-decision-normalize-crlf-before-candidate"
run_id: "2026-09-16-exciting-mccarthy-la7bsl"
decision: "For the 4 TJMS candidates (raw texto_limpo uses CRLF line endings exclusively), normalize texto_limpo to LF before writing candidates.json, rather than asking the annotating subagent to reproduce CRLF verbatim."
reason: "The first verbatim-fidelity check on these 4 candidates failed with a uniform, small per-line diff (CRLF vs LF). The natural first hypothesis -- that the subagent silently normalized line endings while retyping the source, the same class of defect mg2tp1 patched (NBSP->space) -- was tested by patching the tagged file's LF back to CRLF and re-checking. It still failed identically. Root cause: scripts/ingest_juris_technique1_batch.py's reconstruction path wraps the tagged text in `<text>...</text>` and parses it with `xml.etree.ElementTree`, and XML 1.0 sec 2.11 mandates that a conformant parser normalize every CRLF and bare CR to LF during parsing -- this is not a bug in ET, it is unconditional per the XML spec, so no tagged-text patch can make ET's reconstruction ever contain a literal \\r again. The subagent's LF-only output was therefore already correct given the mechanism it was asked to work through; the source string itself is what cannot round-trip through XML unless it is LF-only to begin with. Normalizing texto_limpo to LF before it becomes the candidate's (and later the DocumentRecord's) canonical text makes both sides of the verbatim-fidelity check agree, with zero loss of content (only the line-ending byte sequence changes, not any character span a category could anchor to)."
alternatives_considered: "(1) Drop the 4 TJMS candidates from this batch and only ingest the 3 CRLF-free ones (TJPA x2, TJPI x1) -- rejected because it would discard a genuinely new 25th tribunal for a mechanical artifact with a clean, principled fix rather than a real annotation defect. (2) Try to make the ingestion script preserve CRLF by avoiding XML parsing for reconstruction -- rejected as out of scope for this round: it would mean changing the RFC 0012 Sec 8 production technique (tag-inline via XML) for a line-ending edge case that a simple source-side normalization already resolves without touching the mechanism every prior batch relies on."
---

# Decisao: normalizar CRLF->LF no texto_limpo antes de gerar o candidato

Descobri que XML normaliza `\r\n`/`\r` para `\n` obrigatoriamente na
analise (secao 2.11 da especificacao), entao nenhum ajuste no texto
marcado pelo subagente pode fazer a reconstrucao conter `\r` de volta.
A correcao correta e normalizar o `texto_limpo` de origem para LF antes
de vira-lo candidato/documento, nao pedir ao subagente para preservar
CRLF -- o mecanismo de reconstrucao via XML nunca poderia honrar isso.
