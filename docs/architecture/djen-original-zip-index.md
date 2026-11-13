# DJEN original no IA + índices ZIP/CSV por CNJ

## Decisão

A PR #1721 **não converte o acervo DJEN para Protobuf ou Parquet**.
Os ZIPs do CNJ permanecem intocados em `djen-{tribunal}-{ano}`, organizados
pela data de disponibilização. O site consulta um **índice derivado**:
um ZIP por `ANO_DE_AJUIZAMENTO_UNIDADE_DE_ORIGEM`, com um CSV por CNJ.

Exemplo de índice em `causaganha-2023-8-22`:

```text
2023_0001.zip
  70726450920238220001.csv
```

Conteúdo de um CSV:

```csv
data,membro,id,hash
2026-11-09,TJRO-D-2026-11-09_1.json,778704990,JKOdGxm7gYmLtXh1T7mM5lZy5DBkl2
```

Cada registro permite derivar o original:

- Item: `djen-tjro-{ano(data)}`.
- ZIP: `djen-{data}-TJRO.zip`.
- Membro interno: coluna `membro`.
- Registro: campos `id` e `hash` usados para conferir a identidade.

O ano de ajuizamento e o código de origem são derivados dos dígitos CNJ;
**não** determinam a data de publicação. Também não indicam, sozinhos,
trânsito em julgado ou encerramento do processo.

## O que o Internet Archive faz

O serviço hospeda os ZIPs originais e derivados. A API
`/metadata/{item}/files` permite inventariar o acervo. A busca geral
não indexa automaticamente números CNJ dentro dos JSONs dos ZIPs. Em
testes relatados para o item `djen-tjro-2026`, `advancedsearch` e
`/services/search/v1/scrape` retornaram zero resultados para um CNJ e
um ID reais presentes no ZIP.

A função de visualização de membros ZIP no IA é útil, mas pode variar
conforme o processamento do item. Para não depender de uma extração
automática, a leitura do site usa o diretório central ZIP via HTTP Range
pelo proxy CORS restrito. **A implantação e o smoke test público ainda
são gates da PR.** Não considerar `--no-derive` promessa de extração
permanente de membros internos no IA.

## Atualização diária

O workflow `index-djen-original-zips.yml` consulta a lista de arquivos
ZIP originais. Por execução lê no máximo cinco ZIPs novos ou com hash
de arquivo alterado. O controle `manifest.json` guarda os ZIPs já
processados e as partições existentes. Publicações novas acrescentam
linhas aos CSVs; se um ZIP de origem é republicado, suas linhas daquele
dia são substituídas, sem remover publicações de outras datas.

Cada partição alterada é regravada e publicada no IA. O manifesto é
publicado **por último**, para evitar anunciar um índice antes de seus
arquivos. Essa ordem não oferece transação atômica no IA; quedas durante
o upload exigem reconciliação na rodada seguinte.

É uma arquitetura incremental, não uma promessa de atualização
instantânea: indexação atrasada e falhas permanecem explicitamente
possíveis. Itens antigos não são declarados encerrados; uma publicação
nova em processo antigo atualiza sua partição.

A recomendação conservadora inicial é ficar abaixo de mil arquivos
por item. O código valida esse orçamento e não cria automaticamente
itens adicionais. Uma estratégia de particionamento de itens será
necessária se a coleção crescer além do orçamento.

## Navegador

Com CNJ `70726450920238220001`:

1. Deriva `causaganha-2023-8-22/2023_0001.zip`.
2. Lê `70726450920238220001.csv` por Range.
3. Deriva os endereços dos ZIPs originais a partir das datas.
4. Busca somente o membro JSON pertinente, usando seu diretório
   central e DEFLATE, e identifica o registro pelo par ID/hash.

O navegador não baixa o ZIP integral quando os endpoints respeitam
Range. O CSV não é equivalente ao texto da publicação; a referência é
verificada contra o original na leitura.

Para testar a página `web/public/djen-originais.html`, configure
`?proxy=https://ENDERECO-REAL-DO-WORKER`. O proxy atual deve ser
implantado com as alterações de suporte ao item
`causaganha-index-*` e aos ZIPs DJEN. Sem URL pública e teste E2E,
a consulta não está pronta para o público.

## Validações antes de merge

- Ruff, testes Python e Vitest do proxy verdes.
- Testes reais da leitura HTTP Range em navegador, com medição de bytes,
  suporte a DEFLATE e compatibilidade CORS.
- Verificar idempotência, reprocessamento de ZIP alterado e caso
  CNJ com várias comunicações em dias diferentes.
- Conferir publicação do índice e restauração do manifesto no IA.
- Medir tamanho dos ZIPs de índices e custo de reenvio.
- Tratar ausência de índice separadamente de ausência de comunicação.

A PR #1720 permanece aberta e independente: nenhum formato PB
é requisito para o índice por CNJ.


## Nomeação dos itens de índice (decisão)

A chave é `AAAA.J.TR/OOOO.zip` na notação CNJ, mas o identificador físico
adotado no IA é `causaganha-AAAA-J-TR`, com `OOOO.zip` como arquivo.
Exemplo: `causaganha-2026-8-22/0001.zip`. Os CSVs internos continuam
`{CNJ}.csv`. O prefixo evita colisões de identificadores globais no IA,
e hífens seguem a nomenclatura recomendada. Os originais do DJEN ficam nos
itens `djen-{tribunal}-{ano-publicacao}` sem qualquer alteração.

O piloto mapeia TJRO a `8-22`. Outros tribunais exigem roteamento CNJ
validado antes de serem habilitados. O manifesto de fontes é compartilhado
entre os anos de publicação do TJRO e fica no item
`causaganha-index-control-tjro/manifest.json`. Isso evita que rodadas de
origens anuais diferentes sobrescrevam referências históricas.
