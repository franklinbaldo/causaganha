#!/bin/bash
# ============================================================================
# Redeploy DJEN Proxy com Segurança
# Execute este script NO GOOGLE CLOUD SHELL
# ============================================================================

set -e

echo "🔒 Fazendo redeploy do DJEN Proxy SEGURO..."
echo ""

# Copiar a versão segura
cp djen_proxy_secure.go djen_proxy.go

# Deploy no Cloud Run
gcloud run deploy djen-proxy \
  --source . \
  --region southamerica-east1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 256Mi \
  --cpu 1 \
  --max-instances 10 \
  --timeout 30s \
  --port 8080 \
  --quiet

# Pegar URL
PROXY_URL=$(gcloud run services describe djen-proxy --region southamerica-east1 --format='value(status.url)')

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ PROXY SEGURO DEPLOYADO!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🔒 URL Segura: $PROXY_URL"
echo ""
echo "🧪 Testar segurança:"
echo "   # Deve funcionar:"
echo "   curl $PROXY_URL/health"
echo ""
echo "   # Deve bloquear:"
echo "   curl $PROXY_URL/http://google.com"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
