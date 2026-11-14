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
