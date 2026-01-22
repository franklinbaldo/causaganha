# DJEN Infrastructure

Infraestrutura completa para coleta de dados do Diário de Justiça Eletrônico Nacional (DJEN).

## 🎯 Visão Geral

Sistema de scraping contínuo e gratuito da API DJEN (PJe), com bypass de geo-blocking e armazenamento ilimitado.

```
┌─────────────────────────────────────────────────────────────┐
│                    CLOUDFLARE (Free Tier)                   │
│                                                             │
│   ┌─────────┐     ┌─────────────────┐     ┌─────────────┐  │
│   │  Cron   │────▶│     Worker      │────▶│     R2      │  │
│   │(1x/min) │     │  (TypeScript)   │     │  (buffer)   │  │
│   └─────────┘     └────────┬────────┘     └─────────────┘  │
│                            │                               │
└────────────────────────────┼───────────────────────────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │   Google Cloud Run    │
                  │   Proxy (São Paulo)   │
                  │  ✅ ATIVO E TESTADO   │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │      DJEN API        │
                  │  (geo-bloqueada)     │
                  └──────────────────────┘
```

---

## 🔗 Componente 1: Proxy DJEN (Produção)

### Endereço

```
https://djen-proxy-mhgmawcn3a-rj.a.run.app
```

### Especificações

| Atributo | Valor |
|----------|-------|
| **URL** | `https://djen-proxy-mhgmawcn3a-rj.a.run.app` |
| **Região** | São Paulo, Brasil (`southamerica-east1`) |
| **Plataforma** | Google Cloud Run |
| **Versão** | v4.0 (graceful shutdown + error handling) |
| **Linguagem** | Go 1.21 |
| **Segurança** | Whitelist (zero-trust) |
| **Status** | ✅ Ativo, 100% testado |
| **Custo** | $0/mês (free tier) |

### Segurança

**Whitelist permitida:**
- `/api/*` - API DJEN
- `/swagger/*` - Documentação
- `/comunicacao*` - Comunicações
- `/login*` - Autenticação
- `/health`, `/security` - Proxy endpoints

**Tudo mais retorna 403 Forbidden.**

### Testes

```bash
# Health check
curl https://djen-proxy-mhgmawcn3a-rj.a.run.app/health
# {"status":"ok","version":"v4.0"}

# Teste completo (10 testes de segurança)
./TEST_DJEN_SECURITY.sh
# ✅ 10/10 testes passam
```

### Deploy/Redeploy

```bash
./DEPLOY_DJEN_V4.sh
```

### Documentação

- 📄 [DJEN_PROXY_ENDPOINT.md](docs/DJEN_PROXY_ENDPOINT.md) - Detalhes do endpoint
- 📄 [DJEN_PROXY_SECURITY.md](docs/DJEN_PROXY_SECURITY.md) - Implementação de segurança
- 📄 [DJEN_PROXY_SECURITY_OPTIONS.md](docs/DJEN_PROXY_SECURITY_OPTIONS.md) - Comparação de abordagens

---

## 🤖 Componente 2: Scraper Cloudflare (MVP)

### Arquitetura

```
Cloudflare Cron (cada minuto)
         │
         ▼
    CF Worker (TypeScript)
    ├─ Ler estado (KV)
    ├─ Batch de 50 requests
    │  └─ fetch → Proxy → DJEN
    ├─ Comprimir JSON → gzip
    ├─ Salvar no R2
    └─ Atualizar estado (KV)
```

### Capacidade

| Métrica | Valor |
|---------|-------|
| **Requests/dia** | 72.000 (vs 52k necessário) |
| **Margem** | 38% |
| **Batch size** | 50 requests/minuto |
| **Cron** | Executa a cada minuto |
| **Custo** | $0/mês (free tier) |

### Deploy

```bash
cd djen-scraper

# 1. Setup (primeira vez)
./scripts/setup.sh
# - Login Cloudflare
# - Cria KV namespace
# - Cria R2 bucket
# - Instala dependências

# 2. Deploy
./scripts/deploy.sh
# - Build TypeScript
# - Deploy worker
# - Ativa cron
```

### Monitoramento

```bash
# Logs em tempo real
wrangler tail

# Ver estado atual
curl https://djen-scraper.YOUR_SUBDOMAIN.workers.dev/state | jq

# Listar dados coletados
wrangler r2 object list djen-buffer --prefix "data/"
```

### Documentação

- 📄 [djen-scraper/README.md](djen-scraper/README.md) - Documentação completa

---

## 📊 Dados Coletados

### Formato

**Fase 1 (MVP - Atual):**
- Formato: JSON comprimido (gzip)
- Storage: Cloudflare R2 (10 GB = ~40-100 dias)
- Estrutura: `data/YYYY-MM-DD/timestamp.json.gz`

**Fase 2 (Futuro):**
- Conversão: JSON → Parquet (ZSTD)
- Archive: Internet Archive (ilimitado, gratuito)
- Query: DuckDB direto da URL

### Acessar Dados

```bash
# Listar dados
wrangler r2 object list djen-buffer --prefix "data/2025-01-21/"

# Baixar arquivo
wrangler r2 object get djen-buffer/data/2025-01-21/file.json.gz -o data.json.gz
gunzip data.json.gz

# Query com DuckDB
duckdb -c "SELECT * FROM 'data.json' LIMIT 10"
```

---

## 🔄 Workflow Completo

### 1. Coleta Contínua (Automática)

```
A cada minuto:
  1. Worker acorda via Cron
  2. Lê estado do KV
  3. Determina prioridade (D-1 ou backfill)
  4. Faz 50 requests via proxy
  5. Salva JSON.gz no R2
  6. Atualiza estado no KV
```

### 2. Processamento (Fase 2, Manual)

```bash
# Converter dia específico para Parquet
./scripts/process_and_archive.sh 2025-01-21

# Faz:
# 1. Baixa JSON.gz do R2
# 2. Descompacta e consolida
# 3. Converte para Parquet (DuckDB)
# 4. Upload para Internet Archive
# 5. Deleta do R2
```

---

## 💰 Custos

| Componente | Plataforma | Custo |
|------------|------------|-------|
| Proxy | Google Cloud Run | $0 (free tier) |
| Worker | Cloudflare Workers | $0 (free tier) |
| Estado | Cloudflare KV | $0 (free tier) |
| Buffer | Cloudflare R2 | $0 (free tier) |
| Archive | Internet Archive | $0 (sempre grátis) |
| **TOTAL** | - | **$0/mês** |

---

## 🔐 Segurança

### Proxy
- ✅ Whitelist zero-trust
- ✅ Path traversal bloqueado
- ✅ URLs externas bloqueadas
- ✅ Graceful shutdown
- ✅ Error handling

### Worker
- ✅ Stateless (sem dados sensíveis)
- ✅ KV privado (atomic writes)
- ✅ R2 privado (apenas worker acessa)
- ✅ Rate limiting respeitado

---

## 📁 Estrutura do Repositório

```
/
├── DJEN_INFRASTRUCTURE.md          # Este arquivo
├── DEPLOY_DJEN_V4.sh              # Deploy do proxy
├── TEST_DJEN_SECURITY.sh          # Testes de segurança
├── djen_proxy.go                  # Código do proxy (Go)
├── djen.yml                       # OpenAPI spec DJEN
├── docs/
│   ├── DJEN_PROXY_ENDPOINT.md     # Detalhes do endpoint
│   ├── DJEN_PROXY_SECURITY.md     # Segurança do proxy
│   └── DJEN_PROXY_SECURITY_OPTIONS.md
└── djen-scraper/
    ├── README.md                  # Docs do scraper
    ├── cloudflare/worker/
    │   ├── src/index.ts          # Worker TypeScript
    │   ├── wrangler.toml         # Config Cloudflare
    │   └── package.json
    └── scripts/
        ├── setup.sh              # Setup inicial
        ├── deploy.sh             # Deploy worker
        └── process_and_archive.sh # Fase 2
```

---

## 🚀 Quick Start

### 1. Proxy DJEN (Já está rodando!)

```bash
# Testar
curl https://djen-proxy-mhgmawcn3a-rj.a.run.app/health

# Redeploy (se necessário)
./DEPLOY_DJEN_V4.sh
```

### 2. Deploy Scraper

```bash
cd djen-scraper

# Setup (primeira vez)
./scripts/setup.sh

# Deploy
./scripts/deploy.sh

# Monitorar
wrangler tail
```

---

## 📞 Suporte

- **Proxy:** Ver logs com `gcloud run services logs read djen-proxy`
- **Scraper:** Ver logs com `wrangler tail`
- **Dados:** Acessar R2 com `wrangler r2 object list djen-buffer`

---

**Status:** ✅ Produção
**Última atualização:** 2025-01-21
