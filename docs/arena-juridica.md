# Arena jurídica — Lab do CausaGanha

A arena mede a capacidade de antecipar decisões dos tribunais superiores por
competição entre modelos. A hierarquia é conquistada: ninguém entra como juiz.
Este primeiro módulo implementa o contrato das partidas, replay determinístico,
pontuação e carreira. Não é ainda um benchmark validado nem um serviço de treinamento.

## Executar

```bash
uv run causaganha arena avaliar examples/arena/demonstracao.json
uv run causaganha arena contrato
```

O primeiro comando imprime JSON com regras, identidade dos competidores, histórico
de vagas por rodada e placar por papel. O segundo exporta o JSON Schema de entrada.
Não há chamadas de rede, inferência, custos de API ou alterações no acervo.
A entrada conserva as peças, fundamentações e votos para auditoria.

## Carreira e vagas

Cada competidor é uma versão identificada de modelo (`model` + `revision`).
Não se admite cadastrar o mesmo checkpoint com dois identificadores. A versão
precisa identificar também o agente/configuração quando isso distinguir competidores.
Trocar pesos ou configuração exige nova identidade e nova carreira.

Todos entram na advocacia. Por padrão, três casos distintos no papel anterior,
com média de pelo menos 0,6, habilitam o próximo papel. A habilitação só vale
na rodada seguinte; partidas da mesma rodada usam a mesma distribuição de vagas.

A sequência é advocacia → juízo → tribunal. Depois do tribunal existem dois
circuitos independentes, STJ e STF: a simulação não exige passagem pelo STJ para
chegar ao STF. Esses nomes definem circuitos de competição, sem simular todas as
competências, procedimentos ou formas constitucionais de investidura.

O juízo não tem limite de vagas; tribunal tem 100, STJ 35 e STF 11 por padrão,
configuráveis em `rules`. As vagas são tetos: ficam vazias se faltarem habilitados.
Um habilitado pode disputar ambos os circuitos superiores em processos distintos.

Vagas são recalculadas a cada rodada: primeiro a média no papel anterior, depois
a média no próprio papel e finalmente o identificador como desempate reproduzível.
A habilitação é permanente nesta versão; uma cadeira pode ser perdida por ranking.
O total de recompensas não determina promoção: volume de partidas não compra cargo.
Uma pessoa-modelo só ocupa um papel em cada caso, inclusive entre instâncias.

## Partidas e sinal hierárquico

Cada partida contém autor, réu, peças, sequência opcional de colegiados e uma
âncora STJ/STF com URL HTTPS e SHA-256 do documento. Colegiados seguem juízo →
tribunal → corte da âncora; podem terminar antes do topo. O dispositivo coletivo
exige maioria absoluta dos votos; empates precisam de resolução antes da importação.

O resultado representa a pretensão ORIGINAL: `merits` distingue mérito de
encerramento processual; `claimant_share` é a fração do pedido obtida pelo autor
(0 a 1), ou `null` sem julgamento de mérito. Não se importa simplesmente
“recurso provido” como vitória do autor: um futuro adaptador de acórdãos deve
usar `causaganha.analysis.recurso_resolver` e registrar o polo recorrente.
O importador é responsável por essa normalização; o replay não interpreta textos.
Casos com múltiplos pedidos heterogêneos exigirão um vetor de resultados futuro.

Advogados recebem a fração média obtida por seu polo nas decisões e na âncora.
Se o topo não julgar o mérito, não se atribui sucesso material à advocacia.
Julgadores recebem `1 - abs(fração votada - fração superior)` quando ambos julgam
mérito, 1 quando ambos encerram sem mérito e 0 quando divergem sobre isso.
O voto individual é comparado ao resultado da instância seguinte, ou à âncora
real quando não houver outra instância simulada. Assim, um voto vencido pode
pontuar mais que os votos da maioria. Não há aqui previsão de viradas futuras.

Recompensas multiplicam esses sinais por 1 na advocacia, 2 no juízo, 4 no tribunal
e 8 no STJ/STF. São unidades experimentais de recompensa, sem valor financeiro.
O mesmo caso não pode pontuar duas vezes para o mesmo competidor no mesmo papel.

## Inicialização e limites da primeira entrega

Sem modelos habilitados para julgar, as primeiras partidas não têm colegiado:
a advocacia recebe somente o sinal da âncora. Esse bootstrap é um proxy de
resultado, incapaz por si de avaliar a qualidade ou causalidade da argumentação.
Ele precisa ser substituído ou complementado por arbitragem de inicialização
para um benchmark científico. Depois, as vagas passam a ser preenchidas por mérito.

`examples/arena/demonstracao.json` é inteiramente sintético, com quatro modelos
fictícios, URL example.org e hash zerado. Demonstra a progressão até a elegibilidade
superior, com mínimo reduzido a um caso. Não representa inferência ou resultado real.

A validação exige formato da proveniência, mas NÃO baixa o documento nem verifica
seu hash, autenticidade ou correspondência com o desfecho informado. As pontuações
são condicionais à transcrição importada. Nenhum caso real foi selecionado nesta entrega.

Próximas etapas: selecionar um caso concluído do corpus STJ e verificar sua fonte;
separar autos apresentados aos agentes do desfecho privado; executar advogados e
juízes com limites iguais de recursos; avaliar sensibilidade a lado, estilo e família
de modelo; definir ramo do Ministério Público com sinais próprios. O replay não
oferece ainda execução de agentes, atualização de pesos, Elo, seleção automática de
casos, controle de contaminação ou integração visual. Esses componentes não devem
ser confundidos com o núcleo de carreira entregue aqui.

## Casos formais, MCMC e narrativa

O módulo `arena.formal` acrescenta um primeiro espaço de casos sintéticos:
átomos booleanos com descrição em português, atribuição completa de fatos,
restrições em forma normal conjuntiva (CNF) e uma fórmula de referência privada.
Uma cláusula vazia é falsa; uma lista vazia de restrições é verdadeira.
Não se trata ainda de uma formalização do CPC ou de uma reconstrução de autos reais.

O exemplo `examples/arena/formal/caso.json` representa uma prestação concluída
antes ou depois de um marco acordado. Mudar apenas o fato temporal altera a
conclusão; dizer que a conclusão antecedeu o marco sem que tenha havido conclusão
viola a restrição. O recibo é um fato adicional sem efeito nessa regra fictícia.
O exemplo é pequeno de propósito: demonstra o mecanismo, sem alegar dificuldade.

### Certificado Lean

```bash
uv run causaganha arena formalizar examples/arena/formal/caso.json
uv run causaganha arena verificar-formal examples/arena/formal/caso.json --lean lean
```

O primeiro comando exporta fonte Lean; exportação NÃO implica verificação.
O segundo executa o compilador sobre código gerado por uma gramática fechada,
com timeout de 30 segundos por processo, e só retorna `verified` se a compilação
passar e ambas as provas declararem ausência de dependências axiomáticas.
Registra versão do compilador, SHA-256 do caso e da fonte. Falta de compilador,
contradição ou erro de compilação causam falha, nunca aprovação por fallback.
Não há execução de prova Lean arbitrária fornecida por um modelo.

O certificado comprova admissibilidade e o valor da conclusão NAQUELE mundo
sintético. Usa `by decide`, sem `sorry`, axiomas adicionais ou `native_decide`.
A documentação oficial explica a auditoria por
[`#print axioms`](https://lean-lang.org/doc/reference/latest/Axioms/).
O exemplo e ambas as polaridades foram testados com Lean 4.19.0.
Para executar também a integração real da suíte:

```bash
ARENA_LEAN=lean uv run pytest tests/arena/test_formal.py
```

Não há prova de fidelidade ao direito positivo, à realidade histórica ou aos
tribunais brasileiros. Novas regras jurídicas precisarão de fontes, recortes e
revisão próprios antes de entrar no modelo formal.

### Busca por divergência

```bash
uv run causaganha arena explorar examples/arena/formal/caso.json \
  examples/arena/formal/previsoes.json --steps 100 --beta 5 --seed 0
```

A busca Metropolis usa propostas simétricas: 90% inversão de um fato escolhido
uniformemente e 10% atribuição global uniforme. Propostas incompatíveis com as
restrições são rejeitadas como permanências no estado atual, sem novo sorteio.
O alvo é proporcional a `exp(beta * dificuldade)` nos mundos admissíveis, com
prior uniforme e `dificuldade = 4 * variância populacional das previsões`.
A mistura global permite alcançar regiões admissíveis desconectadas por mudanças
unitárias; isso não garante mistura rápida em espaços grandes.

Previsões são probabilidades importadas de ao menos dois modelos identificados,
calculadas sobre os mesmos fatos públicos. A tabela é vinculada ao hash do caso,
com chaves binárias na ordem de `atoms`; não se inventa previsão ausente.
A tabela precisa permanecer fixa durante a cadeia. `beta=0` remove a preferência
por divergência. O resultado conserva rejeições, semente, estados e melhor
candidato visitado. Não promete ótimo global, convergência ou dificuldade jurídica.

As previsões do exemplo vêm de duas heurísticas fictícias: uma considera o tempo,
a outra o ignora. São demonstração do algoritmo, NÃO medições de LLMs.
O algoritmo só valida restrições em Python; `lean_verified: false` sinaliza que o
candidato ainda deve passar por `verificar-formal`. O campo `best_candidate` contém
um caso formal completo, que pode ser salvo em outro JSON para verificação.
Caso contrafactual nunca herda automaticamente o desfecho real da decisão original.
Não há adaptação de `beta`, diagnóstico de convergência ou prior empírico nesta versão.

### Narrativa vinculada aos fatos

```bash
uv run causaganha arena preparar-narrativa examples/arena/formal/caso.json
uv run causaganha arena auditar-narrativa examples/arena/formal/caso.json \
  examples/arena/formal/narrativa.json
```

O primeiro comando prepara uma requisição para um futuro narrador LLM, contendo
somente pergunta, descrições dos fatos, valores booleanos e identidade da versão.
A fórmula privada, sua conclusão e o certificado não são incluídos. Não chama um
modelo. A saída deve ser interpretada como instrução/dados, não como prova de que
o narrador os obedeceu. Descrições e pergunta também exigem revisão para vazamento.

O narrador devolve trechos ligados a IDs de fatos. A auditoria confere hash,
cobertura completa e ausência de IDs desconhecidos. Sempre retorna
`semantic_fidelity: unverified` e `ready_for_benchmark: false`: um texto pode citar
o ID correto e inverter seu significado. Nenhuma verificação puramente referencial
é apresentada como equivalência semântica. O exemplo de narrativa é um relato
mecânico dos fatos, sem geração por LLM.

Próxima integração: executor de modelos para previsões e narrativa, revisão de
fidelidade e casos com regras jurídicas fundamentadas. Esse corpus formal permanece
separado das temporadas ancoradas em decisões reais até haver um contrato explícito
para medir consistência formal e antecipação de tribunal como métricas distintas.
