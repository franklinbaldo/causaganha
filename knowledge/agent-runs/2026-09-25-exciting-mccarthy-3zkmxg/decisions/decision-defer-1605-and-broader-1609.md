---
type: AgentDecision
id: "2026-09-25-exciting-mccarthy-3zkmxg-decision-defer-1605-and-broader-1609"
run_id: "2026-09-25-exciting-mccarthy-3zkmxg"
question: "Dado #1605 (batch27, branch alheia, conflito de merge) e a ordem de execucao sugerida por docs/SECURITY_THREAT_MODEL.md (#1609 antes de #1611), qual e o melhor trabalho desta rodada?"
choice: "Nao tocar #1605 (sem permissao de push na branch claude/exciting-mccarthy-034xwb). Nao selecionar #1609 apesar de vir primeiro na ordem sugerida -- selecionar #1611 em vez disso."
rationale: "#1605 permanece com o mesmo diagnostico de duas rodadas anteriores (e3tk18, p973xb): conflito real de merge numa branch que esta sessao nao tem autorizacao para editar (a politica de sessao restringe push a claude/exciting-mccarthy-3zkmxg). Sem fato novo, reafirmar a decisao anterior e correto. Quanto a ordem do threat model: a Sec.5 do documento e explicita que 'a ordem nao muda a severidade, ela apenas define o caminho de implementacao com menor dependencia' -- nao e uma trava sequencial. #1609 abrange 3 superficies heterogeneas (relay Python, relay Cloudflare em JavaScript, djen_proxy.go em Go) sem fixture sintetica pronta e exige decisoes de politica de deploy (quotas na camada de deploy, rotacao de RELAY_TOKEN) que uma unica rodada de TDD em Python dificilmente fecha com o mesmo rigor que fechou #1608/#1612/#1615. #1611 e self-contained (um modulo Python), sem credenciais, com gate automatizado ja especificado no corpo da issue -- mesmo padrao de tratabilidade que as 3 issues de seguranca ja fechadas nesta janela. Preferir o item mais tratavel com evidencia real e TDD completo a um item 'primeiro na lista' que ficaria parcialmente feito."
---

# Decisao: #1605 permanece fora de escopo; #1611 escolhida sobre #1609

`#1605` reconfirmada sem fato novo como fora do alcance desta sessao.
Entre as issues de seguranca abertas, `#1611` foi escolhida sobre `#1609`
(que vem primeiro na ordem sugerida pelo threat model) por ser
self-contained e verificavel por TDD em uma unica rodada, sem depender de
decisoes de infraestrutura de deploy fora do controle desta sessao.
