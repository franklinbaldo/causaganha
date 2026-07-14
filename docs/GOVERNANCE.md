# Governança de Dados / Data Governance

> **English summary:** CausaGanha preserves Brazilian judicial publications
> obtained from official public publication channels (DJEN and court
> systems). The default is **integral preservation**: content is not removed
> because a requester finds a lawful judicial publication inconvenient, old,
> or reputationally harmful. Correction, restriction, or removal happens only
> on objective grounds — the official source changed the publication, a
> competent authority ordered it, or the project itself introduced a
> processing error. De-indexing from general search engines is a
> discoverability control, not removal, and does not affect the archive.
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
arquivística do projeto, mas não afasta a observância da LGPD, das
restrições legais de publicidade nem de correções posteriores promovidas
pela fonte oficial.

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
  fontes, não constrói perfis de pessoas naturais e não vende dados. Sua
  finalidade é arquivística e de interesse público, compatível com a
  finalidade que justificou a publicação original.
- O Supremo Tribunal Federal rejeitou um "direito ao esquecimento" genérico
  fundado no mero decurso do tempo (Tema 786). Idade da publicação,
  constrangimento ou impacto reputacional, por si sós, **não são fundamento
  para remoção** do acervo. Excessos concretos têm os remédios ordinários —
  dirigidos, em primeiro lugar, à fonte oficial.
- O que o projeto controla diretamente é a **descobribilidade** do acervo
  por buscadores gerais (Seção 6) — uma salvaguarda de desenho, distinta da
  integridade do arquivo.

## 4. Correção, restrição e desindexação

A regra geral do CausaGanha é a **preservação integral das publicações
oficiais**. O projeto não remove ou altera uma publicação apenas a pedido do
interessado, em razão do decurso do tempo, de alegado prejuízo reputacional
ou porque seu conteúdo seja desfavorável à pessoa mencionada.

O projeto poderá corrigir, restringir ou remover conteúdo nas seguintes
hipóteses objetivas:

1. **Erro do próprio projeto:** corrupção, duplicação, associação ao
   processo ou tribunal incorreto, falha de extração ou inclusão de conteúdo
   que não constava da publicação oficial;
2. **Alteração pela fonte oficial:** correção, despublicação, anonimização,
   decretação de segredo de justiça ou outra restrição determinada pelo
   tribunal ou órgão responsável;
3. **Determinação de autoridade competente:** ordem judicial ou
   administrativa aplicável ao projeto;
4. **Indício grave de divulgação indevida:** quando houver indícios
   objetivos de que dado sigiloso ou protegido foi publicado acidentalmente,
   o conteúdo poderá ser cautelarmente desindexado enquanto o projeto
   solicita confirmação à fonte oficial. A restrição permanente seguirá a
   resposta oficial ou determinação da autoridade competente.

A **desindexação por buscadores gerais não equivale à remoção do acervo**.
O projeto poderá adotar `noindex` ou limitar buscas nominais como
salvaguarda geral, preservando a consulta por número do processo, tribunal,
data e demais critérios diretamente relacionados ao ato judicial.

Pedidos envolvendo crianças e adolescentes, vítimas, violência doméstica,
saúde ou possível quebra de sigilo receberão **análise prioritária e
cautelar, sem presunção automática de remoção**. A análise verificará
especialmente a situação atual na fonte oficial e as restrições legais
aplicáveis (ex.: Resolução CNJ 121).

### Canais

- **Solicitações sensíveis** (sigilo, dados protegidos, situações da lista
  prioritária acima): canal privado, por e-mail —
  <franklinbaldo+causaganha@gmail.com>. Não exponha o conteúdo sensível em
  espaços públicos do repositório.
- **Erros ordinários de qualidade de dados** (tribunal/data errados,
  duplicação, arquivo corrompido): issue pública em
  <https://github.com/franklinbaldo/causaganha/issues> com o título
  `[Revisão de dados]`.
- **O que informar:** tribunal, data da publicação, identificação do trecho
  (número do processo, se houver) e a hipótese objetiva invocada (1–4).
- **Prazo alvo de primeira resposta:** 15 dias.

As providências adotadas e sua fundamentação genérica são registradas de
maneira auditável, sem reproduzir o conteúdo protegido.

## 5. Retenção

A missão do projeto é **preservação de longo prazo**: publicações oficiais
são efêmeras na origem e o acervo existe para que permaneçam verificáveis.
A retenção padrão é, portanto, **indefinida**, ressalvadas as hipóteses
objetivas da Seção 4.

## 6. Indexação por buscadores

O projeto distingue quatro camadas, que não precisam de regras idênticas:
preservação no acervo, consulta interna, busca nominal e indexação por
buscadores gerais. É a mesma distinção que o CNJ faz na Resolução 121, que
reconhece a publicidade de nomes e decisões mas orienta que bases de
decisões evitem a busca por nome quando possível.

- O **dashboard** e as páginas de navegação são indexáveis (são agregados e
  metadados de cobertura, não texto integral de publicações).
- Páginas HTML que exibam **texto integral** de publicações com dados
  pessoais usarão `noindex` por padrão. Essa medida não remove o conteúdo do
  acervo nem impede sua consulta por número do processo, tribunal, data ou
  navegação interna; apenas evita a indexação indiscriminada por buscadores
  gerais. Hoje o texto integral vive nos ZIPs/Parquet no Internet Archive,
  não em páginas HTML do site.

## 7. Licenciamento

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
    manifesto, agregados do dashboard): os direitos que eventualmente
    pertençam ao próprio projeto sobre esses materiais são disponibilizados
    sob [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/).

Pedimos (sem exigir) que reutilizações citem a fonte e a data de geração do
dataset, porque isso preserva a auditabilidade que motiva o projeto.

## 8. Papel e responsabilidade

- O CausaGanha é um **arquivo de atos oficiais**, não a fonte oficial nem o
  autor do conteúdo. A decisão sobre a publicidade de cada ato, e a
  responsabilidade por ela, é do tribunal que o publicou. Para efeitos
  legais (prazos, intimações), vale a publicação original no DJEN/tribunal.
- Preservar publicações oficiais de acesso público é atividade lícita e de
  interesse público. O projeto responde pelos seus próprios erros de
  processamento (Seção 4, hipótese 1) e pela sincronização com a fonte
  oficial (hipótese 2) — não pelo teor dos atos judiciais que preserva.
- O projeto não garante completude: a cobertura real, os atrasos e as
  lacunas conhecidas são expostos no próprio dashboard — a incerteza faz
  parte do produto.
- Alterações relevantes nesta política devem ser feitas por PR neste
  repositório, mantendo o histórico auditável.
