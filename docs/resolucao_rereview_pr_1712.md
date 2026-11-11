## Atualização Técnica do Spike: Redesenho FlatBuffers Híbrido, Leitor Oficial `flatc` e Zstandard (Commit `1cff56fb`)

Em resposta direta ao re-review e à análise de otimização de esquemas, implementamos e validamos as seguintes melhorias técnicas:

---

### 1. Eliminação da Duplicação Integral e Esquema Híbrido (Otimização do `.fbs`)
- **Diagnóstico Confirmado:** O benchmark anterior registrava 728 KB no FlatBuffers porque cada documento duplicava integralmente o JSON bruto comprimido em `payload_original_bruto_gz`.
- **Novo Esquema Compacto:** [`src/datajud/schema/processo_compact.fbs`](src/datajud/schema/processo_compact.fbs) e codec [`src/datajud/schema/compact_codec.py`](src/datajud/schema/compact_codec.py):
  - **Capa Tipada Plana O(1):** Identificadores (`_index`, `_id`, `tribunal`, `grau`), códigos de TPU (`classe_codigo`, `orgao_codigo`, `sistema_codigo`) e datas em timestamps numéricos (epoch ms) residem na vtable do FlatBuffers.
  - **Bloco de Movimentos em Zstandard:** O vetor volumoso de movimentos é serializado e compactado em bloco via Zstd (nível 3).
  - **Sem Duplicação Redundante:** O payload deixa de ser duplicado.

---

### 2. Validação Independente com Classes Geradas Oficialmente pelo `flatc`
- Baixado e versionado o compilador oficial Google `flatc` (v25.12.19).
- Geradas as classes canônicas Python em `src/datajud/schema/generated/`.
- Criado o teste [`test_validacao_independente_classes_geradas_flatc`](tests/datajud/test_schema_roundtrip.py) que lê os buffers serializados utilizando **exclusivamente a classe `ProcessoCNJCollection.GetRootAs(buf, 0)`** gerada pelo `flatc`, eliminando o risco de erro simétrico de codec manual.

---

### 3. Benchmark Comparativo Multi-Variante Atualizado (68 documentos / 57 coleções)

Com a eliminação da redundância e adição do Zstandard sugerido pelo proprietário:

| Formato | Tamanho Total | Encoding (ms) | Decoding Integral (ms) | Projeção Capa (ms) | Ratio vs Bruto |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. JSON Canônico Bruto** | 765.825 B | 5,38 ms | 5,65 ms | - | 1.000x |
| **2. JSON.gz (Nível 6)** | 91.482 B | 7,20 ms | 7,22 ms | - | **0,119x** |
| **3. JSON.zst (Zstandard L3)** | 94.942 B | **1,92 ms** | **5,51 ms** | - | **0,124x** |
| **4. FlatBuffers v1 (c/ cópia Gz)** | 728.696 B | 124,39 ms | 7,23 ms | 2,34 ms | 0,952x |
| **5. FlatBuffers Híbrido (Capa FB + Zstd)** | **92.016 B** | 11,58 ms | 6,73 ms | **1,07 ms** | **0,120x** |
| **6. Parquet (Capa + Payload Gz)** | 110.439 B | 93,66 ms | 118,16 ms | - | 0,144x |

#### Conclusões Chave do Benchmark:
1. **O FlatBuffers Híbrido iguala o tamanho do JSON.gz (92,0 KB vs 91,4 KB — redução de 88,6%)**, comprovando que FlatBuffers não é intrinsecamente volumoso quando se elimina a duplicação bruta.
2. **Acesso à Capa 7x Mais Rápido:** A leitura seletiva da capa no FlatBuffers Híbrido levou apenas **1,07 ms (15,7 microssegundos por documento)** sem precisar descomprimir ou parsear o array de movimentos.
3. **Zstandard:** Reduziu o tempo de compressão em 3,7x comparado ao Gzip (1,92 ms vs 7,20 ms).
4. **Dupla Compressão em ZIPs:** Se os arquivos individuais dentro do ZIP forem `.json.gz`, `.json.zst` ou `.fb`, o arquivo ZIP deve utilizar `ZIP_STORED` (sem compressão no ZIP), viabilizando leitura transparente pelo Internet Archive com offsets exatos.

---

### 4. Status de CI & Testes
- **Testes (TJRO):** **Aprovado (129 testes passando)**.
- **Lint:** **Aprovado** (`ruff check`, `ruff format` e `vulture` limpos).
