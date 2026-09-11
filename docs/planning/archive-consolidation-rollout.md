# Integração operacional da consolidação por tribunal/ano

Implementação local em 11/09/2026; ativação no GitHub Actions e publicação do backlog ainda não realizadas. Implementa parte da [ADR 0012](../adr/0012-acervo-inventariado-no-internet-archive.md), reutilizando o conversor existente.

## Caminho integrado

- `archive_partitions.py` descobre itens pela API de busca do Archive, pagina os resultados e inventaria ZIPs pela API de metadata. Não consulta o manifesto de coleta para decidir completude.
- `consolidate-parquet.yml` seleciona até 12 partições pendentes, anos recentes primeiro, com dois jobs simultâneos e sem cancelamento das outras partições quando uma falha. O limite evita disparar todo o backlog de uma vez.
- `consolidate_partition.py` adapta o inventário ao conversor `consolidate_tribunal_year`. ZIPs com falha impedem substituir os Parquets da partição. Validações NDJSON e Parquet continuam obrigatórias.
- Depois da conversão, compara checksums dos Parquets locais e publicados, testa leitura HTTP Range e grava `consolidation-inputs.json` no item. O recibo registra entradas, saídas, schema e revisão da transformação. ZIP novo/alterado, saída ausente/alterada ou mudança de revisão tornam a partição elegível novamente.
- A consolidação dispara `update-catalog.yml` com `force_reconcile=true`. Esse modo agora reconstrói o catálogo com `--full` e o índice, mesmo sem ZIP novo. O gatilho duplicado por `workflow_run` foi removido.

Falhas de inventário geram avisos identificando o item e não viram “sem dados”. Se não houver trabalho executável e existirem falhas de inventário, o planejamento falha. Recibos só são publicados depois da verificação; o marcador antigo não é critério de conclusão do novo fluxo.

## Ativação

Após integrar a alteração à branch usada pelo workflow, executar primeiro:

```sh
gh workflow run consolidate-parquet.yml -f item=djen-tjro-2026 -f dry_run=true
```

Com a conversão validada, executar o mesmo item com `dry_run=false`. Esse segundo comando publica dados; não foi executado nesta implementação. Os antigos inputs `date`, `force` e `deadline_minutes` do workflow foram substituídos pelo item tribunal/ano; o CLI diário continua disponível para diagnóstico legado.

Conferir o recibo público, a execução encadeada de catálogo/índice e a homepage para `7008332-16.2026.8.22.0007`. Só essa prova completa o rollout. O cron passa a descobrir outras partições pendentes; em caso de partições repetidamente lentas ou com falhas, usar o input `item` para avançar outras e investigar as falhas. Uma partição anual pode exceder memória ou o timeout de 180 minutos; não se deve publicar apenas um subconjunto como se substituísse o ano completo.

## Evidência local

- Planejamento pela API real: `djen-tjro-2026` reconhecido como pendente.
- Conversão sem upload do ZIP real `djen-2026-09-04-TJRO.zip`: 7.179 registros, 9 Parquets validados, 2 comunicações do CNJ de referência.
- Testes de inventário, recibo, alterações de ZIP, erro de fonte, bloqueio antes de upload e gatilhos do catálogo; suites existentes de consolidação também executadas.

## Limites ainda existentes

Os uploads de tabelas de um item não são uma transação atômica: uma falha após alguns uploads pode deixar versões misturadas até a repetição. O recibo não certifica essa execução e o job falha, mas consumidores que leem diretamente os arquivos podem observar esse estado. Publicação por versões imutáveis com promoção atômica exige trabalho adicional.

O catálogo legado também inclui artefatos sem recibo; esta mudança não converte o recibo em um gate universal de leitura nem atualiza toda a apresentação de cobertura no site. A descoberta pela busca do Archive pode ter atraso de indexação; o input explícito permite inventariar um item conhecido diretamente.
