---
type: AgentGoal
id: "2026-09-15-exciting-mccarthy-6kxfkh-goal-scale-segmenter-reviews"
run_id: "2026-09-15-exciting-mccarthy-6kxfkh"
goal: "Escalar ReviewRecords reais de #1051/RFC 0012 sobre o pool de documentos com exatamente uma anotacao unseeded, continuando o next_move de pxa8pi (review_count=21 no inicio desta rodada), e endurecer o prompt canonico Tecnica 1 contra o modo de falha de sub-anotacao severa que pxa8pi documentou."
rationale: "RFC 0012 Sec 5.4 exige >=30 val + >=30 test ReviewRecords adjudicados; review_count=21/evaluation_eligible_count=21 sobre 61 documentos no inicio da rodada, confirmado ao vivo. Cluster Parquet/CNJ (#1468-1472) e o proxy CORS do archive.org (#1482) seguem esgotados no que nao depende de credenciais IA/Cloudflare ausentes deste ambiente. #1051 continua sendo a unica frente de dominio real, desbloqueada e nao esgotada -- inventario ao vivo confirmou 23 documentos com exatamente uma anotacao unseeded e nenhuma review (pool de pxa8pi, 25, menos os 2 ja tocados). pxa8pi tambem registrou um achado de processo: o prompt canonico ainda produz falhas de sub-anotacao severa (1 tag) mesmo com o checkpoint de auto-verificacao existente, e sugeriu embutir um limiar minimo explicito de contagem de tags no proprio prompt em vez de invoca-lo manualmente a cada vez que uma rodada percebe a falha."
success_signal: "uv run python scripts/segmenter_governance_status.py mostra review_count e evaluation_eligible_count subindo de 21 para >=23 ao final da rodada, com pelo menos 2 novos ReviewRecords reais persistidos em data/segmenter/reviews/, cada um resolvendo disagreements reais (nao uma preferencia mecanica) entre a anotacao historica e uma segunda anotacao genuinamente independente (subagente isolado, family distinta, nunca exposto a anotacao existente), ingerida via scripts/annotate_second_independent.py com verbatim-fidelity confirmada programaticamente. store.write_review aceita ambas sem NonIndependentReviewError. data/segmenter_splits/technique1_annotation_prompt.md ganha um limiar explicito de contagem minima de tags. uv run pytest -q e ruff check/format ficam verdes."
status: "achieved"
---

# Goal: escalar ReviewRecords do segmentador (rodada 6kxfkh)

Antes de escalar, endureci o prompt canonico Tecnica 1
(`data/segmenter_splits/technique1_annotation_prompt.md`) com um piso
explicito na etapa 5 de auto-verificacao: "menos de 8 tags para um
documento >3000 chars e quase certamente errado, refaca" -- exatamente a
lacuna que pxa8pi identificou (o checkpoint existente pede para contar
categorias esperadas, mas nao tem um piso numerico absoluto, e um rascunho
de 1 tag ja passou por ele sem ser pego).

Dois documentos-alvo escolhidos entre os 23 candidatos com exatamente uma
anotacao unseeded e nenhuma review (os 2 menores): `doc_888fe4545b72af4a84e0baa6a766dab4`
(4269 chars, sentenca de Juizado Especial) e `doc_3cffd7961e9fc910f6ae628f5aaa6c40`
(3605 chars, acordao TJRO formato "capa+ementa-estruturada"). Dois
subagentes Tecnica 1 isolados (general-purpose/sonnet e general-purpose/haiku,
famílias distintas da anotacao existente em cada doc) produziram a segunda
anotacao independente de cada documento usando o prompt ja endurecido,
sem visibilidade da anotacao existente. Ambos produziram anotacoes
completas (15 e 13 tags brutos) na primeira tentativa -- nenhum precisou de
redirecionamento, ao contrario das duas rodadas anteriores que tocaram este
mesmo prompt.

Adjudicacao de ambos os pares resolveu disagreements reais (ver
evidence-review-doc-888fe e evidence-review-doc-3cffd para o detalhe
categoria-a-categoria), incluindo dois achados de guideline: (1) a
historica de doc_888fe usava um wrapper `custas` que o proprio exemplo do
guideline v7 (linha 35) trata como `fundamentacao_legal`, nao como par
separado; (2) a historica de doc_3cffd tagueava `ementa_fim` no meio do
documento, violando a instrucao explicita do guideline v7 linha 46 de
deixar `ementa_fim` sem par neste formato TJRO especifico.

Resultado: review_count 21 -> 23, evaluation_eligible_count 21 -> 23.
`uv run pytest tests/segmenter_dataset -q`: 377/377 verdes apos uma
correcao de allowlist em `test_segmenter_audit_scripts.py` (ver
evidence-audit-allowlist-fix) -- o heuristico de auditoria semantica
sinalizou `fundamentacao_legal_collapsed` em doc_3cffd por um motivo
estrutural correto e ja documentado (citacoes `ref_normativa`, excluidas
do espaco trainable por decisao do RFC 0012 Sec 5, nao contam para o
heuristico que so olha "art." no texto bruto).
