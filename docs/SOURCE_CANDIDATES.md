# Catálogo de fontes jurídicas candidatas

Este catálogo qualifica fontes **antes** de qualquer integração. A pergunta não é apenas “há dados?”, mas “há um job de produto útil, identidade estável, acesso reproduzível e contrato compatível com ARQUIVO → ESTADO → TEOR?”.

Atualizado em 2026-09-01. A classificação é deliberadamente conservadora: `READY` autoriza abrir uma issue específica de integração; `INVESTIGAR` exige prova adicional; `REJEITADA` registra evidência negativa para evitar redescoberta.

## Resumo

| Fonte | Evidência | Acesso | Job principal | Decisão |
| --- | --- | --- | --- | --- |
| TCU — Jurisprudência | TEOR + metadados | bulk CSV oficial | buscar acórdãos e entendimentos de controle externo com proveniência | READY |
| TSE — Processual 2026 | ESTADO + TEOR + metadados | bulk CSV oficial | consultar processos, assuntos, decisões e recursos eleitorais | READY |
| STF — Corte Aberta | metadados/estatística | painéis com exportação CSV | medir atuação e volume do STF, não substituir pesquisa de teor | INVESTIGAR |
| CNJ — BNMP 3.0 | ESTADO + metadados sensíveis | painel público com exportação | responder sobre medidas penais/prisões agregadas sem criar cadastro pessoal | REJEITADA para integração processual; avaliar só estatística agregada |
| Justiça do Trabalho — Falcão | TEOR + precedentes | busca pública, sem bulk/API oficial documentado nesta qualificação | pesquisar jurisprudência nacional trabalhista | INVESTIGAR |
| TNU/CJF — jurisprudência eproc | TEOR | busca pública eproc, sem bulk/API oficial documentado nesta qualificação | localizar decisões e acórdãos da TNU | INVESTIGAR |

## 1. TCU — Jurisprudência

**Órgão:** Tribunal de Contas da União.

**Fonte oficial:** https://sites.tcu.gov.br/dados-abertos/jurisprudencia/

**Natureza da evidência:** TEOR e metadados. O portal publica cinco bases — Acórdãos, Jurisprudência Selecionada, Publicações, Súmulas e Respostas a Consultas — e separa Acórdãos por ano.

**Unidade e identidade:** acórdão/documento do TCU. Antes da integração, a issue filha deve confirmar em amostra o campo canônico de identidade e sua estabilidade entre republicações.

**Acesso:** download bulk em CSV, com dicionário de dados. O portal de transparência informa atualização diária e formatos abertos; não há motivo para começar por scraping.

**Cobertura/freshness:** cobertura histórica por conjuntos anuais; atualização declarada diária no serviço de Jurisprudência.

**Licença/termos:** o portal de dados abertos caracteriza os dados como livres para uso, reutilização e redistribuição, sujeito no máximo a atribuição/compartilhamento conforme a licença aplicável. A integração deve preservar crédito explícito ao TCU e registrar a URL do artefato baixado.

**Proveniência reproduzível:** forte. O caminho recomendado é download do CSV oficial → checksum do arquivo bruto → preservação imutável → transformação derivada. Não usar os resumos gerados por IA como autoridade de teor.

**Sobreposição:** complementa STJ/JURIS porque cobre controle externo e contas públicas, uma jurisdição material diferente. Não deve ser apresentado como processo judicial comum.

**Job MCP/site:** “encontre acórdãos do TCU sobre X e mostre a fonte oficial”. No MCP, pertence a TEOR; no site, busca temática deve deixar claro que é jurisprudência do TCU.

**Custo/riscos:** baixo custo de aquisição por bulk; risco principal é modelar identidade e campos de teor sem assumir schema antes de amostrar. Resumos por IA do próprio portal são derivados e não substituem texto/espelho oficial.

**Prova mínima:** portal oficial confirma CSV para download, cinco bases e Acórdãos anuais; serviço oficial declara atualização diária.

**Decisão:** **READY**. Abrir integração separada e começar por um único conjunto de Acórdãos, preservando bruto + checksum antes de ampliar cobertura.

## 2. TSE — Processual 2026

**Órgão:** Tribunal Superior Eleitoral / Secretaria Judiciária.

**Fonte oficial:** https://dadosabertos.tse.jus.br/dataset/processual-2026

**Natureza da evidência:** ESTADO, TEOR e metadados. O conjunto publica `Processo Eleitoral`, `Assuntos`, `Decisões` e `Partes`; a descrição oficial também menciona recursos referentes ao pleito de 2026.

**Unidade e identidade:** processo eleitoral e registros relacionados. A integração deve provar em amostra como os CSVs se relacionam e qual identificador é estável entre processo, decisão, assunto e parte.

**Acesso:** bulk CSV oficial pelo Portal de Dados Abertos do TSE. Não requer crawler.

**Cobertura/freshness:** escopo Brasil, pleito de 2026. O portal informa data de geração por arquivo e atualização sob demanda/necessidade — portanto não deve ser vendido como estado live.

**Licença/termos:** Creative Commons Atribuição, conforme a página do dataset.

**Proveniência reproduzível:** forte. Preservar URL de recurso, data de geração, checksum e arquivo bruto; derivar tabelas relacionadas de forma determinística.

**Sobreposição:** DataJud pode conter metadados processuais eleitorais, mas este dataset oficial agrega estruturas eleitorais específicas e decisões/assuntos do pleito. A issue filha deve medir sobreposição numa amostra antes de justificar duplicação de campos.

**Job MCP/site:** “quais decisões/recursos constam neste processo eleitoral e de qual extração oficial vieram?”. ESTADO não deve fingir freshness maior que a geração do arquivo; TEOR precisa provar o que o CSV de decisões realmente contém.

**Custo/riscos:** aquisição simples; riscos de volume, dados de partes e interpretação errada da cadência “sob demanda”. Aplicar minimização na superfície pública e não indexar campos pessoais só porque o arquivo os contém.

**Prova mínima:** página oficial criada em 28/08/2026, fonte PJe, escopo Brasil, recursos CSV e licença CC Atribuição.

**Decisão:** **READY** para uma prova de integração pequena e eleitoralmente explícita, começando sem `Partes` na superfície de produto até revisão de necessidade/PII.

## 3. STF — Corte Aberta

**Órgão:** Supremo Tribunal Federal.

**Fontes oficiais:** https://portal.stf.jus.br/transparencia/default.asp e páginas do Programa Corte Aberta.

**Natureza da evidência:** metadados e estatística agregada sobre processos, decisões, recursos e repercussão geral.

**Unidade e identidade:** os painéis exportam dados em CSV, mas a qualificação atual não provou que cada linha corresponde a um documento decisório estável com teor recuperável e identificador adequado ao modelo do CausaGanha.

**Acesso:** painéis públicos com exportação CSV. Melhor que scraping, mas ainda precisa de uma amostra determinística do export real.

**Cobertura/freshness:** o programa informa dados desde 2000 em seus painéis; a cadência por dataset precisa ser medida no arquivo exportado.

**Licença/termos:** o STF mantém política de transparência e dados abertos, mas esta qualificação não fixou a licença específica de cada export do Corte Aberta.

**Proveniência reproduzível:** potencialmente boa se os URLs/exports forem estáveis; ainda não comprovada em nível de artefato.

**Sobreposição:** alto potencial de sobreposição com DataJud para metadados e com futuras fontes de jurisprudência para decisões. Pode ser ótimo para estatística do STF sem acrescentar TEOR.

**Job MCP/site:** métricas como “quantos processos/decisões do STF em determinado recorte?”; não usar como resposta de teor enquanto não houver documento canônico.

**Custo/riscos:** risco de integrar um painel analítico como se fosse corpus documental; licença por export e identidade ainda precisam ser verificadas.

**Prova mínima:** o Portal STF descreve Corte Aberta como painéis de atuação jurisdicional; material oficial do lançamento registra exportação CSV e extensão histórica desde 2000.

**Decisão:** **INVESTIGAR**. Baixar uma amostra de um painel e provar schema, licença, identidade e complementaridade antes de issue de integração.

## 4. CNJ — BNMP 3.0

**Órgão:** Conselho Nacional de Justiça.

**Fonte oficial:** https://www.cnj.jus.br/novo-painel-do-bnmp-3-0-aprimora-monitoramento-da-populacao-prisional/

**Natureza da evidência:** ESTADO e estatística de medidas penais/prisões, com domínio intrinsecamente sensível.

**Unidade e identidade:** o painel é voltado ao monitoramento da população prisional; a qualificação não estabeleceu um contrato seguro e necessário para registros individualizados no produto.

**Acesso:** painel público com exportação para análises externas.

**Cobertura/freshness:** nacional; cadência e granularidade do export exigiriam prova própria.

**Licença/termos:** não qualificada nesta passada em nível suficiente para ingestão persistente.

**Proveniência reproduzível:** export pode ser reproduzível para estatísticas, mas isso não resolve risco de dados pessoais/sensíveis.

**Sobreposição:** baixa sobreposição com o corpus atual, porém também baixo alinhamento com o job central de acompanhar processos e localizar decisões públicas.

**Job MCP/site:** existe valor em estatística agregada de política pública; não há justificativa atual para transformar o CausaGanha em cadastro pesquisável de pessoas privadas de liberdade ou submetidas a medidas penais.

**Custo/riscos:** risco elevado de PII, dano por desatualização, falsa equivalência entre medida e condenação e expansão de escopo sem necessidade de produto.

**Prova mínima:** CNJ confirma painel público e capacidade de exportação para análises externas.

**Decisão:** **REJEITADA para integração processual individualizada**. Pode voltar como issue distinta apenas para indicadores agregados, com schema que não exponha pessoas.

## 5. Justiça do Trabalho — Falcão

**Órgão:** Justiça do Trabalho; sistema desenvolvido pelo TRT-9 e definido pelo CSJT como repositório oficial de jurisprudência de primeiro e segundo graus trabalhistas.

**Fonte oficial de qualificação:** https://portal.trt14.jus.br/portal/noticias/sistema-falcao-conheca-ferramenta-para-busca-de-jurisprudencia

**Natureza da evidência:** TEOR, precedentes e metadados jurisprudenciais. A fonte informa sentenças, acórdãos, admissibilidade de recurso de revista, IRDR, IAC, arguição de inconstitucionalidade, súmulas, OJs e teses, além de decisões do TST.

**Unidade e identidade:** não qualificada. A interface de busca prova o corpus, mas não um identificador bulk estável.

**Acesso:** pesquisa pública. Nesta passada não foi encontrado mecanismo oficial documentado de bulk/export/API para o corpus; isso impede READY.

**Cobertura/freshness:** nacional na Justiça do Trabalho segundo a descrição do sistema; cadência e cobertura histórica precisam de documentação técnica.

**Licença/termos:** a notícia do TRT-14 permite reprodução da matéria com citação, mas isso não equivale a licença aberta do corpus de jurisprudência.

**Proveniência reproduzível:** insuficiente sem endpoint/export oficial ou artefato versionável.

**Sobreposição:** grande valor potencial porque adiciona sentenças/acórdãos trabalhistas nacionais, hoje fora do foco TJRO/STJ. Pode também duplicar STF/STJ referenciado pelo próprio Falcão.

**Job MCP/site:** “encontre jurisprudência trabalhista nacional sobre X”. É claramente TEOR.

**Custo/riscos:** scraper seria frágil e contrário à política deste catálogo; licença e identidade não provadas.

**Prova mínima:** TRT-14 confirma escopo e natureza do Falcão, mas apenas como ferramenta pública de pesquisa.

**Decisão:** **INVESTIGAR**. Procurar documentação oficial do CSJT/TRT-9 sobre API/export; não construir scraper para avançar a issue.

## 6. TNU/CJF — jurisprudência no eproc

**Órgão:** Conselho da Justiça Federal / Turma Nacional de Uniformização.

**Fonte oficial de qualificação:** https://www.cjf.jus.br/cjf/noticias/2025/junho/tnu-anuncia-novo-ambiente-de-pesquisa-de-jurisprudencia/view

**Natureza da evidência:** TEOR e metadados de decisões/acórdãos da TNU.

**Unidade e identidade:** decisão/acórdão no módulo público de jurisprudência do eproc; identidade bulk ainda não provada.

**Acesso:** interface pública integrada ao eproc. Nesta qualificação não foi encontrado bulk/API oficial documentado.

**Cobertura/freshness:** TNU; cobertura histórica e atualização precisam ser medidas no sistema ou documentação oficial.

**Licença/termos:** não qualificados em nível suficiente para ingestão persistente.

**Proveniência reproduzível:** insuficiente sem artefato ou endpoint oficial estável.

**Sobreposição:** complementaria STJ e Justiça Federal com a camada uniformizadora dos JEFs, especialmente útil para previdenciário e benefícios; precisa provar que o corpus não é obtido de forma melhor por outra fonte aberta.

**Job MCP/site:** “localize decisões da TNU sobre tese X e vincule o resultado à fonte oficial”. TEOR.

**Custo/riscos:** automatizar UI eproc sem contrato oficial cria fragilidade operacional; ausência de licença/endpoint documentado impede READY.

**Prova mínima:** CJF confirma o módulo público de jurisprudência lançado em 09/06/2025 e integrado ao eproc.

**Decisão:** **INVESTIGAR**. Buscar export/API oficial antes de qualquer código de coleta.

## Regra de promoção para READY

Uma fonte só sai de `INVESTIGAR` quando houver evidência versionável de: (1) acesso oficial reproduzível; (2) identidade estável; (3) licença/termos compatíveis; (4) amostra pequena que prove schema e job; (5) diferença real frente ao corpus atual. Scraping não promove uma fonte por si só.
