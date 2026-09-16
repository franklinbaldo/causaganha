---
type: AgentReading
id: "2026-09-16-exciting-mccarthy-c4y4rc-reading-issues"
run_id: "2026-09-16-exciting-mccarthy-c4y4rc"
subject: "open_issues"
reference: "GitHub issues, state=OPEN, 22 total, ordenadas por updated_at desc (list_issues)"
finding: "#1468/#1469/#1470/#1471/#1472 (Parquet/CNJ no IA): reconfirmado esgotado -- comentário da própria rodada anterior (2hb3sq-linhagem, 2026-09-15T21:31Z) em #1469 já documenta que todo critério alcançável sem credenciais IA está implementado e testado em main; só resta a publicação real (#1472), bloqueada por IA_ACCESS_KEY/IA_SECRET_KEY ausentes. #1051/#1050 (segmentador): única frente de domínio desbloqueada. #1050 (issue-mãe de escala de corpus) não tem nenhum comentário ainda -- nunca foi trabalhada diretamente, apesar de ser citada repetidamente como o caminho real para #1051 atingir a meta de RFC 0012 §5 item 4."
---

# Leitura: issues abertas

22 issues abertas (`list_issues`, state=OPEN). Relevantes para esta rodada:

- **#1051** "segmenter: build an independently annotated validation set for
  model selection": em progresso há 10+ rodadas nesta linhagem (PRs
  #1505-#1533), `review_count`/`evaluation_eligible_count` em 31 ao final
  da última rodada mesclada (2hb3sq). `knowledge/backlog/issue-1051.md`
  ainda diz `status: "blocked"` com `last_verified_at: 2026-09-07T02:45:00Z`
  — desatualizado, já reconhecido por pelo menos 2 rodadas anteriores
  (wvzu11, 2hb3sq) sem correção.
- **#1050** "segmenter: repair and scale the real training corpus with
  agent annotation": issue-mãe do suprimento real de corpus (RFC 0012 §5
  item 4 fixa as metas: >=150 treino anotado, >=30 val adjudicado, >=30
  teste adjudicado). **Zero comentários** — nunca foi trabalhada
  diretamente; todo o trabalho até agora ficou em #1051 (adjudicar dentro
  do pool de 61 documentos já existente), não em crescer o próprio pool.
- **#1468/#1469/#1470/#1471/#1472** (epic Parquet/CNJ no Internet
  Archive): #1469 recebeu um comentário de status-sync há poucas horas
  (2026-09-15T21:31Z, de uma rodada desta mesma linhagem) confirmando que
  todo critério de aceite alcançável sem credenciais de escrita no IA já
  está implementado, testado e em `main`; só resta a publicação real
  (#1472), bloqueada por `IA_ACCESS_KEY`/`IA_SECRET_KEY` ausentes neste
  ambiente (`env | grep -i 'IA_\|ARCHIVE'` — verificar ao vivo antes de
  reconfirmar).
- **#1482** (CORS archive.org): investigado e confirmado sem correção
  viável sem proxy dedicado fora de escopo, por rodadas anteriores.
- Demais issues do segmentador (#884, #886, #887, #950, #951, #985, #1022,
  #1053-#1057, #1093) dependem de GPU/active learning/infra de deploy fora
  do alcance desta sessão; #1050/#1051 são o precursor de dados necessário
  antes delas fazerem sentido.

Nenhuma PR de domínio nova além do padrão já conhecido (ver reading-prs).
