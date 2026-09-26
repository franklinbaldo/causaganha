---
type: AgentDecision
id: "2026-09-25-exciting-mccarthy-5txmmk-decision-identity-metadata-not-digest-manifest"
run_id: "2026-09-25-exciting-mccarthy-5txmmk"
goal_id: "2026-09-25-exciting-mccarthy-5txmmk-goal-reconcile-identity-check"
question: "Para fechar #1652 item (3), esta rodada deveria adotar/adaptar o desenho da PR externa #1645 (manifesto JSON estatico com digest SHA-256 por arquivo, config/reconcile-remote-sources.json, mantido a mao), ou reusar o mecanismo de identidade ja embutido no rodape Parquet (KV_METADATA causaganha.schema_version/causaganha.item_id, TM-04)?"
choice: "Reusar o mecanismo KV_METADATA ja existente (TM-04), aplicado em scripts/reconcile_processos.py::fetch_juris_from_ia/fetch_datajud_from_ia. Nao adotada a PR #1645."
rationale: "A PR #1645 (a) esta desatualizada contra main: foi escrita contra uma versao pre-#1657 de _discover_juris_items (ainda usa advancedsearch.php, ja removido); seu CI aparece 'pending' com 0 status, sinal de que nunca rodou de verdade contra o main atual. (b) O desenho de manifesto vazio-por-padrao (config/reconcile-remote-sources.json = {'juris': [], 'datajud': []}) quebraria silenciosamente a reconciliacao em producao: JURIS/DataJud sao crawls continuos (novo arquivo a cada execucao do pipeline de coleta), entao um digest SHA-256 hand-maintained exigiria curadoria manual continua antes de qualquer arquivo novo ser aceito -- o oposto do objetivo de manter o indice atualizado automaticamente. (c) O projeto ja resolveu o problema equivalente para djen ha varias rodadas (TM-04, schema_registry.kv_metadata_for_export + service._validar_metadata_djen) e, nesta mesma data, para juris e datajud no lado de escrita (rodadas qjwekj/r0zxiq, PRs #1648/#1651) -- o rodape Parquet ja se autodescreve com item_id+schema_version, gravado pelo proprio pipeline de coleta no momento da escrita, sem exigir curadoria externa. Aplicar essa mesma verificacao no ponto de ingestao (reconcile) fecha o item (3) com um mecanismo ja testado, ja usado no lado de consulta MCP, e que nao trava o pipeline continuo -- superior ao desenho de #1645 tanto em seguranca (auto-verificavel na fonte, nao dependente de curadoria externa que pode ficar desatualizada) quanto em manutenibilidade."
---

# Decisão: identidade via KV_METADATA no rodapé, não manifesto de digests externo

O item (3) de #1652/TM-16 pede "verificação de digest (SHA-256) de
arquivos remotos contra um manifesto de fontes confiáveis antes de
tratá-los como canônicos". A PR externa #1645 interpreta isso
literalmente (manifesto JSON hand-maintained), mas esse desenho é
frágil contra o crawl contínuo do projeto e está desatualizada contra
o `main` atual. Esta rodada fecha o mesmo requisito com o mecanismo
de identidade auto-verificável que o projeto já usa nos lados de
escrita (TM-04) e consulta — aplicado agora também no ponto de
ingestão.
