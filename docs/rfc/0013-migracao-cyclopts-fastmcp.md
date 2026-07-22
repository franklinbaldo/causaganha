# RFC 0013 — Migração das CLIs Typer para Cyclopts + FastMCP

- **Status:** Fase 1, Fase 2, Fase 2.5, Fase 3A e Fase 3B implementadas
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

Quatro fases sequenciais, cada uma um PR, na ordem abaixo — mais uma Fase
2.5 inserida depois que a Fase 2 expôs uma lacuna concreta (ver abaixo).
Trocar o framework por último significa fazer a parte de maior risco depois
que todo o resto já estiver provado.

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

O portão durável — construído na Fase 2.5, depois que a camada de serviço
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

**Não incluído nesta fase, endereçado na Fase 2.5 abaixo:** a bateria de
testes framework-neutra (`argv → configuração semântica`, camada de serviço
mockada) descrita na Fase 1 como o portão durável de Fase 4. Os testes de
caracterização da Fase 1 (introspecção Click) foram atualizados apenas onde
o contrato de parâmetros mudou de propósito (remoção de `ia_key`/
`ia_secret`) e continuam verdes para o resto.

### Fase 2.5 — gate semântico de argv (implementada)

A review da Fase 2 apontou uma contradição no roteiro original: este RFC
dizia que o portão durável seria "construído na Fase 2" (§ Fase 1, acima),
mas a proposta inicial de Fase 4 lia "com os testes framework-neutros da
Fase 2 como portão" sem que a Fase 2 em si os entregasse — a Fase 2 leva a
camada de serviço, pré-requisito do portão, mas o portão nunca virou item
explícito do seu escopo. Fazer esse gate na mesma PR que a troca para
Cyclopts trocaria o termômetro e o paciente ao mesmo tempo: escrever os
casos depois de já ver o comportamento do Cyclopts deixa fácil, mesmo sem
intenção, moldar o `expected_config` de cada caso ao que a migração
produziu, em vez de ao que o workflow em produção realmente precisa — um
bug de parsing introduzido pela migração e o teste que deveria pegá-lo
nascem do mesmo código-fonte errado e passam juntos. Por isso esta fase
existe isolada, antes de qualquer MCP ou Cyclopts, com os casos derivados
do argv real dos workflows (RFC, Fase 1) e da camada de serviço da Fase 2 —
nunca do comportamento do Cyclopts, que ainda não existe.

`tests/cli_contract/` contém a bateria: uma tabela compartilhada de
`CliContractCase(app_path, argv, mocks, check, expected_exit_code)` por
caso perigoso, mais um `run_case()` comum. Cada caso roda a CLI de verdade
via `CliRunner.invoke` (parsing real, dispatch real), faz mock só da função
de `service.py` que a rota alcança, e o `check()` inspeciona a configuração
semântica recebida — nunca `get_command`, `make_context`, `opts`,
`secondary_opts`, `param.type`, nem a diferença tupla/lista do Click. Uma
migração para Cyclopts só precisa trocar `CliRunner.invoke` por um
adaptador equivalente; todo caso e todo `check()` são reaproveitados
verbatim.

Cobre todo passo literal dos 5 workflows do RFC — não só um comando
representativo por família: `djen-backup` bare + `drain`; `tjro-juris
crawl` + `upload` + `status`; `stj-acordaos download` + `upload` +
`status`; `datajud enrich` + `status`. Reduzir cobertura em relação à Fase
1 (que já caracterizava todos esses argv via introspecção Click) ao trocar
de bateria não seria aceitável — uma migração Cyclopts poderia quebrar
`tjro-juris upload`, por exemplo, com esta bateria inteira verde. Mais os
casos que a review de Fase 2 marcou como perigosos:

- `--no-fail-fast` no callback bare do `djen-backup` — o caso mais frágil
  do RFC (§ Riscos).
- A assimetria do `--use-proxy`: negável no callback bare
  (`--no-use-proxy` aceito), não-negável em `drain` (`--no-use-proxy`
  rejeitado com exit code 2 — testado explicitamente, não só o caminho
  feliz).
- `--tipo` repetido em `tjro-juris crawl`, e o argv real do cron diário
  (`--desde-ano 1988`).
- Defaults de path do `stj-acordaos upload` (`--parquet-path` nunca
  informado no workflow).
- Credenciais de `stj-acordaos` e `datajud`: `--ia-key`/`--ia-secret` não
  são mais opção reconhecida em nenhum dos dois (exit code 2) — e, no
  caminho feliz que reproduz o `env:` real de `stj-sync.yml`/
  `datajud-enrich.yml`, chegam corretamente à camada de serviço a partir de
  sentinelas em `IA_ACCESS_KEY`/`IA_SECRET_KEY`. A garantia não é
  "credenciais vazias" (que uma migração poderia satisfazer por acidente
  mesmo com a fiação ambiente→serviço quebrada) — é "fora do argv/schema,
  vindas só do ambiente".

### Fase 3 — tools MCP

Tools sobre a camada de serviço, começando pelas de leitura sem efeito
destrutivo. Duas fatias, para não misturar categorias de erro diferentes na
mesma fundação de servidor:

#### Fase 3A — status read-only local (implementada)

Pacote novo `src/causaganha_mcp/` (dependência `fastmcp`, servidor
`causaganha_mcp`, script `causaganha-mcp`). Quatro tools, uma por pacote,
todas locais e determinísticas — leem um manifest do disco, sem chamada de
rede, sem credencial:

- `datajud_status` — `datajud.service.manifest_status`.
- `tjro_juris_status` — `tjro_juris.service.manifest_status`.
- `stj_acordaos_status` — `stj_acordaos.service.manifest_summary` (omite a
  lista `rows` por economia de tokens — é resumo, não listagem).
- `djen_backup_status` — `djen_backup.service.manifest_status`, função nova
  nesta fase (`djen_backup` não tinha um comando `status` de CLI); só lê o
  CSV local, nunca o parquet canônico no IA (`docs/planning/
  manifest-source-of-truth.md`), então pode ficar atrás do estado real.

Registro de tool é explícito (`tools/*.py` expõe `register(mcp)`, chamado
por `server.build_server()`) — não decoração em import time. Motivo: é
exatamente a mesma lição da Fase 2 sobre `djen_backup`'s antigo
`structlog.configure()` de import — um processo que importa este módulo
(um teste, outra tool) não deveria disparar side effect nenhum. E, por
falar em side effect de import: esta fase encontrou e removeu outro, o
`djen_backup/__init__.py` ainda reconfigurava `stdout`/`stderr` na
importação — resíduo que a Fase 2 não tinha pego porque só tocou
`__main__.py`. Sem isso corrigido, `from djen_backup import service` (o
que `causaganha_mcp` precisa fazer) reconfiguraria stdio do processo do
servidor MCP inteiro.

Cada tool tem `readOnlyHint=True`, `destructiveHint=False`, retorno
Pydantic estruturado, e é coberta por dois tipos de teste
(`tests/causaganha_mcp/`): schema (nenhum campo com substring
key/secret/token/credential/password em `parameters` ou `output_schema`,
para as quatro tools) e comportamento (`tool.fn(...)` chamado direto contra
manifests fixture, caminho vazio e caminho populado).

#### Fase 3B — consultas remotas (implementada)

`datajud_facetas`, separado de propósito da Fase 3A: consulta a API pública
do DataJud (rede real, `datajud.service.facetas` → `DataJudClient.facetas`),
então tem uma categoria de erro diferente (timeout, rate limit, erro de
rede) da fundação local/determinística da Fase 3A. Misturar as duas na
mesma fase teria aumentado o espaço de depuração sem necessidade.

Registrado em `tools/datajud.py`, junto de `datajud_status` (mesmo pacote
fonte). `readOnlyHint=True`, `destructiveHint=False` como as demais tools —
agrega, nunca muta — mas `openWorldHint=True`, diferente das quatro tools da
Fase 3A: é a única que sai da máquina. Parâmetros: `tribunal` (default
`DEFAULT_TRIBUNAL` do client), `por` (`Literal["classe", "assunto", "orgao",
"grau", "sistema"]`, hardcoded em vez de derivado dinamicamente de
`FACET_FIELDS` para evitar complicação de `Literal` dinâmico — guardado por
um teste de schema que compara os dois conjuntos de chaves) e `limite`
(`Annotated[int, Field(ge=1, le=100)]`). Retorno: `tribunal`, `por`, `total`
(acervo inteiro, não só os buckets retornados) e `buckets` (lista de
`{chave, qtd}`).

Erros de `datajud.client` (`DataJudAuthError`, `DataJudRateLimitError`,
`DataJudError` genérico de ES, mais `httpx.HTTPStatusError`/
`TimeoutException`/`TransportError` não encapsulados — o mesmo
`except (DataJudError, httpx.HTTPError)` que a CLI já usa) nunca sobem como
exceção crua: `_facetas_tool_error()` mapeia cada categoria para uma
mensagem de `fastmcp.exceptions.ToolError`, reportada dentro do canal de
erro do MCP em vez de derrubar o transporte stdio. A correção de logging da
Fase 3A (`_configure_stdio_safe_logging()` em `__main__.py`) é global ao
processo, então já cobre qualquer `log.warning`/`log.error` que
`DataJudClient._search_once` emitir nos ramos de rejeição ES — nenhuma
correção adicional foi necessária aqui.

Testado com `respx` (mesmo padrão de `tests/datajud/test_datajud_enrich.py`)
mockando o endpoint HTTP: sucesso, 401, 429 esgotando o retry budget,
rejeição ES esgotando o retry budget, erro ES genérico não retriável, outro
status HTTP e erro de rede — sete casos, todos verificando que o resultado é
um `ToolError` estruturado, nunca uma exceção crua. Não ganhou teste
dedicado de transporte stdio real (diferente da Fase 3A): o caminho de
sucesso de `facetas()` não loga nada (só os ramos de rejeição/erro da ES
logam, em `warning`/`error`), e a correção de stdio já é genérica ao
processo — um teste adicional testaria a mesma correção duas vezes, não um
caminho novo.

Operações de ingestão/upload de longa duração (o sync completo, `drain`,
`consolidate`, `enrich` com upload) ficam só na CLI/CI em qualquer fase —
nunca viram tool.

### Fase 4 — Typer → Cyclopts

Com os testes framework-neutros da Fase 2.5 como portão (não os da Fase 1,
que são introspecção Click e não sobrevivem à troca de framework):
re-executar `tests/cli_contract/` contra a CLI migrada, trocando só o
adaptador de invocação (`CliRunner.invoke` → o equivalente Cyclopts), antes
de mudar qualquer workflow. O callback bare de `djen-backup` precisa de um
`default_command` explícito equivalente a `invoke_without_command=True`.

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

**Fase 2.5 (implementada):**
- `tests/cli_contract/` com a tabela `CliContractCase` cobrindo todo passo
  literal dos 5 workflows (não um comando por família) e os casos perigosos
  listados acima (`--no-fail-fast`, assimetria `--use-proxy`, `--tipo`
  repetido, defaults de path do STJ, credenciais vindas do ambiente real do
  job, nunca do argv).
- Cada caso mocka só a função de `service.py` alcançada, nunca introspecciona
  Click (`get_command`, `make_context`, `opts`, `secondary_opts`,
  `param.type` não aparecem neste módulo).
- RFC corrigido: a contradição entre "portão construído na Fase 2" (§ Fase 1)
  e "Fase 4 usa os testes da Fase 2" (§ Fase 4, texto original) — a Fase 2
  nunca teve o gate como item de escopo — está resolvida nomeando a fase que
  efetivamente o entrega.
- `pytest`, `ruff check`, `ruff format --check` verdes. Nenhuma mudança de
  código de produção.

**Fase 3A (implementada):**
- `src/causaganha_mcp/` com `datajud_status`, `tjro_juris_status`,
  `stj_acordaos_status`, `djen_backup_status` — todas `readOnlyHint=True`,
  locais (leem manifest do disco), sem credencial em parâmetro ou retorno.
- Registro de tool explícito (`register(mcp)`), não decoração em import
  time — mesmo princípio da Fase 2.
- Side effect de import residual em `djen_backup/__init__.py`
  (reconfiguração de `stdout`/`stderr` fora de `configure_runtime()`)
  identificado e removido — a Fase 2 só tinha coberto `__main__.py`.
- `tests/causaganha_mcp/`: testes de schema (sem campo credencial-like em
  nenhuma das 4 tools) e de comportamento (manifest vazio e populado, por
  tool). `pytest`, `ruff check`, `ruff format --check` verdes.
- Nenhuma tool de ingestão/upload — só as 4 de status.

**Fase 3B (implementada):**
- `datajud_facetas` em `tools/datajud.py`, `readOnlyHint=True`,
  `destructiveHint=False`, `openWorldHint=True` (única tool que faz chamada
  de rede), sem credencial em parâmetro ou retorno.
- Toda a taxonomia de erro de `datajud.client` (`DataJudAuthError`,
  `DataJudRateLimitError`, `DataJudError` de ES, `httpx.HTTPStatusError`,
  `httpx.TimeoutException`/`TransportError`) mapeada para
  `fastmcp.exceptions.ToolError` — nunca uma exceção crua atravessando o
  transporte MCP.
- `por` como `Literal` hardcoded, guardado por teste de schema que compara
  o enum declarado com `datajud.client.FACET_FIELDS.keys()` (drift guard).
- `tests/causaganha_mcp/test_datajud_facetas.py`: sete casos via `respx`
  (sucesso + seis modos de falha), cada um afirmando `ToolError`.
  `tests/causaganha_mcp/test_tool_schema.py` estendido para as 5 tools.
  `pytest`, `ruff check`, `ruff format --check` verdes.
- `server.py`'s `instructions` atualizado para não afirmar mais que o
  servidor inteiro é sem chamada de rede.

## 4. Riscos

- **`--no-fail-fast`** é o caso mais frágil: se o Cyclopts gerar nome ou
  default diferente para o par negável, `collect-zips` passa a rodar com
  `fail_fast=True` e aborta no primeiro 403 do CloudFront — regressão
  silenciosa, visível só na próxima execução (a cada 20 min). É o primeiro
  caso em `tests/cli_contract/` (Fase 2.5) precisamente por isso.
- **`ruff select=["ALL"]`** e **`vulture --min-confidence 100`** sinalizaram
  código novo durante a extração da Fase 2 (complexidade, imports não
  utilizados, docstrings) — resolvido com refino local (ex.: `enrich` do
  `datajud` dividido em `_pending_cnjs`/`_upload_step` para ficar sob o
  limite de complexidade) em vez de whitelist ampla.
- A bateria framework-neutra de argv (Fase 2.5) cobre todo passo literal
  dos 5 workflows — incluindo `tjro-juris upload`/`status`, `stj-acordaos
  download`/`status` e `datajud status`, que uma primeira versão da Fase 2.5
  deixou de fora por engano (a review corrigiu: são passos de produção, não
  hipotéticos, e já eram caracterizados pela Fase 1 — reduzir a cobertura ao
  trocar de bateria não era aceitável). Não cobre todo parâmetro de toda
  subcommand, só o que cada workflow de fato invoca: `djen-backup
  check`/`probe`/`reset` (nenhum workflow os chama), `tjro-juris
  consolidate` e `datajud facetas` (idem, confirmado no RFC §1) ainda
  dependem só da introspecção Click da Fase 1. Ampliar isso é trabalho
  incremental, não bloqueio para começar a Fase 3.
