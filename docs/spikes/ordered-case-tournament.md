# Spike: competição de listas ordenadas de regexes e casos

Referência: [PR #1697](https://github.com/franklinbaldo/causaganha/pull/1697),
base `7701537ac3f61db4e4cc0e87b728418a8863cc85`.

## Pergunta e resultado

Selecionar a composição e a ordem de uma lista de casos melhora o torneio que
classifica pelo maior score histórico? Condições compostas ajudam além da
seleção/ordenação de regexes simples?

Neste experimento, **selecionar listas do catálogo completo deu um ganho pequeno**.
**Reordenar apenas as regras já promovidas não melhorou os totais de acertos e erros**.
**Casos compostos tiveram resultados mistos**: pioraram no treino com rótulos do
classificador e melhoraram algumas métricas na validação cruzada com os rótulos
do benchmark. Os intervalos descritivos do ganho das listas incluem zero.
O spike não demonstra superioridade geral nem autoriza promoção.

O experimento não modifica `src/`, modelos, leaderboard de produção ou estado da
catraca. Não retreina Random Forest nem executa uma rodada do flywheel; seleciona
programas simbólicos em memória para comparação offline. `ModelRatchetGate` é um
gate de segmentador binário e não é simulado por uma AUC inventada para estes
rótulos multiclasses. Uma futura integração/promoção precisa de avaliação no fluxo
completo e do gate aplicável; este relatório não a implementa.

## O que compete

Os 29 padrões são exatamente as sementes de `build_default_tournament()` mais os
cinco candidatos extras de `scripts/run_regex_tournament.py`. Não se propõem novos
padrões textuais, não se usam `proposed_regex`, summaries ou condições baseadas
nos rótulos/metadados produzidos pelo anotador.

| Variante | Seleção | Decisão |
| --- | --- | --- |
| `tournament_top3` | Implementação existente, inclusive fallback | Maior score histórico entre os matches ativos |
| `promoted_order_only` | Mesmos membros ativos; busca troca posições | Primeiro caso satisfeito |
| `catalogue_ordered` | Seleciona e ordena regexes simples do catálogo completo | Primeiro caso satisfeito |
| `composite_cases` | Seleciona e ordena entre 324 casos gerados | Primeiro caso satisfeito |

A gramática dos casos é:

```text
SE todas as regexes de all_of derem match
E nenhuma regex de none_of der match
NO texto completo OU no dispositivo extraído
COM proteção opcional contra negação
ENTÃO retornar a categoria do caso
SENÃO continuar para o próximo caso
Se nenhum caso resolver: unknown
```

`none_of` é uma exclusão do conjunto de padrões das outras categorias. Pares em
`all_of` são gerados entre regexes da mesma categoria. A gramática é enumerada de
forma determinística e independente dos documentos/rótulos. Não há chamadas LLM
nem geração por agente neste spike; um proponente externo poderia futuramente
emitir casos no mesmo formato.

Exemplo efetivamente selecionado nos folds 0, 1 e 3 do treino no benchmark:

```text
SE extinto_art_485 E extinto_julgo_extinto derem match no texto completo
E os matches não estiverem negados
ENTÃO extinto sem mérito
```

Também foram selecionadas condições sobre o dispositivo e exclusões de outras
categorias. A extração do dispositivo e a janela de negação reutilizam o
comportamento do `KeywordClassifier`; não são uma segmentação estrutural perfeita.
Sem marcador de dispositivo, um caso dessa seção não casa, sem fallback implícito.

## Método fixado antes de executar a comparação

- Objetivo da lista: `(acertos respondidos - 2 × erros respondidos) / N - 0,001 × número de casos`.
  Abstenção vale zero; um `unknown` correto não ganha ponto no treino.
- Casos novos precisam casar com pelo menos dois documentos de treino.
- Busca local determinística com inserção, remoção e troca de posições, até dez
  casos e vinte passos. Na comparação apenas de ordem, só são permitidas trocas
  e todos os membros originais são preservados, inclusive quando excedem dez.
- Não é uma busca exaustiva nem um ótimo certificado. A regularização de listas
  ajuda a evitar crescimento sem ganho de utilidade no treino.
- Seed 1697, mesmos documentos de avaliação em cada comparação pareada. Nenhum
  hiperparâmetro é escolhido pelas métricas dos documentos reservados.
- Relatório primário: cinco categorias do torneio mais `unknown`. As 47 decisões
  com rótulos recursais ficam fora dessa tabela, mas estão nos resultados completos.
  Há diagnóstico de polo vencedor para todos os documentos, usando o
  `resolve_winner_polo` existente e o polo recorrente anotado, sem colapsar os
  rótulos recursais durante a seleção das listas.
- F1 macro é a média das cinco categorias; suporte/TP/FP/FN/F1 por classe são
  exportados. Precisão seletiva usa apenas documentos em que houve resposta.

## Dados e duas modalidades de treino

`gold_benchmark.parquet`: 300 registros, 285 textos distintos após normalizar
HTML/espaços. Três grupos têm rótulos conflitantes e são excluídos por inteiro:
restam 282 documentos, dos quais 235 pertencem ao recorte primário. Todos os
300 registros têm `is_human_verified=False`; 100 foram anotados por
`gemini/gemini-2.5-flash-lite` e 200 por `haiku-panel-v1`. Os rótulos são uma
referência falível; concordância com eles não equivale a verdade jurídica.

1. **`external_weak`**: os 1.000 documentos existentes recebem rótulos de
   `KeywordClassifier(texto completo limpo)`. Removem-se identidades/textos presentes
   em qualquer um dos 300 registros do gold, vazios e duplicatas: sobram 981 para
   treino. Os 282 documentos do gold ficam fora da seleção inteira.
2. **`gold_five_fold`**: os 282 documentos são divididos em cinco folds por hash
   determinístico do texto e seed. Cada lista é selecionada nos outros quatro
   folds; cada documento é avaliado uma única vez. Todos os braços usam a mesma
   partição. São exportadas as identidades de treino/teste e as listas de cada fold.

Isto não reproduz o CSV local da rodada original da PR #1697: ele não está
versionado. A modalidade externa usa o Parquet de 1.000 documentos disponível e
o classificador existente, sem o snippet selecionado por Random Forest daquele
gerador de CSV. Os totais entre as duas modalidades não devem ser comparados como
se tivessem o mesmo tamanho/oráculo de treino.

## Resultados em 235 documentos

### Treino externo com 981 rótulos do classificador

| Variante | Respostas | Acertos | Erros | Precisão nas respostas | Macro-F1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| KeywordClassifier, referência adicional | 72 | 50 | 22 | 69,4% | 0,4954 |
| Torneio Top-3 atual | 59 | 43 | 16 | 72,9% | 0,4405 |
| Mesmos promovidos, outra ordem | 59 | 43 | 16 | 72,9% | 0,4412 |
| Catálogo completo, lista selecionada | 59 | 44 | 15 | 74,6% | 0,4553 |
| Lista com casos compostos | 59 | 42 | 17 | 71,2% | 0,4315 |

Aqui a lista simples acrescenta um acerto líquido com o mesmo número de respostas.
A variante somente de ordem altera uma previsão, mas não corrige nenhum erro:
a alteração é entre respostas erradas. O F1 muda pela distribuição por classe.
O classificador original continua com o maior F1 e mais respostas; as listas
não demonstram vantagem como substitutas completas dele.

### Seleção nos quatro folds restantes do benchmark

| Variante | Respostas | Acertos | Erros | Precisão nas respostas | Macro-F1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Torneio Top-3 atual | 43 | 29 | 14 | 67,4% | 0,3300 |
| Mesmos promovidos, outra ordem | 43 | 28 | 15 | 65,1% | 0,3189 |
| Catálogo completo, lista selecionada | 48 | 35 | 13 | 72,9% | 0,3883 |
| Lista com casos compostos | 50 | 35 | 15 | 70,0% | 0,3660 |

A lista simples ganha seis acertos e retira um erro frente ao Top-3. A lista
composta ganha seis acertos, mas acrescenta um erro. O número de condições aumenta
o espaço de busca e pode aumentar sobreajuste; este resultado não determina se a
gramática é ruim ou se faltam dados/busca para aproveitá-la.

### Incerteza e interpretação

Bootstrap pareado, 1.000 reamostragens de documentos, seed 1697, sobre o ganho de
utilidade por documento frente ao Top-3, sem penalidade de tamanho na avaliação:

| Modalidade | Lista simples: ganho e intervalo de 95% | Casos compostos: ganho e intervalo de 95% |
| --- | --- | --- |
| Externo | +0,0128; [−0,0213; +0,0553] | −0,0128; [−0,0340; 0,0000] |
| Cinco folds | +0,0340; [−0,0213; +0,0894] | +0,0170; [−0,0469; +0,0809] |

Intervalos são descritivos, condicionados às listas já selecionadas. Não incluem
incerteza do anotador, dependência entre processos nem variabilidade de todo o
procedimento de seleção. Incluem zero: o ganho observado é um sinal para investigar,
não uma conclusão de superioridade.

O corpus já foi explorado na revisão anterior; estes folds não são um teste final
intocado. Não há corte temporal nem teste de tribunal inédito. A remoção de
duplicatas exatas não garante independência entre documentos do mesmo processo
ou modelos de sentença semelhantes. Esta rodada não mede latência de produção:
pré-cálculo compartilhado e busca são cronometrados separadamente no JSON.

## Reprodução e inspeção

Em um checkout com as dependências do projeto:

```bash
uv run --with pyarrow python scripts/spike_case_tournament.py \
  --seed 1697 --output /tmp/ordered_cases_results.json

uv run --with pyarrow pytest -q \
  tests/test_spike_case_tournament.py tests/test_regex_tournament.py \
  tests/test_structural_segmenter.py tests/test_recurso_resolver.py tests/test_spike_thx02.py

uv run ruff check
uv run ruff format --check scripts/spike_case_tournament.py tests/test_spike_case_tournament.py
```

[Resultados completos](ordered_cases_results.json): hashes SHA-256 dos inputs e do
script, ambiente, origem dos rótulos, auditoria de sobreposição, listas executáveis
de cada fold, partições, previsões por documento, suporte por classe, comparação
pareada e tempos. Não contém cópia dos textos das decisões. Tempos/ambiente/commit
da execução podem variar; a seleção e as previsões são determinísticas para os
mesmos inputs, código e seed.

Validação desta PR: 71 testes passaram (11 novos e 60 existentes), Ruff global
passou e a formatação dos dois arquivos novos passou. O comando de formatação
global aponta um desvio preexistente em `scripts/export_visualizer_data.py`, que
não foi alterado. As políticas exportadas foram reproduzidas contra os textos e
as partições auditadas para confirmar ausência de sobreposição exata.

Próximo experimento sugerido: congelar estas propostas e avaliá-las em um novo
lote temporal, com análise dos documentos em que as previsões mudam. O resultado
atual não sustenta substituir o torneio por casos compostos automaticamente.

## Referências teóricas

- [Learning Certifiably Optimal Rule Lists for Categorical Data](https://jmlr.org/papers/v18/17-716.html).
- [Scalable Bayesian Rule Lists](https://proceedings.mlr.press/v70/yang17h.html).

A busca deste spike é uma aproximação local simples; não implementa esses dois
algoritmos nem reivindica suas garantias.
