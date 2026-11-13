# DJEN: leitura direta dos ZIPs originais (piloto TJRO/2026)

## Objetivo

Preservar os ZIPs do DJEN exatamente como foram recebidos no Internet
Archive (IA). O site consulta índices **finos** por CNJ e recupera um membro
JSON original usando HTTP Range. Não armazena textos integrais novamente e
não depende do PB v2 da PR #1720, que permanece independente e aberta.

## O que o IA indexa e o que não indexa

A API `/metadata/{item}/files` é o inventário de arquivos preservados.
Conforme testes externos com `advancedsearch.php` e
`/services/search/v1/scrape`, CNJ `70726450920238220001` e ID
`778704990` não foram encontrados, embora o item `djen-tjro-2026`
exista. A busca geral do IA não substitui o nosso índice por CNJ.

Não assumir que a ausência na busca do IA prova ausência de publicação.
Os ZIPs foram enviados com `--no-derive`, e não há evidência de indexação
integral dos seus JSONs pelo IA.

## Contrato de dados

- Original: `https://archive.org/download/djen-tjro-2026/djen-AAAA-MM-DD-TJRO.zip`
- Índice: `https://archive.org/download/causaganha-djen-original-index/tjro_2026_<shard>.json`
- Manifesto: `https://archive.org/download/causaganha-djen-original-index/tjro_2026_manifest.json`
- Shard: primeiros dois dígitos hexadecimais de `SHA-256(numero_processo)`,
  ou seja, 256 fragmentos aproximadamente equilibrados
- Cada shard: `numero_processo -> [{item, zip, member, id, hash}]`.
- O manifesto lista checksums dos ZIPs processados e nomes dos shards publicados.
- Não contém texto integral ou novo ZIP derivado.

O número CNJ contém o ano de ajuizamento, **não o ano da publicação**.
O piloto consulta especificamente o acervo TJRO/2026; a consulta
multianual deve usar inventário de anos publicados, não o ano do CNJ.

## Indexação incremental

O workflow `index-djen-original-zips.yml` roda diariamente, restaura o
manifesto anterior e somente os shards listados nele, consulta o inventário
do IA e processa até cinco ZIPs novos/alterados. Atualizações substituem
as referências anteriores do mesmo ZIP, de maneira idempotente. Publica
primeiro os shards alterados e por último o manifesto.

O limite de cinco ZIPs é um orçamento operacional, **não** garantia de
cobertura histórica. O relatório distingue ZIPs indexados de pendentes.
A publicação dos arquivos no IA tem consistência eventual; não declarar
atualização instantaneamente atômica entre vários arquivos.

## Leitura seletiva (piloto)

Nos testes empíricos relatados para `djen-2026-11-09-TJRO.zip`, o IA
retornou HTTP 206 e Content-Range. A leitura do JSON
`TJRO-D-2026-11-09_1.json` consumiu aproximadamente 1,1 MB de bytes
comprimidos, versus aproximadamente 9,15 MB do ZIP inteiro.

O cliente `web/public/djen-zip-range.js` obtém tamanho do ZIP via
metadados do IA, busca EOCD e diretório central, lê cabeçalhos locais,
transfere apenas o membro comprimido por Range e decodifica DEFLATE no
navegador. Os limites do proxy são 2 MiB por requisição Range; o cliente
fraciona leituras maiores. O fluxo ainda depende da configuração de uma
**URL real do proxy Cloudflare** na página, para a qual o piloto permite
`?proxy=https://seu-proxy.example`. Até essa configuração existir,
a página mantém o link ao ZIP original como fallback.

O Worker `deployment/archive-cors-proxy` deve ser implantado com a
alteração desta PR. Seu contrato permanece limitado a `djen-*`,
extensões `.parquet` ou `.zip`, e para ZIP exclusivamente GET com Range
explícito de até 2 MiB. Uma resposta ZIP upstream HTTP 200 não deve
ser aceita como resposta a Range.

## Verificação

```sh
uv run python scripts/index_djen_originals.py --item djen-tjro-2026 --max-zips 2
uv run pytest tests/test_index_djen_originals.py -q
cd deployment/archive-cors-proxy && npm test
```

## Gates antes de tirar de Draft

1. CI verde, incluindo lint/Ruff, proxy e testes de indexação.
2. End-to-end com URL do proxy implantado: CNJ -> shard -> membro JSON
   via HTTP Range -> ID/hash exatos; validar CORS, bytes e navegador.
3. Medir tamanho real e dispersão dos 256 shards com dias acumulados.
4. Verificar integridade do manifesto e reprocessamento de ZIP alterado,
   bem como dados de cobertura/freshness na interface.
5. Ampliar para tribunais e anos preservados sem transformar lacunas do
   inventário em conclusão de ausência de publicações.
