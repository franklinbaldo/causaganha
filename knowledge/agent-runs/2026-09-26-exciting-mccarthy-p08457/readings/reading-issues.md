---
type: AgentReading
id: "2026-09-26-exciting-mccarthy-p08457-reading-issues"
run_id: "2026-09-26-exciting-mccarthy-p08457"
subject: "open_issues"
reference: "GitHub issues abertas, franklinbaldo/causaganha (list_issues, state=OPEN, 21 abertas)"
finding: "21 issues abertas, mesmo conjunto reportado pela rodada ku8qje: #950 (rollout MCP remoto, reaberta, `state_reason: reopened`) e suas dependentes #951/#1093 seguem bloqueadas por credenciais GCP/Cloud Run ausentes nesta sessão (`knowledge/backlog/issue-950.md` confirma `status: blocked`, `last_verified_run_id: uz8msx`, sem fato novo -- não reverificado ao vivo de novo nesta rodada por não ser o goal escolhido e para não arriscar reescrever a nota já cuidadosamente formatada sobre o bug de closing-keyword de #950). #1470/#1469/#1471/#1472/#1468/#1022/#985 (Parquet/CNJ/TCU/TSE) seguem bloqueadas por credenciais Internet Archive ausentes, fato estabelecido por 15+ rodadas anteriores -- não reverificado por não haver sinal de mudança. A trilha do segmenter é a única com trabalho tratável sem credenciais externas: `scripts/segmenter_governance_status.py`, executado ao vivo nesta rodada, confirma que a PR #1665/#1666 (mescladas por uma rodada anterior) já elevaram document_count para 197 e o teto real de val/test para 30/30 -- o piso RFC 0012 Sec 5 item 4 deixou de ser bloqueado por escala de corpus (`corpus_scale_blocks_floor: false`). O gargalo real agora é puramente de cobertura de adjudicação: `val_count=30` (já no teto) mas `test_count=2` (muito abaixo do teto de 30) -- exatamente o achado que o handoff da rodada anterior identificou como próximo passo natural. #1047/#1053-#1057/#884/#886/#887 seguem sendo o roadmap de experimentos subsequentes (baseline OPF, active learning, benchmarks) que dependem de #1050/#1051 amadurecerem primeiro -- não selecionáveis ainda, sem mudança desde a última rodada."
---

# Leitura: issues abertas

21 issues abertas revisadas via `list_issues` (state=OPEN), mesmo
conjunto da rodada anterior. Toda a trilha bloqueada por credenciais
(MCP remoto #950/#951/#1093; Parquet/CNJ/TCU/TSE) reconfirmada sem
fato novo -- não repetida a verificação ao vivo por ausência de sinal
de mudança. O achado que direciona a rodada:
`scripts/segmenter_governance_status.py` mostra `document_count=197`,
`val_ceiling_at_full_adjudication`/`test_ceiling_at_full_adjudication`
= 30/30 (piso RFC 0012 já alcançável), mas `val_count=30` (no teto) e
`test_count=2` -- adjudicação de mais documentos de #1051 volta a ter
efeito mensurável e direto no piso, especificamente no lado do teste.
