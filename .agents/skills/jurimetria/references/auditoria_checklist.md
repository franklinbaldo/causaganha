# Checklist de Auditoria de Jurimetria Empírica

Este checklist deve ser utilizado para auditar pipelines de extração, bases de dados
e classificadores judiciais, identificando lacunas em relação ao estado da arte em jurimetria.

---

## Bloco 1: Taxonomia e Fidelidade ao CPC (Anti-Simplificação)

- [ ] **1.1. Separação Estrita de Juízo de Admissibilidade vs. Mérito:**
  - O pipeline distingue sentenças terminativas (`CPC art. 485`, ilegitimidade, inépcia) de improcedência de mérito (`CPC art. 487, I`)?
  - *Risco de violação:* Tratar extinção sem resolução de mérito como se o réu tivesse "vencido a lide material", quando a ação pode ser reproposta.
- [ ] **1.2. Não-Colapso da Parcial Procedência:**
  - O sistema registra `PARCIALMENTE_PROCEDENTE` como categoria de 1ª classe e não força um arredondamento prematuro para "ganhou" ou "perdeu"?
- [ ] **1.3. Tratamento de Acordos e Transações:**
  - Decisões homologatórias de acordo (`CPC art. 487, III, b`) são classificadas separadamente como resolução consensual (sem vencido formal)?
- [ ] **1.4. Preservação de Tutelas Provisórias e Decisões Interlocutórias:**
  - Tutelas de urgência (`CPC art. 300`) e liminares não são descartadas como meros "despachos sem conteúdo decisório"?
  - O resultado da tutela (`DEFERIDA`, `INDEFERIDA`, `PARCIAL`) é indexado como incidente cognitivo?

---

## Bloco 2: Métricas Econômicas e Proporcionalidade

- [ ] **2.1. Extração do Valor da Causa (`VALOR_DA_CAUSA`):**
  - O pipeline recupera a pretensão econômica inicial expressa pelo autor na petição inicial?
- [ ] **2.2. Extração do Valor da Condenação Principal (`VALOR_CONDENACAO_PRINCIPAL`):**
  - O valor líquido ou estimável arbitrado pelo juiz no dispositivo é extraído em moeda corrente (BRL)?
- [ ] **2.3. Cálculo da Taxa de Êxito Substantivo:**
  - O sistema é capaz de computar $\frac{\text{Condenação}}{\text{Pedido}}$, quantificando o sucesso real das teses do autor e o sucesso de redução de passivo pelo réu?
- [ ] **2.4. Isolamento de Honorários Sucumbenciais e Multas:**
  - Percentuais de sucumbência (ex.: 10% a 20%, `CPC art. 85`) e multas diárias (astreintes, `CPC art. 537`) não são somados indevidamente ao valor indenizatório principal?

---

## Bloco 3: Soberania de Metadados e Grounding (DJEN)

- [ ] **3.1. Governança Soberana do Processo Principal:**
  - O número de processo principal é extraído dos metadados da publicação do DJEN (`numero_processo`) e validado pelo algoritmo Módulo 97 da Res. CNJ 65/2008?
  - Precedentes e processos paradigmas citados no texto são rotulados como `PROCESSO_CITADO`?
- [ ] **3.2. Vinculação Oficial de Polos e Partes:**
  - A identidade do Polo Ativo e do Polo Passivo é consumida diretamente de `destinatarios` do DJEN (evitando inversões em cabeçalhos confusos)?
- [ ] **3.3. Vinculação Determinística de Advogados e OAB:**
  - Os advogados e suas respectivas inscrições na OAB são mapeados a partir de `destinatarioadvogados` do DJEN, permitindo atribuir o resultado ao patrono correto sem alucinação?
- [ ] **3.4. Extração de Magistrados a partir do Texto:**
  - Como a API do DJEN não possui campo estruturado de juiz, o pipeline possui extrator textual para o bloco de assinatura no `ENCERRAMENTO`?

---

## Bloco 4: Dinâmica Recursal e Efeito Substitutivo

- [ ] **4.1. Registro do Polo Recorrente (`recorrente_polo`):**
  - Em acórdãos e decisões monocráticas recursais, o sistema registra se o recurso foi interposto pelo Autor (`A`) ou pelo Réu (`P`)?
- [ ] **4.2. Inversão de Polaridade Substantiva:**
  - O sistema implementa o efeito substitutivo (`CPC art. 1.008`):
    - `PROVIDO` interposto por `P` $\rightarrow$ Vitória do Réu (`P`).
    - `NAO_PROVIDO` interposto por `P` $\rightarrow$ Vitória do Autor (`A`).
- [ ] **4.3. Separação de Inadmissibilidade Recursal:**
  - Recursos não conhecidos por deserção, intempestividade ou falta de pressuposto formal (`NAO_CONHECIDO` / `PREJUDICADO`) são tratados no gate de admissibilidade e não como julgamento de mérito do pedido?

---

## Bloco 5: Rigor Estatístico e Amostragem

- [ ] **5.1. Prevenção de Vazamento Temporal (*Data Leakage*):**
  - Divisões de treino/validação/teste utilizam corte temporal cronológico, evitando que acórdãos futuros influenciem predições de decisões pretéritas?
- [ ] **5.2. Estratificação Multidimensional:**
  - Os benchmarks de avaliação são estratificados por Tribunal (`court`), Classe Processual (`classe_processual`) e Tipo de Decisão (`decision_type`)?
- [ ] **5.3. Relatório de Suporte por Classe:**
  - Métricas de F1 e Acurácia são reportadas com o volume de casos (suporte) e intervalos de confiança, prevenindo distorções em classes raras?

---

## Bloco 6: Engenharia de Desempenho e Eficiência Operacional

- [ ] **6.1. Alta Vazão em CPU Local:**
  - O pipeline processa mais de 200 documentos por segundo em 1 core x86_64, viabilizando o reprocessamento de milhões de decisões sem gargalos de infraestrutura?
- [ ] **6.2. Custo Zero de API em Inferência:**
  - A esteira de produção utiliza regex compilados, trie em linear-time e modelos locais leves (árvores de decisão, Naive Bayes, embeddings quantizados), sem dependência de APIs proprietárias pagas?
