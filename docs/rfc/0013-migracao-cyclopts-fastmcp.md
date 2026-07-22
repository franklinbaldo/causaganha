# RFC 0013 — Migração das CLIs Typer para Cyclopts + FastMCP

- **Status:** Fase 1, Fase 2, Fase 2.5, Fase 3A, Fase 3B e Fase 4 implementadas
  (PRs #849, #850, #851, #852, #853, e o PR desta fase). Fase 3 está fechada —
  trabalho de produto sobre o servidor MCP continua em RFC 0014. RFC 0013
  está fechada — os quatro pacotes CLI (`djen_backup`, `tjro_juris`,
  `stj_acordaos`, `datajud`) rodam em Cyclopts, e as cinco tools FastMCP já
  existiam desde a Fase 3B.
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

**Tradução de exceções na fronteira MCP, não como rede de segurança contra
crash.** As exceções de domínio (`datajud.client`'s `DataJudAuthError`,
`DataJudRateLimitError`, `DataJudProtocolError`, `DataJudError` genérico de
ES) permanecem independentes do FastMCP — nenhuma delas importa `fastmcp`,
mesma separação que a CLI já usa (`except (DataJudError, httpx.HTTPError)`).
Na fronteira MCP, `_facetas_tool_error()` traduz explicitamente cada
categoria conhecida para uma mensagem de `fastmcp.exceptions.ToolError`.
Isso não é o que impede o transporte de cair: o próprio FastMCP já contém
qualquer exceção levantada durante a execução normal de uma tool e a
converte num tool-execution error (`server.py`'s `call_tool` deixa
`FastMCPError` passar, envolve o resto em `ToolError`, com mensagens
especiais para 429/timeout, respeitando `mask_error_details`) — isso nunca
esteve em risco. O que a tradução explícita garante é outra coisa: mensagens
públicas estáveis, acionáveis e seguras, que sobrevivem a
`mask_error_details=True` (o fallback genérico do FastMCP substituiria
qualquer exceção que não seja já um `ToolError` por um "Error calling tool
..." completamente opaco nesse modo) — sem depender do `str()` interno de
cada exceção, que pode mudar de redação ou, no caso do erro genérico de ES,
carregar o payload cru do Elasticsearch. Exceções fora dessa lista conhecida
continuam contidas pelo fallback do FastMCP — defesa em profundidade, não o
contrato principal de erros da tool.

Isso é diferente da correção de stdio da Fase 3A
(`_configure_stdio_safe_logging()` em `__main__.py`, ainda necessária e já
genérica ao processo): aquela era corrupção do canal de transporte (bytes de
log indo parar em stdout, que é exclusivamente JSON-RPC), não uma exceção de
função — uma classe de falha que o `except Exception` do FastMCP não cobre
porque nunca chega como exceção Python. As duas proteções continuam
necessárias, mas por motivos diferentes.

Testado com `respx` (mesmo padrão de `tests/datajud/test_datajud_enrich.py`)
mockando o endpoint HTTP: sucesso, 401, 429 esgotando o retry budget,
rejeição ES esgotando o retry budget, erro ES genérico não retriável (com
asserção explícita de que o payload do ES não vaza na mensagem pública),
outro status HTTP, erro de rede, resposta não JSON, o orçamento MCP em uso e
o deadline duro da tool — dez casos. Não ganhou teste dedicado de transporte
stdio real (diferente da Fase 3A): o caminho de sucesso de `facetas()` não
loga nada (só os ramos de rejeição/erro da ES logam, em `warning`/`error`),
e a correção de stdio já é genérica ao processo — um teste adicional
testaria a mesma correção duas vezes, não um caminho novo.

Correções de review antes do merge:

- **Orçamento de tempo próprio para a chamada MCP, em duas camadas.**
  `DataJudClient` tem defaults calibrados para o `enrich` da CLI — ingestão
  em lote de longa duração, onde vale esperar minutos por um hiccup do
  DataJud: `timeout=90s`, `max_retries=5` (6 tentativas), backoff
  2/4/8/16/30s. Herdar isso integralmente na tool deixaria uma
  indisponibilidade custar até ~10 minutos antes do `ToolError` (e um 429
  persistente, ~1 minuto só em backoff) — tempo longo o bastante para um
  host MCP desistir de esperar antes do erro estruturado chegar.
  `datajud.service.facetas()` ganhou parâmetros opcionais (`request_timeout`,
  `max_retries`, `backoff_base`, todos `None` por default — a CLI continua
  sem passá-los, comportamento idêntico ao de antes); a tool passa um
  orçamento interno próprio, não exposto no schema (`_FACETAS_TIMEOUT=15s`,
  `_FACETAS_MAX_RETRIES=1`, `_FACETAS_BACKOFF_BASE=1.0`, pior caso ~31s em
  vez de ~10 minutos). Uma segunda camada, independente: `@mcp.tool(timeout=
  _FACETAS_TOOL_TIMEOUT)` (45s), o deadline nativo do FastMCP
  (`anyio.fail_after`), como backstop acima do pior caso do orçamento do
  client — cobre qualquer travamento que o timeout do próprio client não
  pegue, ou uma futura mudança no orçamento que o faça crescer de novo; ao
  disparar, vira um `McpError` genérico (não uma das mensagens tratadas de
  `_facetas_tool_error()`), mas ainda contido pelo FastMCP, nunca cru.
  `test_facetas_uses_a_tighter_budget_than_the_ingestion_client` espiona os
  kwargs que a tool passa a `DataJudClient`; `test_facetas_has_a_
  hard_interactive_timeout_as_backstop` confirma o deadline da tool — nenhum
  dos dois precisa de sleeps reais.
- **Resposta não JSON não tinha lugar na taxonomia.**
  `DataJudClient._search_once()` chamava `resp.json()` sem tratamento — um
  WAF/gateway devolvendo HTML ou corpo truncado sob HTTP 200 levanta
  `JSONDecodeError` (um `ValueError`), que não é `DataJudError` nem
  `httpx.HTTPError`. Sem tradução no client, isso pularia a taxonomia de
  domínio inteira e cairia direto no fallback genérico do FastMCP —
  perdendo toda orientação acionável com masking ligado, ou expondo detalhes
  instáveis sem masking. Corrigido com uma nova classe
  `DataJudProtocolError(DataJudError)` e um `_parse_json_body()` que traduz
  só o `ValueError` de `resp.json()` — não um `except ValueError` amplo, que
  mascararia bug de programação — numa mensagem com status e content-type,
  sem ecoar o corpo. Coberto em `tests/datajud/test_datajud_client.py`
  (nível do client) e `tests/causaganha_mcp/test_datajud_facetas.py` (nível
  da tool).
- **O fallback genérico de `_facetas_tool_error()` vazava `str(exc)`.**
  `return ToolError(f"DataJud query failed: {exc}")` acoplava a mensagem
  pública ao texto interno de qualquer exceção não coberta pelos ramos
  explícitos — e o `DataJudError` genérico (erro de ES não-transiente em
  `_search_once`) embute o payload cru do Elasticsearch nesse texto. Trocado
  por uma mensagem fixa, sem interpolação; a causa real continua disponível
  via `raise ... from exc` para logs.

Operações de ingestão/upload de longa duração (o sync completo, `drain`,
`consolidate`, `enrich` com upload) ficam só na CLI/CI em qualquer fase —
nunca viram tool.

**Fase 3 está fechada aqui — fronteira de escopo com a RFC 0014.** As cinco
tools read-only (`datajud_status`, `tjro_juris_status`, `stj_acordaos_status`,
`djen_backup_status`, `datajud_facetas`) cobrem o que esta RFC se propôs:
expor a camada de serviço via FastMCP sem tocar ingestão/upload. Qualquer
trabalho adicional sobre o servidor MCP — onboarding/descoberta, textos em
português nas superfícies exibidas, uma tool agregadora de status, campos de
freshness/proveniência (`encontrado`, `ultima_atualizacao`, `fonte`,
`canonica`, `aviso`), ou `processo_consultar` — é um eixo de produto, não de
migração de framework, e fica em **RFC 0014 — MCP como superfície de
produto**. Esta RFC não será estendida com esse escopo; só Fase 4 (abaixo)
continua pendente aqui.

### Fase 4 — Typer → Cyclopts (implementada)

Com os testes framework-neutros da Fase 2.5 como portão (não os da Fase 1,
que são introspecção Click e não sobrevivem à troca de framework):
re-executar `tests/cli_contract/` contra a CLI migrada, trocando só o
adaptador de invocação (`CliRunner.invoke` → o equivalente Cyclopts), antes
de mudar qualquer workflow. O callback bare de `djen-backup` precisa de um
`default_command` explícito equivalente a `invoke_without_command=True`.

Os quatro pacotes foram migrados nessa ordem: `djen_backup`, `tjro_juris`,
`stj_acordaos`, `datajud`. Achados concretos, não previstos em detalhe pelo
texto original acima:

- **Callback bare via `App.meta`.** `djen-backup` é o único pacote com
  callback bare + setup compartilhado (`configure_runtime()`). Cyclopts não
  tem um `invoke_without_command=True` — `@app.default` só dispara quando
  *nenhum* subcomando bate. O equivalente é o padrão meta-app: comandos
  registrados num `App` interno, `app = App(...).meta`, com
  `@_commands_app.meta.default def _launch(*tokens): configure_runtime();
  return _commands_app(tokens)` rodando antes de qualquer despacho — bare ou
  subcomando. Único pacote que precisou disso; os outros três não têm setup
  compartilhado nem callback bare.
- **`--no-fail-fast`/`--use-proxy` (o risco mais frágil listado abaixo) —
  resolvido.** `Parameter(name=[...])` sozinho **não** suprime o par
  `--no-X` que Cyclopts gera automaticamente para todo booleano — só o nome
  explícito, ao contrário do Typer, onde uma string de opção explícita já
  suprimia a negação. A correção é `Parameter(name="--flag", negative=[])`.
  Aplicado em `djen-backup`'s `drain`/`probe` (`--use-proxy`) e `reset`
  (`--all`), e em `datajud`'s `enrich` (`--skip-upload`) — todo booleano que
  no Typer original só tinha a forma positiva. `tests/cli_contract/`
  confirma `--no-use-proxy`/`--no-skip-upload` continuam inexistentes.
- **Exit code de erro de uso: 1, não 2.** O código de saída default do
  Cyclopts para um erro de parsing/uso (`sys.exit(1)` fixo em
  `cyclopts/core.py`, não configurável via `App(...)`) é **1**, diferente da
  convenção 2 do Click/Typer para a mesma classe de erro — confirmado lendo
  a fonte do Cyclopts e por experimento direto. Nenhum dos 5 workflows de
  produção aciona esse caminho (nenhum passa `--ia-key` nem
  `--no-use-proxy`), então não é regressão de produção — é uma diferença de
  framework real, documentada e travada em 3 casos de
  `test_semantic_argv_contract.py` (`expected_exit_code=1` com comentário
  explicando por quê) em vez de escondida atrás de um harness que mentisse
  sobre o que Cyclopts de fato produz.
- **Testes de caracterização da Fase 1 removidos, como o RFC sempre previu.**
  `tests/{djen_backup,tjro_juris,stj_acordaos,datajud}/test_*_cli_contract.py`
  chamavam `typer.main.get_command(app)` — quebraram na hora em que cada
  `app` virou um `cyclopts.App`, exatamente como a nota da Fase 1 (§ acima)
  antecipava. `tests/cli_contract/test_semantic_argv_contract.py` (Fase 2.5)
  já cobria todo caso que eles travavam; deletados sem substituição. Os
  outros testes que usavam `typer.testing.CliRunner` diretamente
  (`test_cli_exit_code.py` do `djen_backup`, `test_stj_main.py`,
  `test_datajud_enrich.py`) foram reescritos para invocar o `App` do
  Cyclopts diretamente (`app(argv, exit_on_error=False,
  result_action="return_value")`, stdout/stderr capturados via
  `contextlib.redirect_std{out,err}`), preservando as mesmas asserções de
  exit code e saída de texto.
- **`typer` continua como dependência.** `src/segmenter_dataset/__main__.py`
  e `src/causaganha/consolidate/cli.py` usam Typer e estão fora do escopo
  desta RFC (só os quatro pacotes de sincronização DJEN/TJRO/STJ/DataJud).

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
  `DataJudRateLimitError`, `DataJudError` de ES, `DataJudProtocolError` de
  corpo não JSON, `httpx.HTTPStatusError`,
  `httpx.TimeoutException`/`TransportError`) traduzida explicitamente para
  `fastmcp.exceptions.ToolError`, com mensagens públicas estáveis e sem
  interpolar `str(exc)` no ramo de fallback (não vaza payload de ES nem
  outro detalhe interno instável) — não porque isso evite um crash de
  transporte (o FastMCP já contém qualquer exceção de tool sozinho), mas
  porque preserva orientação acionável mesmo sob `mask_error_details=True`.
- `por` como `Literal` hardcoded, guardado por teste de schema que compara
  o enum declarado com `datajud.client.FACET_FIELDS.keys()` (drift guard).
- Orçamento de tempo/retry em duas camadas: interno do client
  (`_FACETAS_TIMEOUT=15s`, `_FACETAS_MAX_RETRIES=1`,
  `_FACETAS_BACKOFF_BASE=1.0`, não exposto no schema, pior caso ~31s em vez
  dos ~10min do perfil de ingestão) e um deadline nativo do FastMCP na tool
  (`@mcp.tool(timeout=45s)`, backstop acima do pior caso do client).
- `tests/causaganha_mcp/test_datajud_facetas.py`: dez casos via `respx`
  (sucesso + sete modos de falha + orçamento do client em uso + deadline da
  tool), cada um de falha afirmando `ToolError` (o do fallback genérico
  também afirma que o payload de ES não aparece na mensagem).
  `tests/datajud/test_datajud_client.py` cobre `DataJudProtocolError` no
  nível do client. `tests/causaganha_mcp/test_tool_schema.py` estendido
  para as 5 tools.
  `pytest`, `ruff check`, `ruff format --check` verdes.
- `server.py`'s `instructions` atualizado para não afirmar mais que o
  servidor inteiro é sem chamada de rede.

**Fase 4 (implementada):**
- Os quatro `__main__.py` (`djen_backup`, `tjro_juris`, `stj_acordaos`,
  `datajud`) rodam em Cyclopts; nenhum importa `typer`.
- `cyclopts` como dependência direta (`pyproject.toml`), não só transitiva
  via `fastmcp[server]`.
- `tests/cli_contract/harness.py` migrado para o adaptador de invocação
  Cyclopts (`_invoke`); as 16 `CliContractCase` (4 pacotes) passam sem
  alteração de `check` — só o adaptador mudou, como planejado.
- Negação de booleano preservada: todo `--flag` que só tinha forma positiva
  no Typer original (`--use-proxy`, `--all`, `--skip-upload`) usa
  `Parameter(negative=[])` em Cyclopts; `--no-*` continua inexistente para
  esses três, confirmado por teste.
- `djen-backup`'s callback bare preservado via `App.meta` — `djen-backup
  --deadline-minutes N ...` (sem subcomando) continua rodando
  `configure_runtime()` antes do pipeline, igual à Fase 2.
- Nenhuma mudança de argv nos 5 workflows de produção — os mesmos comandos
  que a Fase 1 travou continuam resolvendo para a mesma config semântica.
- Testes de caracterização da Fase 1 (introspecção Click) deletados nos
  quatro pacotes; testes que usavam `typer.testing.CliRunner` diretamente
  reescritos para invocar o `App` Cyclopts.
- `pytest`, `ruff check`, `ruff format --check` verdes.

## 4. Riscos

- **`--no-fail-fast`** era o caso mais frágil: se o Cyclopts gerasse nome ou
  default diferente para o par negável, `collect-zips` passaria a rodar com
  `fail_fast=True` e abortaria no primeiro 403 do CloudFront — regressão
  silenciosa, visível só na próxima execução (a cada 20 min). Era o primeiro
  caso em `tests/cli_contract/` (Fase 2.5) precisamente por isso — **resolvido
  na Fase 4**: `--fail-fast`/`--no-fail-fast` são o par negável default do
  Cyclopts (sem necessidade de `negative=[]`, já que o Typer original também
  gerava os dois lados via `/`), e o caso de contrato correspondente passa
  sem alteração.
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
