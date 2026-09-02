# Objetivos de serviço

Limites operacionais declarados para o pipeline de arquivamento, e como são
verificados. Isto é sobre **confiabilidade operacional** — distinto de
`docs/GOVERNANCE.md`, que trata do que é preservado e por quê.

## Por que isto existe

O CI (`test.yml`) só prova que o frontend builda contra dados sintéticos —
nunca que o DJEN está acessível, que o pipeline de sincronização ainda está
rodando, ou que o dashboard público reflete dados frescos. O
`.github/workflows/canary.yml` fecha essa lacuna com uma verificação diária
contra o sistema real e implantado.

## Limites e como são verificados

| Objetivo | Limite | Verificação |
| --- | --- | --- |
| Frescor do status público (`generated_at` em `site-status.json`) | ≤ 48h | `scripts/canary_check.py`, diariamente às 10:00 UTC |
| Frescor do último sucesso de sincronização por fonte (`sources.djen.last_success_at`) | ≤ 48h | mesmo canário — pega o caso "coleta ativa mas nunca conclusiva" |
| Sanidade do manifesto (`coverage_pct` em [0,100], `pairs_total`/`tribunals_total` > 0) | — | mesmo canário |
| Cliente DJEN retorna veredito definitivo (disponível ou ausente, não erro) para um tribunal estável em dia útil recente | — | mesmo canário, 1 lookup ao vivo (TJRO) |
| Atraso publicação→arquivo (`sources.djen.pending_real` em `site-status.json`) | ≤ `PENDING_REAL_THRESHOLD` (50) pares | mesmo canário |
| Artefato público do STJ (`stj_totals.json`) alcançável e estruturalmente não-vazio (`total`, `total_temas`, `ultima_decisao`) | — (sem SLO de frescor: STJ não tem manifesto por par) | mesmo canário, `check_stj_published()` |
| Manifesto próprio do TJRO JURIS (`tjro-juris-manifest.csv`) alcançável, estruturalmente válido e com pelo menos uma entrada | — (prova operacionalidade do pipeline, não da reconciliação — ver nota abaixo) | mesmo canário, `check_tjro_juris_published()` |
| Bundle de estado coerente do DataJud (`datajud-state-{tribunal}.zip`) alcançável, com hashes/generation válidos e manifesto com pelo menos uma entrada | — (sem SLO de frescor: cadência de enriquecimento é limitada por rate-limit, não um intervalo fixo como o do DJEN) | mesmo canário, `check_datajud_published()` |
| O próprio `canary.yml` continua executando (último sucesso registrado pelo GitHub Actions) | ≤ `CANARY_HEARTBEAT_THRESHOLD_HOURS` (192h / 8 dias) | `.github/workflows/canary-heartbeat.yml`, semanalmente às segundas 09:00 UTC, `scripts/canary_heartbeat_check.py` |

O limiar de 48h **não é um número novo**: é exatamente
`FRESHNESS_THRESHOLD_MS` em `web/src/lib/data/siteStatus.ts`, o limiar que
`evaluateSourceFreshness()` já usa para decidir se uma fonte aparece como
"atualizado" ou "atrasado" no próprio dashboard. O canário alarma
ativamente sobre exatamente o que o site já considera obsoleto
passivamente — não inventa um SLO paralelo.

## Canal de alerta

Nenhuma integração nova. O canário falha (`exit 1`) quando um limite é
violado; a notificação padrão do GitHub Actions para falha de workflow
agendado é o canal — o mesmo mecanismo que já sinalizou, por exemplo, os
30/30 runs vermelhos do STJ/TJRO Sync auditados na PR #813. Um 403 do DJEN
(rate-limit da CloudFront/WAF) é registrado como aviso, nunca como falha —
consistente com a regra de `CLAUDE.md`: 403 não é ausência.

## Atraso publicação→arquivo: limitação conhecida do alarme

A meta declarada é 24h entre DJEN confirmar disponibilidade e o ZIP estar no
Internet Archive, alinhada à cadência diária real do pipeline
(`consolidate-parquet.yml` roda às 07:00 UTC). O alarme do canário
(`PENDING_REAL_THRESHOLD` em `scripts/canary_check.py`) é uma proxy por
**contagem**, não uma medição literal de atraso em horas: `site-status.json`
só expõe o agregado `pending_real` (pares que o DJEN confirmou disponíveis
mas ainda sem upload no IA), sem timestamp por par. `pending_real` em
produção fica normalmente em zero, então qualquer acúmulo sustentado acima
do limiar já é anômalo — mas uma medição fiel ao SLO de 24h exigiria
consultar o manifesto por linhas `djen_raw` disponível há mais de 24h sem
`ia_status=uploaded`, o que este alarme não faz.

## TJRO JURIS: manifesto próprio vs. catálogo reconciliado

`check_tjro_juris_published()` lê `tjro-juris-manifest.csv` — a mesma
autoridade que `causaganha_status` consulta e que o workflow diário
(`tjro-sync.yml`) usa para continuidade — não o artefato derivado
`juris_totals.json`. Esse artefato hoje reporta zero porque o reconciliador
ainda não publica os documentos JURIS no catálogo público (gap rastreado na
issue #924, item 3.1), uma limitação distinta da saúde do próprio pipeline
de coleta/upload. Este canário prova apenas que o pipeline continua
crawleando e publicando seu manifesto — não que a lacuna de reconciliação
foi fechada.

## Heartbeat do próprio canário

`canary.yml` prova que o sistema implantado funciona, mas seu próprio canal
de alerta é ele mesmo: se o cron parasse de disparar (trigger desabilitado,
workflow removido, instabilidade de agendamento do lado do GitHub), nada
avisaria ninguém. `canary-heartbeat.yml` é deliberadamente um workflow
separado, em um agendamento diferente (segundas-feiras, em vez do cron
diário do canário), que lê o histórico público de runs de `canary.yml` via
API do GitHub Actions (`causaganha_mcp.workflow_runs.observe_workflow_runs`,
sem token) e falha se o último sucesso registrado for mais antigo que
`CANARY_HEARTBEAT_THRESHOLD_HOURS`. Continua verificando mesmo que
`canary.yml` pare de rodar por completo, porque não vive no mesmo workflow.

## O que ainda não está automatizado

- **Interrupção total do agendamento do GitHub Actions no repositório**
  (não apenas de `canary.yml`): se o próprio GitHub parasse de disparar
  *qualquer* workflow agendado neste repositório, `canary-heartbeat.yml`
  também pararia de rodar e a lacuna reapareceria. Isso exigiria
  monitoramento externo ao GitHub Actions para ser fechado — fora do escopo
  atual.
