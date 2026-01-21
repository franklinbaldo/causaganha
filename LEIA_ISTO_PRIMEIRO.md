# 🚀 DJEN PROXY - INSTRUÇÕES SIMPLES

## ❌ **Por que os scripts anteriores falharam?**

1. Assumiam que arquivos existiam no Cloud Shell
2. Não testavam localmente antes de fazer deploy
3. Faziam deploy de código não testado

---

## ✅ **SOLUÇÃO: Script Completo com Teste Local**

Este script:
1. ✅ Cria TODOS os arquivos necessários
2. ✅ Testa LOCALMENTE primeiro (porta 8888)
3. ✅ Só faz deploy se os testes passarem
4. ✅ Testa novamente no Cloud Run após deploy

---

## 📋 **COPIE E COLE NO GOOGLE CLOUD SHELL:**

```bash
curl -fsSL https://raw.githubusercontent.com/franklinbaldo/causaganha/claude/google-shell-proxy-script-ZARcJ/DJEN_PROXY_COMPLETE.sh | bash
```

---

## 🔍 **O que vai acontecer:**

### **FASE 1: Teste Local (2 min)**
```
📝 Criando arquivos...
✅ Arquivos criados

🧪 TESTE LOCAL
Compilando e rodando localmente...
✅ Proxy rodando local no PID 12345 (porta 8888)

📊 Testes locais:
1️⃣ Health check: {"status":"healthy","secure":"true"}
2️⃣ Security info: {"security":"enabled"}
3️⃣ Debug endpoint: {"path":"/debug","uri":"/debug"}
4️⃣ Bloquear http://google.com: Status: 403 ✅
5️⃣ API DJEN legítima: Status: 200 ✅

✅ Testes locais PASSARAM!

🚀 Deploy no Cloud Run? (y/n):
```

**👉 Se os testes locais falharem, o script PARA e mostra os logs.**

### **FASE 2: Deploy (2 min)**
```
🚀 DEPLOY NO CLOUD RUN
Building using Dockerfile...
✅ Deploy concluído!
```

### **FASE 3: Teste no Cloud Run (30 seg)**
```
🧪 TESTE NO CLOUD RUN
URL: https://djen-proxy-xxx.run.app

1️⃣ Health check: ✅
2️⃣ Debug endpoint: ✅
3️⃣ Bloquear http://google.com: ✅ (403)
4️⃣ API DJEN legítima: ✅ (200)

✅ CONCLUÍDO!
```

---

## 🧪 **O que está sendo testado:**

| Teste | Local | Cloud Run | Esperado |
|-------|-------|-----------|----------|
| Health check | ✅ | ✅ | 200 |
| Security info | ✅ | ✅ | 200 |
| Debug endpoint | ✅ | ✅ | 200 |
| Bloquear `http://google.com` | ✅ | ✅ | **403** |
| Bloquear `https://evil.com` | ✅ | ✅ | **403** |
| API DJEN legítima | ✅ | ✅ | 200 |

---

## 🛡️ **Proteções Implementadas:**

```go
// Bloqueia URLs externas no path OU no URI
if strings.Contains(path, "http://") ||
   strings.Contains(path, "https://") ||
   strings.Contains(uri, "http://") ||
   strings.Contains(uri, "https://") {
    return 403 Forbidden
}
```

**Bloqueia:**
- ❌ `/http://google.com`
- ❌ `/https://evil.com`
- ❌ `/api/http://malicious.com`

**Permite:**
- ✅ `/health`
- ✅ `/security`
- ✅ `/api/v1/comunicacao`
- ✅ `/swagger/djen.yml`

---

## ⏱️ **Tempo Total: ~5 minutos**

- Teste local: 2 min
- Build Docker: 2 min
- Deploy: 1 min
- Teste Cloud Run: 30 seg

---

## 🆘 **Se algo falhar:**

### **Falha nos testes locais:**
```bash
❌ BLOQUEIO FALHOU! Status: 404 (esperado 403)

Ver logs:
[logs do proxy local]
```

**Ação:** O script mostra os logs e para. **NÃO FAZ DEPLOY** de código quebrado.

### **Falha no Cloud Run:**
```bash
❌ BLOQUEIO FALHOU NO CLOUD RUN!

Ver logs do Cloud Run:
[últimas 30 linhas dos logs]
```

**Ação:** Ver logs completos:
```bash
gcloud run services logs read djen-proxy --region southamerica-east1 --limit 100
```

---

## 💰 **Custo: $0 (Free Tier)**

- Cloud Run: 2M requests/mês grátis
- Cloud Build: 120 builds/dia grátis
- Uso estimado: ~10k requests/dia = **100% grátis**

---

## 📝 **Após o deploy:**

Configure no CausaGanha:
```bash
export DJEN_PROXY_URL='https://djen-proxy-590717404688.southamerica-east1.run.app'
```

Testar:
```bash
# Deve funcionar (200)
curl $DJEN_PROXY_URL/health

# Deve bloquear (403)
curl $DJEN_PROXY_URL/http://google.com
```

---

## 🔄 **Para refazer do zero:**

```bash
# 1. Deletar serviço existente
gcloud run services delete djen-proxy --region southamerica-east1 --quiet

# 2. Rodar script novamente
curl -fsSL https://raw.githubusercontent.com/franklinbaldo/causaganha/claude/google-shell-proxy-script-ZARcJ/DJEN_PROXY_COMPLETE.sh | bash
```

---

## ✅ **Pronto!**

**Você tinha razão:** devemos testar localmente antes de fazer deploy. Este script faz exatamente isso! 🚀

**Cole no Google Cloud Shell e veja a mágica acontecer!** ✨
