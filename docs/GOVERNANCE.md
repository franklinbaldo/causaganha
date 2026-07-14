# Governança de Dados / Data Governance

> **English summary:** CausaGanha archives Brazilian judicial publications
> (DJEN and court publication systems) that are already public by law. This
> document states what the project collects, what it deliberately does not
> collect, how it handles personal data present in official publications, how
> to request correction / removal review, the retention and indexing stance,
> and the licensing of the published datasets (distinct from the MIT license
> that covers the code). It is a policy statement, not legal advice.

Este documento define a posição do projeto sobre o ciclo de vida social e
legal dos dados que ele preserva e republica. Ele complementa a documentação
técnica (README, `docs/planning/`) e a página pública
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

Todo o material de origem já é público por força de lei — comunicações
judiciais publicadas em diário oficial eletrônico, cuja publicação produz
efeitos legais (intimação, contagem de prazos).

## 2. O que o projeto deliberadamente NÃO coleta

- Processos ou documentos sob **segredo de justiça**. O filtro primário é do
  próprio DJEN/tribunal: o que não é publicado no diário não entra no acervo.
  O projeto não faz scraping de autos processuais restritos.
- Dados obtidos por autenticação, cadastro ou quebra de controle de acesso.
- Qualquer fonte não-oficial (redes sociais, agregadores comerciais).

## 3. Dados pessoais em publicações oficiais

Publicações judiciais contêm, por natureza, nomes de partes, advogados,
magistrados e, ocasionalmente, outros dados pessoais. A posição do projeto:

- A base do tratamento é a **publicidade legal dos atos processuais**
  (Constituição Federal, art. 93, IX; CPC, art. 189) — o projeto preserva o
  que o Poder Judiciário já tornou público como ato oficial.
- O projeto **não enriquece** as publicações com dados pessoais de outras
  fontes, não constrói perfis de pessoas naturais e não vende dados.
- O projeto reconhece que republicar em forma **mais pesquisável e mais
  durável** que a fonte original muda o impacto prático sobre as pessoas
  citadas. Por isso existe o procedimento de revisão da Seção 4.

## 4. Correção, remoção e desindexação

Qualquer pessoa pode solicitar revisão de conteúdo do acervo:

- **Canal:** abrir uma issue em
  <https://github.com/franklinbaldo/causaganha/issues> com o título
  `[Revisão de dados]`, ou contatar o mantenedor pelo GitHub. Se a
  solicitação contiver dados sensíveis, indique isso na issue **sem
  incluí-los** e um canal privado será combinado.
- **O que informar:** tribunal, data da publicação, identificação do trecho
  (número do processo, se houver) e o motivo do pedido.
- **Critérios de avaliação:**
  - **Erro de coleta/processamento** (dado corrompido, atribuição errada de
    tribunal/data, publicação duplicada): corrigido no dataset derivado e,
    quando aplicável, no item do Internet Archive.
  - **Conteúdo que se tornou restrito na origem** (segredo de justiça
    decretado após a publicação, despublicação oficial pelo tribunal):
    removido dos datasets derivados; o ZIP bruto no Internet Archive é
    tratado conforme as políticas de takedown do próprio Internet Archive,
    com apoio do projeto ao solicitante.
  - **Pedido de desindexação** (o conteúdo permanece público na origem, mas
    a pessoa pede que não seja localizável por buscadores através deste
    projeto): avaliado caso a caso, ponderando o interesse público do ato
    oficial e o impacto sobre a pessoa. Casos envolvendo crianças e
    adolescentes, saúde, violência doméstica ou vítimas de crimes recebem
    tratamento prioritário e presunção favorável à desindexação.
- **Prazo alvo de primeira resposta:** 15 dias.
- Decisões de remoção/desindexação e sua motivação genérica (sem repetir o
  conteúdo removido) são registradas para auditabilidade.

## 5. Retenção

A missão do projeto é **preservação de longo prazo**: publicações oficiais
são efêmeras na origem e o acervo existe para que permaneçam verificáveis.
A retenção padrão é, portanto, **indefinida**, ressalvados os desfechos da
Seção 4.

## 6. Indexação por buscadores

- O **dashboard** e as páginas de navegação são indexáveis (são agregados e
  metadados de cobertura, não texto integral de publicações).
- Páginas que venham a exibir **texto integral** de publicações com dados
  pessoais devem avaliar `noindex` por padrão, mantendo o conteúdo acessível
  a quem chega pela navegação do próprio acervo. Hoje o texto integral vive
  nos ZIPs/Parquet no Internet Archive, não em páginas HTML do site.

## 7. Licenciamento

Duas camadas distintas — não confundir:

- **Código** (este repositório): [MIT](../LICENSE).
- **Dados:**
  - **Publicações originais (ZIPs):** atos oficiais, não protegidos por
    direito autoral (Lei 9.610/98, art. 8º, IV). Domínio público.
  - **Datasets derivados e metadados do projeto** (Parquet consolidado,
    manifesto, agregados do dashboard): dedicados ao domínio público via
    [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/). Isto
    formaliza a declaração já publicada na página "Sobre" de que os dados
    são de domínio público e de uso livre.

Pedimos (sem exigir) que reutilizações citem a fonte e a data de geração do
dataset, porque isso preserva a auditabilidade que motiva o projeto.

## 8. Responsabilidade e limites

- O projeto é um **arquivo**, não a fonte oficial. Para efeitos legais
  (prazos, intimações), vale a publicação original no DJEN/tribunal.
- O projeto não garante completude: a cobertura real, os atrasos e as
  lacunas conhecidas são expostos no próprio dashboard — a incerteza faz
  parte do produto.
- Alterações relevantes nesta política devem ser feitas por PR neste
  repositório, mantendo o histórico auditável.
