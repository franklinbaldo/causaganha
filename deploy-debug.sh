#!/bin/bash
# Deploy versão debug para investigar o problema

set -e

echo "🐛 Fazendo deploy da versão DEBUG..."
echo ""

# Copiar versão debug
cp djen_proxy_debug.go djen_proxy.go

# Deploy
gcloud run deploy djen-proxy \
  --source . \
  --region southamerica-east1 \
  --allow-unauthenticated \
  --memory 512Mi \
  --max-instances 10 \
  --timeout 30s \
  --concurrency 80 \
  --quiet

PROXY_URL=$(gcloud run services describe djen-proxy --region southamerica-east1 --format='value(status.url)')

echo ""
echo "✅ Deploy DEBUG concluído"
echo ""
echo "🔒 URL: $PROXY_URL"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧪 TESTES DEBUG"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "1️⃣ Debug endpoint:"
curl -s "$PROXY_URL/debug"
echo ""
echo ""

echo "2️⃣ Tentar acessar http://google.com:"
curl -s "$PROXY_URL/http://google.com"
echo ""
echo ""

echo "3️⃣ Ver logs (últimas 20 linhas):"
gcloud run services logs read djen-proxy --region southamerica-east1 --limit 20

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
