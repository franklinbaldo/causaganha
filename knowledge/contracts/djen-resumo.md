---
type: DjenResumo
id: djen-example
primeira_publicacao: null
ultima_publicacao: null
n_publicacoes: null
tribunais: [TJRO]
---

# Resumo DJEN

Resumo contratual da presença de publicações DJEN no dossiê de um processo.
Exceto `id`/`tribunais`, os campos são `null` de propósito: `service.buscar_processo`
preenche o que a fonte tiver e deixa o resto `None` (RFC 0014 M2,
`causaganha.processos.models.DjenResumo`) — o exemplo declara essa nulabilidade
real em vez de fingir que todo campo está sempre presente.
