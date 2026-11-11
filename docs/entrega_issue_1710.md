## Entrega da Investigação Empírica do Modelo Real Multíndice (#1710)

Conforme estabelecido pelo proprietário, executamos o inventário empírico completo utilizando chamadas reais à API Pública do DataJud, sem pressupor modelos de deduplicação ou formatos físicos pré-concebidos.

Os artefatos versionados no repositório são:
- **Relatório Completo de Inventário:** [`docs/datajud-multindex-inventory.md`](docs/datajud-multindex-inventory.md)
- **Fixtures Reais Coletadas e Anonimizadas:** `fixtures/datajud_sample/inventario_datajud_bruto.json`
- **Schema FlatBuffers com Zero-Loss:** `src/datajud/schema/processo.fbs`
- **Script de Coleta & Descoberta Multíndice:** `scripts/datajud/inventory_multindex.py`
- **Benchmark Comparativo Reproduzível:** `scripts/datajud/benchmark_formats.py`
- **Testes de Regressão & Roundtrip Estrutural:** `tests/datajud/test_schema_roundtrip.py` (3/3 testes passando)

---

### 1. Principais Evidências Empíricas Descobertas

1. **Restrições de Rede do Gateway do CNJ:**
   - O endpoint do CNJ **não permite** consultas wildcard (`POST /api_publica_*/_search`) nem índices múltiplos na mesma URL (`/api_publica_tjro,api_publica_stj/_search`). O gateway gera timeout. Todas as consultas na origem devem ser tribunal a tribunal.
2. **O CNJ NÃO é Chave Única de Documento:**
   - **Múltiplos Graus no Mesmo Índice (TJRO):** Para o CNJ `7004981-27.2025.8.22.0021`, o índice `api_publica_tjro` retorna **2 documentos distintos**:
     - `_id: TJRO_G1_70049812720258220021` (1ª Instância - Procedimento Comum Cível)
     - `_id: TJRO_G2_70049812720258220021` (2ª Instância - Apelação Cível)
     - Cada um possui seu próprio órgão julgador, sua classe e seu histórico cronológico de movimentos. Sobrescrever pelo CNJ destruiria a primeira instância!
   - **Processos Estaduais e Trabalhistas nos Tribunais Superiores:** Nos índices `api_publica_stj` e `api_publica_tst`, os processos mantêm o número CNJ de origem (ex: `8.13` para TJMG, `5.03` para TRT3), mas recebem IDs com prefixo `STJ_SUP_` e `TST_SUP_`.
3. **Estrutura Determinística do `_id`:**
   - Em 100% dos 82 hits analisados, `_id == f"{tribunal}_{grau}_{numeroProcesso}"`.
   - Valores de grau observados: `G1`, `G2`, `JE` (Juizado Especial), `TR` (Turma Recursal) e `SUP` (Instância Superior).

---

### 2. Prova de Roundtrip FlatBuffers com Zero Perda de Dados

Criamos o esquema `ProcessoCNJCollection` em `src/datajud/schema/processo.fbs`, onde cada CNJ agrega uma lista de documentos (`DocumentoDataJud`).

Para assegurar **fidelidade absoluta e imunidade à evolução de schema do CNJ**:
- Cada documento inclui `campos_desconhecidos_json` e `payload_original_bruto_gz`.
- O teste `tests/datajud/test_schema_roundtrip.py` validou que 100% dos documentos serializados e recuperados são **idênticos bit-a-bit** ao `_source`, `_id` e `_index` originais retornados pelo DataJud.

---

### 3. Resultados Medidos de Formatos (Benchmark)

Sobre a amostra de processos reais agrupados por CNJ:

| Formato | Tamanho Total | Encoding (ms) | Decoding (ms) | Ratio vs JSON | Avaliação |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **JSON Canônico Bruto** | 563.535 B | 4,06 ms | 3,84 ms | 1.000x | Linha de base |
| **JSON.gz (Nível 6)** | 73.650 B | 5,49 ms | 4,72 ms | **0,131x** | **Menor tamanho e leitura nativa simples** |
| **FlatBuffers + Zero-Loss** | 89.656 B | 15,68 ms | 4,64 ms | **0,159x** | Excelente para projeção seletiva sem parsear movimentos |
| **Parquet (Zstd + Gz)** | 93.521 B | 83,06 ms | 91,28 ms | **0,166x** | Ideal para índice analítico da capa, lento para documento integral |

---

### 4. Status dos Critérios de Aceite da Issue #1710

- [x] Evidência real para CNJ presente em múltiplos documentos e múltiplos graus/índices (`fixtures/datajud_sample/`).
- [x] Inventário do shape real, campos e tipos, proveniência e cardinalidade sem expor dados sigilosos (`docs/datajud-multindex-inventory.md`).
- [x] Consulta que recebe **só CNJ** e lista todos os registros encontrados com proveniência e limites de cobertura.
- [x] `_id` tratado como identificador de origem (`{tribunal}_{grau}_{cnj}`), sem assumir que seja chave única do CNJ.
- [x] Protótipo FlatBuffers de ida e volta sem perda demonstrado e com medição comparativa.
- [x] Recomendações formalizadas para as issues #1704 a #1709 e PR #1703.
