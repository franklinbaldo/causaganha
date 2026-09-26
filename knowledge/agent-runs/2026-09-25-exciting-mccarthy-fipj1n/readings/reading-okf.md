---
type: AgentReading
id: "2026-09-25-exciting-mccarthy-fipj1n-reading-okf"
run_id: "2026-09-25-exciting-mccarthy-fipj1n"
subject: "okf_knowledge"
reference: "docs/SECURITY_THREAT_MODEL.md; .wisk/knowledge/experiences/handoffs/handoff-issue-1610-artifact-url-followup.md; knowledge/agent-runs/2026-09-25-exciting-mccarthy-xy5a8a/run.md"
finding: "docs/SECURITY_THREAT_MODEL.md (129 linhas, lido por completo) já estava datado de 2026-09-25 e TM-11 já constava 'Fechado — #1616' (mesclado pela rodada anterior xy5a8a). TM-03/TM-04 (ambas apontando para #1610) documentam extensivamente o que já foi feito (validador central de URL Python+TS, checagem de coerência de tribunal, KV_METADATA para djen) e o que resta pendente e aceito (KV_METADATA equivalente para juris/stj/datajud; hash/row-count de conteúdo completo, fora de alcance por decisão). O handoff Wisk arquivado (.wisk/.../handoff-issue-1610-artifact-url-followup.md, archived_at 2026-09-25T05:38:27Z) documenta uma auditoria prévia extensa de #1610 que fechou o lado TypeScript (PR #1624) e o gap em scripts/render_queries.py, explicitamente descartando causaganha.decisoes.published.resolve_juris_urls_for_cnj como 'not the same threat class' (verificado correto por esta sessão: usa arquivo_ia_url só para Python set membership, nunca SQL) — mas esse handoff não menciona _juris_url/ManifestJuris, o gap real que esta rodada encontrou e fechou. run.md da rodada anterior (xy5a8a, mesclou PR #1641 fechando #1616) tinha next_move explícito pedindo para uma rodada futura reler o threat model por completo e confirmar quais linhas TM-* ainda apontam para issues abertas — exatamente o que esta rodada fez, confirmando que só #1610 resta aberta entre as 10 issues de segurança da matriz."
---

# Leitura: conhecimento OKF relevante

Releitura completa de `docs/SECURITY_THREAT_MODEL.md`, do handoff Wisk
arquivado sobre o follow-up de `#1610`, e do `run.md` da rodada
imediatamente anterior (`xy5a8a`) para continuidade. A combinação das
três fontes apontou precisamente para o gap não auditado que esta rodada
fechou: `ManifestJuris`/`_juris_url` nunca haviam sido examinados pelas
auditorias anteriores de `#1610`.
