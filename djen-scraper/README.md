# DJEN Scraper

Scraper contínuo e gratuito para API DJEN (Diário de Justiça Eletrônico Nacional - PJe).

## 🎯 Características

- ✅ **100% Free Tier** - $0/mês
- ✅ **72.000 requests/dia** - Capacidade superior ao limite da API (52k/dia)
- ✅ **Proxy brasileiro** - Bypass geo-blocking via Cloud Run (São Paulo)
- ✅ **Storage ilimitado** - R2 (buffer) + Internet Archive (histórico)
- ✅ **TypeScript** - Type-safe Cloudflare Worker
- ✅ **Priorização D-1** - Sempre prioriza dia anterior antes de backfill

## 🏗️ Arquitetura

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Cron      │────▶│   Worker    │────▶│     R2      │
│ (cada min)  │     │  (TS, 50    │     │  (JSON.gz)  │
│             │     │   req/min)  │     │             │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  Cloud Run  │ (já existe)
                    │   Proxy SP  │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  DJEN API   │
                    └─────────────┘
```

**Estado:** Cloudflare KV (atomic writes)
**Storage:** R2 (JSON.gz, 10 GB = ~40-100 dias)
**Archive:** Internet Archive (Fase 2, ilimitado)

## 📋 Pré-requisitos

1. **Conta Cloudflare** (free tier)
   - Criar em: https://dash.cloudflare.com/sign-up

2. **Node.js e npm**
   ```bash
   node --version  # v18+
   npm --version   # v9+
   ```

3. **Wrangler CLI**
   ```bash
   npm install -g wrangler
   ```

4. **Cloud Run Proxy** (já existe)
   - URL: `https://djen-proxy-mhgmawcn3a-rj.a.run.app`
   - Status: ✅ Ativo e testado

## 🚀 Deploy (Fase 1 - MVP)

### 1. Setup Cloudflare

```bash
cd djen-scraper
./scripts/setup.sh
```

**O que faz:**
- Login no Cloudflare
- Cria KV namespace `djen-state`
- Cria R2 bucket `djen-buffer`
- Atualiza `wrangler.toml` com IDs
- Instala dependências npm

### 2. Deploy Worker

```bash
./scripts/deploy.sh
```

**O que faz:**
- Build TypeScript
- Deploy para Cloudflare
- Ativa Cron (executa a cada minuto)

### 3. Verificar Status

```bash
# Ver logs em tempo real
wrangler tail

# Verificar estado atual
curl https://djen-scraper.YOUR_SUBDOMAIN.workers.dev/state

# Ou via KV
wrangler kv:key get state --namespace-id=YOUR_KV_ID
```

## 📊 Monitoramento

### Dashboard Cloudflare

1. Acesse: https://dash.cloudflare.com
2. Workers & Pages → djen-scraper
3. Métricas disponíveis:
   - Requests/minuto
   - CPU time
   - Erros

### Logs em Tempo Real

```bash
wrangler tail
```

### Estado Atual

```bash
curl https://djen-scraper.YOUR_SUBDOMAIN.workers.dev/state | jq
```

Exemplo de resposta:
```json
{
  "d1": {
    "date": "2025-01-20",
    "status": "in_progress",
    "orgaos_done": ["TRF1", "TRF2"],
    "orgaos_pending": ["TRF3", "TRF4", "..."],
    "records": 1234
  },
  "backfill": {
    "next_date": null,
    "oldest_target": "2020-01-01",
    "completed_dates": []
  },
  "stats": {
    "total_records": 1234,
    "total_days_archived": 0,
    "last_run": "2025-01-21T10:30:00Z"
  }
}
```

## 💾 Acessar Dados

### Listar dados no R2

```bash
wrangler r2 object list djen-buffer --prefix "data/2025-01-20/"
```

### Baixar arquivo específico

```bash
wrangler r2 object get djen-buffer/data/2025-01-20/file.json.gz -o data.json.gz
gunzip data.json.gz
```

### Query com DuckDB (local)

```bash
# Baixar e query
wrangler r2 object get djen-buffer/data/2025-01-20/file.json.gz -o data.json.gz
gunzip data.json.gz
duckdb -c "SELECT * FROM 'data.json' LIMIT 10"
```

## 📦 Fase 2 - Archive (Futuro)

Converte JSON.gz → Parquet e faz upload para Internet Archive.

### Pré-requisitos adicionais

1. **DuckDB**
   ```bash
   # macOS
   brew install duckdb

   # Linux
   wget https://github.com/duckdb/duckdb/releases/download/v0.10.0/duckdb_cli-linux-amd64.zip
   unzip duckdb_cli-linux-amd64.zip
   sudo mv duckdb /usr/local/bin/
   ```

2. **AWS CLI** (para Internet Archive S3)
   ```bash
   pip install awscli
   ```

3. **Internet Archive Account**
   - Criar em: https://archive.org/account/login.createaccount.php
   - Obter S3 keys: https://archive.org/account/s3.php
   - Configurar:
     ```bash
     aws configure --profile ia
     # Access Key: [your_access]
     # Secret Key: [your_secret]
     # Region: us-east-1
     ```

### Processar e Arquivar

```bash
./scripts/process_and_archive.sh 2025-01-20
```

**O que faz:**
1. Baixa todos os `.json.gz` da data do R2
2. Descompacta e consolida em JSON único
3. Converte para Parquet (ZSTD compression)
4. Upload para Internet Archive
5. Deleta do R2 (libera espaço)

**Resultado:**
- URL: `https://archive.org/download/djen-pje-2025-01-20/data.parquet`
- Query direto: `duckdb -c "SELECT * FROM 'https://...' LIMIT 10"`

## 🔧 Comandos Úteis

### Worker

```bash
# Deploy
wrangler deploy

# Logs
wrangler tail

# Trigger manual (teste)
curl -X POST https://djen-scraper.YOUR_SUBDOMAIN.workers.dev/trigger

# Ver versão deployada
wrangler deployments list
```

### KV (Estado)

```bash
# Ver estado
wrangler kv:key get state --namespace-id=YOUR_KV_ID

# Resetar estado (cuidado!)
wrangler kv:key delete state --namespace-id=YOUR_KV_ID

# Listar todas as keys
wrangler kv:key list --namespace-id=YOUR_KV_ID
```

### R2 (Storage)

```bash
# Listar buckets
wrangler r2 bucket list

# Listar objetos
wrangler r2 object list djen-buffer

# Ver tamanho usado
wrangler r2 bucket info djen-buffer

# Deletar bucket (cuidado!)
wrangler r2 bucket delete djen-buffer
```

## 📈 Capacidade e Limites

| Recurso | Free Tier | Uso Estimado | Margem |
|---------|-----------|--------------|--------|
| Worker requests/dia | 100.000 | 1.440 (1 min) | 98% |
| Subrequests/invocação | 50 | 50 | 0% |
| CPU time/invocação | 10ms | ~5ms | 50% |
| R2 storage | 10 GB | ~250 MB | 97% |
| R2 Class A ops/mês | 1M | ~100k | 90% |
| **Capacidade total/dia** | - | **72.000 req** | - |
| **Necessário/dia** | - | **52.000 req** | **38%** |

## 🐛 Troubleshooting

### Worker não executa

```bash
# Verificar cron
wrangler deployments list

# Ver logs de erro
wrangler tail --format pretty

# Trigger manual
curl -X POST https://djen-scraper.YOUR_SUBDOMAIN.workers.dev/trigger
```

### Erro de KV

```bash
# Verificar namespace existe
wrangler kv:namespace list

# Recriar (se necessário)
wrangler kv:namespace create "DJEN_STATE"

# Atualizar wrangler.toml com novo ID
```

### Erro de R2

```bash
# Verificar bucket existe
wrangler r2 bucket list

# Recriar
wrangler r2 bucket create djen-buffer
```

### Proxy timeout

O proxy Cloud Run tem timeout de 30s. Se requests estão falhando:

```bash
# Ver logs do proxy
# (necessita gcloud configurado)
gcloud run services logs read djen-proxy --region=southamerica-east1
```

## 📁 Estrutura do Projeto

```
djen-scraper/
├── README.md                     # Este arquivo
├── cloudflare/
│   └── worker/
│       ├── src/
│       │   └── index.ts         # Worker TypeScript
│       ├── wrangler.toml        # Configuração Cloudflare
│       ├── tsconfig.json        # Config TypeScript
│       └── package.json         # Dependências
└── scripts/
    ├── setup.sh                 # Setup inicial (KV + R2)
    ├── deploy.sh                # Deploy worker
    └── process_and_archive.sh   # Fase 2: Parquet + IA
```

## 🔐 Segurança

- Worker é **stateless** - sem dados sensíveis no código
- Proxy usa **whitelist** - zero-trust security
- R2 é **privado** - apenas o worker tem acesso
- KV é **privado** - apenas o worker tem acesso

## 📝 Licença

MIT

## 🤝 Contribuindo

Pull requests são bem-vindos!

## 📧 Suporte

Abra uma issue no repositório.

---

**Status:** ✅ MVP Fase 1 Completo
**Próximo:** Implementar Fase 2 (Parquet + Internet Archive)
