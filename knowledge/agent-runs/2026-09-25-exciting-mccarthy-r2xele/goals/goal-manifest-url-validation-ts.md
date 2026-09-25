---
type: AgentGoal
id: "2026-09-25-exciting-mccarthy-r2xele-goal-manifest-url-validation-ts"
run_id: "2026-09-25-exciting-mccarthy-r2xele"
goal: "Fechar a metade TypeScript de #1610 (security/archive): validar arquivo_ia_url (descoberto em indice_processual.parquet, um manifesto canonico) antes de interpola-lo em read_parquet([...])/parquet_kv_metadata([...]) em web/src/lib/processoCnj.ts, espelhando a politica ja implementada e testada no lado Python por causaganha.processos.service._validate_artifact_url (#1622)."
rationale: "arquivo_ia_url vem de um artefato canonico (indice_processual.parquet), nao de input do usuario, mas um manifesto comprometido hoje controla tanto o destino de rede (host/scheme arbitrario em read_parquet) quanto pode quebrar o literal SQL via aspas simples nao escapadas -- exatamente a mesma classe de ameaca que #1622 ja fechou do lado Python (service.py:_fonte_urls). O corpo de #1622 registra explicitamente esta metade TypeScript como fora de escopo/follow-up. E self-contained (um unico modulo, sem credenciais externas, sem infra de deploy), com uma implementacao de referencia ja revisada e mesclada no mesmo repositorio -- risco de design minimo, только espelhar a politica already-proven."
success_signal: "web/src/lib/processoCnj.test.ts ganha casos que RED-confirmam contra o codigo anterior (validateArtifactUrl nao existe) e GREEN-confirmam apos a correcao: (1) URLs https://archive.org/download/.../*.parquet validas passam inalteradas; (2) um path local sem scheme (usado pelos fixtures de teste) passa inalterado; (3) uma URL com aspas simples embutida e rejeitada (ArtifactUrlError); (4) host/scheme fora do allowlist (http://, file://, host estranho) e rejeitado; (5) query/fragment na URL e rejeitado; (6) path fora do padrao esperado (prefixo /download/, sufixo .parquet) e rejeitado; (7) fonteUrls() descarta uma URL invalida do indice e registra um aviso em vez de deixa-la chegar a read_parquet/parquet_kv_metadata, com um teste de integracao em buscarProcesso() mostrando que um indice envenenado degrada a fonte para ausente + aviso, sem lancar excecao (paralelo direto de test_poisoned_manifest_url_degrades_source_instead_of_crashing no lado Python). npx vitest run (suite web completa) fica verde; tsc/eslint (o que o repo rodar) fica limpo."
status: "achieved"
---

# Objetivo: espelho TypeScript da validacao de URL de manifesto (#1610)

Trabalho principal desta rodada, selecionado apos confirmar (leitura de
issues + leitura OKF) que a metade Python de `#1610` ja foi fechada por
`#1622` e que a metade TypeScript (`web/src/lib/processoCnj.ts`, consumida
por `ProcessoLookup.svelte`/`/processo`) permanece aberta como follow-up
explicito daquela mesma PR. Ver `decision_ids`/`evidence_ids`/`check_ids`
para o processo TDD completo.
