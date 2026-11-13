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
O piloto atende TJRO; demais tribunais exigem mapeamento validado.

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

A integração automática do produtor DataJud a esse feed ainda precisa
ser validada. O `indice_processos_{tribunal}.parquet` existente no
`daily_pack.py` contém, na sua versão atual, **apenas uma linha por CNJ**,
logo não prova cobertura completa de todos os graus. Não é seguro usá-lo
como se preservasse todas as identidades documentais.

### Organização e atualização no IA

Originais: `djen-{tribunal}-{ano-publicacao}/{zip-diario}.zip`.

Índices: `causaganha-AAAA-J-TR/OOOO.zip`, contendo
`NNNNNNNDD.pb` (por processo). Os CSVs anteriores não são o formato
desta PR.

O fluxo é incremental: identifica ZIPs originais novos ou alterados,
atualiza apenas partições atingidas, reenvia os ZIPs de índice alterados
e só então publica o manifesto em
`causaganha-index-control-tjro/manifest.json`. O manifesto é
controle de cobertura; não fornece atomicidade transacional no IA.

### Consulta web

O navegador deriva item, ZIP e PB diretamente dos 20 dígitos CNJ.
A leitura por HTTP Range passa pelo proxy CORS restrito, localiza o
membro no diretório central ZIP e decodifica o Protobuf. O DJEN é
recuperado do membro JSON original somente quando solicitado.
O DataJud é apresentado como ponteiro para o snapshot mais recente.

O Worker de CORS deve estar implantado e sua URL pública configurada;
a página piloto suporta `?proxy=https://ENDERECO-REAL` apenas para
smoke tests. Sem essa implantação, a consulta não é produção.

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
