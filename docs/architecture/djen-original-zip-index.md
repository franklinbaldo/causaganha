# Índice federado CausaGanha em Protobuf (.pb)

## Decisão implementada na PR #1721

O índice de cada processo é um **Protobuf de ponteiros**, não uma cópia do
acervo. Os ZIPs originais do DJEN preservados no Internet Archive permanecem
inalterados. Os documentos originais do DataJud também não são reserializados
nesse índice.

### Endereço derivado do CNJ

CNJ: `70726450920238220001` (`7072645-09.2023.8.22.0001`)

- Item IA: `causaganha-2023-8-22`.
- ZIP por unidade de origem: `0001.zip`.
- Membro por processo: `707264509.pb`.

A repetição dos outros 11 dígitos do CNJ no nome/payload é desnecessária:
ano, justiça e tribunal estão no item IA; unidade de origem no ZIP.

### Roteamento pelo CNJ do próprio processo

Cada processo é indexado no item do **seu** segmento J.TR, qualquer que seja
o caderno que o publicou. O DJEN de um tribunal carrega processos de outros
(cartas precatórias, intimações cruzadas): o CNJ `0000186-04.2015.5.14.0092`
(TRT14) tem 17 comunicações no caderno do TJRO e fica em
`causaganha-2015-5-14/0092.zip`. Cada ponteiro de publicação registra
`tribunal_fonte` (campo 5), e a página monta o ZIP original desse caderno.
Reprocessar o dia de um caderno substitui apenas os ponteiros
`(data, tribunal_fonte)` daquele caderno. Ponteiros anteriores ao campo 5
vieram todos do TJRO.

Localmente a partição chama-se `{ano}_{J}_{TR}_{origem}.zip`; nomes antigos
(`{ano}_{origem}.zip`, todos 8.22) são migrados ao ler o manifesto e
apontam para os mesmos caminhos no IA. Uma partição ausente localmente é
sempre buscada no IA, mesmo que o manifesto deste tribunal não a conheça,
porque cadernos de outros tribunais também escrevem nela.

### Contrato Protobuf

O contrato está em `src/causaganha/consolidate/process_pointer.proto`.
O codec Python está em `process_pointer_pb.py`; o leitor leve do navegador
em `web/public/process-pointer-pb.js`.

O `IndiceProcesso` versão 1 tem:

- `publicacoes`: todas as referências DJEN, com data, nome do membro JSON,
  ID numérico e hash oficial;
- `datajud`: somente o ponteiro mais recente para cada identidade documental
  `(tribunal, grau, documento_id)`, com `item_ia`, ZIP, membro e timestamp.

A presença de um CNJ **não** implica um único documento DataJud:
G1/G2 e tribunais diferentes permanecem separados. Nenhum texto,
movimentação ou dado da capa é copiado para o PB.

A atualização diária de ZIP original DJEN substitui somente os ponteiros
da data correspondente. A atualização DataJud faz upsert por identidade,
com comparação de timestamp UTC e erro para conflitos com a mesma data.

### Fonte dos ponteiros DataJud

O indexador aceita `--datajud-locators /caminho/ponteiros.jsonl`.
Cada linha precisa informar explicitamente `numero_processo`,
`tribunal`, `grau`, `documento_id`, `item_ia`, `arquivo_zip`,
`membro` e `atualizado_em` (ISO com timezone). Não inventamos
localizações do DataJud a partir de nomes presumidos.

O `datajud.daily_pack.export_daily_locators` extrai identidades e
localizações dos próprios membros ZIP efetivamente publicados pelo CDC.
O `cdc.py` publica esse sidecar JSONL no item `datajud-{tribunal}`.
O workflow diário da PR #1721 usa `--datajud-from-ia` e consome apenas
sidecars ainda não registrados no manifesto, com checksum. Correções de
um sidecar já processado exigem rebuild explícito: o processo falha de
forma visível em vez de manter referências antigas silenciosamente.

O `indice_processos_{tribunal}.parquet` histórico contém apenas uma linha
por CNJ; ele **não** comprova cobertura de todos os graus. O sidecar
novo reflete somente os membros realmente presentes nos ZIPs DataJud,
sem inventar registros ausentes. A ampliação da cobertura multigrau do
empacotador DataJud continua sendo um trabalho independente.

### Organização e atualização no IA

Originais: `djen-{tribunal}-{ano-publicacao}/{zip-diario}.zip`.

Índices: `causaganha-AAAA-J-TR/OOOO.zip`, contendo
`NNNNNNNDD.pb` (por processo). Os CSVs anteriores não são o formato
desta PR.

O fluxo é incremental: identifica ZIPs originais novos ou alterados,
atualiza apenas partições atingidas, reenvia os ZIPs de índice alterados
e só então publica o manifesto em
`causaganha-index-control-tjro/manifest.json`. O manifesto é
controle de cobertura; a versão 4 sinaliza a incompatibilidade com os ZIPs CSV anteriores e não fornece atomicidade transacional no IA.

### Consulta web

O navegador deriva item, ZIP e PB diretamente dos 20 dígitos CNJ.
A leitura por HTTP Range passa pelo proxy CORS restrito, localiza o
membro no diretório central ZIP e decodifica o Protobuf. O DJEN é
recuperado do membro JSON original somente quando solicitado.
O DataJud é apresentado como ponteiro para o snapshot mais recente.

O proxy é o `djen-proxy` (Cloud Run, `deployment/djen_proxy.go`), o mesmo
do leitor principal. Desde a revisão `djen-proxy-00004-lck` ele libera
`.zip` por HTTP Range nos itens `djen-*`, `datajud-*` e `causaganha-*`.
A página usa esse proxy por padrão; `?proxy=` só serve para smoke tests.

O leitor descobre o tamanho do ZIP com um Range de sufixo
(`bytes=-65557`), que devolve a cauda e o tamanho total no
`Content-Range`; não há chamada a `/metadata`. O documento DataJud
também é lido do membro original (`.json.gz`) e conferido contra CNJ e grau.

### Medição de ponta a ponta (2026-11-15)

Índice local construído com `djen-tjro-2026` (2 ZIPs) e os localizadores
de `datajud-tjro/tjro_2026-11-14.zip` (49.355 documentos); originais lidos
do Internet Archive real. CNJ `0028980-94.2007.8.22.0010` no Chromium:

| Etapa | Requisições | Bytes |
|---|---|---|
| CNJ → `.pb` | 4 | 2,2 KB |
| Publicação DJEN original | 5 | 1,36 MB |
| Documento DataJud original | 7 | 3,8 MB |

O custo do DataJud é dominado pelo diretório central do ZIP diário
(3,6 MB para 49 mil membros). Guardar o offset do cabeçalho local no
localizador reduziria a leitura a cerca de 3 KB; fica como melhoria.

### Gates

1. CI verde de Python, lint, proxy e browser.
2. Teste real: CNJ -> PB -> DJEN original por HTTP Range; confirmar
   ID/hash do registro sem baixar o ZIP completo.
3. Teste integrado com produtor DataJud real, incluindo G1 e G2,
   versões novas/antigas e falha de fonte.
4. Benchmark de número de membros, overhead do diretório central,
   bytes por consulta e tamanho dos ZIPs de índices.
5. Verificação de checksums e versões publicadas no IA antes de
   habilitar o site para todos os usuários.

A PR #1720 é independente e não é necessária para decodificar este índice.
