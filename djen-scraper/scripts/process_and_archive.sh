#!/bin/bash
set -euo pipefail

# ============================================================================
# DJEN Scraper - Fase 2: Processar e Arquivar
# ============================================================================
#
# Converte dados JSON.gz do R2 para Parquet e faz upload para Internet Archive
#
# Dependências:
#   - wrangler (npm install -g wrangler)
#   - duckdb (https://duckdb.org/docs/installation/)
#   - aws-cli (pip install awscli)
#
# Configuração Internet Archive:
#   1. Criar conta em https://archive.org
#   2. Obter S3 keys em https://archive.org/account/s3.php
#   3. Configurar: aws configure --profile ia
#      - AWS Access Key ID: [access]
#      - AWS Secret Access Key: [secret]
#      - Default region: us-east-1
#      - Default output format: json
#
# Uso:
#   ./process_and_archive.sh YYYY-MM-DD
#
# ============================================================================

DATE=${1:?Usage: $0 YYYY-MM-DD}

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 DJEN Scraper - Processar e Arquivar"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📅 Data: $DATE"
echo ""

WORKDIR=$(mktemp -d)
trap "rm -rf $WORKDIR" EXIT

cd "$WORKDIR"

# 1. Baixar arquivos do R2
echo "📥 Baixando dados do R2..."
wrangler r2 object list djen-buffer --prefix "data/${DATE}/" > files.txt

if [ ! -s files.txt ]; then
    echo "❌ Nenhum arquivo encontrado para $DATE"
    exit 1
fi

# Baixar todos os arquivos .json.gz da data
mkdir -p raw
while IFS= read -r file; do
    filename=$(basename "$file")
    echo "   Baixando $filename..."
    wrangler r2 object get "djen-buffer/data/${DATE}/${filename}" -o "raw/${filename}"
done < <(grep -oP "data/${DATE}/[^ ]+" files.txt)

echo "✅ Download completo"
echo ""

# 2. Descompactar e consolidar JSON
echo "🔓 Descompactando arquivos..."
for gz in raw/*.gz; do
    gunzip -c "$gz" >> consolidated.json
done

echo "✅ Consolidado: consolidated.json"
echo ""

# 3. Converter para Parquet
echo "🔄 Convertendo para Parquet..."
duckdb -c "COPY (SELECT * FROM read_json_auto('consolidated.json')) TO 'data.parquet' (COMPRESSION ZSTD, ROW_GROUP_SIZE 100000)"

SIZE=$(du -h data.parquet | cut -f1)
echo "✅ Parquet criado: data.parquet ($SIZE)"
echo ""

# 4. Upload para Internet Archive
echo "☁️  Upload para Internet Archive..."
BUCKET="djen-pje-${DATE}"

# Criar item no Internet Archive via S3
aws s3 cp data.parquet "s3://${BUCKET}/data.parquet" \
    --endpoint-url https://s3.us.archive.org \
    --profile ia \
    --metadata "collection=opensource_media,mediatype=data,title=DJEN ${DATE},description=Comunicações do Diário de Justiça Eletrônico Nacional - ${DATE}"

echo "✅ Upload completo"
echo ""
echo "🔗 URL: https://archive.org/download/${BUCKET}/data.parquet"
echo ""

# 5. Deletar do R2
echo "🗑️  Limpando R2..."
while IFS= read -r file; do
    filename=$(basename "$file")
    echo "   Deletando $filename..."
    wrangler r2 object delete "djen-buffer/data/${DATE}/${filename}"
done < <(grep -oP "data/${DATE}/[^ ]+" files.txt)

echo "✅ R2 limpo"
echo ""

# 6. Atualizar estado (opcional - marcar como arquivado)
echo "📝 Atualizando estado..."
echo "   (implementar se necessário)"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ ${DATE} ARQUIVADO COM SUCESSO!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Resumo:"
echo "   - Formato: Parquet (ZSTD)"
echo "   - Tamanho: $SIZE"
echo "   - Internet Archive: https://archive.org/details/${BUCKET}"
echo ""
echo "💡 Query com DuckDB:"
echo "   duckdb -c \"SELECT * FROM 'https://archive.org/download/${BUCKET}/data.parquet' LIMIT 10\""
echo ""
