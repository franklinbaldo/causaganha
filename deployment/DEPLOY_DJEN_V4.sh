#!/bin/bash
# ============================================================================
# DJEN PROXY - Deploy Script
# ============================================================================
#
# Deploys the proxy from the files already tracked in this directory
# (djen_proxy.go, go.mod, Dockerfile). Earlier versions of this script
# regenerated djen_proxy.go/Dockerfile from an embedded heredoc on every
# run, which meant a manual run would silently overwrite whatever fix was
# committed to djen_proxy.go with this script's own stale copy (see
# docs/SECURITY_THREAT_MODEL.md TM-02, issue #1609). The tracked files are
# now the only source of truth; this script only builds and deploys them.
#
# Run from inside deployment/.

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 DJEN PROXY - Deploy Script"
echo "🗑️  MODO: AUTO-DELETE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "🧪 Rodando testes antes do deploy..."
go test ./...
echo ""

# 1. DELETAR SERVIÇO EXISTENTE
if gcloud run services describe djen-proxy --region southamerica-east1 &>/dev/null; then
    echo "🗑️  Deletando serviço existente..."
    gcloud run services delete djen-proxy --region southamerica-east1 --quiet
    echo "✅ Deletado"
    echo ""
fi

# 2. DEPLOY
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 DEPLOY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

gcloud run deploy djen-proxy \
  --source . \
  --region southamerica-east1 \
  --allow-unauthenticated \
  --memory 512Mi \
  --max-instances 10 \
  --timeout 30s

# 3. PEGAR URL
URL=$(gcloud run services describe djen-proxy --region southamerica-east1 --format='value(status.url)')

# 4. TESTAR
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ DEPLOY CONCLUÍDO!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🔗 URL: $URL"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧪 TESTANDO PROXY..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "1️⃣ Health:"
curl -s "$URL/health"
echo ""

echo ""
echo "2️⃣ Bloqueio /evil (deve retornar 403):"
curl -s "$URL/evil"
echo ""

echo ""
echo "3️⃣ Bloqueio POST em rota permitida (deve retornar 405):"
curl -s -X POST -o /dev/null -w "Status: %{http_code}" "$URL/api/v1/comunicacao?idOrgao=2"
echo ""

echo ""
echo "4️⃣ API DJEN (deve funcionar):"
curl -s -o /dev/null -w "Status: %{http_code}" "$URL/api/v1/comunicacao?idOrgao=2"
echo ""

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📝 CONFIGURAÇÃO"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "export DJEN_PROXY_URL='$URL'"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ CONCLUÍDO"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
