#!/bin/bash
# ============================================================================
# LOCAL BACKFILL RUNNER - causaganha
# ============================================================================

# Load .env if it exists
if [ -f .env ]; then
    echo "Loading environment variables from .env..."
    # Export variables from .env, handling potential spaces/comments
    export $(grep -v '^#' .env | xargs)
fi

# Configuration (mirrors GitHub Actions defaults)
export DJEN_PROXY_URL="${DJEN_PROXY_URL:-https://djen-proxy-mhgmawcn3a-rj.a.run.app}"
WORKERS="${1:-4}"
DEADLINE="${2:-17}"
START_DATE="${3:-2013-01-01}"

echo "============================================================================"
echo "  CAUSAGANHA BACKFILL - LOCAL RUNNER"
echo "============================================================================"
echo "Workers: $WORKERS"
echo "Deadline: ${DEADLINE}m"
echo "Start Date: $START_DATE"
echo "Proxy: $DJEN_PROXY_URL"
echo "============================================================================"

# Ensure data directory exists
mkdir -p data

# Run the backfill command
# Using uv run djen-backup as defined in pyproject.toml
uv run djen-backup \
  --deadline-minutes "$DEADLINE" \
  --workers "$WORKERS" \
  --backfill-state-file data/backfill-state.json \
  --state-file data/ia-state.json \
  --start-date "$START_DATE" \
  --skip-absent-markers \
  --publish-live-status
