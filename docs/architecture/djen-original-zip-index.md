# DJEN: leitura direta dos ZIPs originais (piloto TJRO/2026)

## Objetivo

Preservar os ZIPs do DJEN tal como recebidos no Internet Archive (IA).
O site consulta um índice **fino** por número CNJ e, a partir dele, abre o
ZIP/membro JSON que contém a comunicação. Nenhuma conversão permanente para
Protobuf ou cópia integral do texto em Parquet é necessária neste fluxo.

A PR #1720 continua independente; não modifica nem fecha essa PR.

## Fonte de dados e publicação

* Arquivo original: `https://archive.org/download/djen-tjro-2026/djen-AAAA-MM-DD-TJRO.zip`.
* Índice publicado (novo item): `https://archive.org/download/causaganha-djen-original-index/tjro_2026.json`.
* Interface: `web/public/djen-originais.html?cnj=70039901420268220022`.
* Campos do índice: `numero_processo -> [{item, zip, member, id, hash}]`.
* O índice contém **localizações**, não o texto integral da publicação.
* Cada arquivo ZIP é identificado pelo checksum divulgado nos metadados do IA.
  Quando alterado, as entradas desse ZIP são substituídas, não duplicadas.

## Atualização

O workflow `index-djen-original-zips.yml` roda diariamente, consulta o
inventário de `djen-tjro-2026`, restaura a última versão publicada do índice,
lê até cinco ZIPs pendentes por execução e publica o resultado no IA.
Também aceita execução manual com um item `djen-{tribunal}-{ano}`.

O limite de cinco ZIPs é deliberado para controle de custo, mas significa
que o backfill histórico pode durar muitas execuções. A atualização diária
**não implica** índice histórico completo. O nome do item remoto e a rota da
interface estão limitados ao TJRO/2026 nesta primeira fatia. Expandir
para os demais tribunais requer configuração do roteamento CNJ e agendamento.

O código não interfere no `sync-manifest.parquet` nem no
`indice_processual.parquet` já publicados; eles continuam com suas
responsabilidades e contratos atuais.

## Execução local

```sh
uv run python scripts/index_djen_originals.py --item djen-tjro-2026 --max-zips 2
uv run pytest tests/test_index_djen_originals.py -q
```

Para operação incremental, restaure o índice remoto anterior em
`web/public/indexes/djen-raw/tjro_2026.json` antes de executar o script,
como o workflow faz.

## Leitura pelo navegador e limitações

O leitor busca o índice publicado no IA e identifica os ZIPs/membros. Tenta
ler o JSON interno via endpoint de ZIP do Archive; se CORS ou a extração
HTTP individual falharem, mostra uma mensagem e oferece o link canônico
para o ZIP original. **Não existe prova E2E publicada de que a extração
individual funciona em todos os navegadores**: validar essa capacidade
no ambiente real é um gate antes de substituir os shards atuais.

Não transformar um 404 de índice ou um CNJ não encontrado em prova de
ausência de publicação. Não alterar a preservação dos ZIPs originais.

## Próximos gates

1. CI verde (indexação, idempotência, limites de recursos e UI).
2. Smoke test público: CNJ -> índice IA -> membro JSON -> ID/hash correto,
   no navegador, inclusive CORS e limites de transferência.
3. Cobertura e freshness expostos na UI com total de ZIPs pendentes.
4. Particionamento do índice para evitar downloads excessivos por consulta.
5. Ampliação para os tribunais/anos presentes no inventário verificável,
   sem confundir lacunas do acervo com ausência de publicações.
