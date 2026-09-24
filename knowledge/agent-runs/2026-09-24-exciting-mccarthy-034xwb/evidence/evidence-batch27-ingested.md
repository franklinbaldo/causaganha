---
type: AgentEvidence
id: "2026-09-24-exciting-mccarthy-034xwb-evidence-batch27-ingested"
run_id: "2026-09-24-exciting-mccarthy-034xwb"
goal_id: "2026-09-24-exciting-mccarthy-034xwb-goal-batch27-corpus-growth"
kind: "diff+runtime"
reference: "commit 51e30b3 on claude/exciting-mccarthy-034xwb"
summary: "Vigesimo setimo lote real (Technique 1) ingerido: TJES/577054715 (Sentenca, formato projeto-de-sentenca + homologacao, 3824 chars) e TJGO/543518267 (Sentenca, embargos de declaracao, 4195 chars apos html.unescape() -- mesmo defeito recorrente de entidades HTML cruas ja visto nos lotes 12/16/18/22). document_count 193->195, annotation_count 246->248 (scripts/segmenter_governance_status.py, reconfirmado ao vivo por esta sessao apos o commit, nao apenas pelo autorrelato). Ambos candidatos confirmados limpos via SequenceMatcher.ratio() ao vivo contra os 193 documentos ja no store (max 0.114 e 0.054); TJBA/574460088 e TJMA/42728925 reconfirmados como as mesmas quase-duplicatas ja rejeitadas no lote 26 (ratio 0.980/0.968) -- nao reselecionados."
---

# Evidencia: lote 27 ingerido no corpus real (#1050)

## TDD

RED confirmado antes da ingestao: `assert 193 >= 195` falhou como
esperado. GREEN apos: `tests/segmenter_dataset/test_segmenter_governance_status.py::test_real_store_reflects_batch27_corpus_growth`
-- `1 passed in 0.05s`.

## Verificacao independente (nao apenas autorrelato)

Esta sessao reverificou, de forma independente do subagente que
executou a ingestao:

- **Fidelidade verbatim**: para os dois documentos, removi todas as
  tags XML do texto anotado (`docs/planning/evidence/segmenter-djen-sample-batch27-tagged/{577054715,543518267}.txt`)
  via regex e comparei byte-a-byte contra `texto_limpo` do candidato
  correspondente em `docs/planning/evidence/segmenter-djen-sample-batch27-candidates.json`
  -- `EXACT MATCH` para ambos.
- **Governanca**: `scripts/segmenter_governance_status.py` rodado ao
  vivo por esta sessao (nao so citado do relatorio do subagente):
  `document_count=195, annotation_count=248, val_ceiling=test_ceiling=29,
  meets_rfc_0012_split_floor=false` -- ainda falta ~1 lote deste
  tamanho para cruzar o piso RFC 0012 Sec 5 item 4 (`>=30/>=30`).
- **Auditoria semantica**: `scripts/segmenter_semantic_audit.py`
  rodado ao vivo -- exatamente os mesmos 7 `doc_id`s `_collapsed`/
  outros ja conhecidos da allowlist de
  `tests/segmenter_dataset/test_segmenter_audit_scripts.py`; nenhum
  dos dois novos documentos aparece em qualquer achado.
- **Estilo/testes**: `uv run ruff check` -> "All checks passed!";
  `uv run ruff format --check` -> "454 files already formatted";
  `uv run pytest -q tests/segmenter_dataset` -> 251 testes, 100%
  verde (0 falhas).

## Incerteza genuina registrada, nao escondida

O subagente que executou o lote nao tinha acesso a ferramenta
Task/Agent neste ambiente para spawnar um subagente por documento,
como todos os 26 lotes anteriores fizeram -- anotou os dois
documentos diretamente, seguindo o mesmo metodo do
`technique1_annotation_prompt.md` (enumerar categorias antes de
tagear, inserir tags por offset, nunca retigitar texto), e a
fidelidade verbatim foi reverificada de forma independente por esta
sessao (acima), nao so pelo proprio subagente. Registrado em
`knowledge/backlog/issue-1050.md` para uma rodada futura com acesso a
Task retomar o processo padrao. A escolha editorial de qual
`dispositivo_abertura`/`resultado` e o "operativo" no formato
projeto+homologacao do TJES (tageado na ruling do juiz leigo, nao na
homologacao do juiz togado) foi resolvida por analogia a um
precedente ja existente no corpus (TJMT/74428001) -- inspecionada
diretamente por esta sessao no texto tageado e considerada razoavel e
consistente com a Regra 2 do guideline v7 (um unico
`dispositivo_abertura` operativo por decisao), mas nao coberta por
uma regra explicita do guideline para esse caso especifico; uma
revisao futura (Codex ou humana) pode legitimamente discordar, mesma
classe de achado editorial ja vista nos lotes 23-25.
