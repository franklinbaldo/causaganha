---
type: AgentDecision
id: "2026-09-15-exciting-mccarthy-afj2il-decision-resultado-collegiate-not-voto"
run_id: "2026-09-15-exciting-mccarthy-afj2il"
question: "Nos dois acórdãos desta rodada, nenhuma das duas anotações independentes marcou corretamente o `resultado` operativo no mesmo lugar: em doc_c772414481, A marcou dentro de acordao_decisorio ('RECURSO NÃO CONHECIDO') e B dentro de voto ('VOTO pelo NÃO CONHECIMENTO...'); em doc_4125f9aa, A marcou dentro de voto ('acolho seus embargos declaratórios') e B não marcou nenhum. Qual placement é o correto segundo a guideline, e o que fazer quando nenhuma anotação o captura certo?"
choice: "Em ambos os documentos, `resultado` foi resolvido para a frase operativa DENTRO de `acordao_decisorio` (o resultado colegiado), nunca dentro de `voto` (a posição individual do relator). Em doc_c772414481, isso coincidiu com a escolha de A ('RECURSO NÃO CONHECIDO'); em doc_4125f9aa, nenhuma anotação tinha a tag no lugar certo, então o revisor introduziu 'EMBARGOS DE DECLARAÇÃO ACOLHIDOS' dentro de acordao_decisorio como novo label na resolução."
rationale: "A guideline (seção 'Acórdão (second-instance) notes') é explícita: 'An acórdão's operative result is the collegiate acordao_decisorio (\"ACORDAM ...\"); do not also tag a single-judge dispositivo_abertura inside an individual voto as the decision's operative opening.' A regra é escrita para dispositivo_abertura, mas o mesmo princípio se aplica por extensão direta a resultado -- é a mesma distinção entre a proposta individual do relator (dentro de voto) e o resultado colegiado real (dentro de acordao_decisorio). Adjudicação não é obrigada a escolher entre A ou B quando ambas erram: o job do revisor é produzir sua própria reprodução tagueada correta (README do script: 'the reviewer supplies their own fully tagged reproduction... after examining both inputs' disagreements'), então introduzir um novo label correto quando nenhuma anotação o capturou é o uso pretendido do mecanismo, não um desvio dele."
---

# Decisão: resultado é sempre o resultado colegiado, nunca a proposta individual do voto

Padrão descoberto e aplicado de forma consistente nos dois documentos desta
rodada (ambos acórdãos de órgão colegiado -- Turma Recursal e Câmara
Cível). A guideline já proíbe explicitamente tratar a abertura do
dispositivo individual do voto como a abertura operativa da decisão; a
mesma lógica se estende ao próprio `resultado`. Isso não é uma mudança de
guideline -- é a aplicação direta da regra já escrita, que nenhuma das
quatro anotações (A e B em ambos os documentos) aplicou de forma
totalmente consistente. Vale registrar como precedente explícito para
adjudicações futuras de acórdãos: sempre verificar se `resultado` está
ancorado dentro de `acordao_decisorio`, não dentro de `voto`, mesmo quando
ambas as anotações concordam em colocá-lo no lugar errado.
