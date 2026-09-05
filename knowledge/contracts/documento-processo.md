---
type: DocumentoProcesso
fonte: juris
id_documento: doc-example
processo_nr: "00000000000000000000"
tipo: null
data: null
url: null
resumo: null
---

# Documento do processo

Documento JURIS/STJ projetado no dossiê do processo.
Exceto `fonte`/`id_documento`/`processo_nr`, os campos são `null` de propósito
(`causaganha.processos.models.DocumentoProcesso` tipa cada um como
`str | None`) — o exemplo declara essa nulabilidade real em vez de fingir
que todo campo está sempre presente.
