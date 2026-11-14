# ADR 0013 — Consulta por CNJ: índice Protobuf de ponteiros sobre os originais preservados

Data: 2026-11-14

Status: proposta. Implementação candidata aberta na [PR #1721](https://github.com/franklinbaldo/causaganha/pull/1721); nada desta decisão foi publicado em produção.

Relação: aplica a [ADR 0012](0012-acervo-inventariado-no-internet-archive.md) — o Internet Archive é a fonte de verdade sobre os arquivos preservados — ao caminho de leitura por número de processo.

## Antecedentes

Entre setembro e novembro de 2026 surgiram quatro propostas concorrentes para localizar documentos por CNJ, nenhuma consolidada em decisão:

| Proposta | O que demonstrou | O que deixou em aberto |
|---|---|---|
| Série Parquet/CNJ ([#1468](https://github.com/franklinbaldo/causaganha/issues/1468)–[#1472](https://github.com/franklinbaldo/causaganha/issues/1472)) | Reordenação e regeneração seletiva de Parquets para filtrar por CNJ | Regenerar arquivos inteiros para servir buscas pontuais; complexidade de reordenação, read-back e rollback; parada desde setembro |
| [PR #1714](https://github.com/franklinbaldo/causaganha/pull/1714) | Protobuf reversível com o `processo.proto` sobre capturas reais do DataJud | Experimento; não escolhe arquitetura |
| [PR #1720](https://github.com/franklinbaldo/causaganha/pull/1720) | Codec PB v2 lossless para lotes do DJEN: 10,65 MB contra 40,82 MB de JSON bruto, 0 divergências em 7.493 comunicações | Cria um segundo formato canônico do mesmo conteúdo |
| [PR #1721](https://github.com/franklinbaldo/causaganha/pull/1721) | Índice Protobuf federado por processo, com ponteiros para os ZIPs originais do DJEN e do DataJud | Prova de ponta a ponta no navegador, benchmark real, mapeamento multitribunal |

O site foi reconstruído como leitor estático sem backend ([PR #1715](https://github.com/franklinbaldo/causaganha/pull/1715)), que lê o Archive por HTTP Range ([#1718](https://github.com/franklinbaldo/causaganha/pull/1718), [#1719](https://github.com/franklinbaldo/causaganha/pull/1719)). Ele precisa de um único caminho de CNJ até o documento.

A [issue #1717](https://github.com/franklinbaldo/causaganha/issues/1717) mostra o custo da ausência dessa decisão: o leitor exibe e oferece para download um payload recodificado (`_i`, `t`, `g`, …), não o JSON que a API do DataJud devolve. A otimização de bytes foi feita à custa da fidelidade ao original.

O Parquet foi adotado inicialmente também como índice. A experiência acumulada indica que ele serve mal a esse papel: uma consulta pontual por CNJ exige ordenar e reparticionar arquivos inteiros, e cada documento novo obriga a regenerá-los. O formato continua adequado ao que faz bem — varreduras analíticas em colunas sobre o acervo inteiro.

## Decisão

**O original é canônico; o índice só aponta para ele.**

1. **Canônico.** Os ZIPs originais do DJEN e do DataJud, nos bytes publicados no Archive, são a única representação canônica do conteúdo. Nenhum formato derivado os substitui no caminho de leitura.
2. **Índice por CNJ.** A consulta pontual usa um índice federado em Protobuf, com schema versionado (`process_pointer.proto`), roteado pelo próprio CNJ até item, ZIP e membro. Exemplo da PR #1721: `70726450920238220001` → item `causaganha-2023-8-22` → ZIP `0001.zip` → membro `707264509.pb`. O registro contém apenas ponteiros e identificadores (datas, membros, IDs e hashes oficiais do DJEN; item, ZIP, membro e instante do DataJud), nunca cópias de texto, movimentos ou capas.
3. **Leitura.** O site resolve o ponteiro e busca o membro original por HTTP Range, devolvendo o JSON tal como publicado. A issue #1717 deixa de existir por construção.
4. **Camada analítica.** Os Parquets consolidados por tribunal/ano continuam como camada analítica: estatística, jurimetria, catálogo SQL e consultas DuckDB em lote. Eles não são o caminho de consulta por CNJ e não precisam ser reordenados para isso.
5. **Pesquisa de compressão.** Codecs compactos (PB v2, vocabulários lossless, templates de hash) continuam como pesquisa. Só entram no caminho de leitura por nova ADR, se o custo de armazenamento ou transferência vier a justificar um segundo formato.

## Destino das propostas concorrentes

| Proposta | Destino |
|---|---|
| PR #1721 | Base da implementação; merge condicionado aos critérios de aceite abaixo |
| PR #1720 | Não entra no caminho de leitura. Fica aberta como pesquisa ou é fechada com referência a esta ADR |
| PR #1714 | Fechada como experimento concluído; resultados citados aqui |
| Issues #1468–#1472 | Encerradas como objetivo de índice. O que servir à camada analítica (normalização de escrita e leitura, #1469) é reaproveitado nela |
| Issue #1717 | Resolvida pela leitura do membro original |

## Invariantes

- **Original imutável.** Um ZIP publicado não é sobrescrito; versões novas são snapshots novos ([#1707](https://github.com/franklinbaldo/causaganha/issues/1707)).
- **Índice reconstruível.** Todo o índice pode ser regenerado a partir dos originais no Archive, sem estado oculto.
- **Publicação antes do checkpoint.** O checkpoint de coleta só avança depois que o artefato publicado é verificado por leitura ([#1706](https://github.com/franklinbaldo/causaganha/issues/1706)); o estado sobrevive entre runners ([#1704](https://github.com/franklinbaldo/causaganha/issues/1704)).
- **Ponteiro sem alvo é lacuna.** CNJ ausente no índice, ou ponteiro cujo membro não responde, é estado desconhecido, nunca prova de inexistência do processo ou da publicação, conforme a tabela de evidências da ADR 0012.
- **Identidade preservada.** O índice preserva todos os registros por CNJ recebidos, inclusive graus e documentos distintos ([#1705](https://github.com/franklinbaldo/causaganha/issues/1705)); a deduplicação é feita na leitura, nunca na escrita.

## Riscos e limites

- **Multitribunal.** O roteamento demonstrado cobre o TJRO; outros tribunais exigem o mapeamento completo dos segmentos do CNJ para item e ZIP.
- **Latência no navegador.** Cada consulta resolve índice e membro por HTTP Range; o número de idas e voltas ao Archive precisa ser medido, não presumido.
- **Proxy de CORS.** O leitor depende do proxy para Range sobre o Archive; ele passa a ser componente crítico, com monitoramento próprio.
- **Produtor DataJud.** `daily_pack.py` ainda seleciona um único snapshot por CNJ no lote diário; o índice só preserva identidades que o produtor de fato publica.
- **Migração.** O manifesto v3 em CSV para v4 em PB é incompatível e exige rebuild explícito.

## Critérios de aceite

- Teste de ponta a ponta em navegador limpo para um CNJ do TJRO: publicações do DJEN e capa do DataJud carregadas do Archive, com o JSON exibido idêntico ao da API pública.
- Benchmark real: tamanho do índice, número de requisições e latência por consulta, custo de rebuild completo e incremental.
- Prova de publicação e recuperação no Archive ([#1709](https://github.com/franklinbaldo/causaganha/issues/1709)) e smoke test público do site.
- Destino de cada proposta concorrente registrado nas respectivas PRs e issues.

## Sequência

1. Fechar os P0 do DataJud: checkpoint persistente (#1704) e publicação verificável (#1706). Sem isso, o índice aponta para dados cuja continuidade não está garantida.
2. Completar e mesclar a PR #1721 contra os critérios acima.
3. Executar a prova de ponta a ponta no Archive (#1709).
4. Estender o roteamento a outros tribunais.

Esta decisão não afirma que o índice esteja implementado em produção, que o site já devolva o JSON original ou que a cobertura multitribunal exista.
