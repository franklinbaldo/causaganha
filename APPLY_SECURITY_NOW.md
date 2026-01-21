# 🔒 APLICAR SEGURANÇA NO DJEN PROXY AGORA

## 📋 COPIE E COLE NO GOOGLE CLOUD SHELL:

```bash
curl -fsSL https://raw.githubusercontent.com/franklinbaldo/causaganha/claude/google-shell-proxy-script-ZARcJ/apply-security-final.sh | bash
```

---

## OU faça download manual:

```bash
# 1. Baixar script
wget https://raw.githubusercontent.com/franklinbaldo/causaganha/claude/google-shell-proxy-script-ZARcJ/apply-security-final.sh

# 2. Dar permissão
chmod +x apply-security-final.sh

# 3. Executar
./apply-security-final.sh
```

---

## 🎯 O que esse script faz:

1. ✅ Cria código Go com middleware de segurança
2. ✅ Cria Dockerfile otimizado
3. ✅ Faz deploy seguro no Cloud Run (São Paulo)
4. ✅ **Testa AUTOMATICAMENTE** as 6 proteções:
   - Health check (deve funcionar)
   - Security endpoint (deve funcionar)
   - Bloqueio de http:// externo (deve retornar 403)
   - Bloqueio de https:// externo (deve retornar 403)
   - API DJEN legítima (deve funcionar)
   - Swagger DJEN (deve funcionar)
5. ✅ Mostra relatório completo de segurança

---

## 🛡️ Proteções Implementadas:

### **Nível 1: Código Go (Middleware)**
- ✅ Whitelist: Apenas `comunicaapi.pje.jus.br`
- ✅ Bloqueia `http://` e `https://` no path
- ✅ Valida Host header
- ✅ Logging de tentativas de abuso

### **Nível 2: Cloud Run Nativo**
- ✅ HTTPS obrigatório (TLS 1.2+)
- ✅ DDoS protection (Google)
- ✅ Rate limiting: 80 req concorrentes
- ✅ Timeout: 30s
- ✅ Auto-escala: 0→10 instâncias

---

## ⏱️ Tempo de execução: ~3-4 minutos

O script vai:
- Build do container: ~2 min
- Deploy no Cloud Run: ~1 min
- Testes automáticos: ~30 seg

---

## ✅ Resultado Esperado:

```
🧪 EXECUTANDO TESTES DE SEGURANÇA...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Teste 1: Health check
   ✅ PASSOU - Health check OK (200)

✅ Teste 2: Security endpoint
   ✅ PASSOU - Security endpoint OK (200)

❌ Teste 3: Bloquear http://google.com
   ✅ PASSOU - Bloqueou corretamente (403)

❌ Teste 4: Bloquear https://evil.com
   ✅ PASSOU - Bloqueou corretamente (403)

✅ Teste 5: API DJEN legítima
   ✅ PASSOU - API DJEN OK (200)

✅ Teste 6: Swagger DJEN
   ✅ PASSOU - Swagger OK (200, 548 linhas)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ SEGURANÇA APLICADA E TESTADA!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔒 URL do Proxy Seguro:
   https://djen-proxy-590717404688.southamerica-east1.run.app

🛡️  Proteções ativas:
   ✅ Bloqueia URLs externas
   ✅ Bloqueia manipulação de Host header
   ✅ Rate limiting (80 req/s)
   ✅ Timeout de 30s
   ✅ HTTPS obrigatório
   ✅ DDoS protection
   ✅ Auto-escala 0→10
```

---

## 🚨 Se algo falhar:

```bash
# Ver logs do Cloud Run
gcloud run services logs read djen-proxy \
  --region southamerica-east1 \
  --limit 50

# Ver status do serviço
gcloud run services describe djen-proxy \
  --region southamerica-east1

# Refazer deploy
./apply-security-final.sh
```

---

## 📝 Após o deploy:

Configure no CausaGanha:
```bash
export DJEN_PROXY_URL='https://djen-proxy-590717404688.southamerica-east1.run.app'
```

Testar:
```bash
# Deve funcionar
curl $DJEN_PROXY_URL/health

# Deve bloquear (403)
curl $DJEN_PROXY_URL/http://google.com
```

---

## ❓ Por que o script anterior não funcionou?

O proxy atual ainda está rodando o código antigo (sem proteções). Este novo script:
1. ✅ Usa Dockerfile para garantir build limpo
2. ✅ Força redeploy completo
3. ✅ Aguarda 10s para propagação
4. ✅ Testa TUDO automaticamente

---

## 💰 Custo: $0 (Free Tier)

- Cloud Run: 2M requests/mês grátis
- Cloud Build: 120 builds/dia grátis
- Seu uso: ~10k requests/dia = 100% grátis

---

**Pronto para rodar! 🚀**
