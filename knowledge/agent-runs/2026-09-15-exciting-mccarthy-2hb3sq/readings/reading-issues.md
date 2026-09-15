---
type: AgentReading
id: "2026-09-15-exciting-mccarthy-2hb3sq-reading-issues"
run_id: "2026-09-15-exciting-mccarthy-2hb3sq"
subject: "open_issues"
reference: "GitHub issues, state=OPEN, 22 total, ordenadas por updated_at desc"
finding: "#1051/#1050 (segmenter real corpus) seguem abertas, desbloqueadas e não esgotadas -- pool real de candidatos pareáveis subiu de 11 (relatado por f0q3d4) para 18 nesta rodada. #1468/#1470/#1471/#1472 (Parquet/CNJ no IA) seguem bloqueadas por falta de IA_ACCESS_KEY/IA_SECRET_KEY no ambiente (`env | grep -i 'IA_\\|ARCHIVE'` vazio). #1482 (CORS archive.org) segue sem solução viável sem proxy dedicado fora de escopo (mixed content HTTPS->HTTP no redirect do S3 do IA), já investigado e confirmado por rodadas anteriores (50ns70)."
---

# Leitura: issues abertas

22 issues abertas. As relevantes para trabalho desbloqueável nesta janela:

- **#1051** "segmenter: build an independently annotated validation set for
  model selection" e **#1050** "segmenter: repair and scale the real
  training corpus with agent annotation": ativamente em progresso há 9+
  rodadas (PRs #1505-#1531, ReviewRecords 11->29). `knowledge/backlog/issue-1051.md`
  ainda diz `status: "blocked"` com `last_verified_at: 2026-09-07` -- **esse
  backlog item está desatualizado**, já que o trabalho avançou continuamente
  desde então via subagentes isolados fazendo o papel do "human annotator"
  citado no `unblock_condition`. Vale corrigir esse registro numa rodada
  futura (não fiz isso agora para não desviar do incremento de domínio desta
  rodada, mas registro aqui para não repetir a confusão).
- **#1469** "Parquet/CNJ: unificar escrita normalizada e leitura compatível
  no site": atualizada há poucas horas por mim mesmo (comentário de f0q3d4
  sincronizando o checklist textual desatualizado com o estado real do
  código, já quase inteiramente implementado em main).
- **#1468/#1470/#1471/#1472**: epic Parquet/CNJ no Internet Archive, todas
  bloqueadas por falta de credenciais IA no ambiente desta sessão -- mesma
  situação desde pelo menos 11/09.
- **#1482**: proxy CORS para leitura direta do archive.org -- já
  investigado ao vivo e confirmado sem correção real sem infraestrutura
  dedicada fora do escopo de uma rodada automatizada.
- Demais issues do segmentador (#884, #886, #887, #1053-#1057) dependem de
  treino real com GPU/active learning, fora do alcance desta sessão; #1051
  é o precursor de dados necessário antes delas fazerem sentido.

Nenhuma issue nova relevante desde a última leitura (f0q3d4, mesma
madrugada/noite).
