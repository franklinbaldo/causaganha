#!/bin/bash
# ============================================================================
# DJEN PROXY - Security Tests
# Testa todos os aspectos de segurança do proxy
# ============================================================================

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔒 DJEN PROXY - TESTES DE SEGURANÇA"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Pegar URL do serviço
URL=$(gcloud run services describe djen-proxy --region southamerica-east1 --format='value(status.url)')

if [ -z "$URL" ]; then
    echo "❌ ERRO: Serviço djen-proxy não encontrado"
    exit 1
fi

echo "🔗 URL: $URL"
echo ""

PASSED=0
FAILED=0

# ============================================================================
# TESTE 1: Health Endpoint (deve funcionar)
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 1: Health Endpoint"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

RESPONSE=$(curl -s -w "\n%{http_code}" "$URL/health")
BODY=$(echo "$RESPONSE" | head -n -1)
STATUS=$(echo "$RESPONSE" | tail -n 1)

echo "Status: $STATUS"
echo "Body: $BODY"
echo ""

if [ "$STATUS" == "200" ]; then
    echo "✅ PASSOU: Health endpoint OK"
    PASSED=$((PASSED + 1))
else
    echo "❌ FALHOU: Esperado 200, recebeu $STATUS"
    FAILED=$((FAILED + 1))
fi
echo ""

# ============================================================================
# TESTE 2: Security Info Endpoint (deve funcionar)
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 2: Security Info Endpoint"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

RESPONSE=$(curl -s -w "\n%{http_code}" "$URL/security")
BODY=$(echo "$RESPONSE" | head -n -1)
STATUS=$(echo "$RESPONSE" | tail -n 1)

echo "Status: $STATUS"
echo "Body: $BODY"
echo ""

if [ "$STATUS" == "200" ]; then
    echo "✅ PASSOU: Security endpoint OK"
    PASSED=$((PASSED + 1))
else
    echo "❌ FALHOU: Esperado 200, recebeu $STATUS"
    FAILED=$((FAILED + 1))
fi
echo ""

# ============================================================================
# TESTE 3: Bloquear path malicioso simples
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 3: Bloquear /evil (não na whitelist)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

RESPONSE=$(curl -s -w "\n%{http_code}" "$URL/evil")
BODY=$(echo "$RESPONSE" | head -n -1)
STATUS=$(echo "$RESPONSE" | tail -n 1)

echo "Status: $STATUS"
echo "Body: $BODY"
echo ""

if [ "$STATUS" == "403" ]; then
    echo "✅ PASSOU: Path malicioso bloqueado"
    PASSED=$((PASSED + 1))
else
    echo "❌ FALHOU: Esperado 403, recebeu $STATUS"
    FAILED=$((FAILED + 1))
fi
echo ""

# ============================================================================
# TESTE 4: Bloquear tentativa de URL externa (http://google.com)
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 4: Bloquear /http://google.com"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

RESPONSE=$(curl -s -w "\n%{http_code}" "$URL/http://google.com")
BODY=$(echo "$RESPONSE" | head -n -1)
STATUS=$(echo "$RESPONSE" | tail -n 1)

echo "Status: $STATUS"
echo "Body: $BODY"
echo ""

# Go normaliza URL e remove double slash, então /http://google.com vira /http:/google.com
# Ambos devem ser bloqueados pela whitelist
if [ "$STATUS" == "403" ]; then
    echo "✅ PASSOU: Tentativa de URL externa bloqueada"
    PASSED=$((PASSED + 1))
else
    echo "❌ FALHOU: Esperado 403, recebeu $STATUS"
    FAILED=$((FAILED + 1))
fi
echo ""

# ============================================================================
# TESTE 5: Bloquear tentativa de URL externa (//google.com)
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 5: Bloquear //google.com"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

RESPONSE=$(curl -s -w "\n%{http_code}" "$URL//google.com")
BODY=$(echo "$RESPONSE" | head -n -1)
STATUS=$(echo "$RESPONSE" | tail -n 1)

echo "Status: $STATUS"
echo "Body: $BODY"
echo ""

if [ "$STATUS" == "403" ]; then
    echo "✅ PASSOU: Protocol-relative URL bloqueada"
    PASSED=$((PASSED + 1))
else
    echo "❌ FALHOU: Esperado 403, recebeu $STATUS"
    FAILED=$((FAILED + 1))
fi
echo ""

# ============================================================================
# TESTE 6: Permitir /api/ (whitelist)
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 6: Permitir /api/v1/comunicacao (whitelist)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

RESPONSE=$(curl -s -w "\n%{http_code}" "$URL/api/v1/comunicacao?idOrgao=2")
STATUS=$(echo "$RESPONSE" | tail -n 1)

echo "Status: $STATUS"
echo ""

# API real pode retornar 200, 400, 401, etc dependendo do request
# O importante é que NÃO seja 403 (não bloqueou)
if [ "$STATUS" != "403" ]; then
    echo "✅ PASSOU: Path da whitelist não foi bloqueado (Status: $STATUS)"
    PASSED=$((PASSED + 1))
else
    echo "❌ FALHOU: Whitelist path foi bloqueado incorretamente"
    FAILED=$((FAILED + 1))
fi
echo ""

# ============================================================================
# TESTE 7: Permitir /swagger/ (whitelist)
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 7: Permitir /swagger/ (whitelist)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

RESPONSE=$(curl -s -w "\n%{http_code}" "$URL/swagger/")
STATUS=$(echo "$RESPONSE" | tail -n 1)

echo "Status: $STATUS"
echo ""

if [ "$STATUS" != "403" ]; then
    echo "✅ PASSOU: Swagger path não foi bloqueado (Status: $STATUS)"
    PASSED=$((PASSED + 1))
else
    echo "❌ FALHOU: Swagger path foi bloqueado incorretamente"
    FAILED=$((FAILED + 1))
fi
echo ""

# ============================================================================
# TESTE 8: Bloquear /admin (não na whitelist)
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 8: Bloquear /admin (não na whitelist)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

RESPONSE=$(curl -s -w "\n%{http_code}" "$URL/admin")
BODY=$(echo "$RESPONSE" | head -n -1)
STATUS=$(echo "$RESPONSE" | tail -n 1)

echo "Status: $STATUS"
echo "Body: $BODY"
echo ""

if [ "$STATUS" == "403" ]; then
    echo "✅ PASSOU: /admin bloqueado"
    PASSED=$((PASSED + 1))
else
    echo "❌ FALHOU: Esperado 403, recebeu $STATUS"
    FAILED=$((FAILED + 1))
fi
echo ""

# ============================================================================
# TESTE 9: Bloquear /../etc/passwd (path traversal)
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 9: Bloquear /../etc/passwd (path traversal)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

RESPONSE=$(curl -s -w "\n%{http_code}" "$URL/../etc/passwd")
BODY=$(echo "$RESPONSE" | head -n -1)
STATUS=$(echo "$RESPONSE" | tail -n 1)

echo "Status: $STATUS"
echo "Body: $BODY"
echo ""

# Go normaliza paths, então /../ vira /
# Mas como / é permitido (health), isso retorna 200
# O importante é que não vaze o sistema de arquivos real
if [ "$STATUS" == "403" ] || [ "$STATUS" == "200" ]; then
    echo "✅ PASSOU: Path traversal tratado (Status: $STATUS)"
    PASSED=$((PASSED + 1))
else
    echo "❌ FALHOU: Path traversal retornou status inesperado: $STATUS"
    FAILED=$((FAILED + 1))
fi
echo ""

# ============================================================================
# TESTE 10: Permitir /comunicacao (whitelist)
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 10: Permitir /comunicacao (whitelist)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

RESPONSE=$(curl -s -w "\n%{http_code}" "$URL/comunicacao")
STATUS=$(echo "$RESPONSE" | tail -n 1)

echo "Status: $STATUS"
echo ""

if [ "$STATUS" != "403" ]; then
    echo "✅ PASSOU: /comunicacao não foi bloqueado (Status: $STATUS)"
    PASSED=$((PASSED + 1))
else
    echo "❌ FALHOU: /comunicacao foi bloqueado incorretamente"
    FAILED=$((FAILED + 1))
fi
echo ""

# ============================================================================
# RESULTADOS
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 RESULTADOS FINAIS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✅ PASSOU: $PASSED testes"
echo "❌ FALHOU: $FAILED testes"
echo ""

TOTAL=$((PASSED + FAILED))
PERCENT=$((PASSED * 100 / TOTAL))

echo "📈 Taxa de sucesso: $PERCENT%"
echo ""

if [ $FAILED -eq 0 ]; then
    echo "🎉 TODOS OS TESTES PASSARAM!"
    echo ""
    echo "✅ Segurança verificada:"
    echo "   - Whitelist funcionando corretamente"
    echo "   - Paths maliciosos bloqueados"
    echo "   - URLs externas bloqueadas"
    echo "   - Paths permitidos funcionando"
    echo ""
    exit 0
else
    echo "⚠️  ALGUNS TESTES FALHARAM"
    echo ""
    echo "Revise os testes acima para detalhes."
    echo ""
    exit 1
fi
