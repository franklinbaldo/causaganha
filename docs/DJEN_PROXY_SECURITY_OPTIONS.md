# 🛡️ Opções de Segurança para DJEN Proxy

## Você perguntou: "tem como essa validação ser feita pelo Google antes da função ser acionada?"

**Resposta:** SIM! Existem 3 níveis de proteção:

---

## 🎯 Opção 1: Validação no CÓDIGO (Atual - GRATUITO ✅)

**Como funciona:**
- Validações acontecem dentro do código Go
- Request chega no Cloud Run → código valida → aceita ou rejeita

**Vantagens:**
- ✅ **100% GRATUITO** (free tier Cloud Run)
- ✅ Implementação simples
- ✅ Controle total sobre regras
- ✅ Logging detalhado

**Desvantagens:**
- ❌ Função é acionada mesmo para requests inválidos (consome recursos)
- ❌ Validação acontece DEPOIS do request chegar

**Uso:**
```bash
./scripts/redeploy-secure-djen-proxy.sh
```

**Proteções:**
```go
// Bloqueia URLs externas
if strings.Contains(path, "http://") { return 403 }

// Bloqueia Host manipulation
if Host != ".run.app" { return 403 }
```

---

## 🔥 Opção 2: Cloud Run Ingress (GRATUITO ✅)

**Como funciona:**
- Cloud Run bloqueia no EDGE (antes da função)
- Usa recursos nativos do Google Cloud

**Vantagens:**
- ✅ **100% GRATUITO** (recursos nativos)
- ✅ Bloqueio no EDGE (economiza recursos)
- ✅ HTTPS obrigatório (TLS 1.2+)
- ✅ DDoS protection nativo
- ✅ Rate limiting por concorrência

**Desvantagens:**
- ⚠️ Menos flexível que Cloud Armor
- ⚠️ Não filtra por pattern de URL

**Uso:**
```bash
./scripts/secure-djen-proxy-with-ingress.sh
```

**Proteções nativas:**
```yaml
Max concurrency: 80 req simultâneas
Timeout: 30s
Auto-scale: 0→10 instâncias
HTTPS: Obrigatório (TLS 1.2+)
DDoS: Google Cloud nativo
```

---

## 🚀 Opção 3: Cloud Armor (WAF) (PAGO 💰)

**Como funciona:**
- WAF do Google (Web Application Firewall)
- Requer Load Balancer + Cloud Run
- Bloqueia no EDGE antes de chegar no Load Balancer

**Vantagens:**
- ✅ Máxima proteção
- ✅ Regras avançadas (regex, geolocation, etc)
- ✅ Rate limiting por IP
- ✅ Bloqueio de bots/scanners
- ✅ Dashboard de segurança

**Desvantagens:**
- ❌ **PAGO:** ~$0.75/mês (regras) + $1.00/1M requests (Load Balancer)
- ❌ Setup mais complexo
- ❌ Overhead de Load Balancer

**Uso:**
```bash
./scripts/setup-cloud-armor-djen.sh
```

**Custo estimado (CausaGanha):**
```
Load Balancer: $1/mês (1M forwarding rules)
Cloud Armor:   $1/mês (5 regras)
Requests:      $0.01/10k requests
─────────────────────────────
Total:         ~$3-5/mês
```

**Regras avançadas:**
```yaml
# Bloquear URLs externas no path
expression: "request.path.contains('http://')"
action: deny-403

# Rate limiting: 100 req/min por IP
rate-limit: 100/60s
ban-duration: 10min

# Bloquear scanners
user-agent: contains('nmap') || contains('masscan')
action: deny-403

# Geolocation: Permitir só Brasil
origin.region_code != "BR"
action: deny-403
```

---

## 🎯 Recomendação para CausaGanha

### **Use Opção 1 + Opção 2 (100% GRATUITO)**

```bash
# 1. Deploy com validações no código
./scripts/redeploy-secure-djen-proxy.sh

# 2. Aplicar ingress controls nativos
./scripts/secure-djen-proxy-with-ingress.sh
```

**Por quê?**
- ✅ **Zero custo** (dentro do free tier)
- ✅ **Dupla camada** de proteção
- ✅ Suficiente para 99% dos casos
- ✅ Bloqueia uso malicioso efetivamente

**Proteções combinadas:**
```
Internet → Cloud Run (HTTPS obrigatório, DDoS native, max 80 concurrent)
           ↓
       Código Go (valida domínio, path, headers)
           ↓
       DJEN API
```

---

## 📊 Comparação

| Proteção | Opção 1 (Código) | Opção 2 (Ingress) | Opção 3 (Armor) |
|----------|------------------|-------------------|-----------------|
| **Custo** | 💚 Grátis | 💚 Grátis | 💰 $3-5/mês |
| **Setup** | 🟢 Simples | 🟢 Simples | 🔴 Complexo |
| **Bloqueio no EDGE** | ❌ Não | ✅ Parcial | ✅ Total |
| **Rate limiting** | ❌ Não | ✅ Por concorrência | ✅ Por IP |
| **URL filtering** | ✅ Sim | ❌ Não | ✅ Sim |
| **Geolocation** | ❌ Não | ❌ Não | ✅ Sim |
| **Bot protection** | ⚠️ Básico | ⚠️ Básico | ✅ Avançado |
| **Recomendado?** | ✅ Sim | ✅ Sim | ⚠️ Só se necessário |

---

## 🧪 Testar Proteções

```bash
PROXY_URL="https://djen-proxy-590717404688.southamerica-east1.run.app"

# ✅ Deve funcionar
curl $PROXY_URL/health
curl "$PROXY_URL/api/v1/comunicacao?idOrgao=2"

# ❌ Deve bloquear (403)
curl $PROXY_URL/http://google.com
curl -H "Host: evil.com" $PROXY_URL/

# ❌ Deve bloquear (429 - rate limit)
for i in {1..200}; do curl $PROXY_URL/health & done
```

---

## ✅ Decisão Final

**Para CausaGanha:** Use **Opção 1 + Opção 2** (gratuito)

**Quando considerar Opção 3:**
- Mais de 10M requests/mês
- Ataques DDoS recorrentes
- Necessidade de geolocation filtering
- Orçamento disponível para WAF

---

## 📝 Próximos Passos

1. ✅ Rodar `./scripts/redeploy-secure-djen-proxy.sh` no Cloud Shell
2. ✅ Testar bloqueios de segurança
3. ✅ Monitorar logs por 1 semana
4. ⚠️ Se detectar abuso: considerar Cloud Armor

**Status:** 🛡️ Proxy protegido com validações no código (Opção 1)
