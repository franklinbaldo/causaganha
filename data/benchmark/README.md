# Gold-Standard Benchmark (Ground Truth)

Este diretório contém a base de dados de benchmark do projeto **CausaGanha**, usada para validar e aprimorar os classificadores heurísticos (`KeywordClassifier`) e modelos de aprendizado de máquina (`MLDocumentClassifier`).

## 📁 Estrutura de Arquivos

- `gold_benchmark.parquet`: Arquivo binário otimizado contendo todo o conjunto de dados para processamento em lote rápido por scripts de avaliação.
- `decisions/`: Diretório contendo as decisões de benchmark no formato Markdown (`.md`).
  - O nome de cada arquivo é o `intimation_id` da decisão judicial.
  - Cada arquivo contém um cabeçalho **YAML Frontmatter** com os metadados ricos extraídos pelo LLM e validados, seguido pelo texto bruto da intimação.

## 📋 Schema de Metadados (Versionamento: `schema_version`)

Os arquivos Markdown utilizam o schema de metadados versionados. A versão atual do schema é a **`1.3.0`**, contendo os seguintes campos no frontmatter:

| Campo | Tipo | Descrição |
| :--- | :--- | :--- |
| `text_uuid` | `string` | Identificador único do texto da decisão judicial (hash md5) |
| `intimation_id` | `long` | Identificador único da intimação judicial |
| `outcome` | `string` | Resultado classificado. **Mérito (1ª instância):** `procedente`, `improcedente`, `parcialmente procedente`, `acordo`, `extinto sem mérito`, `unknown`. **Recurso (`1.3.0`):** `provido`, `não provido`, `parcialmente provido`, `não conhecido`, `prejudicado` |
| `recorrente_polo` | `string \| null` | Polo que interpôs o recurso (`A` = autor/ativo, `P` = réu/passivo, `null` para 1ª instância). Necessário para resolver o vencedor em outcomes recursais (ver §Invariante) |
| `decision_type` | `string` | Tipo do ato decisório (`sentença`, `acórdão`, `decisão interlocutória`) |
| `plaintiff_won` | `boolean` | Flag indicando se a parte autora (plaintiff) saiu vitoriosa |
| `confidence_score` | `float` | Grau de confiança atribuído pelo modelo de análise (0.0 a 1.0) |
| `summary` | `string` | Sumário conciso da decisão elaborado pelo LLM |
| `decision_reasoning` | `string` | Resumo de 1 a 2 sentenças sobre a fundamentação jurídica adotada |
| `court` | `string` | Sigla do Tribunal de origem (ex: `TJRO`) |
| `llm_model` | `string` | Nome do modelo LLM que realizou a extração dos dados ricos |
| `validated_at` | `timestamp` | Data/hora UTC em que o registro foi gerado e integrado |
| `is_human_verified` | `boolean` | Flag indicando se o registro passou por curadoria humana |
| `fase_processual` | `string` | Fase do processo (`conhecimento`, `execução`, `recursal`, `cautelar`, `unknown`) |
| `classe_processual` | `string` | Classe judicial (ex: `Procedimento Comum Cível`, `Apelação Cível`) |
| `assunto_principal` | `string` | Assunto de direito em discussão (ex: `Danos Morais`, `Cobrança`) |
| `valor_causa` | `float \| null` | Valor da causa em reais (BRL) |
| `valor_condenacao` | `float \| null` | Valor da condenação em reais (BRL) |
| `proposed_regex` | `string \| null` | Expressão regular proposta pelo LLM para preencher lacunas de classificação nas heurísticas |
| `judge_name` | `string \| null` | Nome completo do magistrado decisor |
| `keywords` | `list[string]` | Palavras-chave que melhor representam o conteúdo da decisão |
| `legal_bases` | `list[string]` | Fundamentos jurídicos mencionados (normas, artigos, súmulas) |
| `precedents` | `dict[string, string]` | Mapeamento de precedentes do CNJ e suas categorias (`confirmado`, `distinto`, `ultrapassado`) |
| `schema_version` | `string` | Versão do esquema de dados adotado (atualmente `1.3.0`) |

> **Nota de versão `1.3.0`:** adiciona a vocabulário recursal (`provido`/`não provido`/`parcialmente provido`/`não conhecido`/`prejudicado`) e o campo `recorrente_polo`, exigidos pelo `recurso_resolver`. Registros `1.2.0` permanecem válidos: `recorrente_polo` ausente é tratado como `null` (1ª instância).

## ⚖️ Alvo de Avaliação: o Invariante (Polo Vencedor)

O rótulo `outcome` é **dependente da postura processual**: um `procedente` de 1ª instância e um `recurso do réu não provido` descrevem o *mesmo evento substantivo* (o autor venceu) com palavras diferentes. Avaliar o rótulo de superfície mede vocabulário processual, não quem venceu — e injeta ruído de rótulo por construção.

O alvo do benchmark é o **invariante**: o polo vencedor, estável entre instâncias:

```
WinnerPolo = A (autor) | P (réu) | draw (acordo) | unknown (não ratável)
```

O mapeamento `(outcome, recorrente_polo) → WinnerPolo` (com inversão de polaridade recursal) é de `recurso_resolver.resolve_winner_polo`; o ponto de entrada de benchmark é `benchmark_metrics.to_winner_polo`.

A avaliação é decomposta em duas tarefas independentes (predição seletiva):

- **Gate** — "esta é uma decisão de mérito ratável?" (`A`/`P`/`draw` vs. `unknown`). Interlocutórias, despachos, `extinto sem mérito` e recursos inadmissíveis caem aqui.
- **Condicional** — "dado que é ratável, qual polo venceu?" pontuado **apenas** sobre casos ratáveis no gold, para que a massa procedural `unknown` não mascare nem infle o desempenho de outcome.

Sempre reporte **suporte por classe** (per-polo F1 sobre poucos casos tem IC largo demais). A amostragem deve ser **estratificada** por `fase_processual × decision_type × outcome`. Detalhes teóricos em [`DESIGN.md`](./DESIGN.md). Execução: `scripts/evaluate_heuristics.py` (usa `benchmark_metrics.evaluate_invariant`).

## 🚀 Como Executar Atualizações

Para re-gerar ou adicionar novos registros ao benchmark amostral de ouro:
```powershell
uv run python scripts/build_gold_benchmark.py --limit 30 --court TJRO --batch-size 5
```
Isso recalculará os arquivos Markdown na pasta `decisions/` e sincronizará o arquivo Parquet.

## ⚠️ Observações sobre o Oráculo e Próximos Passos

1. **Oráculo: LLM-painel independente, não humano**:
   * A validade de um gold standard não exige um anotador humano — exige um juiz **(1) independente do sistema avaliado, (2) ao menos tão capaz quanto ele e (3) de confiabilidade mensurável**. Um painel de LLMs frontier de 2026 satisfaz os três, e sua confiabilidade é medida como a de um painel humano: concordância entre anotadores (κ de Cohen / α de Krippendorff entre modelos).
   * O risco real a evitar é a **circularidade**: rotular o gold com o *mesmo* modelo (ou config) que alimenta o classificador de produção mede auto-concordância, não acurácia. Salvaguardas: **gap de capacidade (professor > aluno)** — o oráculo roda config mais forte (texto completo, painel multi-modelo) que o caminho de produção barato sob teste; **consenso + concordância medida** — o consenso do painel é o rótulo, e κ/α entre modelos é a confiabilidade do próprio benchmark; **sem auto-avaliação** — um classificador não é pontuado contra rótulos gerados pelo seu próprio modelo.
   * `is_human_verified` marca uma *âncora opcional mais forte*, não um pré-requisito de validade. Veja [`DESIGN.md`](./DESIGN.md) §4.
2. **Aprimoramento de Heurísticas**:
   * Este benchmark deve ser usado diretamente para avaliar e aprimorar as expressões regulares em `KeywordClassifier`, sempre pelo invariante (gate + condicional), não pelo rótulo de superfície.
   * Novos vocabulários de outcome (ex.: o eixo recursal da `1.3.0`) são um **bump de schema** e só são benchmarkáveis depois que o analisador que os emite existe e uma amostra recursal **estratificada** é rotulada pelo oráculo-painel.
