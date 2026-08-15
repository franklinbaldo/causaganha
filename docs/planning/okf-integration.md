# Integração CausaGanha × okf-parser

## Estado encontrado em 2026-08-15

O CausaGanha não declarava nem usava `okf-parser` no `pyproject.toml`, e não havia PR aberta de adoção. A release pública mais recente do parser é 0.41.3, enquanto a `main` já está em 0.42.1 sem tag/release publicada. O ganho material da série 0.42 para este projeto é o contrato relacional de bundle: chaves únicas e estrangeiras sobre frontmatter OKF.

## Fase 1 — fundação (esta mudança)

- criar `knowledge/` como bundle OKF do produto;
- modelar `Fonte` e `Pipeline` sem mover os datasets judiciais para Markdown;
- declarar tipos para que o bundle possa ser projetado como relações Ibis tipadas;
- validar `Fonte.nome` e `Pipeline.nome` como identidades naturais;
- validar `Pipeline.fonte -> Fonte.nome` como chave estrangeira;
- executar o gate em CI com um SHA exato do parser enquanto 0.42.x ainda não tem release pública.

## Próximas fatias

1. Trocar o pin de commit por uma release 0.42.x assim que ela existir.
2. Fazer `causaganha_mcp` ler a relação `Pipeline` para metadados estáveis (nome, pacote, origem e tool de status), reduzindo duplicação no agregador sem fazer o MCP chamar o próprio protocolo.
3. Usar as relações tipadas Ibis em testes de arquitetura: todo pipeline declarado deve ter pacote existente e superfície de status correspondente.
4. Avaliar uma relação `Artefato`/`Dataset` ligada a `Pipeline` antes de codificar mais fatos em prosa; só promover o que tiver consumidor real.
5. Não substituir `schema_registry.py` nem os contratos Zod automaticamente: esses arquivos descrevem o plano físico/contratos de dados, enquanto OKF nesta fase descreve conhecimento e relações de produto. Unificação só deve acontecer quando o parser tiver uma projeção que elimine duplicação sem perder garantias existentes.

## Critério de sucesso

OKF deixa de ser documentação passiva quando pelo menos um consumidor do CausaGanha consulta as relações tipadas para tomar uma decisão ou montar uma resposta. A Fase 1 cria o contrato e o gate; a Fase 2 deve produzir esse primeiro consumidor.
