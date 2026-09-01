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

## O que ainda não está automatizado

- **Alerta sobre o próprio job do canário não rodar** (ex.: se o cron do
  GitHub Actions parar de disparar): não há verificação de "o verificador
  está vivo" — limitação conhecida de qualquer canário auto-hospedado no
  mesmo CI que monitora.
