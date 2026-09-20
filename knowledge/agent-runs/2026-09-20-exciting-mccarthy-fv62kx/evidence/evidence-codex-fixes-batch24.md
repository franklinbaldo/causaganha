---
type: AgentEvidence
id: "2026-09-20-exciting-mccarthy-fv62kx-evidence-codex-fixes-batch24"
run_id: "2026-09-20-exciting-mccarthy-fv62kx"
goal_id: "2026-09-20-exciting-mccarthy-fv62kx-goal-djen-sample-batch24"
kind: "review"
reference: "PR #1590 review by chatgpt-codex-connector[bot] (7 inline comments, commit 007cf18); fix commit on claude/exciting-mccarthy-fv62kx"
summary: "Codex flagged 7 inline findings on PR #1590. Live verification confirmed 5 as real defects (TJBA/574460088 near-duplicate already rejected in batch17, SequenceMatcher.ratio=0.9801 reconfirmed; TJGO/543517919 missing capitulo_merito and fundamentacao_legal for art. 508 CPC; TJPI/22443826 missing an entire cabecalho pair vs. a same-format sibling document; TJMA/42725100 missing fundamentacao_legal for the Tema 03 IRDR citation in its own reasoning). TJBA/574460088 was reverted from the store entirely (document + annotation removed); TJGO/TJES/TJPI/TJMA were re-ingested with corrected tags, document_id unchanged (same source text), only annotation content updated. One sub-finding (TJMA's footnote precedent citations from a different court's quoted decision) was verified and kept as-is, matching the guideline's own ref_processual exclusion principle for other cases' material."
---

# Evidência: correções pós-revisão Codex (batch24)

- **Reversão**: `data/segmenter/documents/doc_5bd67f4cebf27315a9ba792b4f0ab89d.xml` e
  sua anotação removidos (TJBA/574460088, near-duplicate 0.9801 de
  TJBA/574460085 já no store desde o lote 17).
- **Re-ingestão com correção** (mesmo `document_id`, nova anotação):
  - `doc_7e0a3ee96c66a6f31fcb150c4c90566b` (TJGO/543517919): +2 labels
    (`capitulo_merito_inicio`, `fundamentacao_legal` extra).
  - `doc_4713da3e1a98c0c56734958f5af021b0` (TJES/577051509): +1 label
    (`fundamentacao_legal` extra).
  - `doc_68ff6f009ff1633894cad78fea63b6be` (TJPI/22443826): +2 labels
    (`cabecalho_inicio`, `cabecalho_fim`).
  - `doc_7ce5036bcb2136ae11da820aeda6de6d` (TJMA/42725100): +1 label
    (`fundamentacao_legal` extra, citação do Tema 03 IRDR).
- Cada correção verificada independentemente antes de reingerir:
  reconstrução via `segmenter_dataset.store._text_element_to_labels`
  idêntica ao texto-fonte original armazenado (nenhuma alteração de
  conteúdo, só inserção de tags).
- `scripts/segmenter_semantic_audit.py` reconfirmado sem achados novos
  após as correções (mesmos 11 achados pré-existentes).
