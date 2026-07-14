# Resposta à revisão de infraestrutura — julho/2026

Uma revisão externa detalhada avaliou o projeto como "um excelente projeto de
infraestrutura pública dentro de um monorepo de pesquisa um tanto crescido
demais", com nota alta para a tese e a arquitetura de arquivamento e notas
baixas para coerência do repositório, confiabilidade operacional e governança
de dados. Este documento registra a triagem das alegações contra o estado
real do código e o plano de ação priorizado.

## Verificação das alegações

| Alegação da revisão | Estado verificado (2026-07-14) |
| --- | --- |
| Descrição do `pyproject.toml` ainda fala em "OpenSkill rating system" | **Confirmado.** Corrigido neste PR. |
| `openskill` e `pydantic-ai` são dependências de runtime | **Confirmado — e piores que o alegado: nenhum arquivo do repositório as importa.** Removidas neste PR. |
| `google-genai` é dependência essencial | **Parcialmente stale.** Só é importada por 5 scripts experimentais (`scripts/pipeline/embed*.py`, `analyze_with_rag.py`, `batch_embed_decisions.py`, `index_ground_truth.py`); nenhum workflow agendado os executa. Movida para o dependency group `lab` neste PR. |
| CLI principal ainda expõe `analyze`, `score`, `groundtruth` | **Stale.** O único entry point de `causaganha` hoje é `consolidate` (`src/causaganha/consolidate/cli.py`). Os conceitos citados sobrevivem apenas em `scripts/` e em `src/causaganha/analysis/`. |
| README ainda vende "Legal Intelligence Platform" | **Stale.** O README já descreve o arquivo DJEN. O texto "About" do GitHub, porém, **está desatualizado** (configuração do repositório, não versionada — ação manual do mantenedor). |
| ~265 violações de estilo pré-existentes tratadas como advisory no CI | **Confirmado** (`.github/workflows/test.yml`). |
| Ausência de política de governança de dados, correção/remoção, retenção e licença dos datasets distinta do MIT | **Confirmado.** `sobre.astro` tinha um parágrafo de licença, nada sobre correção/remoção/retenção. Criado `docs/GOVERNANCE.md` neste PR, com link no README e na página Sobre. |
| Issue #809: dois números de cobertura conflitantes na mesma página | **Confirmado como aberto.** Fora do escopo deste PR — ver plano abaixo. |
| `scripts/` é uma segunda camada de aplicação | **Confirmado** (44 arquivos misturando operação, migração e experimento). |
| Build do frontend usa dados sintéticos; nada prova o sistema implantado de ponta a ponta | **Confirmado.** Não existe canário de integração real. |

## O que este PR entrega (prioridades 1 e 4 da revisão)

1. **Identidade**: `pyproject.toml` agora descreve o projeto como arquivo
   público e camada de dados estruturados do DJEN; dependências mortas
   (`openskill`, `pydantic-ai`) removidas; `google-genai` isolada no grupo
   `lab` — primeiro passo concreto da fronteira "Lab" proposta pela revisão.
2. **Governança**: `docs/GOVERNANCE.md` adota preservação integral como
   regra — correção, restrição ou remoção apenas em hipóteses objetivas
   (erro do próprio projeto ou determinação de autoridade competente — sem
   nenhuma hipótese de juízo próprio do projeto sobre gravidade ou dano).
   Alterações posteriores na fonte oficial não retiram conteúdo do acervo:
   são anotadas como proveniência, pois preservar o registro histórico do
   que foi publicado é a função do arquivo. Descobribilidade é tratada como
   parte da missão, não como risco: nenhum `noindex` ou limitação de busca como regra geral, e nenhum
   compromisso sobre superfícies fora do controle do projeto (o texto
   integral vive no Internet Archive). Sem "direito ao esquecimento"
   genérico, conforme STF Tema 786. Registra a posição do projeto sobre o
   âmbito da LGPD (art. 4º, I — pessoa natural, fins não econômicos;
   reforçada pelo art. 2º, III, art. 4º, II e art. 7º, §§ 3º–4º e IX) e a
   custódia das cópias primárias no Internet Archive, sob jurisdição e
   políticas próprias. Cobre ainda retenção, canais (privado para casos
   sensíveis) e licenciamento em duas camadas (código MIT; textos de atos
   oficiais sem proteção autoral, art. 8º, IV, Lei 9.610/98; direitos do
   projeto sobre datasets derivados em CC0 1.0). README e página Sobre
   linkam a política.

## Plano de ação para o restante (em ordem)

1. **Ação manual do mantenedor (5 min):** atualizar o "About" do repositório
   no GitHub — remover "Legal Intelligence Platform / predictive automation",
   descrever o arquivo público do DJEN. **Ainda pendente** — é configuração
   do repositório, não versionada; nenhum PR alcança isso.
2. ~~**#809 — eliminar o caminho legado de dados em
   `/publicacoes/[tribunal]`**~~ **Feito.** Resolvida por PR #817
   (`fix(web): migrate /publicacoes/[tribunal] off the legacy live-IA data
   path`), mergeada antes mesmo deste PR — `TribunalDetail.svelte` agora lê
   exclusivamente de um novo contrato `tribunal_calendar.qmd` derivado do
   manifesto canônico; `buildTimeData.ts`/`useDashboard.svelte.ts`/
   `QueryProvider.svelte` (o stack legado) foram deletados.
3. **Canário de ponta a ponta:** um par (tribunal, data) pequeno e conhecido
   atravessando coleta → IA → manifesto → Parquet → `render_queries` →
   leitura via browser (Playwright já está nas dev-deps). Roda agendado, não
   por PR; falha alto quando a fronteira real driftar do stub do CI. **Ainda
   pendente** — decisão de produto (frequência do cron batendo em DJEN/IA ao
   vivo, canal de alerta) que cabe ao mantenedor, não a um PR autônomo.
4. **Objetivos de serviço explícitos:** atraso máximo publicação→arquivo,
   idade máxima do status público, alerta quando a coleta funciona mas a
   geração de status não. O painel de status já existe; falta o alarme.
   **Ainda pendente**, mesma razão do item 3 (canal de notificação e
   thresholds são decisão do mantenedor).
5. ~~**Subtração contínua**~~ **Primeiro passo feito neste PR** — ver
   "Auditoria de `scripts/`" abaixo. Removido `scripts/upload_to_ia.py`
   (órfão: seu próprio docstring alegava ser "invocado por collect-zips.yml
   e consolidate-parquet.yml", mas esses workflows na verdade chamam
   `causaganha.pipeline.ia_s3.upload_to_ia`, uma função diferente — zero
   imports, zero testes, zero referências reais). A separação física
   completa em `lab/`/`migrations/` fica para um PR dedicado (ver
   ressalva de acoplamento abaixo).
6. ~~**Revisão humana obrigatória em áreas estreitas**~~ **Feito neste PR**
   — `.github/CODEOWNERS` cobre semântica de status (`djen.py`,
   `manifest.py`), contratos de schema/consolidação (`consolidate/`,
   `web/src/queries/`, `contracts.ts`), o relay de segurança
   (`deployment/relay/`) e `docs/GOVERNANCE.md`. O arquivo é inerte até o
   mantenedor ativar "Require review from Code Owners" na proteção de
   branch — ação de configuração do GitHub, não de código.

## Auditoria de `scripts/` (fase 1 da subtração)

Dos 44 arquivos/diretórios em `scripts/`, 23 são referenciados por algum
workflow (`ops`, produto suportado). Os 17 arquivos + 4 subdiretórios
restantes foram auditados individualmente (referências em outros scripts,
testes, docs) e classificados:

- **`lab`** (experimental — embeddings, LLM, treinamento, benchmark de
  schema): `analyze_with_rag.py`, `annotate_with_llm.py`,
  `batch_embed_decisions.py`, `build_segmenter_training_parquet.py`,
  `classify_from_batch_embeddings.py`, `ensemble_compare.py`,
  `evaluate_regex_segmenter.py`, `index_ground_truth.py`,
  `ref_normativa_prepass.py`, `reconstruct_regions.py`,
  `segment_decision.py`, `scripts/benchmarks/*` (4 arquivos).
- **`migration`/dev-tool** (manutenção pontual, não recorrente, não
  experimental): `setup_dev.sh`, `snapshot_parquets_for_rollback.py`,
  `vendor_pje_swagger.py`, `scripts/db/*` (2 arquivos),
  `scripts/dev/*` (5 arquivos).
- **Borderline, confirmar com o mantenedor antes de mover:**
  `build_gold_benchmark.py` (dataset-building, mas é invocado pelo script
  `ops` `daily_benchmark_update.py` via mensagem de erro/instrução, não
  import — mover exige atualizar essa referência textual);
  `stress_test_djen.py` (diagnóstico manual, mas importado por
  `src/djen_backup/__main__.py`); `scripts/web/generate-data.py` (tem
  teste dedicado mas nenhum workflow o chama — verificar se está
  realmente morto antes de mover).
- **Dead, removido neste PR:** `upload_to_ia.py`.

**Ressalva de acoplamento que bloqueia um move mecânico agora:**
`segment_decision.py` importa de `reconstruct_regions.py` e
`ref_normativa_prepass.py` (ambos candidatos a `lab`), e várias dessas
scripts (`annotate_with_llm.py`, `build_segmenter_training_parquet.py`,
`evaluate_regex_segmenter.py`, `reconstruct_regions.py`) importam de
`prepare_privacy_filter_dataset.py` — que é `ops` (referenciado por
workflow). Mover só os arquivos `lab` para `scripts/lab/` sem mover
`prepare_privacy_filter_dataset.py` mantém essas importações funcionando
(fica em `scripts/` top-level), mas qualquer PR de subtração física precisa
atualizar `from scripts.X import` para `from scripts.lab.X import` nos
arquivos movidos entre si, mais os testes (`tests/test_*.py` que importam
esses módulos por caminho) e `vulture_whitelist.py`. Não fiz esse move
neste PR para não arriscar quebrar import paths sem verificação completa de
teste — registrado aqui para execução deliberada.

## Retratação do revisor (2ª rodada)

Após a reorientação da política de governança, o revisor externo retratou
três sugestões da primeira rodada e aprovou o PR como está:

1. **Retirada por mudança na fonte** — reconheceu que confundia o estado
   atual do processo com o fato histórico da publicação; alterações
   posteriores da fonte são proveniência, não borracha.
2. **`noindex` geral** — reconheceu que tratava descobribilidade como dano
   colateral quando ela é o produto, e que a Resolução CNJ 121 obriga os
   serviços de consulta dos tribunais, não arquivos independentes.
3. **Linguagem hesitante sobre a LGPD** — reconheceu que a seção é uma
   declaração de posição jurídica do projeto, não um parecer; a existência
   de interpretações contrárias não obriga a adotar antecipadamente a mais
   restritiva.

Síntese adotada como princípio de abertura da política: "O projeto preserva
o registro público produzido pelo Estado; não reavalia, não higieniza e não
reescreve esse registro por iniciativa própria."

A política cobre também a **camada analítica** (classificação de quem
ganhou/perdeu e indicadores por advogado — a segunda metade do nome do
projeto), com a distinção de responsabilidade correspondente: a camada de
arquivo responde pela fidelidade ao que o Estado publicou; a analítica,
pela correção do que o próprio projeto calculou (erro de classificação ou
atribuição é hipótese 1, corrigível por demonstração objetiva contra o
registro; indicador desfavorável não gera direito à remoção).

## O que a revisão acerta em espírito

> "Its next stage should be defined by subtraction, consistency and
> operational boredom — not by adding more intelligence features."

Adotado como critério de triagem de novas features: se não torna o arquivo
mais completo, mais auditável ou mais barato de operar, vai para o Lab ou
não entra.
