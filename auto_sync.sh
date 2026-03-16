#!/usr/bin/env bash
# Auto-relogin Simplifi sync script
# Validates token BEFORE fetching data - never uses cached/partial data

set -e
cd "$(dirname "$0")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=== Simplifi Daily Sync with Token Validation ==="
echo ""

# Track if we're using fresh data
DATA_IS_FRESH=false

# Function to validate token by checking API response
test_token_valid() {
    # Use the built-in login --verify command to check cached token
    ./run login --verify >/dev/null 2>&1
    return $?
}

# Function to login with Bitwarden credentials
login_with_bitwarden() {
    echo -e "${YELLOW}Token invalid or expired. Fetching credentials from Bitwarden...${NC}"
    
    # Clear existing invalid token to force fresh login
    echo "Clearing invalid token..."
    rm -f token
    
    # Unlock Bitwarden and get credentials
    export BW_PASSWORD=Carmelo3166.
    export BW_SESSION=$(bw unlock --passwordenv BW_PASSWORD --raw 2>/dev/null)
    
    if [ -z "$BW_SESSION" ]; then
        echo -e "${RED}ERROR: Could not unlock Bitwarden vault${NC}"
        exit 1
    fi
    
    # Get Simplifi credentials
    SIMPLIFI_EMAIL=$(bw get username "quicken.com")
    SIMPLIFI_PASSWORD=$(bw get password "quicken.com")
    
    if [ -z "$SIMPLIFI_EMAIL" ] || [ -z "$SIMPLIFI_PASSWORD" ]; then
        echo -e "${RED}ERROR: Could not retrieve Simplifi credentials from Bitwarden${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}Credentials retrieved. Logging in to Simplifi...${NC}"
    
    # Login using the run script with credentials
    if ! ./run login --email "$SIMPLIFI_EMAIL" --password "$SIMPLIFI_PASSWORD"; then
        echo -e "${RED}ERROR: Login failed${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}Login successful!${NC}"
    
    # Verify new token works
    echo "Verifying new token..."
    if test_token_valid; then
        echo -e "${GREEN}Token validated successfully${NC}"
        return 0
    else
        echo -e "${RED}ERROR: New token still invalid after login${NC}"
        exit 1
    fi
}

# Step 1: Validate token
echo "Step 1: Validating token..."
if test_token_valid; then
    echo -e "${GREEN}Token valid - will fetch fresh data${NC}"
else
    echo -e "${YELLOW}Token expired or invalid${NC}"
    login_with_bitwarden
fi

# Step 2: Clear any cached data to ensure we get fresh data
echo ""
echo "Step 2: Clearing cached data..."
rm -f data/output_accounts.json data/output_transactions.json data/output_categories.json 2>/dev/null || true

# Step 3: Fetch fresh data with validated token
echo ""
echo "Step 3: Fetching fresh data from Simplifi API..."
if ! ./run fetch --transactions --accounts 2>&1 | tee /tmp/simplifi_fetch.log; then
    echo -e "${RED}ERROR: Failed to fetch data from Simplifi API${NC}"
    echo "Check /tmp/simplifi_fetch.log for details"
    exit 1
fi

# Verify we got actual data
if [ ! -f data/output_transactions.csv ] || [ ! -f data/output_accounts.json ]; then
    echo -e "${RED}ERROR: No data files created - API may have returned empty response${NC}"
    exit 1
fi

# Check file sizes (should be > 1KB for real data)
TRANS_SIZE=$(stat -f%z data/output_transactions.csv 2>/dev/null || stat -c%s data/output_transactions.csv 2>/dev/null || echo 0)
if [ "$TRANS_SIZE" -lt 1000 ]; then
    echo -e "${RED}ERROR: Transaction data file too small ($TRANS_SIZE bytes) - possible cached/empty data${NC}"
    exit 1
fi

echo -e "${GREEN}Data fetched successfully ($TRANS_SIZE bytes)${NC}"

# Step 4: Update net worth with fresh data
echo ""
echo "Step 4: Updating net worth..."
if ! ./run networth update 2>&1 | tee /tmp/simplifi_networth.log; then
    echo -e "${RED}ERROR: Failed to update net worth${NC}"
    cat /tmp/simplifi_networth.log
    exit 1
fi

# Step 5: Get summary
echo ""
echo "Step 5: Generating summary..."
./run networth analyze --monthly 2>&1 | tail -20

echo ""
echo -e "${GREEN}=== Sync Complete - All data is fresh ===${NC}"
