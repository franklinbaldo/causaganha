# Integração operacional da consolidação por tribunal/ano

Integração ativada na `main` em 11/09/2026 pelas PRs [#1463](https://github.com/franklinbaldo/causaganha/pull/1463) e [#1464](https://github.com/franklinbaldo/causaganha/pull/1464). Implementa parte da [ADR 0012](../adr/0012-acervo-inventariado-no-internet-archive.md), reutilizando o conversor existente. A ativação não significa que todo o backlog foi convertido; as evidências abaixo delimitam o lote validado.

## Caminho integrado

- `archive_partitions.py` descobre itens pela API de busca do Archive, pagina os resultados e inventaria ZIPs pela API de metadata. Não consulta o manifesto de coleta para decidir completude.
- `consolidate-parquet.yml` seleciona até 12 partições pendentes, com rotação diária sobre a lista ordenada por ano/item, dois jobs simultâneos e sem cancelamento das outras partições quando uma falha. A rotação impede que falhas persistentes monopolizem todos os lotes.
- `consolidate_partition.py` adapta o inventário ao conversor `consolidate_tribunal_year`, incluindo tamanho e MD5 verificados sobre os bytes baixados. ZIPs com falha impedem substituir os Parquets da partição. Validações NDJSON e Parquet continuam obrigatórias. Saídas antigas que deixaram de ser geradas impedem a certificação até serem resolvidas.
- Depois da conversão, compara checksums dos Parquets locais e publicados, testa leitura HTTP Range e grava `consolidation-inputs.json` no item. O recibo registra entradas, saídas, schema e revisão da transformação. ZIP novo/alterado, saída ausente/alterada ou mudança de revisão tornam a partição elegível novamente.
- A consolidação dispara `update-catalog.yml` com `force_reconcile=true`. Esse modo agora reconstrói o catálogo com `--full` e o índice, mesmo sem ZIP novo. O gatilho duplicado por `workflow_run` foi removido.

Falhas de inventário geram avisos identificando o item e não viram “sem dados”. Se não houver trabalho executável e existirem falhas de inventário, o planejamento falha. Recibos só são publicados depois da verificação; o marcador antigo não é critério de conclusão do novo fluxo.

## Ativação

Após integrar a alteração à branch usada pelo workflow, executar primeiro:

```sh
gh workflow run consolidate-parquet.yml -f item=djen-tjro-2026 -f dry_run=true
```

Com a conversão validada, executar o mesmo item com `dry_run=false`. Esse segundo comando publica dados. Os antigos inputs `date`, `force` e `deadline_minutes` do workflow foram substituídos pelo item tribunal/ano; o CLI diário continua disponível para diagnóstico legado.

Conferir o recibo público, a execução encadeada de catálogo/índice e a homepage para `7008332-16.2026.8.22.0007`. Só essa prova completa o rollout. O cron passa a descobrir outras partições pendentes; em caso de partições repetidamente lentas ou com falhas, usar o input `item` para avançar outras e investigar as falhas. Uma partição anual pode exceder memória ou o timeout de 180 minutos; não se deve publicar apenas um subconjunto como se substituísse o ano completo.

## Evidência local

- Planejamento pela API real: `djen-tjro-2026` reconhecido como pendente.
- Conversão sem upload do ZIP real `djen-2026-09-04-TJRO.zip`: 7.179 registros, 9 Parquets validados, 2 comunicações do CNJ de referência.
- Testes de inventário, recibo, alterações de ZIP, erro de fonte, bloqueio antes de upload e gatilhos do catálogo; suites existentes de consolidação também executadas.

## Evidência no GitHub Actions

- [Dry-run anual do TJRO 2026](https://github.com/franklinbaldo/causaganha/actions/runs/34618341873): 158 ZIPs, 1.041.723 comunicações e 9 Parquets validados, sem upload.
- A [primeira publicação](https://github.com/franklinbaldo/causaganha/actions/runs/34620026191) enviou os arquivos, mas falhou ao verificar metadata ainda desatualizada. Não produziu recibo. A PR #1464 passou a consultar o subrecurso `/metadata/{item}/files`, aguardar propagação e preservar checksums como artefato da execução.
- A [publicação certificada](https://github.com/franklinbaldo/causaganha/actions/runs/34621485125) concluiu com sucesso e disparou o catálogo automaticamente. O [recibo público](https://archive.org/download/djen-tjro-2026/consolidation-inputs.json) foi lido novamente e comparado com o artefato da execução: mesmas 158 entradas e mesmos checksums dos 9 Parquets. Os nove URLs responderam a leitura HTTP Range com o cabeçalho Parquet esperado.
- CI de Python, frontend, lint e CodeQL aprovou as PRs integradas.

## Limites ainda existentes

Os uploads de tabelas de um item não são uma transação atômica: uma falha após alguns uploads pode deixar versões misturadas até a repetição. O recibo não certifica essa execução e o job falha, mas consumidores que leem diretamente os arquivos podem observar esse estado. Publicação por versões imutáveis com promoção atômica exige trabalho adicional.

O workflow usa `--verified-inventory`: falhas na descoberta ou metadata abortam a publicação do catálogo; Parquets anuais só entram quando todos os checksums do recibo correspondem aos arquivos publicados. Arquivos diários legados continuam aceitos. Consumidores diretos dos URLs não passam por esse gate. A descoberta pela busca do Archive pode ter atraso de indexação; o input explícito permite inventariar um item conhecido diretamente. A apresentação de cobertura no site ainda precisa de trabalho próprio.
