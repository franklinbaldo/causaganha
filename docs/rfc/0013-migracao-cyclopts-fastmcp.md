# RFC 0013 — Migração das CLIs Typer para Cyclopts + FastMCP

- **Status:** Proposto (Fase 1 implementada neste PR)
- **Data:** 2026-07-21
- **Base:** comparação de arquitetura com o repo irmão `pink` (mesma stack alvo:
  Cyclopts + FastMCP, tools declaradas uma vez, CLI como despachante genérico
  sobre uma camada de serviço)

## 1. Problema

Os quatro pacotes CLI do repositório (`djen_backup`, `tjro_juris`,
`stj_acordaos`, `datajud`) usam Typer. A intenção é migrar para Cyclopts
(CLI) e expor as operações de consulta como tools FastMCP, seguindo o modelo
já validado no `pink`. Um diagnóstico da topologia atual revelou que a
migração não é troca mecânica de framework:

- **A assinatura da CLI é contrato de produção.** Cinco jobs agendados
  chamam as CLIs com argv exato:
  - `collect-zips.yml` (`*/20 * * * *`) → `djen-backup --deadline-minutes N
    --workers N --start-date D --use-proxy --no-fail-fast [--end-date D]
    [--tribunal X]` — **sem subcomando**.
  - `upload-backlog.yml` → `djen-backup drain --workers 24 --batch-size 200
    --deadline-minutes 55 --use-proxy`.
  - `tjro-sync.yml` → `tjro-juris crawl data/tjro-juris [--ano N] [--mes M]
    [--desde-ano N] [--tipo X ...]`, depois `upload`, depois `status`.
  - `stj-sync.yml` → `stj-acordaos download --data-dir D --manifest-path P`,
    depois `upload` (mesmos parâmetros + credenciais IA), depois `status`.
  - `datajud-enrich.yml` → `datajud enrich --tribunal T --limit N
    [--skip-upload]`, depois `status --data-dir D`.
- **O callback de `djen-backup` usa `invoke_without_command=True`** — padrão
  sem equivalente direto em Cyclopts; o job mais frequente (a cada 20 min)
  depende dele.
- **Duas declarações do mesmo parâmetro (`use_proxy`) divergem no mesmo
  arquivo**: o callback bare gera `--use-proxy/--no-use-proxy` (Typer infere
  o par automaticamente quando não há string explícita), mas `drain` passa
  `"--use-proxy"` explicitamente e suprime a negação. Uma migração mecânica
  apaga essa diferença sem ninguém notar.
- **Credenciais como opção de CLI com `envvar=`** (`ia_key`/`ia_secret` em
  `stj_acordaos`/`datajud`) — se a migração for mecânica, esses parâmetros
  viram campo de schema exposto a um agente MCP.
- **Bug latente**: `djen_backup/__main__.py` descarta o retorno de
  `_run_pipeline` no callback bare — o exit code do processo nunca reflete o
  resultado real do sync, nem mesmo `KeyboardInterrupt` (130).
- **Side effects de import**: reconfiguração de `stdout`/`stderr` e
  `structlog.configure(...)` global no topo de `djen_backup/__main__.py` —
  um servidor MCP que importe esse módulo reconfigura o processo inteiro.
- **Lint sem escape hatch fácil**: `ruff.toml` usa `select = ["ALL"]` e
  `vulture --min-confidence 100` roda sem whitelist generosa — código novo de
  serviço/tools vai brigar com os dois durante a extração.

`segmenter-dataset` e `causaganha.consolidate` (Typer) **não são chamados por
nenhum workflow** — o consolidate real em produção é
`scripts/pipeline/consolidate.py`, `argparse`, fora do escopo Typer. Ficam de
fora desta migração.

## 2. Proposta

Quatro fases sequenciais, cada uma um PR, na ordem abaixo. Trocar o framework
por último significa fazer a parte de maior risco depois que todo o resto já
estiver provado.

### Fase 1 — este PR: rede de segurança

Testes de caracterização por pacote, sem tocar em código de produção:

1. **Contrato de parâmetros** das subcommands exercidas por cron — `opts`,
   `secondary_opts` (flags negáveis), `envvar`, `multiple` — via introspecção
   Click (`typer.main.get_command(app)`), não execução.
2. **Parsing exato do argv literal** de cada invocação de workflow, via
   `Command.make_context` (só parsing — nunca invoca o callback, sem rede,
   sem I/O), com o `ctx.params` resultante comparado ao valor esperado hoje.

Esses testes travam o comportamento atual do Typer, mas fazem isso via
introspecção de `Command`/`Parameter` do Click (`opts`, `secondary_opts`,
`param.type`, `Command.make_context`) — infraestrutura que desaparece com o
Cyclopts. Não sobrevivem verbatim à Fase 4: são caracterização transitória
do Typer, não o portão de aceitação durável da migração. Congelam também
detalhes de implementação do Click sem relevância para os workflows (`tuple`
vs. `list`, `Path` vs. `str` cru, a representação interna de
`secondary_opts`), o que os torna frágeis a mudanças que não afetam nenhum
cron.

O portão durável — a construir na Fase 2, depois que a camada de serviço
existir — é framework-neutro: casos no formato `argv → configuração
semântica esperada`, exercitando a CLI com a camada de serviço mockada e
comparando a configuração entregue a ela. Typer e Cyclopts precisam então
apenas de um adaptador fino para rodar os mesmos casos; a Fase 4 reexecuta
essa bateria (não a desta Fase 1) contra a CLI já migrada.

### Fase 2 — camada de serviço

Extrair, por pacote, funções de config→resultado sem Typer/Rich/`echo`
(mesmo padrão do `service/` do pink). Matar os side effects de import.
Resolver o bug de exit code descartado. Tirar `ia_key`/`ia_secret` de opção
de CLI — só env/keyring.

### Fase 3 — tools MCP

Tools sobre a camada de serviço, começando pelas de leitura sem efeito
destrutivo: `datajud status`/`facetas`, `tjro-juris status`, `stj-acordaos
status`, consultas de manifest. Operações de ingestão/upload de longa duração
(o sync completo, `drain`, `consolidate`) ficam só na CLI/CI — nunca viram
tool.

### Fase 4 — Typer → Cyclopts

Com os testes framework-neutros da Fase 2 como portão (não os desta Fase 1,
que são introspecção Click e não sobrevivem à troca de framework):
re-executar contra a CLI migrada antes de mudar qualquer workflow. O
callback bare de `djen-backup` precisa de um `default_command` explícito
equivalente a `invoke_without_command=True`.

## 3. Critérios de aceitação (desta Fase 1)

- Este RFC mergeado.
- Quatro arquivos de teste novos, um por pacote, cobrindo o argv literal dos
  5 workflows listados acima e o contrato de parâmetros correspondente.
- `pytest`, `ruff check`, `ruff format --check` verdes.
- Nenhuma mudança de código de produção.

## 4. Riscos

- **`--no-fail-fast`** é o caso mais frágil: se o Cyclopts gerar nome ou
  default diferente para o par negável, `collect-zips` passa a rodar com
  `fail_fast=True` e aborta no primeiro 403 do CloudFront — regressão
  silenciosa, visível só na próxima execução (a cada 20 min).
- **`ruff select=["ALL"]`** e **`vulture --min-confidence 100`** vão sinalizar
  código novo/temporariamente órfão durante a extração da Fase 2 — orçar
  tempo de whitelist, não tratar como bloqueio de escopo.
- Testes de caracterização não cobrem execução (rede, I/O) — o bug de exit
  code descartado só será corrigido/verificado na Fase 2, não antes.
