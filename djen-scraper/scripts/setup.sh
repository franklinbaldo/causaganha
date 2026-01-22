#!/bin/bash
set -euo pipefail

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔧 DJEN Scraper - Setup Cloudflare"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

cd "$(dirname "$0")/../cloudflare/worker"

# 1. Verificar se wrangler está instalado
if ! command -v wrangler &> /dev/null; then
    echo "❌ wrangler não encontrado!"
    echo "   Instale com: npm install -g wrangler"
    exit 1
fi

echo "✅ wrangler encontrado"
echo ""

# 2. Login Cloudflare (se necessário)
echo "🔐 Verificando autenticação Cloudflare..."
if ! wrangler whoami &> /dev/null; then
    echo "   Você precisa fazer login no Cloudflare"
    wrangler login
fi

echo "✅ Autenticado no Cloudflare"
echo ""

# 3. Criar KV Namespace
echo "📦 Criando KV Namespace 'djen-state'..."
KV_OUTPUT=$(wrangler kv:namespace create "DJEN_STATE" 2>&1 || true)
echo "$KV_OUTPUT"

# Extrair ID do KV
KV_ID=$(echo "$KV_OUTPUT" | grep -oP '(?<=id = ")[^"]+' | head -1 || true)

if [ -z "$KV_ID" ]; then
    echo "⚠️  KV já existe ou erro ao criar. Tentando listar..."
    KV_ID=$(wrangler kv:namespace list | grep -i "djen" | grep -oP '(?<="id":")[^"]+' | head -1 || true)
fi

if [ -n "$KV_ID" ]; then
    echo "✅ KV Namespace ID: $KV_ID"

    # Atualizar wrangler.toml
    sed -i "s/YOUR_KV_NAMESPACE_ID/$KV_ID/" wrangler.toml
    echo "✅ wrangler.toml atualizado com KV ID"
else
    echo "❌ Não foi possível obter KV ID"
    echo "   Configure manualmente o ID no wrangler.toml"
fi

echo ""

# 4. Criar R2 Bucket
echo "🪣 Criando R2 Bucket 'djen-buffer'..."
if wrangler r2 bucket create djen-buffer 2>&1; then
    echo "✅ R2 Bucket 'djen-buffer' criado"
else
    echo "⚠️  R2 Bucket já existe ou erro ao criar"
    echo "   Verifique: wrangler r2 bucket list"
fi

echo ""

# 5. Instalar dependências
echo "📦 Instalando dependências npm..."
npm install

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ SETUP COMPLETO!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📝 Próximos passos:"
echo "   1. Revise as configurações em wrangler.toml"
echo "   2. Execute: ../scripts/deploy.sh"
echo ""
