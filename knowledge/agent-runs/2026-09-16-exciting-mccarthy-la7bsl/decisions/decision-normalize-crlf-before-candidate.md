---
type: AgentDecision
id: "2026-09-16-exciting-mccarthy-la7bsl-decision-normalize-crlf-before-candidate"
run_id: "2026-09-16-exciting-mccarthy-la7bsl"
goal_id: "2026-09-16-exciting-mccarthy-la7bsl-goal-djen-sample-batch5"
question: "The 4 TJMS candidates' verbatim-fidelity check failed with a small, uniform per-line diff (CRLF vs LF). Patching the tagged file's LF back to CRLF (the same class of fix as mg2tp1's NBSP patch) did not fix it -- the reconstructed text still came back as LF-only. Should the batch drop these 4 candidates, or should the fix target the candidate's source text instead of the tagged output?"
choice: "Normalize texto_limpo to LF before writing candidates.json for these 4 candidates, rather than asking the annotating subagent to reproduce CRLF, and keep all 4 in the batch."
rationale: "Root cause: scripts/ingest_juris_technique1_batch.py's reconstruction path wraps the tagged text in <text>...</text> and parses it with xml.etree.ElementTree, and XML 1.0 sec 2.11 mandates that a conformant parser normalize every CRLF and bare CR to LF during parsing -- this is unconditional per the XML spec, so no tagged-text patch can make ET's reconstruction ever contain a literal \\r again. The subagent's LF-only output was therefore already correct given the mechanism it was asked to work through; the source string itself is what cannot round-trip through XML unless it is LF-only to begin with. Normalizing texto_limpo to LF before it becomes the candidate's (and later the DocumentRecord's) canonical text makes both sides of the verbatim-fidelity check agree, with zero loss of content -- only the line-ending byte sequence changes, not any character span a category could anchor to."
---

# Decisao: normalizar CRLF->LF no texto_limpo antes de gerar o candidato

Descobri que XML normaliza `\r\n`/`\r` para `\n` obrigatoriamente na
analise (secao 2.11 da especificacao), entao nenhum ajuste no texto
marcado pelo subagente pode fazer a reconstrucao conter `\r` de volta.
A correcao correta e normalizar o `texto_limpo` de origem para LF antes
de vira-lo candidato/documento, nao pedir ao subagente para preservar
CRLF -- o mecanismo de reconstrucao via XML nunca poderia honrar isso.
