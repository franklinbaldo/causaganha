#!/bin/bash
set -euo pipefail

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 DJEN Scraper - Deploy para Cloudflare"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

cd "$(dirname "$0")/../cloudflare/worker"

# 1. Build TypeScript + Deploy
echo "📦 Building e deploying Worker..."
wrangler deploy

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ DEPLOY COMPLETO!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🔗 Worker URL: https://djen-scraper.YOUR_SUBDOMAIN.workers.dev"
echo ""
echo "📊 Comandos úteis:"
echo "   wrangler tail              # Ver logs em tempo real"
echo "   wrangler kv:key get state  # Ver estado atual"
echo "   curl https://djen-scraper.YOUR_SUBDOMAIN.workers.dev/state"
echo ""
echo "⏱️  Cron ativo: executa a cada minuto"
echo "   Primeiro batch em ~1 minuto"
echo ""
