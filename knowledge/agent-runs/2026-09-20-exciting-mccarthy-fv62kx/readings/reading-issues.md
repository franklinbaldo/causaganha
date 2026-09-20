---
type: AgentReading
id: "2026-09-20-exciting-mccarthy-fv62kx-reading-issues"
run_id: "2026-09-20-exciting-mccarthy-fv62kx"
subject: "open_issues"
reference: "mcp__github__list_issues (owner=franklinbaldo, repo=causaganha, state=OPEN), 22 total"
finding: "#1050 continua a linhagem mais ativa com caminho de execucao provado (23 lotes reais mesclados). Estado ao vivo confirmado nesta rodada via scripts/segmenter_governance_status.py: document_count=179, val_ceiling=test_ceiling=27, ainda abaixo do piso RFC 0012 Sec 5 item 4 (>=30/>=30). #1051 continua bloqueada estruturalmente ate #1050 crescer. #1482 (CORS) e #1468-1472 (Parquet/CNJ) seguem bloqueadas por credenciais externas ausentes nesta sessao (confirmado: sem env CF_*/CLOUDFLARE_* e sem credenciais IA). Nenhuma issue aberta oferece caminho de execucao imediato sem bloqueio externo alem de #1050."
---

# Leitura: issues abertas

`mcp__github__list_issues` (owner=franklinbaldo, repo=causaganha,
state=OPEN, orderBy=UPDATED_AT desc) retornou 22 issues. Mais
relevantes, reverificadas nesta rodada:

- **#1050** -- linhagem mais ativa do repositorio, 23 lotes reais ja
  mesclados (batch22 via PR #1585, batch23 via PR #1586, ambos apos a
  ultima rodada). Estado ao vivo confirmado agora:
  `document_count=179`, `annotation_count=232`, `review_count=31`,
  `val_count=27`, `test_count=4`, `val_ceiling=test_ceiling=27`,
  `meets_rfc_0012_split_floor=false`, `corpus_scale_blocks_floor=true`.
  Ainda faltam ~3 lotes deste tamanho para cruzar o piso de 30/30.
- **#1051** -- continua bloqueada estruturalmente (mesmo
  `corpus_scale_blocks_floor=true` acima).
- **#1482** (CORS em archive.org) -- workaround de codigo (#1521,
  Cloudflare Worker) ja mesclado, mas bloqueado em deploy real por
  credenciais Cloudflare ausentes (`env | grep -i cloudflare` vazio
  nesta sessao tambem).
- **#1468-#1472** (cadeia Parquet/CNJ) -- seguem bloqueadas por
  credenciais IA ausentes.
- **#1053-#1057** (roadmap de treino do segmentador) -- dependem de
  #1050 cruzar o piso RFC 0012 primeiro.

Conclusao: nenhuma issue aberta hoje oferece um caminho de execucao
imediato sem bloqueio de credenciais externas com tanto contexto
acumulado quanto #1050. A linhagem #1050 continua sendo a escolha mais
direta para avanco real nesta rodada -- alem disso, ha um PR de codigo
ja aberto por uma sessao concorrente (#1588, ver leitura de PRs) que
corrige a causa raiz de um workaround usado nos ultimos lotes.
