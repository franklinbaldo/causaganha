---
type: AgentDecision
id: "2026-09-16-exciting-mccarthy-jyqinl-decision-skip-html-entity-encoded-candidates"
run_id: "2026-09-16-exciting-mccarthy-jyqinl"
goal_id: "2026-09-16-exciting-mccarthy-jyqinl-goal-djen-sample-batch2"
question: "TJTO (285645419) and TJGO (543565569) both failed twice: the first attempt at each introduced a genuine annotation defect (spurious HTML wrapper; HTML-entity substitution), but after a targeted redo, both failed again -- TJTO with an XML parse error on an undefined entity, TJGO with a massive verbatim-fidelity mismatch (12358 vs 14974 chars). Root-caused: both candidates' own `texto_limpo` field in data/segmenter_samples/*.jsonl is not actually HTML-entity-decoded -- it contains hundreds of literal `&Aacute;`/`&ccedil;`/`&nbsp;`/etc. sequences as raw text (confirmed live: 394 such sequences in TJGO's candidate alone). My own redo instructions were wrong for these two documents: I told the TJGO subagent to always use literal UTF-8 characters and never HTML entities, which is correct when the source itself uses real UTF-8 letters, but here the source's own stored text is the dirty HTML-entity string -- 'verbatim' means preserving that literal string (with each `&` XML-escaped to `&amp;` so the tagged output still parses), not decoding it into the character it was presumably meant to represent. Should this round attempt a third redo with corrected instructions, or drop these two candidates from batch2 and record the finding for a future round?"
choice: "Drop TJTO and TJGO from this batch. Ingest the other 6 (TJPB, TJRN, TJRJ, TJMA, TJBA, TJRR -- all real, all newly represented tribunals) and record this as a genuine, previously-unknown data-quality finding in knowledge/backlog/issue-1050.md: some data/segmenter_samples/*.jsonl candidates carry un-decoded HTML entities in texto_limpo, which the current Technique 1 annotation prompt has no instruction for, and which cost two full redo cycles to root-cause here."
rationale: "A third redo per document would need a materially different, untested instruction (escape literal source ampersands as &amp;entity; rather than decoding or rejecting them) with no guarantee of success on the first try, given two consecutive misses already -- the marginal ceiling gain from these two specific documents (any two additional documents move the val/test ceiling by roughly the same increment as any other two, since the ceiling is total_eligible * ratio rounded) does not justify a third round-trip in this session when 6 other genuine, verified documents are already ready to ship. #1050's own criterion is corpus growth and tribunal diversity, both already satisfied by the 6 successful documents (6 new tribunals: TJPB, TJRN, TJRJ, TJMA, TJBA, TJRR). Recording the finding (rather than silently dropping the two candidates) means a future batch either preprocesses/HTML-decodes texto_limpo before building candidates.json, or gives subagents an explicit worked example for escaping literal source ampersands -- avoiding the same two-redo detour."
---

# Decisao: descartar TJTO/TJGO deste lote, registrar achado de qualidade de dados

Ambos falharam duas vezes por uma causa raiz comum e nova (nao vista no
lote 1): `texto_limpo` de alguns candidatos em `data/segmenter_samples/`
contem entidades HTML literais nao decodificadas (`&Aacute;`, `&nbsp;`,
etc.) como texto puro. Minha propria instrucao de correcao para o TJGO
("nunca use entidades HTML") estava errada para este caso especifico --
"verbatim" aqui significa preservar a string suja original, escapando cada
`&` como `&amp;` para o XML continuar valido, nao decodificar para o
caractere pretendido. Descartar os dois desta rodada e registrar o achado
para uma rodada futura evita um terceiro ciclo de redo sem garantia de
sucesso.
