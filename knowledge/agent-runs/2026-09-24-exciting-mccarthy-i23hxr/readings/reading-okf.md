---
type: AgentReading
id: "2026-09-24-exciting-mccarthy-i23hxr-reading-okf"
run_id: "2026-09-24-exciting-mccarthy-i23hxr"
subject: "okf_knowledge"
reference: "knowledge/agent-runs/2026-09-24-exciting-mccarthy-{my6ovw,khpkk2,eb5f9r}/run.md, knowledge/agent-runs/2026-09-20-exciting-mccarthy-x3954c/run.md, .claude/agent-run-scaffold.md, .claude/hourly-loop.md, scripts/segmenter_semantic_audit.py, tests/segmenter_dataset/test_segmenter_audit_scripts.py"
finding: "4 relatorios AgentRun recentes (2026-09-24, mesma janela de execucao) documentam a linhagem #1050 ate document_count=193 apos o merge de #1603/#1604 (batch26). khpkk2 (a rodada mais recente ja mesclada) deixou next_move explicito: confirmar #1604 mesclado (confirmado: origin/main HEAD=1f37845=#1604), levar em conta resposta do dono sobre a tensao #1256-vs-gatilho-agendado (nenhuma resposta nova encontrada), e selecionar o vigesimo setimo lote de #1050 reconfirmando governance_status.py ao vivo (batch27 ja em voo como PR #1605 de outra sessao -- ver reading-prs). O achado NOVO desta rodada, nao coberto por nenhum relatorio anterior: `tests/segmenter_dataset/test_segmenter_audit_scripts.py`'s unico teste de regressao sobre o corpus real (`test_real_store_has_at_most_the_one_known_collapsed_false_positive`) filtra e so afirma sobre findings do tipo `*_collapsed` -- os outros tipos que `scripts/segmenter_semantic_audit.py` sabe detectar (`long_anchor`, `dispositivo_inside_voto`, `operative_on_reasoning_or_verb`, `capitulo_merito_on_prose`, `ref_processual_mismatch`, `ref_normativa_overlap`) nunca tiveram cobertura de teste nenhuma. Rodando `uv run python scripts/segmenter_semantic_audit.py` ao vivo contra `data/segmenter` revelou 4 findings reais desses tipos nao cobertos, presentes desde 2026-09-15 (completed_at das anotacoes flagged), nunca mencionados em nenhum relatorio anterior: 3x `long_anchor` (ancoras `acordao_decisorio_inicio` de 127-202 caracteres, violando a Regra 1 de `annotation_guideline_v7.md` -- '~120 caracteres... nunca um paragrafo inteiro') e 1x `dispositivo_inside_voto` (um `dispositivo_abertura` marcado dentro de um `voto` individual de acordao, violando a nota explicita 'Acordao (second-instance) notes' do proprio guideline). Isso e exatamente a classe de defeito que a propria issue #1050 pede para resolver ('corpus audit has no unresolved known semantic defects hidden as accepted gold') e que nenhuma das ~27 rodadas de ingestao de lote jamais checou, porque cada rodada roda o script e le a saida, mas a saida sempre inclui os 7 collapsed ja conhecidos -- sem comparar contra a lista completa de tipos, um humano/agente lendo a saida corrida facilmente perde 4 findings genuinamente novos misturados aos 7 esperados."
---

# Leitura: conhecimento OKF relevante

Releu os `run.md` das ultimas rodadas na mesma janela de trabalho
(`my6ovw`, `khpkk2`, `eb5f9r`, mais `x3954c` de 2026-09-20 para o
contexto do fix de performance de `dedup.py`) para entender
continuidade antes de escolher o trabalho desta rodada. Confirmou:
`#1604` (fechamento do relatorio `khpkk2`) esta mesclado em `main`
(`origin/main` HEAD = `1f3784543e3f8aba1e733c47b84c87dd46f4388f`),
`document_count=193`, `val_ceiling=test_ceiling=29` (abaixo do piso
RFC 0012 Sec5 item4 de `>=30/>=30`).

Releu tambem `.claude/hourly-loop.md`, que documenta explicitamente
que `knowledge/agent-runs/`/`AgentRun` sao "legado historico" e que
"novas rodadas devem usar exclusivamente o runtime do Wisk" no loop
horario -- mas essa politica vive nesse arquivo separado, nao no
prompt desta sessao agendada especifica, que continua instruindo a
criacao de um `AgentRun` via `.claude/agent-run-scaffold.md` passo a
passo. `uv run wisk start`/`wisk session next` reconfirmados ao vivo
como `blocked: no-eligible-session`/`null` nesta janela (mesmo estado
de rodadas anteriores) -- nao ha fato novo que justifique reescalar
essa tensao (ja escalada por rodadas anteriores) nem que torne o Wisk
uma alternativa viavel para esta sessao agora.

O achado que efetivamente moveu esta rodada veio de rodar os proprios
scripts de auditoria do dominio, nao de reler relatorios: o teste de
regressao existente so cobre findings `*_collapsed`; os outros 4
findings reais que `segmenter_semantic_audit.py` sabe detectar nunca
tiveram teste nem allowlist documentada. Rodar o script ao vivo
revelou 4 findings genuinos, presentes desde 2026-09-15, nunca citados
em nenhum relatorio das ~27 rodadas de ingestao de lote desta
linhagem. Ver `goal_ids` para o objetivo desta rodada e
`decision_ids`/`evidence_ids` para o processo TDD que os resolveu.
