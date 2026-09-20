---
type: AgentCheck
id: "2026-09-20-exciting-mccarthy-fv62kx-check-verbatim-fidelity-batch24"
run_id: "2026-09-20-exciting-mccarthy-fv62kx"
command: "Script Python independente usando segmenter_dataset.store._text_element_to_labels (uv run) para reconstruir o texto de cada um dos 6 documentos tagueados e comparar byte-a-byte contra o texto-fonte (texto_limpo) de candidates.json, sem confiar no autorrelato de cada subagente."
result: "passed"
evidence_id: "2026-09-20-exciting-mccarthy-fv62kx-evidence-batch24-ingested"
summary: "6/6 verbatim_match=True na primeira tentativa; nenhum defeito de transcricao (NBSP, & nao escapado, HTML residual) encontrado. resultado confirmado presente e como irmao de inicio/fim (nao filho) em todos os 6, evitando a classe de risco 17."
---

# Check: fidelidade verbatim independente (batch24)

Rodado antes de qualquer ingestão real. Saída por documento
(`doc_id / tribunal / verbatim_match / n_labels / len_diff`):

```
22443826 TJPI verbatim_match=True n_labels=6  len_diff=0
42725100 TJMA verbatim_match=True n_labels=14 len_diff=0
543517919 TJGO verbatim_match=True n_labels=15 len_diff=0
574460088 TJBA verbatim_match=True n_labels=15 len_diff=0
577051509 TJES verbatim_match=True n_labels=22 len_diff=0
578906897 TJPB verbatim_match=True n_labels=22 len_diff=0
```

Todos batem byte-a-byte com o `texto_limpo` de origem. Verificação
adicional (grep manual) confirmou `resultado` presente em todos os 6 e
posicionado como irmão de `<inicio>`/`<fim>` em cada par (não como
filho literal), a instrução explícita dada aos subagentes para evitar
reintroduzir a classe de risco 17 (corrigida em código pela PR
concorrente #1588, ainda não mesclada no início desta rodada).
