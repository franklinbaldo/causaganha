---
type: StjAcordao
id: stj-example
classe: "REsp"
relator: null
tema: null
tese: null
ementa: null
data_decisao: null
data_publicacao: null
---

# Acórdão STJ

Resumo contratual de acórdão do STJ associado ao processo.
Exceto `id`/`classe`, os campos são `null` de propósito: um acórdão pode ser
localizado sem que todo metadado já esteja disponível
(`causaganha.processos.models.StjAcordao`) — o exemplo declara essa
nulabilidade real em vez de fingir que todo campo está sempre presente.
