# DJEN Proxy - Endpoint de Produção

## 🔗 URL de Produção

```
https://djen-proxy-mhgmawcn3a-rj.a.run.app
```

## 📍 Informações

| Parâmetro | Valor |
|-----------|-------|
| **URL** | `https://djen-proxy-mhgmawcn3a-rj.a.run.app` |
| **Região** | São Paulo, Brasil (`southamerica-east1`) |
| **Plataforma** | Google Cloud Run |
| **Status** | ✅ Ativo |
| **Versão** | v4.0 |
| **Segurança** | Whitelist (zero-trust) |
| **Custo** | $0 (free tier) |

## 🔒 Segurança

**Whitelist permitida:**
- `/api/*` - API DJEN
- `/swagger/*` - Documentação Swagger
- `/comunicacao*` - Endpoint de comunicações
- `/login*` - Autenticação
- `/health` - Health check do proxy
- `/security` - Info de segurança

**Todos os outros paths retornam 403 Forbidden.**

## 🧪 Endpoints de Teste

### Health Check
```bash
curl https://djen-proxy-mhgmawcn3a-rj.a.run.app/health
```
**Resposta esperada:**
```json
{"status":"ok","version":"v4.0"}
```

### Security Info
```bash
curl https://djen-proxy-mhgmawcn3a-rj.a.run.app/security
```
**Resposta esperada:**
```json
{
  "whitelist": ["/api/", "/swagger/", "/comunicacao", "/login"],
  "version": "v4.0"
}
```

### API DJEN (Exemplo)
```bash
curl "https://djen-proxy-mhgmawcn3a-rj.a.run.app/api/v1/comunicacao?dataPublicacao=2025-01-21&idOrgao=TRF1"
```
**Resposta:** JSON com comunicações do TRF1

## 🚀 Uso no DJEN Scraper

O scraper Cloudflare Worker usa este proxy automaticamente:

```typescript
// Em djen-scraper/cloudflare/worker/wrangler.toml
[vars]
PROXY_URL = "https://djen-proxy-mhgmawcn3a-rj.a.run.app"
```

## 📊 Testes de Segurança

Execute a suite completa de testes:

```bash
./TEST_DJEN_SECURITY.sh
```

**Resultados esperados:**
- ✅ 10/10 testes passam
- ✅ Taxa de sucesso: 100%

## 🔄 Redeploy

Se precisar fazer redeploy (atualizar código, etc):

```bash
./DEPLOY_DJEN_V4.sh
```

**O script faz:**
1. Deleta serviço existente automaticamente
2. Deploy do código v4.0 com graceful shutdown
3. Testa health, segurança e API
4. Mostra nova URL (normalmente a mesma)

## 📝 Logs

Ver logs em tempo real:

```bash
# Requer gcloud configurado
gcloud run services logs read djen-proxy \
  --region=southamerica-east1 \
  --project=virtual-computer-fsb
```

## ⚠️ Limites

| Limite | Valor |
|--------|-------|
| Timeout | 30s por request |
| Memória | 512 MB |
| Concorrência | 10 instâncias max |
| Custo | $0 (free tier) |

## 🔐 Propriedades de Segurança

- ✅ **Zero-trust whitelist** - Apenas paths explicitamente permitidos
- ✅ **Path traversal bloqueado** - `/../etc/passwd` retorna 403
- ✅ **URLs externas bloqueadas** - `/http://google.com` retorna 403
- ✅ **Protocol-relative bloqueado** - `//google.com` retorna 403
- ✅ **Graceful shutdown** - Não perde requests durante deploy
- ✅ **Error handling** - Logs apropriados, timeouts configurados

## 📦 Código-fonte

- **Proxy Go:** `djen_proxy.go` (80 linhas)
- **Deploy script:** `DEPLOY_DJEN_V4.sh`
- **Testes:** `TEST_DJEN_SECURITY.sh`

## 🌐 Acesso Público

O proxy está configurado como `--allow-unauthenticated` para permitir uso pelo Cloudflare Worker.

**Segurança é garantida pela whitelist de paths, não por autenticação.**

---

**Última atualização:** 2025-01-21
**Status:** ✅ Produção, testado e funcionando
