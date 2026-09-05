---
type: JurisDecisao
id: juris-example
n_documentos: null
tipos: [acordao]
data_julgamento: null
orgao: null
relator: null
classe: null
url: null
---

# Decisão JURIS

Resumo contratual da decisão localizada no TJRO JURIS para o processo.
Exceto `id`/`tipos`, os campos são `null` de propósito: uma decisão pode ser
localizada sem que todo metadado já esteja disponível
(`causaganha.processos.models.JurisDecisao`) — o exemplo declara essa
nulabilidade real em vez de fingir que todo campo está sempre presente.
`relator` também é `null` aqui: `service._juris_sql` lê a coluna `relator` do
parquet JURIS como qualquer outra, sem garantia de preenchimento.
