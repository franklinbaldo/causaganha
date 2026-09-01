# MCP: experiência orientada a jobs

Este documento é a especificação de implementação da segunda fatia do ciclo de duas superfícies.

## Objetivo

O catálogo MCP deve permitir que um agente sem conhecimento prévio do repositório escolha e componha tools pelo trabalho que precisa realizar, não pela topologia dos pipelines.

## Jobs públicos

O catálogo deve tornar evidentes cinco jobs:

1. **Consultar um processo** — obter o snapshot multi-fonte conhecido para um CNJ, com proveniência e época do dataset.
2. **Consultar estado** — quando houver suporte live, obter metadata/movimentação atual sem inferir teor.
3. **Buscar publicações** — localizar comunicações DJEN por CNJ, OAB, parte, texto e período.
4. **Buscar teor** — localizar decisão/acórdão/documento JURIS/STJ sem exigir schema de origem.
5. **Entender cobertura** — qualificar ausência, freshness e limitações antes de concluir que algo não existe.

## Hierarquia do catálogo

### Primeira classe: produto

Tools de produto devem usar nomes e descrições orientados ao job e responder com vocabulário estável do domínio:

- `resumo`;
- `evidencias` ou blocos equivalentes;
- `natureza`: `arquivo`, `estado`, `teor`;
- fonte/proveniência;
- época/freshness;
- `limitacoes`;
- `next_actions` quando outra consulta for semanticamente justificada.

### Segunda classe: operação

Tools `*_status` existem para diagnóstico de mantenedor e observabilidade. Elas não são pré-requisito para perguntas normais e suas descrições devem deixar isso explícito.

## Regra de composição

Uma tool não deve chamar outra fonte silenciosamente apenas para produzir uma resposta aparentemente completa.

Exemplo:

- `processo_consultar` continua snapshot-only;
- se o snapshot estiver antigo e a pergunta exigir estado atual, retorna uma próxima ação explícita;
- movimento DataJud chamado “Sentença” não autoriza inferir o conteúdo da sentença;
- presença de documento JURIS/STJ é evidência de teor somente para o conteúdo efetivamente retornado.

## Agent-experience gate

A implementação desta fatia deve adicionar um teste/eval pequeno que apresente somente catálogo, schemas e descriptions a um consumidor simulado e verifique ao menos que:

- pergunta por CNJ escolhe `processo_consultar`;
- pergunta por publicação escolhe a busca DJEN;
- pergunta por fundamento/ementa/decisão escolhe a superfície de teor quando disponível;
- pergunta “isso significa que não existe?” não é respondida apenas com uma tool operacional de status;
- tools `*_status` não dominam instruções gerais do servidor.

O gate não deve hardcodar conhecimento de Parquet, Internet Archive, nomes de manifests ou schemas internos no consumidor.

## Dependências

Esta fatia implementa a direção de #914 e #891. A superfície de teor é entregue na próxima PR da stack, baseada em #918.
