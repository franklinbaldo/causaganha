---
type: AgentEvidence
id: "2026-09-05-exciting-mccarthy-qnpypw-evidence-web-sql-contract-parity"
run_id: "2026-09-05-exciting-mccarthy-qnpypw"
goal_id: "2026-09-05-exciting-mccarthy-qnpypw-goal-close-1042-catalog-parity-proof"
kind: "runtime"
reference: "Literal SQL from web/src/lib/processoCnj.ts (buildIndiceSql, buildDjenSql, buildJurisSql, buildDatajudSql), executed via native DuckDB+httpfs against the arquivo_ia_url values discovered for CNJ 0000001-66.2018.8.22.0001 in the published indice_processual.parquet"
summary: "Executed the frontend's own SQL query strings verbatim (not a reimplementation) against the real published parquets (djen-2026-01-29/comunicacoes.parquet; 8 tjro-juris-2020/* parquets; datajud-tjro/datajud-capa-tjro.parquet). Result field-for-field identical to processo-consultar-live: djen=(n_publicacoes=1, primeira=ultima=2026-01-29, tribunais=[TJRO]); juris=(n_documentos=8, tipos=[VOTO,ACORDAO,RELATORIO,EMENTA], data_julgamento=2020-10-22, orgao='2a Camara Civel', relator='MARCOS ALAOR DINIZ GRANGEIA', classe='APELACAO CIVEL', url matches); datajud=(classe_oficial='Apelacao Civel', assuntos='Perdas e Danos', orgao_julgador='GABINETE DESA. INES MOREIRA', grau=G2, ultima_atualizacao=2026-08-18T19:22:52.292000Z). Full browser render of the deployed /processo page was attempted but blocked by this session's sandboxed headless-Chromium failing TLS to any external host (net::ERR_CONNECTION_RESET), confirmed environment-wide via curl to $HTTPS_PROXY/__agentproxy/status (systemic ws_closed_mid_exchange failures, including to unrelated hosts like www.google.com) rather than specific to this site."
---

# Evidência — paridade de contrato SQL MCP × web

O mesmo CNJ, consultado com a string SQL literal que `/processo` executa via DuckDB-WASM, produz resultado idêntico campo a campo ao da tool MCP `processo_consultar`. Render real em browser não foi possível neste sandbox (limitação de proxy confirmada, não do produto); documentado como lacuna de ambiente, não de produto.
