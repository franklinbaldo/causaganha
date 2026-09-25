# Threat model operacional do CausaGanha

Atualizado em 2026-09-25.

Este documento converte o threat model do CausaGanha em controles verificáveis. A unidade de trabalho é:

```
ameaça -> invariante -> controle atual -> gate automatizado -> issue
```

O objetivo não é transformar segurança em checklist genérico de aplicação web. O CausaGanha não possui contas de usuário, sessão autenticada, banco multi-tenant, pagamentos ou dashboard mutável. Os riscos dominantes são integridade/proveniência do acervo judicial, abuso de superfícies públicas de consulta, conteúdo jurídico não confiável, privacidade local no navegador, credenciais de publicação/deploy e supply chain.

## 1. Ativos e fronteiras

Ativos prioritários:

- integridade e proveniência de publicações, decisões, estados processuais e datasets derivados;
- credenciais do Internet Archive, relay e autoridade de deploy GitHub/GCP;
- disponibilidade dos coletores, canários, MCP e consultas públicas;
- estado privado salvo no browser (`localStorage` e backups exportados);
- capacidade de distinguir **ARQUIVO**, **ESTADO** e **TEOR**;
- identidade correta entre pessoa, processo, tribunal, período, geração e artefato.

Fronteiras relevantes:

1. **usuário anônimo** — controla argumentos de tools MCP, busca pública, paginação e filtros;
2. **fontes oficiais/públicas** — conteúdo de rede pode estar malformado, enorme, comprometido ou conter prompt injection;
3. **Internet Archive** — raiz prática de confiança do arquivo publicado, mas não assinatura independente;
4. **browser** — conteúdo judicial é renderizado e pesquisas/snapshots podem permanecer em `localStorage`;
5. **MCP -> host/agente** — texto judicial é evidência não confiável, mesmo quando o MCP é read-only;
6. **relays/proxies** — atravessam restrições de WAF e por isso precisam de egress deliberadamente estreito;
7. **workflows e supply chain** — jobs agendados/manuais podem carregar segredos e autoridade de publicação.

## 2. Regra de severidade

A severidade é calibrada pelo impacto real no produto:

- **Crítica**: execução remota/PR-controlled em contexto com segredos e autoridade sistêmica; compromise de build que backdoore site/MCP ou corrompa amplamente o arquivo canônico; escape do comportamento read-only com obtenção de autoridade de deploy.
- **Alta**: stored XSS com impacto amplo; bypass de relay/segredo que permita SSRF ou requests mutáveis; adulteração/fabricação relevante do acervo; atribuição errada com propagação ampla; prompt injection somente quando demonstrado que um host comum executa ação sensível.
- **Média**: DoS/abuso sustentado, bombs de ingestão, quota exhaustion, formula injection, poisoning que exija compromisso prévio de artefato canônico, omissão silenciosa de partição limitada.
- **Baixa / aceita**: versão/health não sensíveis, erros detalhados sem segredos, exposição de estado local compatível com a fronteira documentada, SQL arbitrário digitado pelo próprio usuário no Explorer.

A classificação abaixo é a prioridade do risco **neste repositório hoje**, não uma propriedade eterna. Se um precondition mudar, a severidade deve ser reavaliada.

## 3. Matriz operacional

| ID | Severidade | Ameaça | Invariante de segurança | Controle atual | Gate automatizado necessário | Issue |
| --- | --- | --- | --- | --- | --- | --- |
| TM-01 | Alta | Command injection em `workflow_dispatch` com secrets via string + `eval` em `.github/workflows/tjro-sync.yml`. | Input de dispatch nunca vira código de shell; entra apenas como argumento validado de um comando fixo. | Permissões do workflow são `contents: read`; secrets ficam no environment/job. O gap é a reinterpretação por `eval`. | Teste estático proíbe `eval`; payloads com metacaracteres são rejeitados/tratados como dados; casos válidos preservam argumentos esperados. | [#1608](https://github.com/franklinbaldo/causaganha/issues/1608) |
| TM-02 | Alta | Relay roubado/abusado vira WAF-bypass contra tribunais, aceita método/rota indevida ou encaminha headers sensíveis. | Egress do relay é HTTPS-only, métodos fechados, host/rota fechados, headers mínimos, redirects manuais e budgets de tamanho/quota. | `djen_proxy.go` (fixed-host) agora só encaminha GET sob `/api/` — `/login`, `/swagger/` e `/comunicacao` solto foram removidos por falta de uso real (`deployment/djen_proxy_test.go`, CI job `djen-proxy`). Python relay (`deployment/relay/function/main.py`) agora exige HTTPS, restringe método a GET/HEAD/POST, faz stripping explícito de `Authorization`/`Cookie` e aplica budgets de tamanho de request (5 MiB, 413) e resposta (50 MiB, 502 durante o streaming) — ver `deployment/relay/README.md#egress-policy-1609tm-02`. CF relay já é HTTPS + GET/HEAD/POST e faz stripping mais forte dos headers de infraestrutura, mas ainda não stripa `Authorization`/`Cookie` explicitamente — documentado como dead infra (nunca ligado a produção, ver `tests/test_archive_cors_proxy_ci_coverage.py`), então essa lacuna específica permanece de baixo risco real e não foi fechada nesta rodada. | Testes rejeitam HTTP, métodos mutáveis, host/rota fora da política, headers sensíveis e body/resposta acima do limite; mantêm requests oficiais necessários. Feito para `djen_proxy.go` e para o relay Python (`tests/deployment/relay/test_main.py`); pendente apenas para o CF relay (dead infra). | [#1609](https://github.com/franklinbaldo/causaganha/issues/1609) |
| TM-03 | Alta se houver alteração canônica; média para egress isolado | Manifest/index envenenado controla URL entregue a DuckDB/httpfs ou browser. | Toda URL derivada de autoridade remota passa por uma única política: HTTPS, host canônico, path/extensão esperados, quantidade limitada e quoting central. | `arquivo_ia_url` vindo de `indice_processual.parquet` passa por `service._validate_artifact_url` (Python) e `validateArtifactUrl` (TypeScript, `web/src/lib/processoCnj.ts`) antes de qualquer `read_parquet`/lista SQL — mesma política nos dois runtimes (HTTPS, host `archive.org`, prefixo `/download/`, sufixo `.parquet`, sem query/fragment/aspas). | Fixtures `file://`, `http://`, host estranho, quotes, fragments/query e paths inesperados falham fechado antes de DuckDB/fetch; Python e TS usam política equivalente. Feito — `TestValidateArtifactUrl`/`test_poisoned_manifest_url_degrades_source_instead_of_crashing` (Python) e testes equivalentes em `processoCnj.test.ts`. | [#1610](https://github.com/franklinbaldo/causaganha/issues/1610) |
| TM-04 | Alta | Manifesto formalmente válido aponta para geração/tribunal/período errado, produzindo omissão ou atribuição incorreta sem precisar de SSRF. | Cada transição preserva identidade verificável: source, retrieval time, raw artifact, hash, normalization version, generation id, tribunal/período, schema fingerprint, row count e derived artifact. | DataJud bundles já usam generation + SHA-256 + size; manifests e canários possuem vários checks de coerência. Para o dossiê unificado (`indice_processual.parquet`), `service._validar_tribunal_coerente`/`_tribunal_da_url` agora cruzam o `tribunal` declarado por linha contra o tribunal que o próprio `arquivo_ia_url` nomeia no item IA (`djen-{tribunal}-{ano}`, `datajud-{tribunal}`) — as duas fontes particionadas por tribunal; `juris`/`stj` usam item fixo, sem o que cruzar. `arquivo_ia_url` também é selecionado com `tribunal` em `web/src/lib/processoCnj.ts::buildIndiceSql` (paridade de linha com o harness #1107), mas a checagem em si ainda não existe do lado Web. Generation id, hash, schema fingerprint e row-count-do-parquet não existem em nenhum gerador do repositório (nem `reconcile_processos.py`, nem `djen_backup/manifest.py`) — cadeia de proveniência segue não uniforme. | Fixture com tribunal incompatível com o artefato falha antes da composição — feito para djen/datajud em `tests/causaganha/processos/test_service.py` (`TestTribunalCoerenteComUrl`, `test_poisoned_manifest_tribunal_degrades_source_instead_of_trusting`). Pendente: a mesma checagem do lado Web; e fixture com hash/generation/schema/row-count incompatível, que exige primeiro inventar esses campos no gerador do manifesto. | [#1610](https://github.com/franklinbaldo/causaganha/issues/1610) |
| TM-05 | Média | Decompression bomb, JSON/membro gigante, quantidade excessiva de membros ou download ilimitado exaure RAM/disco do runner. | Toda entrada de rede/arquivo tem orçamento explícito aplicado durante streaming/leitura, antes de materialização perigosa. | `download_zip` faz streaming para disco; `stream_zip_to_ndjson` não materializa o conjunto inteiro, mas faz `json.load` por membro e não impõe budgets de tamanho/contagem/razão. | ZIPs sintéticos exercitam many-members, tamanho declarado, alta razão de compressão, JSON gigante, traversal e download que excede teto. Erro é distinto de dataset vazio. | [#1611](https://github.com/franklinbaldo/causaganha/issues/1611) |
| TM-06 | Média | Flood sequencial do MCP público consome CPU/memória, banda IA e quota DataJud apesar do limite global de concorrência. | Superfície pública tem deadlines, concorrência e abuse controls de deploy suficientes para manter custo por chamador limitado. | `http_server.py` já define timeout e concorrência global; modelos limitam paginação/resultados. `OperationalLimitsMiddleware` agora também aplica um limite fixo por cliente (`CAUSAGANHA_MCP_RATE_LIMIT_PER_MINUTE`, default 120/60s, chave = primeiro hop de `X-Forwarded-For` ou IP do socket — `tests/causaganha_mcp/test_http_rate_limit.py`), então um único chamador sequencial não monopoliza mais o budget global. Pendente: quotas/abuse controls na própria camada de deploy (Cloud Run) — fora do que uma sessão sem acesso a infraestrutura de deploy pode fechar. | Load/admission tests provam rejeição bounded por cliente (feito); deploy documenta quota/body/request limits (pendente na camada de deploy); limites não convertem falha upstream em “ausência” (mantido — `ToolError` distinto de saturação/timeout). | [#950](https://github.com/franklinbaldo/causaganha/issues/950) |
| TM-07 | Média | `tribunal` livre alcança path/artefato DataJud inesperado ou causa amplificação de requests. | Tribunal é identidade de domínio, não fragmento livre de URL/path; somente códigos canônicos atravessam rede/artefato. | Tools normalizam lowercase e aplicam limites de retorno/timeout, mas aceitam `tribunal: str`. | Casos válidos passam; `../`, slash, backslash, `?`, `#`, `%`, whitespace e Unicode confusável falham antes de qualquer request. | [#1615](https://github.com/franklinbaldo/causaganha/issues/1615) |
| TM-08 | Alta se explorável em muitos usuários | Stored XSS em texto judicial ou regressão do sanitizer altera evidência exibida e acessa estado same-origin. | Conteúdo HTML não confiável só chega a `{@html}` após sanitização testada; CSP limita script/worker/connect origins ao mínimo necessário. | `web/src/lib/djen.ts` usa DOMPurify, proíbe `script`/`style` e `style=`; links são normalizados; `PublicationReader.svelte` e `PublicationDetailPanel.svelte` são sinks explícitos. `Layout.astro` agora declara uma CSP (`web/src/lib/csp.ts`, `<meta http-equiv>` — único mecanismo disponível num build 100% estático) com `script-src 'self'` (sem `unsafe-inline`/`unsafe-eval`), `object-src 'none'`, `base-uri`/`form-action 'self'` e `connect-src`/`worker-src` restritos a `archive.org`, `comunicaapi.pje.jus.br`, o proxy DJEN e `cdn.jsdelivr.net` (origem real do worker/módulo DuckDB-WASM); `advogados.astro`/`comparador.astro` (as duas páginas que não usam `Layout.astro`) recebem a mesma política. `style-src` mantém `'unsafe-inline'` — decisão documentada: o `<style>` escopado do Svelte é estático e nunca carrega conteúdo do usuário. `frame-ancestors`/`sandbox`/`report-uri` ficam de fora (ignorados pelo spec quando entregues via `<meta>`, e GitHub Pages não permite header HTTP custom) — limitação aceita, não escondida. | Corpus XSS falha inerte (`web/src/lib/djenXssCorpus.test.ts`); teste estático impede novo sink `{@html}` fora do caminho autorizado (`web/src/lib/htmlSinks.inventory.test.ts`); CSP é exercitada por teste + build real (`web/src/layouts/Layout.csp.test.ts`) e worker remoto não aceita origem arbitrária. | [#1613](https://github.com/franklinbaldo/causaganha/issues/1613) |
| TM-09 | Média | CSV exportado contém célula iniciada por `=`, `+`, `-` ou `@` e vira fórmula em desktop spreadsheet. | Valor textual controlável pela fonte permanece inerte ao abrir o CSV em planilha. | Export já tem teste de paginação/arquivo e quoting estrutural; não há neutralização de fórmula. | `PublicationSearch.export.test.ts` cobre prefixos perigosos e variantes com whitespace, além de strings benignas. | [#1612](https://github.com/franklinbaldo/causaganha/issues/1612) |
| TM-10 | Crítica se comprometer job/build com autoridade de publicação | Resolução livre de dependências/base image permite build não reprodutível ou pacote compatível malicioso. | Mesmo commit resolve para inputs verificáveis e runtime possui privilégio mínimo. | Ações são majoritariamente SHA-pinned; JS possui lockfiles. Python usa mínimos amplos; MCP Docker faz `pip install .` online sobre `python:3.12-slim` e roda sem usuário não-root explícito. | Gate exige `uv.lock` frozen, base por digest, usuário não-root, SBOM e scans sobre o conjunto realmente implantado. | [#1614](https://github.com/franklinbaldo/causaganha/issues/1614) |
| TM-11 | Média; alta apenas se host executar ação sensível de forma confiável | Prompt injection indireta em publicação/decisão influencia o LLM consumidor a usar tools externas ao MCP. | Texto judicial é evidência não confiável e não instrucional de forma machine-readable; ARQUIVO/ESTADO/TEOR não se misturam. | `publicacoes_buscar` e `decisoes_buscar` marcam cada item com `tipo_conteudo="untrusted_legal_text"` (`causaganha_mcp.evidence.UNTRUSTED_LEGAL_TEXT`, `src/causaganha_mcp/tools/publicacoes.py` e `decisoes.py`) — texto passa verbatim, nunca sanitizado/promovido a campo operacional. `processo_consultar` (campos gerados por codegen OKF: `resumo`/`tese`/`ementa`) ainda não carrega o marcador — ver #1616 para essa fatia. | Schema preserva marker de confiança (`tests/causaganha_mcp/test_untrusted_evidence_marker.py`); fixture “ignore instruções anteriores” permanece no campo de teor e nunca vira campo operacional/next action — feito para `publicacoes_buscar`/`decisoes_buscar`, pendente para `processo_consultar`. | [#1616](https://github.com/franklinbaldo/causaganha/issues/1616) |
| TM-12 | Baixa / risco aceito | `localStorage`/backup plaintext expõe pesquisas e snapshots a extensão, malware, script same-origin, dispositivo compartilhado ou arquivo exportado. | Produto não promete confidencialidade criptográfica no browser; retenção local deve ser clara e bounded. | Sem contas/servidor de estado privado; armazenamento é local e exportável. | Testes de import/export/shape e limite de tamanho/quantidade quando aplicável; documentação pública deixa a fronteira explícita. | Sem issue de segurança enquanto a fronteira continuar local-only e documentada. |
| TM-13 | Baixa / fora do perfil remoto | Tool stdio local com path fornecido pelo operador lê filesystem local. | Paths de operador nunca entram no catálogo MCP público remoto. | `profiles.py` separa perfil operador/local do público; comentários em `datajud_status` registram a fronteira. | Schema/catalog test falha se tool/parâmetro de filesystem aparecer no perfil público. | Cobertura existente; abrir issue apenas se houver regressão. |
| TM-14 | Baixa / comportamento deliberado | DuckDB Explorer executa SQL arbitrário digitado pelo próprio visitante, podendo consumir recursos locais/fazer fetch escolhido pelo usuário. | SQL do Explorer nunca é pré-populado/executado por conteúdo remoto sem gesto explícito. | Execução é client-side e deliberada. | Teste de produto deve falhar se uma URL/parâmetro compartilhado passar a executar SQL automaticamente. | Sem issue enquanto continuar self-directed. |
| TM-15 | Crítica/Alta conforme alcance | Credencial IA/relay/deploy exposta permite alterar futuras gerações, manifests ou serviço publicado. | Segredos não entram em PRs não confiáveis, logs, schemas, artefatos ou headers encaminhados; uso é mínimo e rotacionável. | Environment secrets, permissões de workflow e OIDC/scoped permissions reduzem superfície; o risco de command injection (#1608), relay forwarding (#1609) e supply chain (#1614) são caminhos concretos. | Secret scanning + testes de permissões/workflow + regressões de forwarding; documentação de rotação e revogação. | [#1608](https://github.com/franklinbaldo/causaganha/issues/1608), [#1609](https://github.com/franklinbaldo/causaganha/issues/1609), [#1614](https://github.com/franklinbaldo/causaganha/issues/1614) |

## 4. Invariantes transversais

Os gates acima devem convergir para estes invariantes, independentemente da implementação:

### 4.1 Proveniência é parte do dado

Uma resposta relevante deve ser rastreável, quando tecnicamente aplicável, por:

```
fonte oficial
  -> instante de aquisição
  -> artefato bruto
  -> hash
  -> versão da normalização
  -> geração
  -> artefato derivado
  -> resultado consultado
```

Checksum interno prova consistência de bytes, não autoria independente. Assinatura externa de release/manifests pode ser adicionada como camada posterior, mas não substitui validação de geração/identidade.

### 4.2 Ausência nunca é erro de transporte

Timeout, 403, manifesto ilegível, hash incompatível, schema inesperado ou fonte indisponível não podem ser convertidos em “zero resultados” ou “processo sem movimento”. A taxonomia existente de `present/absent/unknown/unavailable` e ARQUIVO/ESTADO/TEOR deve ser preservada em novos controles de segurança.

### 4.3 Conteúdo judicial é dado hostil para parsers e agentes

Texto oficial pode conter HTML, fórmulas de planilha, bytes inesperados e instruções dirigidas a um LLM. Fidelidade ao registro não implica confiar na sua interpretação operacional.

### 4.4 Egress é uma capacidade privilegiada

Toda URL derivada de manifesto, usuário ou metadata externa deve passar por policy explícita antes de rede/DuckDB. “Host oficial” não autoriza método, path, body ou header arbitrário.

### 4.5 Security gates devem ser regressões executáveis

Uma issue desta matriz não termina apenas com documentação. O fechamento exige um teste, scanner, policy check ou canário capaz de falhar quando o bug reaparece, salvo quando a linha estiver explicitamente marcada como risco aceito/out of scope.

## 5. Ordem de execução

A ordem abaixo considera exploitabilidade, blast radius e dependências:

1. **#1608** — remover `eval` do workflow secret-bearing;
2. **#1609** — estreitar relays e DJEN proxy;
3. **#1610** — boundary única para URLs de manifestos + identidade de geração;
4. **#1611** — budgets de ingestão;
5. **#1615** e **#950** — limitar egress/amplificação do MCP/DataJud;
6. **#1612** — formula injection;
7. **#1613** — CSP + piso XSS/runtime remoto;
8. **#1614** — lock/build/container/SBOM;
9. **#1616** — contrato machine-readable de conteúdo não confiável para agentes.

A ordem não muda a severidade. Ela apenas define o caminho de implementação com menor dependência e maior redução de risco por mudança.

## 6. Regra para novos achados

Novo achado de segurança deve responder, no mínimo:

1. qual fronteira de confiança foi atravessada;
2. qual invariante foi violado;
3. qual impacto concreto existe no CausaGanha;
4. se o ataque exige usuário anônimo, fonte comprometida, colaborador, operador ou segredo prévio;
5. qual gate automatizado provará a correção;
6. qual issue rastreia a implementação.

Checklist genérico sem relação com uma fronteira/ativo deste documento não é suficiente para alterar prioridade.
