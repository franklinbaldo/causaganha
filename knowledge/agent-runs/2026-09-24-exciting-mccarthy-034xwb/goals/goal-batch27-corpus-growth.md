---
type: AgentGoal
id: "2026-09-24-exciting-mccarthy-034xwb-goal-batch27-corpus-growth"
run_id: "2026-09-24-exciting-mccarthy-034xwb"
goal: "Ingerir um vigesimo setimo lote real (Technique 1, RFC 0012 Sec 8/9) de documento(s) multi-tribunal no corpus do segmentador (#1050), seguindo TDD (teste RED de crescimento do corpus antes da ingestao, GREEN depois), com verificacao de near-duplicate via SequenceMatcher contra o corpus inteiro (nao so a checagem padrao de (tribunal, id)) antes de anotar qualquer candidato, buscando aproximar document_count do piso RFC 0012 Sec 5 item 4 (val_ceiling/test_ceiling >= 30)."
rationale: "Leituras desta rodada (issues, PRs, OKF) confirmam que #1050 e o unico trabalho de dominio real e desbloqueado: as demais issues executaveis dependem de credenciais ausentes (Parquet/CNJ, proxy Cloudflare de #1482) ou estao explicitamente fora de prioridade imediata (#1093), e a fila pos-corpus do segmentador (#1051/#1053-#1057) so se torna executavel depois que #1050 cruzar o piso RFC 0012. Nao ha PR de dominio aberta para retomar (reading-prs) -- as tres rodadas anteriores de hoje ja mescladaram tudo que estava pronto (#1602/#1603/#1604), entao o proximo avanco natural e comecar um novo lote do zero, exatamente como o next_move de my6ovw/khpkk2 recomendou. document_count=193/val_ceiling=test_ceiling=29 reconfirmado ao vivo nesta rodada (check-governance-status-baseline)."
success_signal: "scripts/segmenter_governance_status.py mostra document_count>193 (idealmente >=194) apos a ingestao, com annotation_count crescendo na mesma proporcao; um teste RED especifico do lote (ex.: test_real_store_reflects_batch27_corpus_growth) falha antes da ingestao e passa depois; scripts/segmenter_semantic_audit.py nao produz achados novos alem da allowlist de 7 ja conhecida; uv run ruff check/format --check e uv run pytest -q (repo inteiro) verdes; knowledge/backlog/issue-1050.md atualizado com a narrativa do lote e last_verified_run_id apontando para esta rodada; PR aberta com o diff de dados + testes + este relatorio."
status: "achieved"
---

# Goal: vigesimo setimo lote real do corpus (#1050)

Unico item de trabalho real, desbloqueado e alinhado com a
continuidade recomendada pelas tres rodadas anteriores de hoje. Segue
o processo Technique 1 ja estabelecido em 26 lotes anteriores
(`data/segmenter_splits/technique1_annotation_prompt.md`,
`scripts/ingest_djen_sample_technique1_batch.py`), com atencao
reforcada a near-duplicate (licao explicita do lote 26, que descartou
dois candidatos por serem quase-duplicatas com ratio >=0.96 contra
documentos ja no store).
