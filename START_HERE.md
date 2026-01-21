# 🚀 DJEN PROXY - SOLUÇÃO FINAL SIMPLES

## ❌ Esqueça tudo que tentamos antes

Começamos do **ZERO** com solução MÍNIMA e FUNCIONAL.

---

## 📋 COPIE E COLE NO GOOGLE CLOUD SHELL:

```bash
curl -fsSL https://raw.githubusercontent.com/franklinbaldo/causaganha/claude/google-shell-proxy-script-ZARcJ/DJEN_FINAL.sh | bash
```

---

## ✅ O que esse script faz:

1. **Cria 2 arquivos** (djen_proxy.go + Dockerfile)
2. **Testa local** (3 testes, 2 segundos)
3. **Pergunta** se quer fazer deploy
4. **Deploy** no Cloud Run (São Paulo)
5. **Mostra URL**

**Tempo total: 3 minutos**

---

## 🛡️ Whitelist (zero-trust):

### Permite apenas:
```
✅ /api/*
✅ /swagger/*
✅ /comunicacao*
✅ /login*
✅ /health
✅ /security
```

### Bloqueia tudo mais:
```
❌ /evil          → 403
❌ /malicious     → 403
❌ QUALQUER OUTRA COISA → 403
```

---

## 🧪 Testes:

```bash
# Após deploy
export PROXY_URL="https://djen-proxy-xxx.run.app"

# Deve funcionar (200)
curl $PROXY_URL/health

# Deve bloquear (403)
curl $PROXY_URL/evil

# API DJEN (permitido)
curl "$PROXY_URL/api/v1/comunicacao?idOrgao=2"
```

---

## 📝 Usar no CausaGanha:

```bash
export DJEN_PROXY_URL='https://djen-proxy-xxx.run.app'
```

---

## 🔄 Refazer do zero:

```bash
# Deletar serviço
gcloud run services delete djen-proxy --region southamerica-east1 --quiet

# Rodar script novamente
curl -fsSL https://raw.githubusercontent.com/franklinbaldo/causaganha/claude/google-shell-proxy-script-ZARcJ/DJEN_FINAL.sh | bash
```

---

## 💰 Custo: $0 (Free tier)

---

## ✅ Pronto!

**Simples, funcional, seguro.** 🎯
