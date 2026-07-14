# Governança de Dados / Data Governance

> **O projeto preserva o registro público produzido pelo Estado; não
> reavalia, não higieniza e não reescreve esse registro por iniciativa
> própria.**

> **English summary:** CausaGanha preserves Brazilian judicial publications
> obtained from official public publication channels (DJEN and court
> systems). The default is **integral preservation**: content is not removed
> because a requester finds a lawful judicial publication inconvenient, old,
> or reputationally harmful. Correction, restriction, or removal happens only
> on objective grounds — the project itself introduced a processing error,
> or a competent authority ordered it. Later changes at the official source
> (correction, unpublication, supervening secrecy) are recorded as
> provenance metadata, not grounds for removal: preserving the history of
> what was actually published is the archive's function. Discoverability is part of the mission: the project
> does not degrade the findability of lawful public acts, and does not
> claim control it does not have over material deposited with the Internet
> Archive — a US nonprofit library under its own jurisdiction and
> preservation policies, where the primary copies live. The project is
> maintained by a private individual on a non-commercial basis and takes
> the position that the LGPD does not apply to this processing (art. 4º,
> I), a position reinforced by the law's own foundations and exemptions.
> The project also computes derived analytics — case-outcome
> classification and per-lawyer indicators — exclusively from the public
> record: these are declared statistical estimates with open methodology,
> an unfavorable indicator is not grounds for removal, and analytical
> errors (misclassification, misattribution) are the project's own errors,
> corrected on objective demonstration against the record.
> This document states the policy; it is not legal advice.

Este documento define a posição do projeto sobre o ciclo de vida legal dos
dados que ele preserva. Ele complementa a documentação técnica (README,
`docs/planning/`) e a página pública
["Sobre"](https://franklinbaldo.github.io/causaganha/sobre/).

Este documento é uma declaração de política do projeto. **Não é
aconselhamento jurídico.**

## 1. O que o projeto coleta

- **Publicações judiciais oficiais** distribuídas pelo DJEN (Diário de
  Justiça Eletrônico Nacional) e por sistemas de publicação dos próprios
  tribunais (ex.: STJ, TJRO).
- **Metadados de coleta** produzidos pelo próprio projeto: manifesto de
  sincronização, códigos de resposta HTTP, datas de arquivamento.
- **Dados derivados**: tabelas Parquet estruturadas a partir dos ZIPs
  originais, e agregados de cobertura exibidos no dashboard.

Todo o material de origem é obtido de canais oficiais de publicação judicial
de acesso público — comunicações cuja publicação produz efeitos legais
(intimação, contagem de prazos) e cuja publicidade decorre de decisão do
próprio Poder Judiciário. Essa circunstância fundamenta a finalidade
arquivística do projeto. Ela não dispensa a observância das restrições
legais de publicidade **na coleta**: o que a fonte oficial não publicou não
entra no acervo (Seção 2). Alterações posteriores da fonte são tratadas
como proveniência, não como retirada (Seção 5). Sobre o âmbito de aplicação
da LGPD, ver Seção 3.

## 2. O que o projeto deliberadamente NÃO coleta

- Processos ou documentos sob **segredo de justiça**. O filtro primário é do
  próprio DJEN/tribunal: o que não é publicado no diário não entra no acervo.
  O projeto não faz scraping de autos processuais restritos.
- Dados obtidos por autenticação, cadastro ou quebra de controle de acesso.
- Qualquer fonte não-oficial (redes sociais, agregadores comerciais).

## 3. Dados pessoais em publicações oficiais

Publicações judiciais contêm, por natureza, nomes de partes, advogados e
magistrados. A posição do projeto:

- A decisão de tornar esses atos públicos **é do Poder Judiciário**, no
  exercício da publicidade legal dos atos processuais (Constituição Federal,
  art. 93, IX; CPC, art. 189). O CausaGanha preserva fielmente o que a fonte
  oficial publicou; ele não é o autor nem o editor do conteúdo.
- O projeto **não enriquece** as publicações com dados pessoais de outras
  fontes e não vende dados. Os indicadores analíticos que produz (Seção 4)
  derivam exclusivamente do próprio registro público. Sua finalidade é
  arquivística, informacional e de interesse público, compatível com a
  finalidade que justificou a publicação original.
- O Supremo Tribunal Federal rejeitou um "direito ao esquecimento" genérico
  fundado no mero decurso do tempo (Tema 786). Idade da publicação,
  constrangimento ou impacto reputacional, por si sós, **não são fundamento
  para remoção** do acervo. Excessos concretos têm os remédios ordinários —
  e, quando devam alcançar o acervo, chegam ao projeto na forma de
  determinação de autoridade competente (Seção 5).
- **Âmbito de aplicação da LGPD.** O projeto é mantido por pessoa natural,
  em caráter cidadão, sem qualquer finalidade econômica. O entendimento do
  projeto é que esse tratamento está **fora do âmbito de aplicação da
  LGPD**, por força do seu art. 4º, I (tratamento realizado por pessoa
  natural para fins exclusivamente particulares e não econômicos). Esse
  entendimento é reforçado por outras previsões da própria lei:
  - a liberdade de informação, de comunicação e de opinião é **fundamento**
    da LGPD, não exceção a ela (art. 2º, III);
  - a lei exclui do seu âmbito o tratamento para fins exclusivamente
    **jornalísticos e acadêmicos** (art. 4º, II) — naturezas que o trabalho
    de documentação e pesquisa sobre atos judiciais públicos compartilha;
  - o tratamento de dados **tornados públicos** por determinação legal é
    expressamente contemplado, considerada a finalidade e o interesse
    público que justificaram sua disponibilização (art. 7º, §§ 3º e 4º);
  - subsidiariamente, o **legítimo interesse** (art. 7º, IX) ampara o
    tratamento para finalidade arquivística e de apoio à pesquisa.
  Em qualquer dessas leituras, o resultado é o mesmo: a lei não restringe
  este trabalho. As salvaguardas desta política são adotadas por escolha do
  projeto, como boa prática, e **não constituem admissão de obrigação
  legal**.
- A **descobribilidade** do acervo é parte da missão do projeto, não um
  dano a mitigar (Seção 8).

## 4. Camada analítica: classificação de resultados e indicadores

Além de preservar publicações, o projeto produz — hoje sob a fronteira
experimental "Lab" — **análises derivadas**: classificação do resultado
das causas (quem ganhou, quem perdeu) e indicadores estatísticos de
atuação por advogado, calculados exclusivamente a partir do registro
público preservado no acervo. É a segunda metade do nome do projeto, e
esta política aplica-se a ela com a mesma lógica:

- **Mesma matéria-prima, nenhum enriquecimento externo.** Os indicadores
  derivam somente dos atos oficiais do acervo. O projeto não cruza esses
  dados com fontes externas sobre pessoas naturais, não usa dados
  cadastrais privados e não comercializa indicadores.
- **Natureza declarada: estimativa, não julgamento.** A classificação de
  resultados é feita por métodos automatizados (heurísticas, modelos de
  linguagem) e é falível. Superfícies que exibam indicadores devem
  declarar a metodologia — que é código aberto e auditável neste
  repositório — e a natureza estimativa dos números. Indicadores não são
  medição oficial de qualidade profissional.
- **Análise legítima do registro público.** Calcular e publicar
  estatísticas sobre a atuação de advogados em processos públicos é
  exercício de liberdade de informação e de pesquisa sobre dados que o
  Estado tornou públicos — a mesma base que ampara estudos acadêmicos e
  jornalismo de dados sobre o Judiciário. **Um indicador desfavorável não
  gera direito à remoção**, pelas mesmas razões da Seção 5: o projeto não
  gerencia reputações, nem para baixo nem para cima.
- **Erro analítico é erro do projeto.** Aqui a responsabilidade difere da
  camada de arquivo: a classificação e a atribuição são produto do
  projeto, não do Estado. Resultado classificado incorretamente, causa
  atribuída ao advogado errado (homônimos, OAB incorreta) ou erro de
  cálculo são a **hipótese 1 da Seção 5**: demonstrado o erro contra o
  registro público, corrige-se — verificação objetiva, sem juízo de
  mérito.

Em síntese: a camada de arquivo responde pela **fidelidade ao que o Estado
publicou**; a camada analítica responde pela **correção do que o próprio
projeto calculou**. Nenhuma das duas negocia remoção por desconforto.

## 5. Correção, restrição e desindexação

A regra geral do CausaGanha é a **preservação integral das publicações
oficiais**. O projeto não remove ou altera uma publicação apenas a pedido do
interessado, em razão do decurso do tempo, de alegado prejuízo reputacional
ou porque seu conteúdo seja desfavorável à pessoa mencionada.

O projeto poderá corrigir, restringir ou remover conteúdo nas seguintes
hipóteses objetivas:

1. **Erro do próprio projeto:** corrupção, duplicação, associação ao
   processo ou tribunal incorreto, falha de extração ou inclusão de conteúdo
   que não constava da publicação oficial;
2. **Determinação de autoridade competente:** ordem judicial ou
   administrativa aplicável ao projeto.

**Alterações posteriores na fonte oficial** (correção, despublicação,
anonimização, decretação superveniente de segredo de justiça) **não
retiram, por si sós, conteúdo do acervo**. Preservar o registro histórico
do que foi efetivamente publicado em cada data — inclusive quando a fonte
depois o altera ou suprime — é precisamente a função do arquivo,
resguardando seu eventual valor probatório e de auditoria. Quando
detectadas, alterações da fonte são **anotadas como metadados de
proveniência**, sem reescrever o registro original. Se uma restrição
superveniente deve alcançar também o acervo, isso virá por determinação de
autoridade competente dirigida ao projeto (hipótese 2).

Não há hipótese de restrição por juízo próprio do projeto sobre gravidade,
sensibilidade ou dano. **O projeto não avalia mérito**: existindo o
registro histórico e não havendo determinação de autoridade competente,
ele permanece no acervo. Quem entende que uma publicação oficial é indevida
deve dirigir-se ao Poder Judiciário — se a situação for de fato grave, é
dali que virá a ordem (hipótese 2), e o projeto a cumprirá com
naturalidade.

Restrições de descobribilidade **não são adotadas**: tornar atos públicos
localizáveis é a razão de ser do projeto (Seção 8).

### Canais

- **Solicitações que envolvam alegação de sigilo ou dados protegidos:**
  canal privado, por e-mail — <franklinbaldo+causaganha@gmail.com>. Não
  exponha o conteúdo sensível em espaços públicos do repositório.
- **Erros ordinários de qualidade de dados** (tribunal/data errados,
  duplicação, arquivo corrompido, resultado de causa classificado
  incorretamente, causa atribuída ao advogado errado): issue pública em
  <https://github.com/franklinbaldo/causaganha/issues> com o título
  `[Revisão de dados]`.
- **O que informar:** tribunal, data da publicação, identificação do trecho
  (número do processo, se houver) e a hipótese objetiva invocada (1–2).
- **Prazo alvo de primeira resposta:** 15 dias.

As providências adotadas e sua fundamentação genérica são registradas de
maneira auditável, sem reproduzir o conteúdo protegido.

## 6. Custódia no Internet Archive e jurisdição

As cópias primárias dos ZIPs e dos datasets consolidados são depositadas no
**Internet Archive**, biblioteca digital sem fins lucrativos sediada nos
Estados Unidos, com jurisdição própria e políticas próprias de preservação,
acesso e remoção.

Consequências práticas dessa custódia:

- Uma vez depositado, o material passa a ser regido **também** pelas
  políticas do Internet Archive. O projeto não controla unilateralmente a
  permanência ou remoção de itens lá arquivados.
- As hipóteses da Seção 5 aplicam-se ao que o projeto controla diretamente:
  os datasets derivados que ele gera, o site e a indexação das suas
  páginas. Para os itens depositados no Internet Archive, remoções seguem
  os procedimentos de takedown do próprio Internet Archive; quando uma
  hipótese objetiva da Seção 5 se confirmar, o projeto coopera com o
  solicitante nesses procedimentos.
- Essa separação é deliberada: a custódia por uma biblioteca independente,
  em outra jurisdição, protege o acervo contra pressões informais e contra
  o ponto único de falha que seria o próprio mantenedor.

## 7. Retenção

A missão do projeto é **preservação de longo prazo**: publicações oficiais
são efêmeras na origem e o acervo existe para que permaneçam verificáveis.
A retenção padrão é, portanto, **indefinida**, ressalvadas as hipóteses
objetivas da Seção 5 e as políticas do Internet Archive (Seção 6).

## 8. Indexação e descobribilidade

A descobribilidade é **parte da missão**, não um risco a mitigar. O
CausaGanha existe para tornar publicações oficiais localizáveis e
verificáveis; o projeto não adota medidas de desenho para dificultar o
encontro de atos públicos lícitos — fazê-lo contrariaria a razão de ser do
acervo.

- O **site** publica agregados e metadados de cobertura, e suas páginas são
  indexáveis.
- O **texto integral** das publicações vive nos ZIPs e tabelas Parquet
  depositados no Internet Archive (Seção 6). A indexação e o acesso a esse
  material são regidos pelas políticas do próprio Internet Archive — o
  projeto **não controla, e por isso não promete controlar**, como
  buscadores tratam o material lá depositado. Esta política não assume
  compromissos sobre superfícies que não estão sob controle do projeto.
- A Resolução CNJ 121 disciplina os serviços de consulta **dos próprios
  tribunais** (é ela, por exemplo, que orienta bases de decisões do
  Judiciário a evitar busca nominal); ela não impõe essas restrições a
  arquivos independentes — e a publicidade dos atos que ela reconhece é
  exatamente o que este acervo preserva.
- O projeto **não pratica restrições de descobribilidade por iniciativa
  própria**. Alterações no acervo ocorrem exclusivamente nas hipóteses
  objetivas da Seção 5 (erro do próprio projeto ou determinação de
  autoridade competente).

## 9. Licenciamento

Duas camadas distintas — não confundir:

- **Código** (este repositório): [MIT](../LICENSE).
- **Dados:**
  - **Publicações originais (ZIPs):** os textos de decisões judiciais e dos
    demais atos oficiais não são protegidos por direitos autorais, nos
    termos do art. 8º, IV, da Lei 9.610/1998. Essa declaração não abrange
    automaticamente obras de terceiros eventualmente reproduzidas nas
    publicações nem afasta direitos relativos à privacidade, proteção de
    dados, honra ou imagem.
  - **Datasets derivados e metadados do projeto** (Parquet consolidado,
    manifesto, agregados do dashboard, indicadores analíticos da Seção 4):
    os direitos que eventualmente
    pertençam ao próprio projeto sobre esses materiais são disponibilizados
    sob [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/).

Pedimos (sem exigir) que reutilizações citem a fonte e a data de geração do
dataset, porque isso preserva a auditabilidade que motiva o projeto.

## 10. Papel e responsabilidade

- O CausaGanha é um **arquivo de atos oficiais**, não a fonte oficial nem o
  autor do conteúdo. A decisão sobre a publicidade de cada ato, e a
  responsabilidade por ela, é do tribunal que o publicou. Para efeitos
  legais (prazos, intimações), vale a publicação original no DJEN/tribunal.
- Preservar publicações oficiais de acesso público é atividade lícita e de
  interesse público. O projeto responde pelos seus próprios erros de
  processamento e de análise (Seções 4 e 5, hipótese 1) e pelo cumprimento
  de determinações de autoridade competente (hipótese 2) — não pelo teor
  dos atos judiciais que preserva, nem por refletir alterações que a fonte
  fizer depois: o registro histórico é o produto.
- O projeto não garante completude: a cobertura real, os atrasos e as
  lacunas conhecidas são expostos no próprio dashboard — a incerteza faz
  parte do produto.
- Alterações relevantes nesta política devem ser feitas por PR neste
  repositório, mantendo o histórico auditável.
