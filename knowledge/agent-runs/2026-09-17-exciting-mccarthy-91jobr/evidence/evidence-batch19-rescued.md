---
type: AgentEvidence
id: "2026-09-17-exciting-mccarthy-91jobr-evidence-batch19-rescued"
run_id: "2026-09-17-exciting-mccarthy-91jobr"
goal_id: "2026-09-17-exciting-mccarthy-91jobr-goal-rescue-batch19"
kind: "diff"
reference: "git apply /tmp/batch19-data.patch; docs/planning/evidence/segmenter-djen-sample-batch19-*; scripts/segmenter_governance_status.py"
summary: "6 documentos/anotacoes reais da PR stale #1576 (TJMT/74430633, TJRR/568209392, TJRR/568328945, TRF3/42490599, TRF5/349186353, TRF5/463264301) resgatados e reaplicados sobre o main atual (pos-#1577). document_count 149->155, annotation_count 202->208 (confirmado ao vivo). Artefatos de auditoria renomeados de batch18 para batch19 para eliminar colisao de nome com o que o Wisk ja commitou."
---

# Evidencia: resgate do lote 18 stale (#1576) como lote 19

`git merge-tree $(git merge-base origin/main
origin/claude/exciting-mccarthy-726qh5) origin/main
origin/claude/exciting-mccarthy-726qh5` confirmou que os 6 pares
`data/segmenter/documents/*.xml` +
`data/segmenter/annotations/*/*.xml` de #1576 sao adicoes puras sem
overlap de `document_id` com o que #1577 (Wisk) ja mesclou -- os unicos
4 marcadores de conflito estavam em dois arquivos de evidencia de
auditoria com nome fixo por numero de lote
(`segmenter-djen-sample-batch18-{candidates,overrides}.json`), pura
colisao de nomenclatura entre as duas PRs concorrentes.

Fluxo desta rodada:

1. `git diff <merge-base>..origin/claude/exciting-mccarthy-726qh5 --
   data/segmenter/documents data/segmenter/annotations` gerado como
   patch isolado (exclui os arquivos de evidencia colidentes).
2. `git apply --check` confirmou aplicacao limpa sobre o `main` atual;
   `git apply` aplicou com sucesso (77 avisos de whitespace no `<text>`
   verbatim das anotacoes, esperado -- o conteudo verbatim preserva
   espacos/NBSP genuinos da fonte).
3. Os dois arquivos de evidencia colidentes foram recuperados via `git
   show origin/claude/exciting-mccarthy-726qh5:<path>` e regravados com
   o sufixo `-batch19-` (`segmenter-djen-sample-batch19-candidates.json`,
   `-overrides.json`, `-fix-missing-spaces.py`); nenhuma referencia
   interna a "batch18" sobrevive nesses arquivos (`grep -n batch18`
   vazio nos 3).
4. `scripts/segmenter_governance_status.py` (ao vivo, apos a aplicacao):
   `document_count=155` (149->155), `annotation_count=208` (202->208),
   `val_ceiling=test_ceiling=23` (22->23, lote train-only eleva o teto
   porque o piso e limitado pelo tamanho total do corpus).
5. `git status --short data/segmenter` confirma exatamente 6 novos
   `documents/*.xml` e 6 novos `annotations/<id>/`, sem write no-op
   silencioso.
6. `uv run python -m scripts.segmenter_semantic_audit --store
   data/segmenter`: nenhum achado novo para os 6 IDs de documento deste
   lote (`doc_051dcfad4315379b78b3cc0e93317432`,
   `doc_191df3a5f58bedd555b15db5ce51a9f9`,
   `doc_7d7eb03476445ffbb5af6f3b9fe68898`,
   `doc_c13699ae06d1a843552e460ec9da6dd6`,
   `doc_cef4677db81a15cd7104a72b26ac3131`,
   `doc_e2db8e8f01de2dc529b6d5802828b663`) -- todos os achados
   reportados pertencem a documentos pre-existentes de lotes
   anteriores.
7. `uv run ruff check .` e `uv run ruff format --check .` limpos no
   repositorio inteiro.
