# Protótipo Operacional: DataJud Internet Archive Static Reader (Zero-Backend)

> **Referência:** Issue [#1711](https://github.com/franklinbaldo/causaganha/issues/1711) e PR [#1712](https://github.com/franklinbaldo/causaganha/pull/1712)  
> **Objetivo:** Demonstrar operacionalmente que um site 100% estático (sem banco de dados ou servidor de aplicação) pode consultar qualquer processo no Internet Archive via **HTTP Range Requests** com o mínimo absoluto de requisições:
> - **1ª Consulta (*Cold*):** Exatamente **2 requisições HTTP** (1 para o micro-índice + 1 para o Range do processo).
> - **Consultas Seguintes (*Warm*):** Exatamente **1 requisição HTTP** (índice já cacheado no IndexedDB/memória).

---

## 1. Arquitetura Operacional do Protótipo

```
                    NAVEGADOR DO USUÁRIO
                             │
     Digita CNJ: 0001311-51.2024.8.13.0647
                             │
       ┌─────────────────────┴─────────────────────┐
       ▼                                           ▼
[REQUISIÇÃO 1: ROTEAMENTO]                [REQUISIÇÃO 2: DADOS]
Site Estático / CDN                       Internet Archive (IA)
Busca partição:                           GET /download/{item}/{shard}.zip
/indexes/8.13_2024.json                   Range: bytes=48775-53109
(Cacheada no IndexedDB)                   (Baixa 4.335 B do CNJ agrupado)
       │                                           │
       ▼                                           ▼
Retorna: Shard ZIP + Offset               Descomprime Zstd via WASM no browser (0.37ms)
                                                   │
                                                   ▼
                                         Reconstrói com Catálogo TPU (Estratégia B)
                                         e renderiza a tela com G1, G2 e STJ!
```

---

## 2. Estrutura de Arquivos

```
experiments/datajud_ia_static_reader/
├── build_shards_and_indexes.py   # Gerador de Shard ZIP STORED e micro-índices
├── serve_static.py               # Servidor com HTTP Range (RFC 7233) e CORS
├── test_end_to_end_reader.py     # Teste automatizado de ponta a ponta
└── public/
    ├── index.html                # SPA com Telemetria HTTP em tempo real
    ├── fzstd.umd.js              # Descompressor Zstandard WASM/JS (8 KB)
    ├── catalogo_tpu.json         # Catálogo global dos 278 templates TPU
    ├── indexes/
    │   ├── router_map.json       # Mapa mestre de partições Tribunal/Ano
    │   ├── 8.13_2024.json        # Micro-índice TJMG 2024 (Offsets e Shards)
    │   └── ...                   # Demais partições
    └── shards/
        └── shard_001.zip         # Container ZIP STORED com .json.zst
```

---

## 3. Como Executar e Testar

### Passo 1: Construir os Shards e Índices
```bash
uv run python experiments/datajud_ia_static_reader/build_shards_and_indexes.py
```

### Passo 2: Executar o Teste Automatizado de Ponta a Ponta
```bash
uv run python experiments/datajud_ia_static_reader/test_end_to_end_reader.py
```

### Passo 3: Abrir a Interface no Navegador
```bash
uv run python experiments/datajud_ia_static_reader/serve_static.py
```
Acesse no navegador: `http://localhost:8088`

---

## 4. Resultados Comprovados no Teste

No processo real `0001311-51.2024.8.13.0647` (caso multíndice com G1, G2 no TJMG e Recurso no STJ):
- **Requisição 1 (Micro-índice):** 681 bytes transferidos.
- **Requisição 2 (HTTP Range no ZIP):** 4.335 bytes transferidos (`HTTP 206 Partial Content`).
- **Descompressão Zstandard Client-side:** **0,37 ms** para descomprimir 37 KB de dados em memória.
- **Reconstrução Multigrau:** 3 documentos (`TJMG G1`, `TJMG G2`, `STJ SUP`) e 362 movimentações processuais renderizadas instantaneamente.
- **Segunda Consulta (Warm):** Exatamente **1 requisição HTTP** (Range direto).
