# Gold-Standard Benchmark (Ground Truth)

Este diretório contém a base de dados de benchmark do projeto **CausaGanha**, usada para validar e aprimorar os classificadores heurísticos (`KeywordClassifier`) e modelos de aprendizado de máquina (`MLDocumentClassifier`).

## 📁 Estrutura de Arquivos

- `gold_benchmark.parquet`: Arquivo binário otimizado contendo todo o conjunto de dados para processamento em lote rápido por scripts de avaliação.
- `decisions/`: Diretório contendo as decisões de benchmark no formato Markdown (`.md`).
  - O nome de cada arquivo é o `intimation_id` da decisão judicial.
  - Cada arquivo contém um cabeçalho **YAML Frontmatter** com os metadados ricos extraídos pelo LLM e validados, seguido pelo texto bruto da intimação.

## 📋 Schema de Metadados (Versionamento: `schema_version`)

Os arquivos Markdown utilizam o schema de metadados versionados. A versão atual do schema é a **`1.2.0`**, contendo os seguintes campos no frontmatter:

| Campo | Tipo | Descrição |
| :--- | :--- | :--- |
| `text_uuid` | `string` | Identificador único do texto da decisão judicial (hash md5) |
| `intimation_id` | `long` | Identificador único da intimação judicial |
| `outcome` | `string` | Resultado classificado (`procedente`, `improcedente`, `parcialmente procedente`, `acordo`, `extinto sem mérito`, `unknown`) |
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
| `schema_version` | `string` | Versão do esquema de dados adotado (atualmente `1.2.0`) |

## 🚀 Como Executar Atualizações

Para re-gerar ou adicionar novos registros ao benchmark amostral de ouro:
```powershell
uv run python scripts/build_gold_benchmark.py --limit 30 --court TJRO --batch-size 5
```
Isso recalculará os arquivos Markdown na pasta `decisions/` e sincronizará o arquivo Parquet.
