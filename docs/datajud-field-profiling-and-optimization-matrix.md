# Profiling Estatístico, Estrutural e Matriz de Otimização do DataJud

> **Referência:** Issues [#1710](https://github.com/franklinbaldo/causaganha/issues/1710) e [#1711](https://github.com/franklinbaldo/causaganha/issues/1711#issuecomment-6801195268)  
> **Objetivo:** Isolar com rigor científico os ganhos decorrentes de **Modelagem de Dados** (eliminação de redundâncias, deduplicação de strings TPU e reconstrução de chaves) dos ganhos decorrentes do **Formato de Serialização** (JSON vs FlatBuffers vs Zstandard/Gzip).  
> **Corpus Real Analisado:** 68 documentos de 57 coleções de processos coletados da API Pública do DataJud abrangendo Justiça Estadual (`TJRO`, `TJMG`, `TJSP`, `TJPR`), Justiça Federal (`TRF4`) e Tribunal Superior (`STJ`).  
> **Script Reproduzível:** `scripts/datajud/field_profiler.py`  

---

## 1. Orçamento de Bytes por Campo (Onde Está o Peso Real do DataJud)

A medição em bytes de cada chave revela uma distribuição assimétrica extrema:

| Campo | Ocorrências | Tamanho Total (Bytes) | % do Tamanho do Documento | Diagnóstico Arquitetural |
| :--- | :--- | :--- | :--- | :--- |
| `_source.movimentos` | 68 docs (3.206 eventos) | **709.041 B** | **92,9%** | **O gargalo do acervo está aqui.** |
| `_source.assuntos` | 68 docs | 8.970 B | 1,2% | Pequeno, facilmente comprimível |
| `_source.orgaoJulgador` | 68 docs | 7.466 B | 1,0% | Nome do órgão é repetitivo |
| `_source.classe` | 68 docs | 4.393 B | 0,6% | Código + Nome da TPU |
| `_source.dataHoraUltimaAtualizacao` | 68 docs | 4.077 B | 0,5% | String ISO 8601 |
| `_source.formato` | 68 docs | 3.332 B | 0,4% | Quase estático ("Eletrônico") |
| `_source.@timestamp` | 68 docs | 3.063 B | 0,4% | Metadado de ingestão do cluster |
| `_source.sistema` | 68 docs | 3.050 B | 0,4% | Código + Nome do sistema judicial |
| `_source.numeroProcesso` | 68 docs | 2.856 B | 0,4% | String 20 dígitos |
| `_id` | 68 docs | 2.652 B | 0,3% | 100% derivável (redundante) |
| **Total Analisado** | **68 documentos** | **763.010 B** | **100,0%** | - |

> [!IMPORTANT]
> **Conclusão Orçamentária:**  
> O array de movimentações processuais consome **92,9% de todos os bytes do acervo**. Otimizar metadados de capa sem tocar nos movimentos gera ganhos inferiores a 7%. Qualquer estratégia de alta compressão precisa atacar a repetição de strings nos movimentos.

---

## 2. Derivabilidade e Redundância do `_id`

Analisamos se o identificador do Elasticsearch `_id` pode ser derivado sem armazenamento explícito:

$$\texttt{\_id} = \texttt{\{TRIBUNAL\}\_\{GRAU\}\_\{NUMEROPROCESSO\}}$$

- **Total de documentos testados:** 68
- **Documentos em estrita conformidade:** 68 (**100,0%**)
- **Exceções encontradas:** 0

### Regra de Reconstrução sem Perda (Lossless Contract):
1. **Armazenamento:** O campo `_id` não é serializado se coincidir com `f"{tribunal}_{grau}_{numeroProcesso}"`.
2. **Fallback para Exceções:** Caso um registro futuro possua formato divergente, o valor literal é preservado no campo opcional `id_excecao`.
3. **Consumidor:** O decodificador reconstrói o `_id` a partir da fórmula canônica, retornando exatamente o valor original.

---

## 3. Faixas Numéricas Reais e Tipos Mínimos Seguros

Mapeamento de valores mínimos e máximos para dimensionar tipos binários no FlatBuffers sem risco de overflow:

| Campo | Mínimo | Máximo | Valores Únicos | Tipo Anterior | Tipo Mínimo Seguro |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `classe.codigo` | 7 | 14.695 | 24 | `long` (64-bit) | **`ushort` (16-bit)** |
| `movimento.codigo` | 22 | 15.621 | 118 | `long` (64-bit) | **`ushort` (16-bit)** |
| `complemento.codigo` | 2 | 36 | 14 | `long` (64-bit) | **`ubyte` (8-bit)** |
| `sistema.codigo` | -1 | 4 | 5 | `long` (64-bit) | **`byte` (8-bit com sinal)** |
| `formato.codigo` | 1 | 1 | 1 | `long` (64-bit) | **`ubyte` (8-bit)** |
| `nivelSigilo` | 0 | 0 | 1 | `int` (32-bit) | **`ubyte` (8-bit)** |
| `orgaoJulgador.codigo` | 3.349 | 93.649 | 42 | `long` (64-bit) | **`uint` (32-bit)** |
| `orgaoJulgador.codigoMunicipioIBGE`| 1.100.049 | 5.300.108 | 9 | `long` (64-bit) | **`uint` (32-bit)** |

> [!NOTE]
> Observou-se `sistema.codigo = -1` em tribunais que não identificam o sistema de origem. Portanto, campos de código devem aceitar tipos com sinal (`byte`/`short`) para preservar sentinelas de erro.

---

## 4. Matriz Comparativa Abrangente: JSON vs FlatBuffers vs Parquet vs Protocol Buffers

Para responder com precisão científica e estrita paridade de conteúdo à pergunta do experimento:
$$\text{"Qual formato atinge a menor pegada de armazenamento reversível e a melhor viabilidade de consulta estática?"}$$

Submetemos o acervo aos mesmos níveis de modelagem, com a garantia formal e testada em suite automatizada de que:
$$\operatorname{decode}(\operatorname{encode}(D)) == D \quad (\forall D \in \text{Corpus})$$

O vocabulário reversível compartilhado contém **394 termos únicos** e o catálogo de templates TPU (Estratégia B) contém **278 tipos estruturais estáveis**:

| Formato / Variante | Tamanho Total (Bytes) | Redução s/ Bruto | Tempo Enc | Tempo Dec | Características de Acesso |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. JSON Bruto Original** | 763.146 B | 0,0% (Base) | 6,1 ms | 6,1 ms | Texto puro não comprimido |
| **2. FlatBuffers v1 (Esquema Canônico)** | 728.696 B | 4,5% | 123,9 ms | **1,2 ms** | Zero-copy com overhead de vtables e padding |
| **3. Protocol Buffers Canônico (Sem Compressão)** | **385.762 B** | **49,5%** | **25,4 ms** | **1,2 ms** | Varints (LEB128) sem padding de alinhamento |
| **4. JSON.gz (nível 6 padrão)** | 90.909 B | 88,1% | 8,1 ms | 6,5 ms | Compactação padrão de mercado |
| **5. FlatBuffers Híbrido (Capa FB + Zstd)** | 92.016 B | 87,9% | 13,8 ms | 1,1 ms | Capa O(1) em FB + movimentos em Zstd |
| **6. Protocol Buffers Canônico + Zstandard** | **83.047 B** | **89,1%** | 1,9 ms | 2,7 ms | Supera o JSON.gz padrão |
| **7. JSON Tokenizado Lossless + Zstandard** | 58.767 B | 92,3% | 1,6 ms | 6,0 ms | Zstd nível 3 + vocabulário compartilhado |
| **8. Parquet Nativo Aninhado + Zstandard** | 47.464 B | 93,8% | - | 4,5 ms | Colunar com Dictionary Encoding e Bit-Packing |
| **9. Protocol Buffers Compacto + Zstd (Estratégia B)** | **41.272 B** | **94,6%** | **1,8 ms** | **1,4 ms** | **Menor marca absoluta (Campeão em densidade)** |

### O que os Dados Rigorosamente Comprovam:

1. **Protocol Buffers é 47% Menor que FlatBuffers sem Compressão:**
   - O Protobuf Canônico sem Zstd ocupa **385 KB**, contra **728 KB** do FlatBuffers v1.
   - O uso de **varints (LEB128)** permite que inteiros pequenos (códigos TPU, níveis de sigilo, IDs) ocupem de 1 a 2 bytes em vez de 8 bytes fixos, sem os bytes vazios de alinhamento (*zero-padding*) exigidos pelo FlatBuffers.
2. **Protobuf Compacto + Zstandard é o Campeão Absoluto (41,2 KB):**
   - Ao adotar a **Estratégia B** (templates TPU como IDs no Protobuf e complementos dinâmicos em arrays), o acervo cai para **41.272 bytes** (~720 bytes por processo completo com todos os graus e instâncias).
   - Supera o Parquet (**47,4 KB**) e o JSON Tokenizado (**58,7 KB**).
3. **Parquet vs Protobuf para a Web Estática no Internet Archive:**
   - **Parquet (Colunar):** Exige runtime de 30 MB (DuckDB-WASM) no navegador e fragmenta os dados de um mesmo processo em múltiplos chunks colunares distantes no arquivo.
   - **Protobuf (Documental Contíguo):** O processo inteiro é um bloco sequencial contíguo de bytes. Permite o resgate via **1 único HTTP Range request** e decodifica em **1,4 ms** com bibliotecas JS levíssimas (~15 KB).

---

## 5. Recomendações Arquiteturais Finais

1. **Armazenamento de Processos no Internet Archive:**
   - Shards empacotados em **`ZIP_STORED`** contendo documentos contíguos em **Protocol Buffers Compacto + Zstandard (`.pb.zst`)**.
   - Menor tamanho de rede (**41 KB total / ~720 B por processo**) e resgate em 1 requisição HTTP Range.
2. **Índice Público de Roteamento:**
   - Micro-índices estáticos particionados por Tribunal e Ano (`indexes/{J.TR}_{ANO}.json` ou `.parquet`), cacheados no IndexedDB do navegador.
3. **Catálogo de Andamentos:**
   - Tabela estática de templates TPU servida junto aos assets do site estático para reconstrução instantânea da linha do tempo.
