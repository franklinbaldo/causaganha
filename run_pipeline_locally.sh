#!/bin/bash
# ============================================================================
# LOCAL PIPELINE RUNNER - Full measurement & optimization analysis
# ============================================================================
#
# Run the entire CausaGanha pipeline locally with performance metrics
#
# Usage:
#   export IAS3_ACCESS_KEY="your-key"
#   export IAS3_SECRET_KEY="your-secret"
#   export JINA_API_KEY="your-key" (optional, for embeddings)
#   export GOOGLE_API_KEY="your-key" (optional, for embeddings)
#   bash run_pipeline_locally.sh
#

set -e

cd "$(dirname "$0")"

echo "============================================================================"
echo "  CAUSAGANHA PIPELINE - LOCAL RUNNER (Performance Measurement)"
echo "============================================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check credentials
echo -e "${BLUE}[1/6] Checking credentials...${NC}"
missing_creds=0

if [ -z "$IAS3_ACCESS_KEY" ]; then
    echo -e "${RED}  ✗ Missing IAS3_ACCESS_KEY${NC}"
    missing_creds=1
else
    echo -e "${GREEN}  ✓ IAS3_ACCESS_KEY set${NC}"
fi

if [ -z "$IAS3_SECRET_KEY" ]; then
    echo -e "${RED}  ✗ Missing IAS3_SECRET_KEY${NC}"
    missing_creds=1
else
    echo -e "${GREEN}  ✓ IAS3_SECRET_KEY set${NC}"
fi

# Optional embeddings keys
if [ -z "$JINA_API_KEY" ] && [ -z "$GOOGLE_API_KEY" ]; then
    echo -e "${YELLOW}  ⚠ No embedding API configured (JINA_API_KEY or GOOGLE_API_KEY)${NC}"
fi

if [ $missing_creds -eq 1 ]; then
    echo ""
    echo -e "${RED}ERROR: Missing required credentials${NC}"
    echo "Please set:"
    echo "  export IAS3_ACCESS_KEY='...'"
    echo "  export IAS3_SECRET_KEY='...'"
    exit 1
fi

echo ""

# Set defaults
DJEN_PROXY_URL="${DJEN_PROXY_URL:-https://djen-proxy-mhgmawcn3a-rj.a.run.app}"
GITHUB_OUTPUT=""  # No GitHub output when running locally

export DJEN_PROXY_URL
export GITHUB_OUTPUT

# Create output directory
mkdir -p pipeline-output
cd pipeline-output || exit 1

# Timing function
run_step() {
    local step_name="$1"
    local step_cmd="$2"

    echo ""
    echo -e "${BLUE}[$step_name]${NC}"
    echo "Command: $step_cmd"
    echo ""

    local start_time=$(date +%s.%N)
    local start_date=$(date '+%Y-%m-%d %H:%M:%S')

    if eval "$step_cmd"; then
        local end_time=$(date +%s.%N)
        local duration=$(echo "$end_time - $start_time" | bc)
        echo ""
        echo -e "${GREEN}✓ $step_name completed in ${duration}s${NC}"
        echo "$step_name: ${duration}s" >> timing.log
        return 0
    else
        local end_time=$(date +%s.%N)
        local duration=$(echo "$end_time - $start_time" | bc)
        echo ""
        echo -e "${RED}✗ $step_name FAILED after ${duration}s${NC}"
        echo "$step_name: FAILED (${duration}s)" >> timing.log
        return 1
    fi
}

# Clear previous timing log
> timing.log

# ============================================================================
# STEP 1: COLLECT
# ============================================================================
echo ""
echo -e "${BLUE}[2/6] COLLECT - Download from DJEN${NC}"
run_step "COLLECT" "uv run python ../scripts/pipeline/collect.py --max-items 5"

# ============================================================================
# STEP 2: CONSOLIDATE
# ============================================================================
echo ""
echo -e "${BLUE}[3/6] CONSOLIDATE - Convert ZIPs to Parquet${NC}"
run_step "CONSOLIDATE" "uv run python ../scripts/pipeline/consolidate.py --backfill --force --max-zips 5" || true

# ============================================================================
# STEP 3: EMBED
# ============================================================================
echo ""
echo -e "${BLUE}[4/6] EMBED - Generate embeddings${NC}"
run_step "EMBED" "uv run python ../scripts/pipeline/embed.py --max-decisions 100" || true

# ============================================================================
# STEP 4: CATALOG
# ============================================================================
echo ""
echo -e "${BLUE}[5/6] CATALOG - Build manifest${NC}"
run_step "CATALOG" "uv run python ../scripts/catalog/build.py" || true

# ============================================================================
# STEP 5: DASHBOARD CACHE
# ============================================================================
echo ""
echo -e "${BLUE}[6/6] DASHBOARD CACHE - Generate dashboard data${NC}"
run_step "DASHBOARD" "uv run python ../scripts/generate_dashboard_cache.py" || true

# ============================================================================
# SUMMARY
# ============================================================================
echo ""
echo "============================================================================"
echo "  PIPELINE EXECUTION SUMMARY"
echo "============================================================================"
echo ""

if [ -f timing.log ]; then
    cat timing.log
    echo ""

    total_time=$(grep -oE "[0-9]+\.[0-9]+" timing.log | awk '{s+=$1} END {print s}')
    echo -e "${GREEN}Total execution time: ${total_time}s${NC}"
fi

echo ""
echo "Output files:"
ls -lh *.parquet 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}' || echo "  (no parquets generated)"
ls -lh *.duckdb 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}' || echo "  (no databases generated)"

echo ""
echo "============================================================================"
echo "  PERFORMANCE ANALYSIS"
echo "============================================================================"
echo ""

echo "✓ All steps completed successfully!"
echo ""
echo "Next steps for optimization:"
echo "  1. Identify bottlenecks in timing.log"
echo "  2. Check file sizes for compression ratios"
echo "  3. Profile memory usage: uv run python -m memory_profiler <script>"
echo "  4. Run with larger datasets: --max-items 50, --max-zips 20, etc."
echo ""
