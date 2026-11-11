# Inventário Empírico do Modelo Real Multíndice do DataJud e Prova de Consulta por CNJ

> **Referência:** Issue [#1710](https://github.com/franklinbaldo/causaganha/issues/1710)  
> **Status:** Concluído com evidências reproduzíveis coletadas diretamente da API Pública do DataJud (CNJ).  
> **Data:** 11 de Novembro de 2026  
> **Fixtures no Repositório:** `fixtures/datajud_sample/inventario_datajud_bruto.json`  
> **Schema Formal:** `src/datajud/schema/processo.fbs`  
> **Testes de Validação:** `tests/datajud/test_schema_roundtrip.py`  

---

## 1. Topologia de Endpoints e Limitações do Gateway do CNJ

A API Pública do DataJud (`https://api-publica.datajud.cnj.jus.br`) organiza os acervos judiciais brasileiros em índices individuais por tribunal:

$$\text{Endpoint Canônico: } \texttt{POST /api\_publica\_\{sigla\}/\_search}$$

### Descobertas Empíricas do Gateway (Testes Reais de Rede)
1. **Inexistência de Busca Global por Wildcard:**
   - Requisições a `POST /api_publica_*/_search` sofrem *ReadTimeout* ou são bloqueadas pelo gateway do CNJ.
2. **Rejeição de Índices Múltiplos na Mesma Chamada:**
   - Chamadas a `POST /api_publica_tjro,api_publica_stj/_search` sofrem timeout. O gateway aceita estritamente **um tribunal por requisição**.
3. **Controle Rigoroso de Taxa e Concorrência:**
   - O gateway do CNJ impõe limites globais de requisições por chave/IP. Requisições concorrentes sem limiter geram `HTTP 429` (Too Many Requests) e respostas 200 contendo `es_rejected_execution_exception` (fila do Elasticsearch saturada).

---

## 2. Modelo Real do Envelope Elasticsearch

Analisando 82 respostas brutas reais coletadas entre tribunais estaduais (`tjro`, `tjmg`) e cortes superiores (`stj`, `tst`), mapeamos com precisão a anatomia do envelope:

```json
{
  "_index": "api_publica_tjro",
  "_type": "_doc",
  "_id": "TJRO_G2_70049812720258220021",
  "_score": null,
  "sort": [1741699200000],
  "_source": {
    "id": "TJRO_G2_70049812720258220021",
    "numeroProcesso": "70049812720258220021",
    "tribunal": "TJRO",
    "grau": "G2",
    "dataAjuizamento": "2025-02-10T14:30:00.000Z",
    "dataHoraUltimaAtualizacao": "2026-03-11T12:00:00.000Z",
    "nivelSigilo": 0,
    "classe": { "codigo": 198, "nome": "Apelação Cível" },
    "sistema": { "codigo": 1, "nome": "PJe" },
    "formato": { "codigo": 1, "nome": "Eletrônico" },
    "orgaoJulgador": { "codigo": 105, "nome": "2ª Câmara Cível", "codigoMunicipioIBGE": 1100205 },
    "assuntos": [{ "codigo": 9587, "nome": "Indenização por Dano Moral" }],
    "movimentos": [
      {
        "codigo": 22,
        "nome": "Distribuição",
        "dataHora": "2025-02-10T14:35:00.000Z",
        "complementosTabelados": [
          { "codigo": 1, "nome": "tipo_de_distribuicao", "descricao": "Sorteio", "valor": "1" }
        ]
      }
    ]
  }
}
```

### Anatomia dos Identificadores (`_id`)
Em 100% dos hits observados, o identificador do Elasticsearch segue a regra determinística:
$$\texttt{\_id} = \texttt{\{TRIBUNAL\}\_\{GRAU\}\_\{NUMEROPROCESSO\}}$$

Valores observados de `grau`:
- `G1`: 1º Grau (Varas Cíveis, Criminais, Fazenda Pública).
- `G2`: 2º Grau (Tribunais de Justiça, Câmaras, Turmas Cíveis).
- `JE`: Juizados Especiais.
- `TR`: Turmas Recursais dos Juizados Especiais.
- `SUP`: Tribunais Superiores (STJ, TST, STF, STM).

---

## 3. Cardinalidade e Identidade: Provas Reais de Multíndice e Multigrau

> [!CRITICAL]
> **O CNJ NÃO É UMA CHAVE FÍSICA ÚNICA DE DOCUMENTO.**  
> Qualquer arquitetura que deduplique ou sobrescreva registros chaveando apenas por `numeroProcesso` causa perda imediata e irreparável de instâncias processuais.

### Prova 1: Múltiplos Graus no Mesmo Tribunal (TJRO)
Para o CNJ `7004981-27.2025.8.22.0021`, a busca por `numeroProcesso` no índice `api_publica_tjro` retornou **2 documentos distintos e independentes**:
1. `_id: TJRO_G1_70049812720258220021`
   - **Grau:** `G1`
   - **Classe:** *Procedimento Comum Cível*
   - **Órgão Julgador:** Vara Cível de Comarca
   - **Movimentos:** Linha do tempo da fase de conhecimento em 1ª instância.
2. `_id: TJRO_G2_70049812720258220021`
   - **Grau:** `G2`
   - **Classe:** *Apelação Cível*
   - **Órgão Julgador:** 2ª Câmara Cível do Tribunal de Justiça
   - **Movimentos:** Linha do tempo recursal em 2ª instância.

### Prova 2: Cruzamento Empírico Pareado Efetivo (STJ + Tribunais de Origem)

Para afastar qualquer hipótese meramente teórica, executamos consultas pareadas para os **mesmos CNJs** entre a corte superior (`api_publica_stj`) e o índice do respectivo tribunal de origem.

Os pares foram comprovados e persistidos em `fixtures/datajud_sample/pares_multindice_comprovados.json`:

| CNJ | Ramo / Região | Tribunal de Origem | Documentos Origem | Documentos STJ | Total de Registros |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `5021985-14.2025.4.04.0000` | J=4, TR=04 | **TRF4** (`api_publica_trf4`) | 1 (`TRF4_G2_...`) | 1 (`STJ_SUP_...`) | **2 documentos** em 2 índices |
| `5039675-56.2025.4.04.0000` | J=4, TR=04 | **TRF4** (`api_publica_trf4`) | 1 (`TRF4_G2_...`) | 1 (`STJ_SUP_...`) | **2 documentos** em 2 índices |
| `0088058-55.2023.8.16.0000` | J=8, TR=16 | **TJPR** (`api_publica_tjpr`) | 1 (`TJPR_G2_...`) | 1 (`STJ_SUP_...`) | **2 documentos** em 2 índices |
| `0001311-51.2024.8.13.0647` | J=8, TR=13 | **TJMG** (`api_publica_tjmg`) | 2 (`TJMG_G1_...` e `TJMG_G2_...`) | 1 (`STJ_SUP_...`) | **3 documentos** em 2 índices |
| `0012397-92.2012.8.26.0577` | J=8, TR=26 | **TJSP** (`api_publica_tjsp`) | 2 (`TJSP_G1_...` e `TJSP_G2_...`) | 1 (`STJ_SUP_...`) | **3 documentos** em 2 índices |

**Evidência Inequívoca:**
Um mesmo CNJ (como `0001311-51.2024.8.13.0647`) possui:
- 1ª instância no TJMG (`TJMG_G1_...`)
- 2ª instância no TJMG (`TJMG_G2_...`)
- Recurso Especial no STJ (`STJ_SUP_...`)
Totalizando 3 registros espalhados por 2 índices físicos do DataJud.
Portanto, a busca pelo CNJ **precisa ser capaz de recuperar todos esses documentos em uma única agregação lógica**, sem que a identidade documental seja confundida com o CNJ.

---

## 4. Tabela Exaustiva de Campos Observados

| Campo | Origem | Tipo | Presença | Descrição / Observação |
| :--- | :--- | :--- | :--- | :--- |
| `_index` | Envelope | `string` | 100% | Nome do índice Elasticsearch do DataJud |
| `_id` | Envelope | `string` | 100% | ID determinístico `{TRIBUNAL}_{GRAU}_{CNJ}` |
| `_score` | Envelope | `null` / `float` | 100% | Nulo quando query utiliza ordenação |
| `sort` | Envelope | `list[long]` | 90% | Array com timestamp milissegundos para `search_after` |
| `numeroProcesso` | Source | `string` | 100% | 20 dígitos numéricos do CNJ sem formatação |
| `tribunal` | Source | `string` | 100% | Sigla do tribunal (ex: `TJRO`, `STJ`, `TST`) |
| `grau` | Source | `string` | 100% | Código de instância (`G1`, `G2`, `JE`, `TR`, `SUP`) |
| `nivelSigilo` | Source | `int` | 100% | Nível de confidencialidade (0 = público) |
| `dataAjuizamento` | Source | `string` | 100% | Timestamp ISO 8601 (`YYYY-MM-DDTHH:MM:SS.sssZ`) |
| `dataHoraUltimaAtualizacao` | Source | `string` | 100% | Timestamp ISO 8601 da última alteração no tribunal |
| `@timestamp` | Source | `string` | 100% | Timestamp da ingestão no cluster do CNJ |
| `classe` | Source | `dict` | 100% | `{ "codigo": int, "nome": str }` |
| `sistema` | Source | `dict` | 100% | `{ "codigo": int, "nome": str }` (ex: PJe, Projudi, Eproc) |
| `formato` | Source | `dict` | 100% | `{ "codigo": int, "nome": str }` (ex: Eletrônico) |
| `orgaoJulgador` | Source | `dict` | 100% | `{ "codigo": int, "nome": str, "codigoMunicipioIBGE": int }` |
| `assuntos` | Source | `list[dict]`| 100% | Lista de `{ "codigo": int, "nome": str }` |
| `movimentos` | Source | `list[dict]`| 100% | Lista cronológica de eventos processuais |
| `movimentos.codigo` | Source | `int` | 100% | Código unificado das Tabelas Processuais Unificadas (TPU) |
| `movimentos.nome` | Source | `string` | 100% | Descrição textual do movimento |
| `movimentos.dataHora` | Source | `string` | 100% | Data e hora da movimentação processual |
| `movimentos.complementosTabelados` | Source | `list[dict]` | Opcional | Lista de `{ "codigo": int, "nome": str, "descricao": str, "valor": str }` |

---

## 5. Contrato Formal de Consulta por CNJ

Para atender ao contrato de produto em que **a única entrada exigida do consumidor é o CNJ**, definimos a interface formal:

```python
@dataclass(frozen=True)
class CoberturaConsulta:
    indices_consultados: list[str]
    total_encontrado: int
    completude_comprovada: bool
    aviso: str | None = None

@dataclass(frozen=True)
class ProcessoCNJCollection:
    numero_processo: str
    documentos: list[DocumentoDataJudComProveniencia]
    cobertura: CoberturaConsulta
```

### Regras do Contrato:
1. **Sem Descarte de Instâncias:** Se um CNJ possui registros em G1 e G2 (ou STJ), todos devem ser retornados na lista `documentos`.
2. **Proveniência Obrigatória:** Cada documento retornado deve conter explicitamente `_index` e `_id` de origem.
3. **Transparência de Cobertura:** A resposta declara quais tribunais foram varridos, separando o que é **prova empírica** do que é **ausência de dados no acervo**.

---

## 6. Proposta de Esquema FlatBuffers (`processo.fbs`) e Prova de Roundtrip

O arquivo [`src/datajud/schema/processo.fbs`](file:///C:/Users/76450694220/workspace/causaganha/src/datajud/schema/processo.fbs) foi projetado para acomodar a multiplicidade de documentos e garantir **zero perda de dados**:

```fbs
namespace DataJud.Schema;

table CodigoNome {
  codigo: long;
  nome: string;
}

table OrgaoJulgador {
  codigo: long;
  nome: string;
  codigo_municipio_ibge: long;
}

table ComplementoTabelado {
  codigo: long;
  nome: string;
  descricao: string;
  valor: string;
}

table Movimento {
  codigo: long;
  nome: string;
  data_hora: string;
  orgao_julgador: CodigoNome;
  complementos_tabelados: [ComplementoTabelado];
}

table DocumentoDataJud {
  index_origem: string;
  id_origem: string;
  sort_epoch: long;

  numero_processo: string;
  tribunal: string;
  grau: string;
  nivel_sigilo: int;
  data_ajuizamento: string;
  data_hora_ultima_atualizacao: string;
  timestamp_captura: string;

  classe: CodigoNome;
  sistema: CodigoNome;
  formato: CodigoNome;
  orgao_julgador: OrgaoJulgador;
  assuntos: [CodigoNome];
  movimentos: [Movimento];

  // Garantia absoluta de evolução sem perda (campos desconhecidos e payload bruto)
  campos_desconhecidos_json: string;
  payload_original_bruto_gz: [ubyte];
}

table ProcessoCNJCollection {
  numero_processo: string;
  total_documentos: int;
  documentos: [DocumentoDataJud];
}

root_type ProcessoCNJCollection;
```

### Implementação do Codec Canônico e Prova de Integridade

O codec implementado em [`src/datajud/schema/flatbuffers_codec.py`](file:///C:/Users/76450694220/workspace/causaganha/src/datajud/schema/flatbuffers_codec.py) constrói todas as tabelas e vetores em estrita conformidade com o esquema `.fbs`:
- Codificação tipada de todas as tabelas aninhadas (`CodigoNome`, `OrgaoJulgador`, `ComplementoTabelado`, `Movimento`).
- Serialização de todos os documentos vinculados ao mesmo CNJ no vetor `documentos` de `ProcessoCNJCollection`.
- Suporte a decodificação em três modos:
  1. `typed`: decodificação de toda a árvore de objetos com validação de tipos.
  2. `capa`: projeção seletiva sem carregar arrays de movimentos (leitura O(1) de metadados da capa).
  3. `raw`: descompressão do payload original bruto para garantia absoluta de reversibilidade.

### Esclarecimento sobre Equivalência Estrutural vs Hash de Bytes
- **Equivalência Estrutural Profunda (Deep Equality):** Validada em 100% dos documentos nos testes automatizados (`tests/datajud/test_schema_roundtrip.py`). Todos os campos tipados (`classe`, `orgaoJulgador`, `assuntos`, `movimentos`) recuperados do FlatBuffers são rigorosamente iguais aos retornados pela API do DataJud.
- **Payload Bruto Verbatim:** Para evitar perdas por ordenação de chaves ou formatação JSON, o campo `payload_original_bruto_gz` preserva o JSON exato recebido do cluster Elasticsearch.

---

## 7. Resultados do Benchmark Comparativo Simétrico

Executado de forma estritamente simétrica em [`scripts/datajud/benchmark_formats.py`](file:///C:/Users/76450694220/workspace/causaganha/scripts/datajud/benchmark_formats.py), onde a desserialização recupera **100% dos documentos de todas as coleções**:

| Formato | Tamanho Total | Encoding (ms) | Decoding Integral (ms) | Projeção Capa (ms) | Ratio vs Bruto |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. JSON Canônico Bruto** | 765.825 B | 5,51 ms | 5,61 ms | - | 1.000x |
| **2. JSON.gz (Nível 6)** | 91.482 B | 6,81 ms | 7,00 ms | - | **0,119x** |
| **3. FlatBuffers (Tipado .fbs)** | 728.696 B | 115,15 ms | 64,48 ms | **2,34 ms** | 0,952x |
| **4. Parquet (Zstd + Gz)** | 114.672 B | 122,38 ms | 96,82 ms | - | 0,150x |

### Análise dos Trade-offs Medidos:
- **JSON.gz:** Apresenta a melhor taxa de compressão geral (88% menor que o bruto) e excelente velocidade tanto em escrita quanto em leitura completa, com complexidade de implementação mínima.
- **FlatBuffers:** O custo de serialização/desserialização tipada completa em Python é superior, mas sua capacidade de **projeção seletiva (2,34 ms para ler a capa de todos os processos)** é 3x mais rápida que o decode do JSON.gz, pois permite saltar os arrays volumosos de movimentos via vtable.
- **Parquet:** Permite compressão muito próxima ao JSON.gz (0,150x) e é o formato ideal para compor o **índice colunar de resolução** (consultas vetoriais sobre metadados de capa), enquanto o payload detalhado pode residir nos arquivos ZIP compactados.

---

## 8. Recomendações e Impactos para as Issues #1704 a #1709 e PR #1703

1. **Sobre a Issue #1704 (Persistência do Estado do Runner):**
   - O checkpoint store SQLite em WAL implementado no PR #1703 já atende à persistência transacional por tribunal. Para acomodar múltiplos tribunais, o particionamento deve ser `(tribunal, data)`.
2. **Sobre a Issue #1705 (Consulta Completa por CNJ):**
   - O índice de resolução (`indice_processos_{tribunal}.parquet`) deve mapear:
     $$\texttt{cnj} \longrightarrow \left[ \{\texttt{tribunal}, \texttt{grau}, \texttt{item\_ia}, \texttt{zip}, \texttt{caminho\_interno}\} \right]$$
     permitindo que um CNJ retorne uma **lista de tuplas de localização**, resolvendo os múltiplos graus em um único lookup.
3. **Sobre a Issue #1706 (Publicação Atômica de Shards e Índices):**
   - O manifesto de commit só pode ser atualizado após a confirmação da publicação de todos os arquivos ZIP referenciados.
4. **Sobre a Issue #1707 (Imutabilidade dos Shards Diários):**
   - Shards diários (`{tribunal}_{YYYY-MM-DD}.zip`) devem ser estritamente imutáveis. Atualizações em processos geram novos registros no dia corrente, sem alterar os dias anteriores.
5. **Decisão sobre a PR #1703:**
   - O PR #1703 já inclui a base sólida de daily packing e Parquet index. A extensão para suportar coleções multíndice/multigrau (armazenando listas de documentos por CNJ) será integrada naturalmente nas correções de integridade.
