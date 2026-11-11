## Resolução Completa dos Pontos da Revisão (Commit `dfb1067c`)

Todos os pontos levantados na revisão (P0 e P1) foram corrigidos e validados com testes automatizados:

---

### 1. P0 — Implementação Canônica do Codec FlatBuffers (`processo.fbs`)
- **Implementado em:** [`src/datajud/schema/flatbuffers_codec.py`](src/datajud/schema/flatbuffers_codec.py)
- **Conformidade Estrita:** O codec implementa campo a campo todas as tabelas e vetores de `src/datajud/schema/processo.fbs`:
  - `DocumentoDataJud` (todas as 18 posições tipadas com vtables correspondentes).
  - Tabelas aninhadas: `CodigoNome`, `OrgaoJulgador`, `ComplementoTabelado`, `Movimento`.
  - Vetores: `assuntos: [CodigoNome]`, `movimentos: [Movimento]`, `complementosTabelados: [ComplementoTabelado]`.
  - Preservação de campos desconhecidos em `campos_desconhecidos_json` (slot 16).
  - Preservação do payload bruto original compactado em `payload_original_bruto_gz` (slot 17).
- **Projeção Seletiva Real:** Adicionado método `decode_collection(buf, mode='capa')` que lê instantaneamente os metadados da capa sem carregar o vetor volumoso de movimentos.

---

### 2. P0 — Amostragem e Prova Efetiva de Busca Multíndice Pareada
- **Implementado em:** [`scripts/datajud/cross_match_multindex.py`](scripts/datajud/cross_match_multindex.py)
- **Fixture Comprovada:** [`fixtures/datajud_sample/pares_multindice_comprovados.json`](fixtures/datajud_sample/pares_multindice_comprovados.json)
- **Resultados Empíricos Comprovados (Consultas Reais na API Pública do DataJud):**
  - **CNJ `5021985-14.2025.4.04.0000`:** Encontrado simultaneamente em `api_publica_stj` (SUP) e `api_publica_trf4` (G2).
  - **CNJ `5039675-56.2025.4.04.0000`:** Encontrado simultaneamente em `api_publica_stj` (SUP) e `api_publica_trf4` (G2).
  - **CNJ `0088058-55.2023.8.16.0000`:** Encontrado simultaneamente em `api_publica_stj` (SUP) e `api_publica_tjpr` (G2).
  - **CNJ `0001311-51.2024.8.13.0647`:** Encontrado simultaneamente em `api_publica_stj` (1 doc SUP) e `api_publica_tjmg` (**2 docs: G1 e G2**). Total: **3 documentos em 2 índices distintos para o mesmo CNJ**.
  - **CNJ `0012397-92.2012.8.26.0577`:** Encontrado simultaneamente em `api_publica_stj` (1 doc SUP) e `api_publica_tjsp` (**2 docs: G1 e G2**). Total: **3 documentos em 2 índices distintos para o mesmo CNJ**.

---

### 3. P0 — Teste de Coleção e Cardinalidade Completo
- **Atualizado em:** [`tests/datajud/test_schema_roundtrip.py`](tests/datajud/test_schema_roundtrip.py)
- O teste `test_multigrau_e_multindice_cardinality_all_documents` agora itera e recupera **todos os documentos de cada coleção** ($0 \dots N-1$), validando a identidade de proveniência por tupla `(index, id)` em todos os graus (`G1`, `G2`, `SUP`).
- Adicionado `test_pares_multindice_comprovados_existencia` que valida formalmente a ausência de colisão de índices e a presença dos mesmos CNJs em múltiplos tribunais.

---

### 4. P1 — Anonimização Contextual de PII
- Substituída a checagem por chave isolada pela função hierárquica `sanitizar_contextual` (que inspeciona o caminho na árvore: `partes`, `poloAtivo`, `poloPassivo`, `advogados`).
- Adicionado teste automatizado `test_auditoria_contextual_pii_fixtures` que audita todas as fixtures em disco.

---

### 5. P1 — Benchmark Simétrico e Rigoroso
- **Atualizado em:** [`scripts/datajud/benchmark_formats.py`](scripts/datajud/benchmark_formats.py)
- A desserialização agora recupera **100% dos documentos de todas as coleções** em todos os formatos:

| Formato | Tamanho Total | Encoding (ms) | Decoding Completo (ms) | Projeção Capa (ms) | Ratio vs Bruto |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **JSON Canônico Bruto** | 765.825 B | 5,51 ms | 5,61 ms | - | 1.000x |
| **JSON.gz (Nível 6)** | 91.482 B | 6,81 ms | 7,00 ms | - | **0,119x** |
| **FlatBuffers (Tipado .fbs)** | 728.696 B | 115,15 ms | 64,48 ms | **2,34 ms** | 0,952x |
| **Parquet (Zstd + Gz)** | 114.672 B | 122,38 ms | 96,82 ms | - | 0,150x |

*Destaque:* A projeção seletiva da capa no FlatBuffers (ler apenas capa sem decodificar movimentos) levou apenas **2,34 ms**, demonstrando a vantagem de acesso aleatório via vtables.

---

### 6. P1 — Lint & Validação
- Executado `ruff format` e `ruff check` (0 erros).
- Executados os testes de regressão: **128 testes passando**.
