---
type: AgentDecision
id: "2026-09-15-exciting-mccarthy-f3feqb-decision-reject-garbled-ooxml-anchor"
run_id: "2026-09-15-exciting-mccarthy-f3feqb"
goal_id: "2026-09-15-exciting-mccarthy-f3feqb-goal-scale-segmenter-reviews"
question: "Em doc_ad9d4a846d91353b317e3017245ffee5, o texto extraído carrega um artefato de conversão .docx corrompido logo antes de 'SENTENÇA' ('Advogado do(a) EXECUTADO: Normal 0 21 false false false PT-BR X-NONE X-NONE SENTENÇA'). A nova anotação independente (B, haiku) tagueou cabecalho_fim como o literal 'X-NONE' (a última ocorrência antes de SENTENÇA). A anotação histórica (A) não tem nenhum label (zero-tag). Qual âncora adotar na adjudicação?"
choice: "Rejeitado 'X-NONE' como âncora; adotado 'Advogado do(a) EXECUTADO:' (última menção real de parte/advogado antes de SENTENÇA)."
rationale: "A guideline define cabecalho_fim como 'Last party/OAB before SENTENÇA' -- uma âncora de conteúdo substantivo do cabeçalho processual, não literalmente a última substring antes da palavra SENTENÇA independente do que seja. 'X-NONE'/'Normal 0 21 false false false PT-BR' é lixo de metadado OOXML vazado na extração de texto do .docx original (idioma/revisão do documento Word), não uma parte do cabeçalho processual real. A leitura mais fiel à intenção da guideline é ancorar no último conteúdo substantivo genuíno ('Advogado do(a) EXECUTADO:'), tratando o lixo de extração como ruído fora do cabeçalho, exatamente como a guideline já trata outros artefatos de fonte (falhas de fonte nunca definem conteúdo substantivo)."
---

# Decisão: rejeitar âncora de metadado OOXML corrompido

`cabecalho_fim` não pode ancorar em lixo de extração de .docx
("X-NONE"/"Normal 0 21 false false false PT-BR"); a âncora correta é o
último conteúdo substantivo real de parte/OAB antes de SENTENÇA. Registra
também, via nota anexada à ReviewRecord, um gap de qualidade de extração
pré-existente nesta store (não corrigido aqui -- é o texto já persistido
em `DocumentRecord`, fora do escopo desta rodada de adjudicação).
