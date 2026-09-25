---
type: AgentReading
id: "2026-09-25-exciting-mccarthy-e0vvbh-reading-claude-md"
run_id: "2026-09-25-exciting-mccarthy-e0vvbh"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Leitura integral no início da rodada. Regras aplicáveis ao trabalho selecionado (TM-04 de #1610, coerência de tribunal entre indice_processual.parquet e arquivo_ia_url): TRY300/TRY301/TRY401 (nenhum raise novo em bloco try; ArtifactProvenanceError é levantada fora de qualquer try em _validar_tribunal_coerente), 'não adicionar validação para cenários que não podem acontecer' (a checagem só age quando a URL já bate com o padrão IA conhecido -- URLs locais de teste ou de fontes sem partição por tribunal retornam None e não são bloqueadas), 'não usar except Exception amplo' (o novo except em _fonte_urls é ArtifactProvenanceError, tipo específico, ao lado do ArtifactUrlError já existente). A CSS token boundary e as regras de djen-backup/sync-manifest não se aplicam (trabalho é Python puro em causaganha/processos/service.py + um ajuste mínimo de paridade em web/src/lib/processoCnj.ts, sem tocar Panda/Svelte/sync-manifest). Confirmada a armadilha do run.md em rascunho: completed_at ficará vazio até o fim da rodada, o que muda temporariamente a forma inferida dos schemas Zod/domain-model gerados -- não regenerar web/src/lib/processoConsultar.gen.ts nem src/causaganha_mcp/_generated/domain_models.py para 'corrigir' isso."
---

# Leitura: CLAUDE.md

Releitura integral do guia do projeto no início da rodada, conforme exigido
pelo contrato `AgentRun`. Nenhuma regra do arquivo bloqueia ou reorienta o
trabalho selecionado; a advertência sobre os três testes que falham
enquanto este `run.md` está em rascunho foi lida e será respeitada sem
regenerar os arquivos gerados por OKF.
