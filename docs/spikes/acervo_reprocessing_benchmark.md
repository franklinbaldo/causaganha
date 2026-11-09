# Benchmark de Reprocessamento do Acervo Completo CausaGanha

Medições empíricas em CPU (Intel / AMD x86_64) no acervo expanded do DJEN.

## 1. Latência e Throughput por Componente (1 Core)

| Componente | Throughput (docs/s) | Média (ms) | p50 (ms) | p95 (ms) | p99 (ms) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1. Topologia + Taxonomia (3 níveis) | 5484.5 | 0.18 | 0.18 | 0.29 | 0.39 |
| 2. Dispositivo Híbrido (Random Forest 22 features) | 60.2 | 14.52 | 13.61 | 18.81 | 23.48 |
| 3. Estrutural Completo (7 seções canônicas) | 782.2 | 1.28 | 0.74 | 3.71 | 7.06 |
| 4. Pipeline Completo Integrado (Taxonomia + RF + Estrutura) | 61.5 | 16.19 | 15.24 | 23.04 | 27.76 |

## 2. Estimativa de Tempo de Reprocessamento por Volume de Acervo

### Cenário A: Recorte Cirúrgico de Dispositivo (Random Forest 22 features)

| Volume | Descrição | 1 Core (Local) | 8 Cores (Servidor) | 32 Cores (Node Cloud) |
| :--- | :--- | :--- | :--- | :--- |
| 100.000 | Vara / Acervo Regional | 27m 40s | 3m 50s | 1m 1s |
| 1.000.000 | Tribunal Médio / DJEN Mensal | 4h 36m | 38m 26s | 10m 15s |
| 5.000.000 | Grande Tribunal (TJSP / TRF) | 23h 3m | 3h 12m | 51m 15s |
| 20.000.000 | DJEN Nacional Anual Consolidado | 92h 15m | 12h 48m | 3h 25m |

### Cenário B: Pipeline Completo (Taxonomia + Dispositivo + Estrutura 7 Seções)

| Volume | Descrição | 1 Core (Local) | 8 Cores (Servidor) | 32 Cores (Node Cloud) |
| :--- | :--- | :--- | :--- | :--- |
| 100.000 | Vara / Acervo Regional | 27m 5s | 3m 45s | 1m 0s |
| 1.000.000 | Tribunal Médio / DJEN Mensal | 4h 30m | 37m 37s | 10m 2s |
| 5.000.000 | Grande Tribunal (TJSP / TRF) | 22h 34m | 3h 8m | 50m 10s |
| 20.000.000 | DJEN Nacional Anual Consolidado | 90h 18m | 12h 32m | 3h 20m |

## 3. Comparativo de Custo e Viabilidade vs. LLMs em Nuvem

| Método | Throughput | Tempo (1 Milhão) | Tempo (20 Milhões) | Custo Estimado (20M) |
| :--- | :--- | :--- | :--- | :--- |
| **RF Híbrida (8 vCPUs)** | ~434 docs/s | **38m 26s** | **12h 48m** | **$0** (Hardware existente) |
| **RF Híbrida (32 vCPUs)**| ~1626 docs/s| **10m 15s** | **3h 25m** | **~$15 em cloud spot** |
| **Pipeline Full (32 vCPUs)**| ~1661 docs/s| **10m 2s** | **3h 20m** | **~$45 em cloud spot** |
| **LLM (15 RPM free tier)**| 0.25 docs/s | 46 dias | 2.5 anos | Inviável por rate limit |
| **LLM pago (50 req/s)** | 50 docs/s | 5.5 horas | 4.6 dias | ~$30.000 - $60.000 USD |
