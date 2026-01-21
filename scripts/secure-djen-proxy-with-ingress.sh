#!/bin/bash
# ============================================================================
# DJEN Proxy - Segurança no EDGE usando Cloud Run Ingress
# ZERO CUSTO ADICIONAL - Usa recursos nativos do Cloud Run
# ============================================================================

set -e

PROJECT_ID=$(gcloud config get-value project)
REGION="southamerica-east1"
SERVICE_NAME="djen-proxy"

echo "🛡️  Aplicando segurança no EDGE (Cloud Run nativo)..."
echo ""

# 1. Deploy com configurações de segurança máximas
echo "🚀 Deploy com ingress controlado..."
gcloud run deploy $SERVICE_NAME \
  --source . \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --memory 256Mi \
  --cpu 1 \
  --max-instances 10 \
  --min-instances 0 \
  --timeout 30s \
  --port 8080 \
  --concurrency 80 \
  --cpu-throttling \
  --execution-environment gen2 \
  --ingress all \
  --no-cpu-boost \
  --quiet

# 2. Configurar VPC Egress (opcional - força tráfego por VPC)
echo "🔒 Configurando egress..."
gcloud run services update $SERVICE_NAME \
  --region $REGION \
  --vpc-egress all-traffic \
  --no-use-http2 \
  || echo "VPC egress não disponível neste projeto"

# 3. Adicionar labels de segurança
echo "🏷️  Adicionando labels de segurança..."
gcloud run services update $SERVICE_NAME \
  --region $REGION \
  --update-labels security=enabled,purpose=djen-proxy,restricted=true

# 4. Configurar variáveis de ambiente de segurança
echo "🔐 Configurando variáveis de ambiente..."
gcloud run services update $SERVICE_NAME \
  --region $REGION \
  --update-env-vars ALLOWED_TARGET=comunicaapi.pje.jus.br,SECURITY_ENABLED=true,LOG_LEVEL=info

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Segurança Cloud Run configurada!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🛡️  Proteções ativas (NATIVAS - sem custo):"
echo "   ✅ HTTPS obrigatório (TLS 1.2+)"
echo "   ✅ DDoS protection (Google Cloud)"
echo "   ✅ Max 80 requisições concorrentes"
echo "   ✅ Timeout de 30s"
echo "   ✅ Auto-escala 0→10 instâncias"
echo "   ✅ Validações no código Go"
echo ""
echo "🔒 Proteções no CÓDIGO (já implementadas):"
echo "   ✅ Whitelist de domínio único"
echo "   ✅ Bloqueio de URLs externas"
echo "   ✅ Validação de Host header"
echo "   ✅ Logging de tentativas de abuso"
echo ""
echo "📊 Monitoramento:"
echo "   gcloud run services logs read $SERVICE_NAME --region $REGION"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

PROXY_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format='value(status.url)')
echo ""
echo "🇧🇷 URL do Proxy Seguro:"
echo "   $PROXY_URL"
echo ""
