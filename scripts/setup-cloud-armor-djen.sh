#!/bin/bash
# ============================================================================
# Cloud Armor - Segurança no EDGE (antes da função)
# Bloqueia requests maliciosos ANTES de chegar no Cloud Run
# ============================================================================

set -e

PROJECT_ID=$(gcloud config get-value project)
REGION="southamerica-east1"
SERVICE_NAME="djen-proxy"

echo "🛡️  Configurando Cloud Armor para DJEN Proxy..."
echo ""

# 1. Criar política de segurança do Cloud Armor
echo "📝 Criando política de segurança..."
gcloud compute security-policies create djen-proxy-security \
  --description "Segurança para DJEN Proxy - Bloqueia uso malicioso" \
  --region $REGION \
  || echo "Política já existe, continuando..."

# 2. REGRA 1: Bloquear URLs com http:// ou https:// no path
echo "🚫 Regra 1: Bloqueando URLs externas no path..."
gcloud compute security-policies rules create 1000 \
  --security-policy djen-proxy-security \
  --expression "request.path.contains('http://') || request.path.contains('https://')" \
  --action "deny-403" \
  --description "Bloqueia tentativas de proxy para URLs externas" \
  --region $REGION \
  || echo "Regra 1 já existe"

# 3. REGRA 2: Bloquear certos user-agents maliciosos
echo "🚫 Regra 2: Bloqueando user-agents suspeitos..."
gcloud compute security-policies rules create 2000 \
  --security-policy djen-proxy-security \
  --expression "has(request.headers['user-agent']) && (request.headers['user-agent'].contains('masscan') || request.headers['user-agent'].contains('nmap') || request.headers['user-agent'].contains('nikto'))" \
  --action "deny-403" \
  --description "Bloqueia scanners de vulnerabilidade" \
  --region $REGION \
  || echo "Regra 2 já existe"

# 4. REGRA 3: Rate limiting (100 req/minuto por IP)
echo "⏱️  Regra 3: Configurando rate limiting..."
gcloud compute security-policies rules create 3000 \
  --security-policy djen-proxy-security \
  --expression "true" \
  --action "rate-based-ban" \
  --rate-limit-threshold-count 100 \
  --rate-limit-threshold-interval-sec 60 \
  --ban-duration-sec 600 \
  --conform-action "allow" \
  --exceed-action "deny-429" \
  --description "Limita a 100 req/min por IP" \
  --region $REGION \
  || echo "Regra 3 já existe"

# 5. REGRA 4: Whitelist de paths permitidos
echo "✅ Regra 4: Permitindo apenas paths legítimos..."
gcloud compute security-policies rules create 4000 \
  --security-policy djen-proxy-security \
  --expression "request.path.matches('^/(health|security|api/.*|swagger/.*)$')" \
  --action "allow" \
  --description "Permite apenas paths da API DJEN" \
  --region $REGION \
  || echo "Regra 4 já existe"

# 6. REGRA DEFAULT: Deny all (fallback)
echo "🔒 Regra default: Bloqueando tudo que não passou..."
gcloud compute security-policies rules update 2147483647 \
  --security-policy djen-proxy-security \
  --action "deny-403" \
  --region $REGION \
  || echo "Regra default já configurada"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Cloud Armor configurado com sucesso!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🛡️  Proteções ativas:"
echo "   1. Bloqueio de URLs externas no path"
echo "   2. Bloqueio de scanners de vulnerabilidade"
echo "   3. Rate limiting: 100 req/min por IP"
echo "   4. Whitelist de paths permitidos"
echo ""
echo "📊 Ver regras:"
echo "   gcloud compute security-policies describe djen-proxy-security --region $REGION"
echo ""
echo "📈 Ver logs de bloqueio:"
echo "   gcloud logging read 'resource.type=\"cloud_run_revision\" AND jsonPayload.securityPolicyRequestData.action=\"DENY\"' --limit 50"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# NOTA: Para aplicar ao Cloud Run, precisa criar Load Balancer
# Cloud Run standalone não suporta Cloud Armor diretamente
# Alternativa: usar Cloud Run + Load Balancer + Cloud Armor

echo ""
echo "⚠️  IMPORTANTE:"
echo "   Cloud Armor requer Cloud Load Balancer"
echo "   Cloud Run standalone usa proteções do código Go"
echo ""
echo "🔄 Para usar Cloud Armor completo:"
echo "   1. Criar Load Balancer"
echo "   2. Apontar para Cloud Run backend"
echo "   3. Aplicar política Cloud Armor"
echo ""
echo "💡 SOLUÇÃO ATUAL (sem custo adicional):"
echo "   ✅ Validações no código Go (já implementado)"
echo "   ✅ HTTPS obrigatório (Cloud Run nativo)"
echo "   ✅ DDoS protection (Google Cloud nativo)"
echo ""
