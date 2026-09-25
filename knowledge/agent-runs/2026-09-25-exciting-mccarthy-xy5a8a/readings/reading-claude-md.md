---
type: AgentReading
id: "2026-09-25-exciting-mccarthy-xy5a8a-reading-claude-md"
run_id: "2026-09-25-exciting-mccarthy-xy5a8a"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Leitura integral no inicio da rodada. O trabalho selecionado (estender o marcador tipo_conteudo=untrusted_legal_text, ja em producao para publicacoes_buscar/decisoes_buscar, para os campos de texto judicial de processo_consultar -- DocumentoResult.resumo e StjAcordaoResult.tese/ementa em src/causaganha_mcp/tools/processo.py) nao toca o motor djen-backup, a fronteira CSS/Panda nem os contratos .qmd -- nenhuma dessas secoes do guia restringe ou orienta esta mudanca. Regras de estilo Python aplicaveis: 'No blind except Exception' (nao introduzido -- nenhum novo bloco de excecao), TRY300/TRY301/TRY401 (nao aplicavel, nenhuma funcao com raise nova), ruff estrito (verificado com uv run ruff check/format --check, limpo). TDD como fluxo padrao seguido: RED com 4 testes novos contra o campo tipo_conteudo inexistente antes de qualquer mudanca em producao, GREEN apos adicionar o campo aos dois modelos Pydantic."
---

# Leitura: CLAUDE.md

Releitura integral do guia do projeto no inicio da rodada, conforme
exigido pelo contrato `AgentRun`. Nenhuma das arquiteturas centrais do
guia (djen-backup/manifest, fronteira CSS/Panda, contratos `.qmd`) se
aplica ao trabalho desta rodada, que fica inteiramente em
`src/causaganha_mcp/tools/processo.py` e seus testes. As regras de estilo
Python gerais (ruff estrito, sem `except Exception` cego, TDD como fluxo
padrão) foram seguidas e verificadas.
