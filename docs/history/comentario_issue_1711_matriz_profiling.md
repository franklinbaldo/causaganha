## Profiling Estatístico de Campos e Matriz Controlada 2x4 (Modelagem vs Serialização)

Conforme registrado nos comentários das issues [#1710](https://github.com/franklinbaldo/causaganha/issues/1710) e [#1711](https://github.com/franklinbaldo/causaganha/issues/1711), executamos o profiling estatístico, estrutural e orçamentário detalhado de todos os campos do DataJud a partir da amostra real (68 documentos / 57 coleções em múltiplos tribunais e graus).

Os resultados completos estão versionados em:
- **Relatório de Profiling:** [`docs/datajud-field-profiling-and-optimization-matrix.md`](../datajud-field-profiling-and-optimization-matrix.md)
- **Script Reproduzível:** [`scripts/datajud/field_profiler.py`](../../scripts/datajud/field_profiler.py)

---

### 1. Orçamento Real de Bytes por Campo: Onde Reside o Peso do Processo

A análise orçamentária comprovou que a otimização deve se concentrar nos movimentos:

| Campo | Tamanho Total (Bytes) | % do Documento | Diagnóstico |
| :--- | :--- | :--- | :--- |
| `_source.movimentos` | **709.041 B** | **92,9%** | **O gargalo do acervo está aqui.** |
| `_source.assuntos` | 8.970 B | 1,2% | Pequeno, facilmente comprimível |
| `_source.orgaoJulgador` | 7.466 B | 1,0% | Nome do órgão é repetitivo |
| `_source.classe` | 4.393 B | 0,6% | Código + Nome da TPU |
| `_source.dataHoraUltimaAtualizacao` | 4.077 B | 0,5% | Timestamp ISO |
| `_source.formato` | 3.332 B | 0,4% | Quase estático ("Eletrônico") |
| `_source.@timestamp` | 3.063 B | 0,4% | Metadado de ingestão do cluster |
| `_source.sistema` | 3.050 B | 0,4% | Código + Nome do sistema |
| `_source.numeroProcesso` | 2.856 B | 0,4% | String 20 dígitos |
| `_id` | 2.652 B | 0,3% | 100% derivável (redundante) |
| **Total** | **763.010 B** | **100,0%** | - |

**Conclusão:** 92,9% do volume físico é consumido pelo array de movimentações. Otimizações de metadados da capa sem tratar movimentos geram impacto inferior a 7,1%.

---

### 2. Análise de Redundância e Derivabilidade do `_id`

- **Fórmula:** `_id == f"{tribunal}_{grau}_{numeroProcesso}"`
- **Conformidade Observada:** **100,0%** em todos os 68 documentos reais (0 exceções).
- **Contrato Lossless:** Não armazenamos o `_id` no formato otimizado quando derivável; preservamos o identificador literal apenas em caso de exceção futura, garantindo 100% de fidelidade de reconstrução.

---

### 3. Faixas Numéricas e Tipos Mínimos Seguros

- `classe.codigo`: min 7, max 14.695 $\rightarrow$ cabe em **`ushort` (16-bit)** em vez de `long` (64-bit).
- `movimento.codigo`: min 22, max 15.621 $\rightarrow$ cabe em **`ushort` (16-bit)**.
- `complemento.codigo`: min 2, max 36 $\rightarrow$ cabe em **`ubyte` (8-bit)**.
- `sistema.codigo`: min -1, max 4 $\rightarrow$ cabe em **`byte` (8-bit com sinal)**.
- `orgaoJulgador.codigo`: min 3.349, max 93.649 $\rightarrow$ cabe em **`uint` (32-bit)**.
- `codigoMunicipioIBGE`: min 1.100.049, max 5.300.108 $\rightarrow$ cabe em **`uint` (32-bit)**.

---

### 4. Matriz Controlada 2x4 (Isolando Modelagem vs Serialização)

Para isolar o efeito da **Modelagem Lógica** (eliminação de redundância de `_id` e nomes repetidos TPU) do efeito do **Formato de Serialização** (JSON vs FlatBuffers vs Zstd):

| Nível de Otimização | JSON | FlatBuffers | Delta FB vs JSON | Economia da Modelagem |
| :--- | :--- | :--- | :--- | :--- |
| **1. Dados Originais (Bruto)** | 808.223 B (4,5 ms) | 728.696 B (119,0 ms) | **0,90x** | 0,0% (Base) |
| **2. Modelo Compacto Otimizado** | **145.900 B** (3,0 ms) | **92.016 B** (13,8 ms) | **0,63x** | **82,0% de redução** |
| **3. Modelo Compacto + Zstandard** | **39.840 B** (0,8 ms) | **89.263 B** (0,7 ms) | **2,24x** | **95,1% de redução** |

---

### 5. Resposta Conclusiva à Pergunta do Experimento

1. **A maior economia (82%) decorre da Modelagem Lógica:** O JSON compactado encolheu de 808 KB para 145 KB apenas com normalização de strings TPU e eliminação do `_id` derivável.
2. **Sem compressão de stream, FlatBuffers é 37% menor que JSON (92 KB vs 145 KB):** Devido ao alinhamento binário de tipos inteiros e vtables.
3. **Com compressão de stream, JSON Compacto + Zstd atinge a menor pegada física (39,8 KB):** Redução total de 95% do volume original.
4. **O trade-off definitivo do FlatBuffers é Latência e Acesso O(1):**
   - Ler a capa de todos os processos: **1,07 ms** (15,7 µs por documento) no FlatBuffers Híbrido sem descompressão.
   - No JSON + Zstd, é obrigatório descomprimir todo o stream de 3.206 movimentos para ler 1 campo da capa.
