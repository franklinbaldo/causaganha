---
type: AgentDecision
id: "2026-09-15-exciting-mccarthy-afj2il-decision-reject-voto-scoped-tags"
run_id: "2026-09-15-exciting-mccarthy-afj2il"
question: "Em doc_c772414481, a anotação B (subagente Técnica 1) tagueou `dispositivo_abertura` ('Ante o exposto') dentro do VOTO individual do relator. Adotar esse label na resolução?"
choice: "Rejeitado. `dispositivo_abertura` não aparece na resolução final; o texto 'Ante o exposto' permanece sem tag."
rationale: "A guideline proíbe explicitamente essa exata construção: 'do not also tag a single-judge dispositivo_abertura inside an individual voto as the decision's operative opening.' B cometeu exatamente o anti-padrão descrito -- 'Ante o exposto, VOTO pelo NÃO CONHECIMENTO...' é a abertura do voto individual do relator, não a abertura do dispositivo da decisão colegiada (que neste documento nem existe como dispositivo_abertura separado -- o acórdão vai direto de EMENTA para ACÓRDÃO/acordao_decisorio, sem uma seção de dispositivo_abertura independente). Manter esse label teria contaminado o dataset de treino com um falso positivo estrutural, o mesmo tipo de erro que a guideline foi escrita para prevenir."
---

# Decisão: rejeitar dispositivo_abertura/resultado ancorados no voto individual

Ver `decision-resultado-collegiate-not-voto` para o raciocínio completo
sobre `resultado`; esta decisão documenta especificamente por que
`dispositivo_abertura` de B foi descartado por inteiro (não é um caso de
fronteira em disputa, é um label que não deveria existir nesta posição).
