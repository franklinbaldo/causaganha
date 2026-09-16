---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-2hb3sq-evidence-red-verbatim-mismatch"
run_id: "2026-09-15-exciting-mccarthy-2hb3sq"
goal_id: "2026-09-15-exciting-mccarthy-2hb3sq-goal-scale-segmenter-reviews"
kind: "test_red"
reference: "annotate_second_independent.build_second_annotation's verbatim-fidelity check (VerbatimFidelityError)"
summary: "RED real em ambos os subagentes desta rodada, antes de qualquer ingestão: reconstructed_text != document.text. doc_b8a4a405: subagente omitiu a palavra 'ACORDAO' inteira entre a ementa e o dispositivo colegiado (4222 vs 4230 chars). doc_ec1f5133: subagente digitou '0113598-96...' e '0008695-05...' sem o espaço que o documento original tem depois do hifen ('0113598- 96...', '0008695- 05...') em 2 dos 5 numeros de precedente citados (4388 vs 4390 chars). Corrigidos manualmente por comparacao caractere-a-caractere com o texto original antes de reingestar -- GREEN confirmado (reconstructed_text == document.text) para os dois antes de qualquer chamada a annotate_second_independent.py."
---

# Evidencia: RED de fidelidade verbatim, corrigido antes da ingestao

Reproduz exatamente o padrao de erro ja documentado por f0q3d4 ("uma
palavra 'ACORDAO' omitida") -- desta vez em um subagente diferente
(haiku, nao general-purpose), confirmando que a omissao acidental de
palavras/espacos em transcricoes longas e um modo de falha sistemico do
Tecnica 1, nao um acidente isolado de uma familia de modelo especifica.

Verificacao programatica usada (nao apenas o proprio self-check do
subagente, que passou nos dois casos apesar do erro):

```
uv run python -c "
from xml.etree import ElementTree as ET
from segmenter_dataset.store import _text_element_to_labels
root = ET.fromstring(f'<text>{tagged_text.strip()}</text>')
reconstructed, labels = _text_element_to_labels(root)
assert reconstructed == original_text
"
```

Ambos os casos: corrigido via edicao pontual do arquivo tagged (reinserir a
palavra/espaco faltante na posicao exata indicada pelo primeiro ponto de
divergencia caractere-a-caractere), sem alterar nenhuma outra parte do
texto ou das tags. Reconfirmado GREEN antes de proceder a
`annotate_second_independent.py`.
