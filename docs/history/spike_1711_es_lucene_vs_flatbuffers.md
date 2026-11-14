## Análise Técnica e Plano de Execução do Spike (#1711)

Em alinhamento direto com a diretriz de **não antecipar decisões físicas nem esquemas de serialização sem evidência empírica** (#1710), este comentário formaliza a viabilidade técnica, os trade-offs arquiteturais e o protocolo de experimentação para comparar **índices de busca (Elasticsearch/Lucene/Tantivy)** contra **ZIPs imutáveis + FlatBuffers / JSON.gz / Parquet** distribuídos no Internet Archive (IA).

---

### 1. Desconstrução Técnica das Alternativas

#### Alternativa 1: Snapshots Oficiais do Elasticsearch no Internet Archive
- **Mecanismo:** O Elasticsearch grava snapshots atômicos de índices em um repositório (`_snapshot/<repo>/<snapshot>`). Os arquivos gerados são os segmentos Lucene imutáveis (`*.cfs`, `*.si`) acrescidos de metadados de commit (`index-*.json`, `indices/<uuid>/...`).
- **Publicação no IA:** O Internet Archive expõe endpoint S3 (`s3.us.archive.org`). O Elasticsearch suporta plugin `repository-s3` (com chaves S3 do IA) ou repositório `repository-url` (read-only sobre HTTPS).
- **Consumo:** O consumidor **precisa rodar uma instância própria do Elasticsearch** (JVM, 2GB–4GB RAM de heap mínimo) e executar a chamada `POST /_snapshot/<repo>/<snapshot>/_restore`.
- **Veredito preliminar:** Excelente para quem já opera cluster Elasticsearch e deseja restauração idêntica; barreira de entrada alta para consumidores leves, CLIs efêmeros, bibliotecas de consulta ou aplicações client-side/WASM.

#### Alternativa 2: Searchable Snapshots / Repositório Remoto Read-Only
- **Mecanismo:** O nó do cluster monta os índices diretamente do repositório remoto lendo segmentos sob demanda (bloqueando dados em cache local).
- **Restrições de Licença e API:**
  1. *Licenciamento:* No Elasticsearch (Elastic ELv2/SSPL), *Searchable Snapshots* é recurso exclusivo de licença comercial (Enterprise/Platinum). No ecossistema OpenSearch 2.x, há suporte para *Remote Store*, mas ainda exige cluster ativo.
  2. *Compatibilidade IA HTTP:* O Internet Archive não possui garantias de SLA para leituras aleatórias concorrentes via S3/HTTP necessárias para manter um motor de busca transacional pesquisando sem latência proibitiva.
- **Veredito preliminar:** Inviável como padrão público aberto e gratuito devido a amarras de licenciamento e características de latência do IA.

#### Alternativa 3: Índice Lucene Embarcado / Tantivy (Zero-Server Search)
- **Mecanismo:** Em vez de manter um daemon Elasticsearch, gera-se diretamente a estrutura de arquivos de um índice invertido.
  - *Opção Java:* Apache Lucene puro (`org.apache.lucene`), empacotado e lido localmente via leitor embarcado.
  - *Opção Rust/Python/WASM:* **Tantivy** (motor de busca full-text no estilo Lucene, em Rust, com bindings Python e compilação para WebAssembly).
- **Publicação e Consumo no IA:** Shards imutáveis contendo a pasta de índice (segmentos, dicionário de termos, postings list). O consumidor pode:
  - Baixar o shard de índice localmente (tamanho tipicamente pequeno quando apenas chaves são indexadas) e abrir diretamente na sua aplicação sem subir nenhum serviço.
- **Veredito preliminar:** Muito promissora para cenários onde a busca por texto livre (ex.: inteiro teor de movimentos, partes, assuntos) é mandatória e não se quer impor servidor ao consumidor.

#### Alternativa 4: ZIPs Imutáveis + FlatBuffers / JSON.gz (Padrão IA Nativo)
- **Mecanismo:** Consolidação baseada na experiência do projeto `franklinbaldo/ficha`:
  - **Armazenamento de Dados:** Shards/ZIPs diários ou particionados por tribunal publicados no item do IA (`{tribunal}_{data}.zip`).
  - **Transparent Unzip do IA:** O Internet Archive expõe descompactação transparente via HTTP: `https://archive.org/download/{item}/{arquivo.zip}/{caminho_interno}`. Permite ler o documento exato do processo sem baixar o arquivo ZIP inteiro.
  - **Índice de Resolução:** Um arquivo Parquet ou DuckDB particionado leve (`indice_processos_{tribunal}.parquet`) que indexa `cnj -> [ {item, zip, path, data_atualizacao, grau, index_origem} ]`.
- **Consumo:** Zero-server e zero-instalação de serviços pesados. Um script em Python, uma query DuckDB ou DuckDB-WASM no navegador faz HTTP Range Request no índice Parquet e depois busca os bytes do processo específico.

#### Alternativa 5: Híbrido (Índice Invertido para Descoberta + FlatBuffers/JSON para Payload)
- **Mecanismo:** Desacoplar indexação de armazenamento denso:
  - **Camada de Busca:** Índice Lucene/Tantivy/DuckDB contendo apenas chaves de pesquisa (`numeroProcesso`, `classe`, `assunto`, `tribunal`, `dataAjuizamento`, `poloAtivo`, `poloPassivo`) apontando para um URI imutável do documento.
  - **Camada de Armazenamento:** Documento íntegro (capa, partes, histórico completo de movimentos, envelope raw `_source` e campos desconhecidos) serializado em FlatBuffers ou JSON.gz dentro de ZIPs imutáveis no IA.
- **Vantagem:** Evita inflar o índice de busca com campos longos e textos repetidos (evita custo do `_source` armazenado em Lucene), mantendo o índice ultra-leve e o documento 100% preservado.

---

### 2. Matriz Comparativa de Arquitetura

| Critério | (1) ES Snapshot | (2) Searchable Snapshot | (3) Lucene / Tantivy Embarcado | (4) ZIP + FlatBuffers / JSON.gz | (5) Híbrido (Busca + Shard ZIP) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Consulta por CNJ único** | Nativa (`term`) | Nativa (`term`) | Nativa (`term`) | Via Índice Parquet / DuckDB | Via Índice de Busca |
| **Múltiplos registros por CNJ** | 1 documento por registro | 1 documento por registro | 1 documento por registro | Lista de ponteiros no índice | Lista de ponteiros no índice |
| **Buscas secundárias (assunto, classe, partes)** | Excelente | Excelente | Excelente | Requer colunas no Parquet | Excelente |
| **Necessidade de servidor / daemon** | **Sim** (Elasticsearch JVM) | **Sim** (Elasticsearch JVM) | **Não** (Embarcado na app / WASM) | **Não** (Zero-server / HTTP Range) | **Não** (Embarcado) |
| **Acesso Web / WASM / Client-side** | Impossível sem backend | Impossível sem backend | Possível (Tantivy-WASM) | Excelente (DuckDB-WASM + IA Unzip) | Excelente |
| **Aproveitamento de features do IA** | Parcial (repositório S3) | Frágil (latência HTTP) | Médio (download de segmento) | **Total** (Transparent Unzip + Range) | **Total** |
| **Amplificação de escrita incremental** | Segmentos imutáveis | Segmentos imutáveis | Segmentos imutáveis | Shard diário imutável | Shard diário + delta de índice |
| **Preservação de campos desconhecidos** | Sim (documento bruto) | Sim (documento bruto) | Depende do schema indexado | Sim (se raw payload preservado) | Sim (payload bruto intocado) |
| **Barreira de Licenciamento** | Open / SSPL | Comercial / Paga | Apache 2.0 / MIT | Domínio Público / Open Source | Apache 2.0 / MIT |

---

### 3. Protocolo de Experimentação Empírica (Benchmark Unificado)

Para garantir comparabilidade rigorosa, o spike #1711 será executado seguindo este roteiro:

1. **Amostra Comum (#1710):** Utilizar o mesmo conjunto de dados reais levantados em #1710 (amostra de 5.000 a 10.000 documentos do DataJud contemplando CNJs com múltiplos graus, instâncias no STJ/TRF e atualizações históricas).
2. **Contrato de Consulta Padronizado:**
   ```python
   def consultar_processo(cnj: str) -> list[DocumentoProcessual]:
       """Retorna TODOS os registros do CNJ na amostra, com proveniência completa."""
       ...
   ```
3. **Métricas a Coletar em Cada Formato:**
   - **Tamanho Total em Disco / IA:** Bytes totais do conjunto gerado (índices + dados brutos).
   - **Latência Cold / Warm:** Tempo para resolver um CNJ sem cache prévio e com cache local.
   - **Footprint de Memória (RAM):** Consumo de memória do processo cliente durante a resolução do CNJ.
   - **Tráfego de Rede (Egress):** Quantidade de bytes trafegados do IA para responder a uma consulta de 1 único CNJ.
   - **Fidelidade Documental:** Verificação de integridade bit-a-bit contra o `_source` original do DataJud (nenhum campo omitido ou tipado incorretamente).

---

### 4. Próximos Passos Imediatos

1. Concluir a amostragem empírica de múltiplos índices em #1710.
2. Com a massa de testes de #1710 versionada em fixture, implementar os 4 protótipos de leitura/escrita em scripts de spike dedicados:
   - `spikes/datajud/benchmark_es_snapshot.py`
   - `spikes/datajud/benchmark_tantivy_embedded.py`
   - `spikes/datajud/benchmark_parquet_zip_flatbuffers.py`
   - `spikes/datajud/benchmark_hybrid.py`
3. Publicar relatório quantitativo no encerramento de #1711 com recomendação definitiva respaldada por números.
