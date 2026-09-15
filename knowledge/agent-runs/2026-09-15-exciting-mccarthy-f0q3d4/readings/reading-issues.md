---
type: AgentReading
id: "2026-09-15-exciting-mccarthy-f0q3d4-reading-issues"
run_id: "2026-09-15-exciting-mccarthy-f0q3d4"
subject: "open_issues"
reference: "GitHub issues abertas (franklinbaldo/causaganha, 22 abertas)"
finding: "#1469 (unificar escrita/leitura CNJ) está com o código de produção já completo e mergeado (exporter.py, processoCnj.ts, reconcile_processos.py) exceto o que depende de #1472 (publicação real no IA, bloqueada por credenciais ausentes); as checkboxes do corpo da issue seguem desatualizadas porque edição do corpo é do dono. #1051 (segmenter: validation set independente) segue sendo a única frente de domínio real, desbloqueada e não esgotada: 27 ReviewRecords adjudicados sobre 61 documentos, meta inicial de 30-50 documentos, 27 candidatos remanescentes com exatamente uma anotação unseeded e nenhuma review."
---

# Leitura: issues abertas

Listadas as 22 issues abertas via `mcp__github__list_issues`. Duas frentes de
domínio dominam o painel: o epic Parquet/CNJ (#1468-1472) e o cluster
segmenter (#1051 e afins #1047/#1053-1057/#884/#886/#887).

Inspecionei o corpo de #1469 em detalhe e cruzei cada critério de aceite
contra o código real (`src/causaganha/consolidate/exporter.py`,
`web/src/lib/processoCnj.ts`, `scripts/reconcile_processos.py`,
`docs/planning/parquet-storage-optimization-plan.md`): todos os critérios
alcançáveis sem credenciais IA já estão implementados e testados (unificação
exporter.py/consolidate.py, ORDER BY CNJ-first, normalização de 20 dígitos,
ZSTD+ROW_GROUP_SIZE 122880, certificação de rodapé, igualdade direta
condicional em processoCnj.ts com testes de rodapé ausente/misto, ordem
física explícita em reconcile_processos.py). Só restam: (a) a igualdade
direta ficar dormente até a publicação real do acervo reordenado (#1472,
bloqueada por falta de `IA_ACCESS_KEY`/`IA_SECRET_KEY` neste ambiente — `env
| grep -i 'IA_\|ARCHIVE'` vazio, mesma situação desde 11/09), e (b) atualizar
o checklist textual da própria issue via comentário.

#1051 segue como a frente de trabalho real mais madura e desbloqueada: o
mecanismo de escalonamento (annotate_second_independent.py +
adjudicate_segmenter_review.py, subagentes Técnica 1 isolados) já produziu
27 ReviewRecords em rodadas sucessivas (11→13→...→27, PRs #1505-#1529). Meta
textual da issue: "Start around 30-50 documents". Faltam poucos incrementos
para cruzar o piso de 30.
