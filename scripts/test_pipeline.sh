#!/bin/bash
# ============================================================================
# Quick pipeline test - Load .env and run pipeline with performance analysis
# ============================================================================

cd "$(dirname "$0")" || exit 1

# Load environment
if [ -f ../.env ]; then
    echo "📦 Loading credentials from .env..."
    set -a
    source ../.env
    set +a
else
    echo "❌ Error: ../.env not found"
    exit 1
fi

# Verify credentials
echo ""
echo "✓ Credentials loaded:"
echo "  IAS3_ACCESS_KEY: ${IAS3_ACCESS_KEY:0:10}***"
echo "  IAS3_SECRET_KEY: ${IAS3_SECRET_KEY:0:10}***"
echo ""

# Show options
echo "Available commands:"
echo ""
echo "  bash test_pipeline.sh collect       - Download from DJEN (5 items)"
echo "  bash test_pipeline.sh consolidate   - Convert ZIPs to Parquet"
echo "  bash test_pipeline.sh embed         - Generate embeddings"
echo "  bash test_pipeline.sh catalog       - Build manifest"
echo "  bash test_pipeline.sh dashboard     - Generate dashboard cache"
echo ""
echo "  bash test_pipeline.sh full          - Run all steps (small data)"
echo "  bash test_pipeline.sh analyze       - Full performance analysis"
echo "  bash test_pipeline.sh clean         - Clean output directory"
echo ""

# If no argument, show menu
if [ $# -eq 0 ]; then
    echo "Usage: bash test_pipeline.sh <command>"
    exit 0
fi

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# Create output directory
mkdir -p pipeline-output
cd pipeline-output || exit 1

case "$1" in
    collect)
        echo -e "${BLUE}[COLLECT] Downloading from DJEN${NC}"
        uv run python ../scripts/pipeline/collect.py --max-items 5
        ;;
    consolidate)
        echo -e "${BLUE}[CONSOLIDATE] Converting ZIPs to Parquet${NC}"
        uv run python ../scripts/pipeline/consolidate.py --backfill --force --max-zips 3
        ;;
    embed)
        echo -e "${BLUE}[EMBED] Generating embeddings${NC}"
        uv run python ../scripts/pipeline/embed.py --max-decisions 50
        ;;
    catalog)
        echo -e "${BLUE}[CATALOG] Building manifest${NC}"
        uv run python ../scripts/generate_catalog.py
        ;;
    dashboard)
        echo -e "${BLUE}[DASHBOARD] Generating cache${NC}"
        uv run python ../scripts/generate_dashboard_cache.py
        ;;
    full)
        echo -e "${BLUE}[FULL PIPELINE] Running all steps (small data)${NC}"
        echo ""
        uv run python ../scripts/pipeline/collect.py --max-items 5
        uv run python ../scripts/pipeline/consolidate.py --backfill --force --max-zips 3
        uv run python ../scripts/pipeline/embed.py --max-decisions 50
        uv run python ../scripts/catalog/build.py
        uv run python ../scripts/generate_dashboard_cache.py
        echo ""
        echo -e "${GREEN}✓ Full pipeline completed${NC}"
        ;;
    analyze)
        echo -e "${BLUE}[ANALYZE] Running performance analysis${NC}"
        cd ..
        uv run python analyze_pipeline_performance.py
        ;;
    clean)
        echo "Cleaning pipeline-output..."
        cd ..
        rm -rf pipeline-output
        echo -e "${GREEN}✓ Cleaned${NC}"
        ;;
    *)
        echo "Unknown command: $1"
        exit 1
        ;;
esac
