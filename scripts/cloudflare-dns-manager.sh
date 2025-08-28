#!/bin/bash

# =============================================================================
# Cloudflare DNS Manager for FortiGate Nextrade
# Automatically manages DNS records and tunnel configuration
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Cloudflare Configuration
CF_API_TOKEN="${CF_API_TOKEN:-}"
CF_API_URL="https://api.cloudflare.com/client/v4"
CF_TUNNEL_TOKEN="${CLOUDFLARE_TUNNEL_TOKEN:-}"

# Check if required environment variables are set
check_env_vars() {
    if [ -z "$CF_API_TOKEN" ]; then
        echo -e "${RED}Error: CF_API_TOKEN environment variable is not set${NC}"
        echo "Set it using: export CF_API_TOKEN='your-api-token'"
        echo "Or add to GitHub Secrets as CF_API_TOKEN"
        exit 1
    fi
}

# Default values
DOMAIN=""
SUBDOMAIN="fortinet"
TUNNEL_NAME="fortinet-tunnel"
RECORD_TYPE="CNAME"
TUNNEL_ID="8ea78906-1a05-44fb-a1bb-e512172cb5ab"

# Function to display usage
usage() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  setup       Complete setup (zone, tunnel, DNS)"
    echo "  create-dns  Create DNS record only"
    echo "  list-zones  List all available zones"
    echo "  list-dns    List DNS records for a zone"
    echo "  delete-dns  Delete DNS record"
    echo "  verify      Verify DNS and tunnel configuration"
    echo ""
    echo "Options:"
    echo "  --domain DOMAIN     Domain name (e.g., jclee.me)"
    echo "  --subdomain NAME    Subdomain (default: fortinet)"
    echo "  --tunnel-id ID      Tunnel ID (for existing tunnels)"
    echo ""
    echo "Examples:"
    echo "  $0 setup --domain jclee.me"
    echo "  $0 create-dns --domain jclee.me --subdomain app"
    echo "  $0 verify --domain jclee.me"
    exit 1
}

# Parse command line arguments
COMMAND=$1
shift

while [[ $# -gt 0 ]]; do
    case $1 in
        --domain)
            DOMAIN="$2"
            shift 2
            ;;
        --subdomain)
            SUBDOMAIN="$2"
            shift 2
            ;;
        --tunnel-id)
            TUNNEL_ID="$2"
            shift 2
            ;;
        --help|-h)
            usage
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            usage
            ;;
    esac
done

# Function to make Cloudflare API calls
cf_api() {
    local method=$1
    local endpoint=$2
    local data=$3
    
    if [ -z "$data" ]; then
        curl -s -X "$method" \
            "$CF_API_URL/$endpoint" \
            -H "Authorization: Bearer $CF_API_TOKEN" \
            -H "Content-Type: application/json"
    else
        curl -s -X "$method" \
            "$CF_API_URL/$endpoint" \
            -H "Authorization: Bearer $CF_API_TOKEN" \
            -H "Content-Type: application/json" \
            -d "$data"
    fi
}

# Function to get zone ID
get_zone_id() {
    local domain=$1
    echo -e "${BLUE}Getting zone ID for $domain...${NC}"
    
    local response=$(cf_api GET "zones?name=$domain")
    local zone_id=$(echo "$response" | jq -r '.result[0].id // empty')
    
    if [ -z "$zone_id" ]; then
        echo -e "${RED}Zone not found for domain: $domain${NC}"
        echo -e "${YELLOW}Available zones:${NC}"
        list_zones
        return 1
    fi
    
    echo "$zone_id"
}

# Function to list all zones
list_zones() {
    echo -e "${BLUE}Fetching available zones...${NC}"
    
    local response=$(cf_api GET "zones")
    echo "$response" | jq -r '.result[] | "\(.name) (ID: \(.id))"'
}

# Function to create tunnel
create_tunnel() {
    echo -e "${BLUE}Creating Cloudflare tunnel...${NC}"
    
    # Check if tunnel already exists
    local existing=$(cf_api GET "accounts/\$ACCOUNT_ID/cfd_tunnel?name=$TUNNEL_NAME")
    local tunnel_id=$(echo "$existing" | jq -r '.result[0].id // empty')
    
    if [ -n "$tunnel_id" ]; then
        echo -e "${YELLOW}Tunnel already exists with ID: $tunnel_id${NC}"
        echo "$tunnel_id"
        return 0
    fi
    
    # Create new tunnel
    local data="{\"name\":\"$TUNNEL_NAME\",\"tunnel_secret\":\"$CF_TUNNEL_TOKEN\"}"
    local response=$(cf_api POST "accounts/\$ACCOUNT_ID/cfd_tunnel" "$data")
    tunnel_id=$(echo "$response" | jq -r '.result.id // empty')
    
    if [ -z "$tunnel_id" ]; then
        echo -e "${RED}Failed to create tunnel${NC}"
        echo "$response" | jq .
        return 1
    fi
    
    echo -e "${GREEN}✓ Tunnel created with ID: $tunnel_id${NC}"
    echo "$tunnel_id"
}

# Function to create DNS record
create_dns_record() {
    local zone_id=$1
    local name=$2
    local target=$3
    
    echo -e "${BLUE}Creating DNS record: $name.$DOMAIN → $target${NC}"
    
    # Check if record already exists
    local existing=$(cf_api GET "zones/$zone_id/dns_records?name=$name.$DOMAIN")
    local record_id=$(echo "$existing" | jq -r '.result[0].id // empty')
    
    if [ -n "$record_id" ]; then
        echo -e "${YELLOW}DNS record already exists. Updating...${NC}"
        # Update existing record
        # For A records, use the target IP directly
        if [ "$RECORD_TYPE" = "A" ]; then
            local data="{\"type\":\"A\",\"name\":\"$name\",\"content\":\"$target\",\"proxied\":true}"
        else
            local data="{\"type\":\"$RECORD_TYPE\",\"name\":\"$name\",\"content\":\"$target\",\"proxied\":true}"
        fi
        cf_api PUT "zones/$zone_id/dns_records/$record_id" "$data" > /dev/null
    else
        # Create new record
        # For A records, use the target IP directly
        if [ "$RECORD_TYPE" = "A" ]; then
            local data="{\"type\":\"A\",\"name\":\"$name\",\"content\":\"$target\",\"proxied\":true}"
        else
            local data="{\"type\":\"$RECORD_TYPE\",\"name\":\"$name\",\"content\":\"$target\",\"proxied\":true}"
        fi
        cf_api POST "zones/$zone_id/dns_records" "$data" > /dev/null
    fi
    
    echo -e "${GREEN}✓ DNS record created/updated${NC}"
}

# Function to list DNS records
list_dns_records() {
    local zone_id=$1
    echo -e "${BLUE}DNS records for $DOMAIN:${NC}"
    
    local response=$(cf_api GET "zones/$zone_id/dns_records")
    echo "$response" | jq -r '.result[] | "\(.type)\t\(.name)\t→ \(.content)\t(Proxied: \(.proxied))"'
}

# Function to delete DNS record
delete_dns_record() {
    local zone_id=$1
    local name=$2
    
    echo -e "${BLUE}Deleting DNS record: $name.$DOMAIN${NC}"
    
    local existing=$(cf_api GET "zones/$zone_id/dns_records?name=$name.$DOMAIN")
    local record_id=$(echo "$existing" | jq -r '.result[0].id // empty')
    
    if [ -z "$record_id" ]; then
        echo -e "${YELLOW}DNS record not found${NC}"
        return 0
    fi
    
    cf_api DELETE "zones/$zone_id/dns_records/$record_id" > /dev/null
    echo -e "${GREEN}✓ DNS record deleted${NC}"
}

# Function to verify configuration
verify_configuration() {
    echo -e "${BLUE}=== Verifying Cloudflare Configuration ===${NC}"
    
    # 1. Check zone
    local zone_id=$(get_zone_id "$DOMAIN")
    if [ -z "$zone_id" ]; then
        return 1
    fi
    echo -e "${GREEN}✓ Zone found: $DOMAIN (ID: $zone_id)${NC}"
    
    # 2. Check DNS record
    local dns_check=$(cf_api GET "zones/$zone_id/dns_records?name=$SUBDOMAIN.$DOMAIN")
    local dns_exists=$(echo "$dns_check" | jq -r '.result[0].id // empty')
    
    if [ -n "$dns_exists" ]; then
        echo -e "${GREEN}✓ DNS record exists: $SUBDOMAIN.$DOMAIN${NC}"
        echo "$dns_check" | jq -r '.result[0] | "  Type: \(.type), Target: \(.content), Proxied: \(.proxied)"'
    else
        echo -e "${RED}✗ DNS record not found: $SUBDOMAIN.$DOMAIN${NC}"
    fi
    
    # 3. Test DNS resolution
    echo -e "\n${BLUE}Testing DNS resolution...${NC}"
    local dns_result=$(dig +short "$SUBDOMAIN.$DOMAIN" @1.1.1.1)
    if [ -n "$dns_result" ]; then
        echo -e "${GREEN}✓ DNS resolves to: $dns_result${NC}"
    else
        echo -e "${YELLOW}⚠ DNS not yet propagated${NC}"
    fi
    
    # 4. Test HTTPS connectivity
    echo -e "\n${BLUE}Testing HTTPS connectivity...${NC}"
    if curl -s -f -m 5 "https://$SUBDOMAIN.$DOMAIN/api/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ HTTPS connection successful${NC}"
    else
        echo -e "${YELLOW}⚠ HTTPS connection failed (tunnel might not be running)${NC}"
    fi
}

# Function to setup everything
setup_complete() {
    echo -e "${CYAN}=== Cloudflare Complete Setup ===${NC}"
    
    # 1. Get zone ID
    local zone_id=$(get_zone_id "$DOMAIN")
    if [ -z "$zone_id" ]; then
        return 1
    fi
    
    # 2. Get account ID from zone
    local account_info=$(cf_api GET "zones/$zone_id")
    local account_id=$(echo "$account_info" | jq -r '.result.account.id')
    export ACCOUNT_ID=$account_id
    
    # 3. Create tunnel (if needed)
    local tunnel_id
    if [ -z "$TUNNEL_ID" ]; then
        # For now, we'll use the tunnel created by cloudflared service
        echo -e "${YELLOW}Note: Tunnel should be created by 'cloudflared service install' command${NC}"
        tunnel_id="fortinet-tunnel"
    else
        tunnel_id="$TUNNEL_ID"
    fi
    
    # 4. Create DNS record
    # For Cloudflare Tunnel, we need to point to the tunnel
    local tunnel_cname="${TUNNEL_ID}.cfargotunnel.com"
    create_dns_record "$zone_id" "$SUBDOMAIN" "$tunnel_cname"
    
    # 5. Show summary
    echo -e "\n${GREEN}=== Setup Complete ===${NC}"
    echo -e "Domain: ${CYAN}$SUBDOMAIN.$DOMAIN${NC}"
    echo -e "Tunnel: ${CYAN}$tunnel_id${NC}"
    echo -e "Status: ${GREEN}Active${NC}"
    echo -e "\nNext steps:"
    echo -e "1. Ensure Kubernetes deployment is running"
    echo -e "2. Wait 1-2 minutes for DNS propagation"
    echo -e "3. Access your application at: ${CYAN}https://$SUBDOMAIN.$DOMAIN${NC}"
}

# Check environment variables before execution
check_env_vars

# Main execution
case $COMMAND in
    setup)
        if [ -z "$DOMAIN" ]; then
            echo -e "${RED}Domain is required${NC}"
            usage
        fi
        setup_complete
        ;;
    create-dns)
        if [ -z "$DOMAIN" ]; then
            echo -e "${RED}Domain is required${NC}"
            usage
        fi
        zone_id=$(get_zone_id "$DOMAIN")
        if [ -n "$zone_id" ]; then
            # Create CNAME record for Cloudflare Tunnel
            local tunnel_cname="${TUNNEL_ID}.cfargotunnel.com"
            create_dns_record "$zone_id" "$SUBDOMAIN" "$tunnel_cname"
        fi
        ;;
    list-zones)
        list_zones
        ;;
    list-dns)
        if [ -z "$DOMAIN" ]; then
            echo -e "${RED}Domain is required${NC}"
            usage
        fi
        zone_id=$(get_zone_id "$DOMAIN")
        if [ -n "$zone_id" ]; then
            list_dns_records "$zone_id"
        fi
        ;;
    delete-dns)
        if [ -z "$DOMAIN" ]; then
            echo -e "${RED}Domain is required${NC}"
            usage
        fi
        zone_id=$(get_zone_id "$DOMAIN")
        if [ -n "$zone_id" ]; then
            delete_dns_record "$zone_id" "$SUBDOMAIN"
        fi
        ;;
    verify)
        if [ -z "$DOMAIN" ]; then
            echo -e "${RED}Domain is required${NC}"
            usage
        fi
        verify_configuration
        ;;
    *)
        echo -e "${RED}Invalid command: $COMMAND${NC}"
        usage
        ;;
esac