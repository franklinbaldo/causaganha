---
type: AgentEvidence
id: "2026-09-05-exciting-mccarthy-qnpypw-evidence-processo-consultar-live"
run_id: "2026-09-05-exciting-mccarthy-qnpypw"
goal_id: "2026-09-05-exciting-mccarthy-qnpypw-goal-close-1042-catalog-parity-proof"
kind: "runtime"
reference: "uv run python -c 'causaganha.processos.service.buscar_processo(\"0000001-66.2018.8.22.0001\", ...)' against https://archive.org/download/causaganha-dashboard/indice_processual.parquet"
summary: "Live, non-fixture call to the exact function backing the processo_consultar MCP tool, for a real CNJ discovered (via duckdb+httpfs GROUP BY over the published indice_processual.parquet) to have records in djen+juris+datajud simultaneously. Result: fontes_presentes=[datajud, djen, juris]; djen.n_publicacoes=1 (2026-01-29, TJRO); juris.n_documentos=8 (VOTO/ACORDAO/EMENTA/RELATORIO, 2a Camara Civel, rel. Marcos Alaor Diniz Grangeia, Apelacao Civel); datajud.classe_oficial='Apelacao Civel', assuntos='Perdas e Danos', orgao_julgador='GABINETE DESA. INES MOREIRA', grau=G2, ultima_atualizacao=2026-08-18T19:22:52.292000Z."
---

# Evidência — `processo_consultar` ao vivo, CNJ multi-fonte real

CNJ `0000001-66.2018.8.22.0001` consultado diretamente pela função de produto (não fixture), lendo o índice publicado no run mais recente. Resultado completo registrado para comparação com o contrato SQL do frontend.
