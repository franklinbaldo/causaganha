### Ajustes de Protocolo Aprovados para o Benchmark (#1711)

Em conformidade com a orientação da coordenação, incorporamos os seguintes refinamentos mandatários antes da execução dos testes comparativos:

1. **Critério Decisivo de Completude por CNJ (Ground Truth do DataJud):**
   - Construir previamente um conjunto de referência de verdade absoluta (*ground truth*) gerado diretamente a partir das respostas brutas coletadas da API pública do DataJud.
   - **Condição de eliminação:** Qualquer alternativa avaliada (ES snapshot, Tantivy, ZIP + FlatBuffers, JSON.gz ou Híbrido) deve recuperar **100% dos mesmos registros** para cada CNJ consultado. Nenhuma perda ou truncamento de documento/grau será tolerada.

2. **Diferenciação Estrita de Custo Real de Consulta (Cold vs Warm):**
   - **Custo Frio (Cold):** Mensuração do overhead real de rede para resolver e recuperar registros sem cache local (tráfego de requisições ao Internet Archive via HTTP Range Requests, download de chunks ou descompactação transparente).
   - **Custo Quente (Warm):** Desempenho e latência de consulta quando shards, segmentos ou índices já se encontram em cache local ou em memória.

3. **Verificação Experimental de Compatibilidade de Infraestrutura:**
   - Não aceitar promessas de documentação técnica como fatos consumados. Validar na prática com chamadas reais:
     - Comportamento de *HTTP Range Requests* e *Transparent Unzip* no Internet Archive sob diferentes volumes e padrões de concorrência.
     - Viabilidade de execução de *Tantivy-WASM* em ambiente de execução leve / client-side.
     - Restauração e montagem efetiva de snapshots remotos sob o endpoint do IA.

4. **Nuance de Licenciamento & Distribuição:**
   - Qualificar a análise de *Searchable Snapshots / Remote Store* atrelando-a especificamente à versão e distribuição utilizadas (ex.: Elasticsearch oficial v7.x / v8.x sob SSPL/ELv2 vs OpenSearch 2.x com Apache 2.0 e capacidade de *Remote Store*).

---
**Status do Spike:**
O desenho do protocolo e os critérios de aceite estão formalizados. A execução quantitativa aguarda a entrega da amostra representativa e caracterização do modelo real na **#1710**.
