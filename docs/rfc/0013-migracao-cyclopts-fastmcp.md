# RFC 0013 — Migração das CLIs Typer para Cyclopts + FastMCP

- **Status:** Fase 1 e Fase 2 implementadas
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

### Fase 2 — camada de serviço (implementada)

Cada pacote ganhou um `service.py` com funções config→resultado, sem
Typer/Rich/`echo`; os `__main__.py` ficaram reduzidos a parsing de argv +
tradução do resultado em echo/exit code:

- **`djen_backup`**: `service.py` com `PipelineRunConfig`, `resolve_djen_url`,
  `resolve_ia_auth` (levanta `MissingCredentialsError` em vez de
  `typer.Exit`) e `run_pipeline` (chama `engine.run_sync`). Os side effects
  de import (`structlog.configure(...)`, reconfiguração de
  `stdout`/`stderr`) saíram do topo do módulo para `configure_runtime()`,
  chamada uma vez no callback `main()` — Click sempre invoca o callback do
  grupo antes de qualquer subcomando, então isso cobre `check`/`upload`/
  `drain`/`probe`/`reset` também. O bug de exit code descartado — só
  documentado no callback bare — na verdade existia igual em `check` e
  `upload`; os três agora fazem `raise typer.Exit(code=_run_pipeline(...))`.
- **`tjro_juris`**: `service.py` recebeu praticamente todo o corpo de
  `crawl`/`upload`/`status`/`consolidate` (a lógica já era quase
  config→resultado; só usava `typer.BadParameter`/`typer.echo` pontualmente).
  `crawl_bounds` agora levanta `ValueError` — framework-neutro —, e o
  `__main__.py` traduz para `typer.BadParameter` na borda da CLI.
- **`stj_acordaos`**: `service.py` com `download_one` (retorna
  `DownloadOutcome` em vez de `typer.echo` direto — o `__main__.py` traduz o
  outcome em mensagens), `upload_all` (idem, via `UploadResult`) e
  `manifest_summary`. `ia_key`/`ia_secret` deixaram de ser opção de CLI —
  `upload` não os aceita mais como parâmetro; `service.ia_credentials()` lê
  `IA_ACCESS_KEY`/`IA_SECRET_KEY` do ambiente diretamente.
- **`datajud`**: mesmo padrão — `service.enrich`/`facetas`/`manifest_status`
  sem Typer/echo, `ia_key`/`ia_secret` removidos da opção `enrich` (idem
  `ia_credentials()`).

**Não incluído nesta fase:** a bateria de testes framework-neutra (`argv →
configuração semântica`, camada de serviço mockada) descrita na Fase 1 como
o portão durável de Fase 4. Os testes de caracterização da Fase 1
(introspecção Click) foram atualizados apenas onde o contrato de parâmetros
mudou de propósito (remoção de `ia_key`/`ia_secret`) e continuam verdes para
o resto — mas ainda são a única rede de segurança de argv hoje. Construir a
bateria framework-neutra fica para o início da Fase 4, quando o formato dos
casos pode ser desenhado já sabendo a API real do Cyclopts.

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

## 3. Critérios de aceitação

**Fase 1:**
- Este RFC mergeado.
- Quatro arquivos de teste novos, um por pacote, cobrindo o argv literal dos
  5 workflows listados acima e o contrato de parâmetros correspondente.
- `pytest`, `ruff check`, `ruff format --check` verdes.
- Nenhuma mudança de código de produção.

**Fase 2 (implementada):**
- `service.py` por pacote, sem Typer/Rich/`echo`.
- Side effects de import mortos em `djen_backup` (`configure_runtime()`
  chamada do callback, não do topo do módulo).
- Bug de exit code descartado corrigido em `djen_backup` (callback bare,
  `check` e `upload`).
- `ia_key`/`ia_secret` fora da opção de CLI em `stj_acordaos`/`datajud` —
  só `IA_ACCESS_KEY`/`IA_SECRET_KEY` via ambiente.
- Testes de caracterização da Fase 1 continuam verdes (exceto os dois que
  documentavam o contrato antigo de credenciais, atualizados para afirmar a
  ausência da opção). `pytest`, `ruff check`, `ruff format --check` verdes.
- Nenhuma mudança de argv nos 5 workflows — `check`/`upload`/`drain`/
  `probe`/`reset`/`crawl`/`status`/`consolidate`/`download`/`facetas`
  mantêm nome, default e negação de flag idênticos ao que a Fase 1 travou.

## 4. Riscos

- **`--no-fail-fast`** é o caso mais frágil: se o Cyclopts gerar nome ou
  default diferente para o par negável, `collect-zips` passa a rodar com
  `fail_fast=True` e aborta no primeiro 403 do CloudFront — regressão
  silenciosa, visível só na próxima execução (a cada 20 min).
- **`ruff select=["ALL"]`** e **`vulture --min-confidence 100`** sinalizaram
  código novo durante a extração da Fase 2 (complexidade, imports não
  utilizados, docstrings) — resolvido com refino local (ex.: `enrich` do
  `datajud` dividido em `_pending_cnjs`/`_upload_step` para ficar sob o
  limite de complexidade) em vez de whitelist ampla.
- A bateria framework-neutra de argv (ver Fase 2 acima) ainda não existe —
  até que exista, a Fase 4 depende só da introspecção Click da Fase 1 mais
  os testes unitários de `service.py`, nenhum dos quais sobrevive à troca de
  framework sem edição.
