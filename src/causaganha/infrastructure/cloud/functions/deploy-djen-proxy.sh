#!/bin/bash
# Deploy DJEN proxy Cloud Function to São Paulo region

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Deploying DJEN Proxy Cloud Function${NC}"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI not found. Please install: https://cloud.google.com/sdk/docs/install${NC}"
    exit 1
fi

# Check authentication mode
if [ -z "$REQUIRE_AUTH" ]; then
    REQUIRE_AUTH="false"
    echo -e "${GREEN}Authentication disabled by default (DJEN is public)${NC}"
    echo -e "${YELLOW}To enable auth: export REQUIRE_AUTH=true before deploying${NC}"
else
    echo -e "${YELLOW}Authentication mode: $REQUIRE_AUTH${NC}"
fi

# Generate API key if auth is enabled
if [ "$REQUIRE_AUTH" = "true" ]; then
    if [ -z "$PROXY_API_KEY" ]; then
        echo -e "${YELLOW}⚠️  PROXY_API_KEY not set. Generating random key...${NC}"
        PROXY_API_KEY=$(openssl rand -base64 32)
        echo -e "${GREEN}Generated API Key: $PROXY_API_KEY${NC}"
        echo -e "${YELLOW}Save this key! Add to .env and GitHub Secrets:${NC}"
        echo -e "  DJEN_PROXY_API_KEY=$PROXY_API_KEY"
    fi
fi

# Configuration
FUNCTION_NAME="djen-proxy"
REGION="southamerica-east1"  # São Paulo, Brazil
RUNTIME="python312"
MEMORY="256MB"
TIMEOUT="60s"
ENTRY_POINT="djen_proxy_handler"
PROJECT_ID=$(gcloud config get-value project)

echo ""
echo "Configuration:"
echo "  Function: $FUNCTION_NAME"
echo "  Region: $REGION (São Paulo, Brazil)"
echo "  Runtime: $RUNTIME"
echo "  Memory: $MEMORY"
echo "  Timeout: $TIMEOUT"
echo "  Project: $PROJECT_ID"
echo ""

# Confirm deployment
read -p "Deploy to this project? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${RED}Deployment cancelled${NC}"
    exit 1
fi

echo -e "${GREEN}📦 Deploying function...${NC}"

# Deploy function
if [ "$REQUIRE_AUTH" = "true" ]; then
    gcloud functions deploy $FUNCTION_NAME \
        --gen2 \
        --runtime=$RUNTIME \
        --region=$REGION \
        --source=. \
        --entry-point=$ENTRY_POINT \
        --trigger-http \
        --allow-unauthenticated \
        --memory=$MEMORY \
        --timeout=$TIMEOUT \
        --set-env-vars="REQUIRE_AUTH=true,PROXY_API_KEY=$PROXY_API_KEY"
else
    gcloud functions deploy $FUNCTION_NAME \
        --gen2 \
        --runtime=$RUNTIME \
        --region=$REGION \
        --source=. \
        --entry-point=$ENTRY_POINT \
        --trigger-http \
        --allow-unauthenticated \
        --memory=$MEMORY \
        --timeout=$TIMEOUT \
        --set-env-vars="REQUIRE_AUTH=false"
fi

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Deployment successful!${NC}"
    echo ""

    # Get function URL
    FUNCTION_URL=$(gcloud functions describe $FUNCTION_NAME \
        --region=$REGION \
        --gen2 \
        --format='value(serviceConfig.uri)')

    echo "Function URL: $FUNCTION_URL"
    echo ""
    echo -e "${GREEN}Next steps:${NC}"
    echo "1. Add to .env file:"
    echo "   DJEN_PROXY_URL=$FUNCTION_URL"
    echo "   DJEN_PROXY_API_KEY=$PROXY_API_KEY"
    echo ""
    echo "2. Add to GitHub Secrets:"
    echo "   gh secret set DJEN_PROXY_URL --body=\"$FUNCTION_URL\""
    echo "   gh secret set DJEN_PROXY_API_KEY --body=\"$PROXY_API_KEY\""
    echo ""
    echo "3. Test the function:"
    echo "   curl -H \"X-API-Key: $PROXY_API_KEY\" \"$FUNCTION_URL/health\""
    echo ""
else
    echo -e "${RED}❌ Deployment failed${NC}"
    exit 1
fi
