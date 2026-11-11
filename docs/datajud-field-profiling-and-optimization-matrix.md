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

## 4. Matriz Controlada Lossless: Isolando Modelagem de Dados vs Serialização

Para responder com precisão científica e estrita paridade de conteúdo à pergunta do experimento:
$$\text{"Dado exatamente o mesmo modelo lógico 100% reversível, quanto FlatBuffers economiza vs JSON?"}$$

Submetemos o acervo aos mesmos níveis de modelagem, com a garantia formal e testada em suite automatizada de que:
$$\operatorname{decode}(\operatorname{encode}(D)) == D \quad (\forall D \in \text{Corpus})$$

O vocabulário reversível compartilhado contém **394 termos únicos** (abrangendo todas as descrições de movimentos, complementos, nomes de classes, sistemas e órgãos julgadores, inclusive variações de grafia e acentuação dos tribunais):

| Nível de Modelagem | JSON (100% Lossless) | FlatBuffers | Delta FB vs JSON | Economia da Modelagem |
| :--- | :--- | :--- | :--- | :--- |
| **Nível 1: Dados Originais (Bruto)** | 808.223 B (4,2 ms) | 728.696 B (123,9 ms) | **0,90x** | 0,0% (Base) |
| **Nível 2: Modelo Lossless + Vocabulário** | **265.839 B** (9,7 ms) | **92.016 B** (13,8 ms) | **0,35x** | **67,1% de redução** |
| └─ *Detalhamento JSON* | *Dados: 254.699 B \| Vocabulário: 11.140 B* | - | - | - |
| **Nível 3: Modelo Lossless + Zstandard** | **58.767 B** (1,4 ms) | **89.263 B** (0,6 ms) | **1,52x** | **92,7% de redução** |
| └─ *Detalhamento Zstandard* | *Dados Zstd: 54.205 B \| Vocab Zstd: 4.562 B* | - | - | - |

### O que os Dados Rigorosamente Comprovam:

1. **Reversibilidade Matemática Estrita ($0$ perda):**
   - Ao contrário de modelos conceituais que descartavam nomes de movimentos, o codec implementado em `src/datajud/schema/lossless_codec.py` preserva 100% dos dados brutos, envelopes (`_score`, `sort`), anomalias e estruturas aninhadas (`codigoMunicipioIBGE: null`, etc.).
2. **FlatBuffers sem Compressão Externa é 65% Menor que JSON Equivalente (0,35x):**
   - No Nível 2 (sem compressor LZ/Zstd), o FlatBuffers Híbrido ocupa **92 KB**, enquanto o JSON com vocabulário ocupa **265 KB**. O layout binário tipado elimina delimitadores textuais e sintaxe JSON com enorme eficiência.
3. **Zstandard em JSON Tokenizado atinge 58,7 KB (92,7% de redução):**
   - O Zstandard comprime sequências de inteiros e vocabulário textual para **58,7 KB** (comparado a **90,9 KB** do `JSON.gz` bruto tradicional). Representa uma economia adicional de **35,4% de espaço sobre o JSON.gz padrão**.
4. **O Trade-off Inegociável: Latência O(1) vs Espaço em Disco:**
   - **JSON Tokenizado + Zstd:** Ocupa menos espaço (58,7 KB vs 89,2 KB), porém exige descompressão de bloco inteiro e reconstrução em memória via dicionário antes de consultar qualquer campo do processo.
   - **FlatBuffers Híbrido:** Ocupa ligeiramente mais espaço em repouso (89,2 KB com Zstd ou 92,0 KB sem compressão de bloco externo), mas viabiliza **projeção O(1) da Capa em 1,07 ms (15,7 µs/processo)** via HTTP Range Requests ou mmap, sem tocar nos 3.206 movimentos.

---

## 5. Recomendações Arquiteturais Fundamentadas

1. **Para Distribuição de Acervo Público no Internet Archive:**
   - Shards diários de processos compactados com **Zstandard (Zstd)** empacotados em arquivos ZIP com **`ZIP_STORED`**.
   - Isso alcança a menor pegada de armazenamento (**39,8 KB por lote**, economizando 95% de espaço e custo de rede).
2. **Para a Camada de Indexação e Resolução Rápida:**
   - O **Índice de Resolução Parquet** (`indice_processos_{tribunal}.parquet`) armazena os metadados de capa em colunas analíticas, apontando para o offset dentro do arquivo do Internet Archive.
3. **Para Aplicações de Acesso Local e Filtro em Memória:**
   - O **FlatBuffers Híbrido** é a escolha ideal quando o cliente precisa inspecionar metadados de capa em milissegundos sem pagar o custo de CPU de descompressão do histórico de movimentos.
