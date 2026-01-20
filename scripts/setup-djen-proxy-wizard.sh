#!/bin/bash
# Interactive Wizard for DJEN Proxy Setup
# Guides users through deploying the geo-blocking bypass proxy

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Clear screen and show banner
clear
echo -e "${CYAN}"
cat << "EOF"
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║          🌎 DJEN API Proxy Setup Wizard 🇧🇷                      ║
║                                                                  ║
║  Bypass geo-blocking by deploying a proxy in São Paulo, Brazil  ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

echo -e "${BOLD}This wizard will help you:${NC}"
echo "  1️⃣  Check prerequisites (gcloud CLI)"
echo "  2️⃣  Configure Google Cloud project"
echo "  3️⃣  Choose authentication mode"
echo "  4️⃣  Deploy Cloud Function to Brazil"
echo "  5️⃣  Update your local configuration"
echo "  6️⃣  Test the proxy"
echo ""
read -p "Press Enter to start..."
clear

# ==============================================================================
# Step 1: Prerequisites Check
# ==============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}Step 1/6: Checking Prerequisites${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check gcloud
if command -v gcloud &> /dev/null; then
    GCLOUD_VERSION=$(gcloud version --format="value(core)" 2>/dev/null || echo "unknown")
    echo -e "${GREEN}✓${NC} gcloud CLI installed (version: $GCLOUD_VERSION)"
else
    echo -e "${RED}✗${NC} gcloud CLI not found"
    echo ""
    echo -e "${YELLOW}Please install Google Cloud SDK:${NC}"
    echo "  https://cloud.google.com/sdk/docs/install"
    echo ""
    read -p "Install now? (opens browser) [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        python3 -m webbrowser "https://cloud.google.com/sdk/docs/install"
    fi
    echo -e "${RED}Exiting. Please install gcloud and run this wizard again.${NC}"
    exit 1
fi

# Check authentication
if gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    ACTIVE_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n1)
    echo -e "${GREEN}✓${NC} Authenticated as: $ACTIVE_ACCOUNT"
else
    echo -e "${YELLOW}⚠${NC}  Not authenticated"
    echo ""
    read -p "Authenticate now? [Y/n] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        gcloud auth login
    else
        echo -e "${RED}Authentication required. Exiting.${NC}"
        exit 1
    fi
fi

echo ""
read -p "Press Enter to continue..."
clear

# ==============================================================================
# Step 2: Project Configuration
# ==============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}Step 2/6: Google Cloud Project${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null || echo "none")
echo -e "Current project: ${CYAN}$CURRENT_PROJECT${NC}"
echo ""

if [ "$CURRENT_PROJECT" = "none" ] || [ -z "$CURRENT_PROJECT" ]; then
    echo -e "${YELLOW}No project selected.${NC}"
    echo ""
    echo "Available projects:"
    gcloud projects list --format="table(projectId,name)"
    echo ""
    read -p "Enter project ID: " PROJECT_ID
    gcloud config set project "$PROJECT_ID"
else
    read -p "Use this project? [Y/n] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        echo ""
        echo "Available projects:"
        gcloud projects list --format="table(projectId,name)"
        echo ""
        read -p "Enter project ID: " PROJECT_ID
        gcloud config set project "$PROJECT_ID"
    else
        PROJECT_ID="$CURRENT_PROJECT"
    fi
fi

echo ""
echo -e "${GREEN}✓${NC} Using project: ${CYAN}$PROJECT_ID${NC}"

# Check/enable required APIs
echo ""
echo "Checking required APIs..."
APIS=("cloudfunctions.googleapis.com" "cloudbuild.googleapis.com" "run.googleapis.com")
for API in "${APIS[@]}"; do
    if gcloud services list --enabled --filter="name:$API" --format="value(name)" | grep -q "$API"; then
        echo -e "${GREEN}✓${NC} $API enabled"
    else
        echo -e "${YELLOW}⚠${NC}  $API not enabled"
        read -p "Enable $API? [Y/n] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            gcloud services enable "$API"
            echo -e "${GREEN}✓${NC} $API enabled"
        fi
    fi
done

echo ""
read -p "Press Enter to continue..."
clear

# ==============================================================================
# Step 3: Authentication Mode
# ==============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}Step 3/6: Authentication Mode${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo "The DJEN API serves public court records."
echo "Authentication is optional for the proxy."
echo ""
echo -e "${BOLD}Options:${NC}"
echo ""
echo -e "  ${GREEN}1) Public Access (Recommended)${NC}"
echo "     • No API key required"
echo "     • Simple to use"
echo "     • Good for personal/development use"
echo ""
echo -e "  ${YELLOW}2) Protected Access${NC}"
echo "     • Requires API key"
echo "     • Better for production"
echo "     • Prevents unauthorized usage"
echo ""
read -p "Choose mode [1/2]: " -n 1 -r AUTH_CHOICE
echo ""

if [ "$AUTH_CHOICE" = "2" ]; then
    REQUIRE_AUTH="true"
    echo ""
    echo -e "${YELLOW}API Key required for protected mode.${NC}"
    read -p "Generate random API key? [Y/n] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        PROXY_API_KEY=$(openssl rand -base64 32)
        echo -e "${GREEN}Generated API Key:${NC}"
        echo -e "${CYAN}$PROXY_API_KEY${NC}"
        echo ""
        echo -e "${YELLOW}⚠️  Save this key! You'll need it to configure your application.${NC}"
        echo ""
        read -p "Press Enter when you've saved the key..."
    else
        read -p "Enter your API key: " PROXY_API_KEY
    fi
else
    REQUIRE_AUTH="false"
    PROXY_API_KEY=""
    echo -e "${GREEN}✓${NC} Public access mode selected"
fi

echo ""
read -p "Press Enter to continue..."
clear

# ==============================================================================
# Step 4: Deploy Function
# ==============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}Step 4/6: Deploy Cloud Function${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

FUNCTION_NAME="djen-proxy"
REGION="southamerica-east1"
RUNTIME="python312"
MEMORY="256MB"
TIMEOUT="60s"
ENTRY_POINT="djen_proxy_handler"

echo "Configuration Summary:"
echo -e "  Function Name:  ${CYAN}$FUNCTION_NAME${NC}"
echo -e "  Region:         ${CYAN}$REGION${NC} (São Paulo, Brazil 🇧🇷)"
echo -e "  Runtime:        ${CYAN}$RUNTIME${NC}"
echo -e "  Memory:         ${CYAN}$MEMORY${NC}"
echo -e "  Timeout:        ${CYAN}$TIMEOUT${NC}"
echo -e "  Authentication: ${CYAN}$([ "$REQUIRE_AUTH" = "true" ] && echo "Protected" || echo "Public")${NC}"
echo ""
echo -e "${YELLOW}Estimated cost:${NC} ~$2.50/month (likely free tier)"
echo ""
read -p "Deploy now? [Y/n] " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Nn]$ ]]; then
    echo -e "${RED}Deployment cancelled.${NC}"
    exit 1
fi

echo ""
echo -e "${CYAN}Deploying function (this may take 2-3 minutes)...${NC}"
echo ""

cd "$(dirname "$0")/../src/causaganha/infrastructure/cloud/functions"

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
        --set-env-vars="REQUIRE_AUTH=true,PROXY_API_KEY=$PROXY_API_KEY" \
        --quiet
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
        --set-env-vars="REQUIRE_AUTH=false" \
        --quiet
fi

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ Deployment successful!${NC}"
else
    echo ""
    echo -e "${RED}✗ Deployment failed${NC}"
    exit 1
fi

# Get function URL
FUNCTION_URL=$(gcloud functions describe $FUNCTION_NAME \
    --region=$REGION \
    --gen2 \
    --format='value(serviceConfig.uri)')

echo ""
echo -e "${GREEN}Function URL:${NC}"
echo -e "${CYAN}$FUNCTION_URL${NC}"

echo ""
read -p "Press Enter to continue..."
clear

# ==============================================================================
# Step 5: Configuration
# ==============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}Step 5/6: Update Local Configuration${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

cd "$(dirname "$0")/.."

ENV_FILE=".env"

echo "Updating .env file..."
echo ""

# Add or update DJEN_PROXY_URL
if grep -q "^DJEN_PROXY_URL=" "$ENV_FILE" 2>/dev/null; then
    # Update existing
    sed -i.bak "s|^DJEN_PROXY_URL=.*|DJEN_PROXY_URL=$FUNCTION_URL|" "$ENV_FILE"
    echo -e "${GREEN}✓${NC} Updated DJEN_PROXY_URL in .env"
else
    # Add new
    echo "" >> "$ENV_FILE"
    echo "# DJEN API Proxy (geo-blocking bypass)" >> "$ENV_FILE"
    echo "DJEN_PROXY_URL=$FUNCTION_URL" >> "$ENV_FILE"
    echo -e "${GREEN}✓${NC} Added DJEN_PROXY_URL to .env"
fi

# Add API key if protected mode
if [ "$REQUIRE_AUTH" = "true" ]; then
    if grep -q "^DJEN_PROXY_API_KEY=" "$ENV_FILE" 2>/dev/null; then
        sed -i.bak "s|^DJEN_PROXY_API_KEY=.*|DJEN_PROXY_API_KEY=$PROXY_API_KEY|" "$ENV_FILE"
        echo -e "${GREEN}✓${NC} Updated DJEN_PROXY_API_KEY in .env"
    else
        echo "DJEN_PROXY_API_KEY=$PROXY_API_KEY" >> "$ENV_FILE"
        echo -e "${GREEN}✓${NC} Added DJEN_PROXY_API_KEY to .env"
    fi
fi

echo ""
echo -e "${YELLOW}GitHub Secrets (for CI/CD):${NC}"
echo ""
echo "Run these commands to add secrets to GitHub:"
echo ""
echo -e "${CYAN}gh secret set DJEN_PROXY_URL --body=\"$FUNCTION_URL\"${NC}"
if [ "$REQUIRE_AUTH" = "true" ]; then
    echo -e "${CYAN}gh secret set DJEN_PROXY_API_KEY --body=\"$PROXY_API_KEY\"${NC}"
fi

echo ""
read -p "Press Enter to continue..."
clear

# ==============================================================================
# Step 6: Test
# ==============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}Step 6/6: Test the Proxy${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo "Testing proxy connectivity..."
echo ""

# Test health endpoint
echo -e "${CYAN}1. Health Check:${NC}"
if [ "$REQUIRE_AUTH" = "true" ]; then
    HEALTH_RESPONSE=$(curl -s -H "X-API-Key: $PROXY_API_KEY" "$FUNCTION_URL/health")
else
    HEALTH_RESPONSE=$(curl -s "$FUNCTION_URL/health")
fi

if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
    echo -e "   ${GREEN}✓${NC} Health check passed"
    echo "   $HEALTH_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "   $HEALTH_RESPONSE"
else
    echo -e "   ${RED}✗${NC} Health check failed"
    echo "   $HEALTH_RESPONSE"
fi

echo ""
echo -e "${CYAN}2. DJEN API Request:${NC}"

# Test actual API call
if [ "$REQUIRE_AUTH" = "true" ]; then
    API_RESPONSE=$(curl -s -H "X-API-Key: $PROXY_API_KEY" "$FUNCTION_URL/api/v1/comunicacao?siglaTribunal=TJRO&limit=1")
else
    API_RESPONSE=$(curl -s "$FUNCTION_URL/api/v1/comunicacao?siglaTribunal=TJRO&limit=1")
fi

if echo "$API_RESPONSE" | grep -q "items"; then
    echo -e "   ${GREEN}✓${NC} API request successful"
    echo "   Retrieved data from DJEN API through proxy"
else
    echo -e "   ${YELLOW}⚠${NC}  API request returned unexpected response"
    echo "   Response: $API_RESPONSE"
fi

echo ""
echo -e "${CYAN}3. Python Test:${NC}"
echo "   Run: ${YELLOW}uv run python experiments/test_djen_api.py${NC}"

echo ""
read -p "Press Enter to finish..."
clear

# ==============================================================================
# Success!
# ==============================================================================
echo -e "${GREEN}"
cat << "EOF"
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║                    ✅ Setup Complete! ✅                          ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

echo -e "${BOLD}Your DJEN proxy is ready!${NC}"
echo ""
echo -e "${CYAN}Function URL:${NC}"
echo "  $FUNCTION_URL"
echo ""
if [ "$REQUIRE_AUTH" = "true" ]; then
    echo -e "${CYAN}API Key:${NC}"
    echo "  $PROXY_API_KEY"
    echo ""
fi
echo -e "${BOLD}Next Steps:${NC}"
echo "  1️⃣  Test with: ${YELLOW}uv run python experiments/test_djen_api.py${NC}"
echo "  2️⃣  View logs: ${YELLOW}gcloud functions logs read $FUNCTION_NAME --region=$REGION${NC}"
echo "  3️⃣  Monitor: ${YELLOW}gcloud functions describe $FUNCTION_NAME --region=$REGION${NC}"
echo ""
echo -e "${BOLD}Cost Monitoring:${NC}"
echo "  • Free tier: 2M invocations/month"
echo "  • Expected: ~$2.50/month for MVP usage"
echo "  • Set up billing alerts in GCP Console"
echo ""
echo -e "${GREEN}Happy coding! 🚀${NC}"
echo ""
