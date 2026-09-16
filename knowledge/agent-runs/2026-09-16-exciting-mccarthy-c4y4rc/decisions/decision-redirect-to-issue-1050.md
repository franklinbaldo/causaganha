---
type: AgentDecision
id: "2026-09-16-exciting-mccarthy-c4y4rc-decision-redirect-to-issue-1050"
run_id: "2026-09-16-exciting-mccarthy-c4y4rc"
question: "10+ rodadas consecutivas escalaram ReviewRecords dentro do pool fixo de 61 documentos do segmentador, tratando isso como o caminho direto para o piso de RFC 0012 Sec 5.4. A verificacao ao vivo desta rodada (assign_splits real + simulacao de 100% de adjudicacao) mostrou que o teto e val=9/test=9 em ambos os casos -- adjudicar mais documentos do pool atual nao pode cruzar 30/30. Esta rodada deveria continuar adicionando mais 1-2 ReviewRecords ao pool de 61 (como as rodadas anteriores), ou registrar o teto e redirecionar explicitamente a linhagem para #1050 (escala de corpus)?"
choice: "Nao adicionar mais ReviewRecords ao pool de 61 nesta rodada. Em vez disso: (1) tornar o teto um fato testado e publicado (scripts/segmenter_governance_status.py + testes); (2) corrigir knowledge/backlog/issue-1051.md, que estava desatualizado desde 2026-09-07 e ja tinha sido apontado como tal por 2 rodadas anteriores sem correcao; (3) comentar em #1051 e #1050 no GitHub redirecionando o proximo passo real da linhagem para a escala do corpus (#1050), nao mais para adjudicacao isolada dentro do pool fixo."
rationale: "Mais um ReviewRecord teria custo real (tokens, verificacao de fidelidade verbatim, revisao humana-por-subagente) sem mover a linhagem em direcao a meta real -- o teto e matematico (val_target = round(total_eligible * val_ratio) sobre o TOTAL do corpus, nao sobre o pool elegivel), nao uma questao de mais rodadas. Publicar esse fato agora evita que a proxima duzia de rodadas repita o mesmo padrao (mais um documento, mais um review) sem perceber que o gargalo mudou de #1051 para #1050. Isso e coerente com a instrucao de preferir uma solucao correta e coerente ao estado atual, e com 'se um goal ainda nao tiver evidencia de avanco, produza essa evidencia' -- aqui o avanco real e desbloquear o proximo passo certo, nao inflar um contador que ja provou nao levar a lugar nenhum sozinho."
---

# Decisao: parar de adjudicar dentro do pool de 61 e redirecionar para #1050

Decisao arquitetural desta rodada: o proximo passo natural da linhagem
#1051 deixa de ser "mais um documento adjudicado" e passa a ser "crescer o
corpus total" (#1050), com evidencia matematica e testada para sustentar
essa mudanca de direcao.
