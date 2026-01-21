# 🔒 DJEN Proxy Security

## 🚨 Problema Identificado

O proxy DJEN inicial **ACEITAVA QUALQUER DOMÍNIO**, permitindo que terceiros usassem maliciosamente o proxy para acessar outros sites.

**Testes de vulnerabilidade:**
```bash
# ❌ VULNERÁVEL: Aceitava proxy para outros sites
curl https://djen-proxy-xxx.run.app/google.com  # Retornava 200
```

---

## 🛡️ Proteções Implementadas

O novo `djen_proxy_secure.go` implementa:

### 1. **Whitelist de Domínio**
```go
const ALLOWED_TARGET = "https://comunicaapi.pje.jus.br"
```
- ✅ Aceita APENAS `comunicaapi.pje.jus.br`
- ❌ Bloqueia todos os outros domínios

### 2. **Bloqueio de URLs Externas**
```go
if strings.Contains(r.URL.Path, "http://") || strings.Contains(r.URL.Path, "https://") {
    return HTTP 403 Forbidden
}
```
- Detecta tentativas de injetar URLs no path
- Retorna `403 Forbidden` com mensagem clara

### 3. **Validação de Host Header**
```go
if r.Host != "" && !strings.Contains(r.Host, ".run.app") {
    return HTTP 403 Forbidden
}
```
- Bloqueia manipulação de Host header
- Previne ataques de host header injection

### 4. **Logging de Segurança**
```go
log.Printf("🚨 BLOCKED: Attempted to proxy external URL: %s", r.URL.Path)
```
- Registra todas as tentativas de abuso
- Facilita auditoria e monitoramento

---

## 🚀 Deploy da Versão Segura

### **No Google Cloud Shell:**

```bash
# 1. Clone o repositório
git clone https://github.com/franklinbaldo/causaganha.git
cd causaganha

# 2. Execute o script de deploy seguro
chmod +x scripts/redeploy-secure-djen-proxy.sh
./scripts/redeploy-secure-djen-proxy.sh
```

---

## 🧪 Testes de Segurança

### ✅ **Testes que DEVEM funcionar:**

```bash
PROXY_URL="https://djen-proxy-590717404688.southamerica-east1.run.app"

# 1. Health check
curl $PROXY_URL/health
# {"status":"healthy","proxy":"djen-br-secure",...}

# 2. API DJEN legítima
curl "$PROXY_URL/api/v1/comunicacao?idOrgao=2"
# {"status":"success","count":10000,...}

# 3. Info de segurança
curl $PROXY_URL/security
# {"security":"enabled","allowed_target":"comunicaapi.pje.jus.br",...}
```

### ❌ **Testes que DEVEM ser BLOQUEADOS:**

```bash
# 1. Tentativa de proxy para Google
curl $PROXY_URL/http://google.com
# {"error":"Forbidden: This proxy only serves comunicaapi.pje.jus.br"}
# HTTP 403

# 2. Tentativa de proxy para site malicioso
curl $PROXY_URL/https://evil.com/hack
# {"error":"Forbidden: This proxy only serves comunicaapi.pje.jus.br"}
# HTTP 403

# 3. Manipulação de Host header
curl -H "Host: evil.com" $PROXY_URL/
# {"error":"Forbidden: Invalid Host header"}
# HTTP 403
```

---

## 📊 Monitoramento

### **Ver logs de segurança no Cloud Run:**

```bash
# Ver últimos 50 logs (incluindo bloqueios)
gcloud run services logs read djen-proxy \
  --region southamerica-east1 \
  --limit 50

# Filtrar apenas bloqueios de segurança
gcloud run services logs read djen-proxy \
  --region southamerica-east1 \
  --limit 100 | grep "BLOCKED"
```

### **Exemplo de log de bloqueio:**
```
🚨 BLOCKED: Attempted to proxy external URL: /http://google.com
🚨 BLOCKED: Suspicious Host header: evil.com
```

---

## 💰 Custos

O proxy é **gratuito** no free tier do Cloud Run:
- ✅ 2M requests/mês grátis
- ✅ 360.000 GB-segundos/mês grátis
- ✅ Escala automática para zero (custo zero quando não usado)

**Uso típico do CausaGanha:**
- ~10.000 requests/dia = ~300k/mês
- **100% dentro do free tier**

---

## 🔐 Boas Práticas Adicionais

### 1. **Adicionar autenticação (opcional)**
```go
// Requerer API key para requests
if r.Header.Get("X-API-Key") != os.Getenv("PROXY_API_KEY") {
    return HTTP 401 Unauthorized
}
```

### 2. **Rate limiting (opcional)**
```go
// Limitar a 100 req/min por IP
import "golang.org/x/time/rate"
limiter := rate.NewLimiter(rate.Limit(100), 10)
```

### 3. **CORS restrito (opcional)**
```go
// Aceitar apenas do domínio do CausaGanha
w.Header().Set("Access-Control-Allow-Origin", "https://causaganha.com.br")
```

---

## 📝 Arquivo Principal

- **Código seguro:** `djen_proxy_secure.go`
- **Deploy script:** `scripts/redeploy-secure-djen-proxy.sh`
- **URL atual:** `https://djen-proxy-590717404688.southamerica-east1.run.app`

---

## ✅ Checklist de Segurança

- [x] Whitelist de domínio único
- [x] Bloqueio de URLs externas
- [x] Validação de Host header
- [x] Logging de tentativas de abuso
- [x] HTTPS obrigatório
- [x] Timeouts configurados
- [x] Deploy em região brasileira
- [ ] Autenticação por API key (opcional)
- [ ] Rate limiting por IP (opcional)
- [ ] CORS restrito (opcional)

---

## 🆘 Suporte

Se detectar atividade suspeita:

1. Ver logs: `gcloud run services logs read djen-proxy --region southamerica-east1`
2. Reportar issue: https://github.com/franklinbaldo/causaganha/issues
3. Desligar proxy (emergência): `gcloud run services delete djen-proxy --region southamerica-east1`

---

**Status:** 🔒 **SEGURO** - Proxy bloqueado para uso exclusivo do DJEN API
