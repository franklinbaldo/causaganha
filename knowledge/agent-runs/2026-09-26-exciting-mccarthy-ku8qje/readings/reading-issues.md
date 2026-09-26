---
type: AgentReading
id: "2026-09-26-exciting-mccarthy-ku8qje-reading-issues"
run_id: "2026-09-26-exciting-mccarthy-ku8qje"
subject: "open_issues"
reference: "GitHub issues abertas, franklinbaldo/causaganha (list_issues, state=OPEN, 21 abertas)"
finding: "21 issues abertas: nenhuma de segurança (backlog do threat model permanece exaurido, confirmado por rodadas anteriores). #950 (rollout MCP remoto) está aberta (`state_reason: reopened`) e bloqueada por falta de credenciais GCP/Cloud Run nesta sessão -- `#951`/`#1093` dependem dela e continuam igualmente bloqueadas. #1470/#1469/#1471/#1472/#1468/#1022/#985 (Parquet/CNJ/TCU/TSE) seguem bloqueadas por credenciais Internet Archive ausentes neste tipo de sessão, fato já estabelecido por 15+ rodadas anteriores -- reconfirmado sem tentar burlar (nenhuma variável IAS3_*/IA_* no ambiente, `~/.config/internetarchive/ia.ini` ausente). A trilha do segmenter é a única com trabalho tratável sem credenciais externas: #1050 (crescer o corpus real multi-tribunal) e #1051 (adjudicar validação/teste) são as duas frentes ativas; `#1047`/`#1053`-`#1057`/`#884`/`#886`/`#887` são o roadmap de experimentos subsequentes (baseline OPF, active learning, benchmarks) que dependem de #1050/#1051 amadurecerem primeiro -- não selecionáveis ainda. Verificação ao vivo desta rodada (`scripts/segmenter_governance_status.py`) mostrou que o teto real de val/test (29/29) está UM documento abaixo do piso RFC 0012 Sec 5 item 4 (>=30/>=30) mesmo com adjudicação 100% do pool atual de 195 documentos -- ou seja, mais adjudicação de #1051 sozinha não pode mais avançar o piso enquanto #1050 não crescer o corpus além de 197 documentos. Esse é o achado que direciona o goal desta rodada para #1050, não #1051 (que PR #1665, mesclada nesta própria rodada, já havia avançado)."
---

# Leitura: issues abertas

21 issues abertas revisadas via `list_issues` (state=OPEN). Toda a
trilha bloqueada por credenciais (MCP remoto #950/#951/#1093,
Parquet/CNJ/TCU/TSE #1470/#1469/#1471/#1472/#1468/#1022/#985)
reconfirmada sem fato novo. O achado que direciona a rodada:
`scripts/segmenter_governance_status.py` mostra que o teto real de
val/test do corpus atual (195 documentos) é 29/29 -- um documento
abaixo do piso de RFC 0012 Sec 5 item 4 (>=30/>=30) mesmo com 100% de
adjudicação. Adjudicar mais documentos de #1051 não pode mais mover
esse piso; crescer o corpus via #1050 é o único caminho que reabre
progresso real para #1051 também.
