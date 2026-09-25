---
type: AgentGoal
id: "2026-09-25-exciting-mccarthy-5txmmk-goal-reconcile-identity-check"
run_id: "2026-09-25-exciting-mccarthy-5txmmk"
goal: "Fechar #1652 (TM-16) item (3): scripts/reconcile_processos.py::fetch_juris_from_ia/fetch_datajud_from_ia devem verificar a identidade (causaganha.schema_version/causaganha.item_id) do rodape KV_METADATA de todo arquivo JURIS/DataJud baixado do fallback IA, antes de aceita-lo como fonte canonica para indice_processual.parquet -- reusando o mesmo mecanismo de identidade auto-verificavel que tjro_juris.service e datajud.archive ja gravam no lado de escrita (TM-04) e que causaganha.processos.service ja le no lado de consulta."
rationale: "#1652 documenta 3 superficies de descoberta/download IA sem allowlist/verificacao. Itens (1) e (2) ja fechados por rodadas anteriores desta mesma data. O item (3) permanece aberto: mesmo com a identidade do ITEM ja allowlisted pelo manifesto do projeto (fix do item 2), o ARQUIVO baixado de dentro desse item nunca teve sua identidade verificada antes de virar linha em indice_processual.parquet -- um item legitimo comprometido (ou um arquivo trocado sob o mesmo nome) ainda seria aceito silenciosamente. A PR externa #1645 propoe um manifesto JSON de digests SHA-256 mantido a mao, mas esta desatualizada (pre-#1657) e, por ser vazio-por-padrao, quebraria a reconciliacao em producao ate populacao manual continua -- inadequado para um pipeline de crawl continuo. O projeto ja resolveu o problema equivalente para djen (TM-04, ha varias rodadas) e para juris/datajud no lado de escrita (rodadas qjwekj/r0zxiq, hoje): o rodape Parquet ja se autodescreve. Aplicar essa mesma verificacao no ponto de ingestao fecha o item (3) sem inventar um mecanismo novo nem depender de curadoria manual externa."
success_signal: "Testes novos em tests/test_reconcile_processos.py provam RED->GREEN: (1) um shard JURIS baixado do fallback IA sem KV_METADATA de identidade e rejeitado (SourceDataError) por fetch_juris_from_ia; (2) um shard JURIS cujo item_id no rodape diverge do item do qual foi baixado e rejeitado; (3) um capa DataJud cujo item_id no rodape diverge do item/tribunal do qual foi baixado e rejeitado; (4) todos os testes existentes de fluxo feliz (fetch_juris_from_ia/fetch_datajud_from_ia/reconcile) permanecem verdes apos os fixtures passarem a gravar o KV_METADATA correto (juris via novo parametro item= em _juris_parquet; datajud ja gravava via write_capa_parquet, sem mudanca de fixture necessaria). Suite completa (uv run pytest -q) verde. uv run ruff check/format --check limpos. docs/SECURITY_THREAT_MODEL.md TM-16 e a propria issue #1652 atualizados para fechar o item (3)."
status: "achieved"
---

# Goal: verificação de identidade no fetch remoto de JURIS/DataJud

Fecha o item (3), última superfície aberta de #1652/TM-16: aplica ao
ponto de ingestão (`scripts/reconcile_processos.py`) o mesmo mecanismo
de identidade auto-verificável (KV_METADATA no rodapé Parquet) que o
projeto já usa nos lados de escrita e consulta, em vez de um manifesto
de digests externo mantido à mão.
