#!/bin/bash

# ArgoCD Duplicate Configuration Cleanup Script
# Removes duplicate ArgoCD application configurations and applies unified config

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}=== FortiNet ArgoCD Configuration Cleanup ===${NC}"
echo "Project root: $PROJECT_ROOT"

# Function to safely remove files
safe_remove() {
    local file="$1"
    if [[ -f "$file" ]]; then
        echo -e "${YELLOW}Removing duplicate: ${file}${NC}"
        # Create backup first
        cp "$file" "${file}.backup.$(date +%Y%m%d_%H%M%S)"
        rm "$file"
        echo -e "${GREEN}✓ Removed and backed up${NC}"
    else
        echo -e "${YELLOW}File not found: ${file}${NC}"
    fi
}

# Duplicate ArgoCD application files to remove
DUPLICATE_FILES=(
    "$PROJECT_ROOT/argocd-apps/fortinet.yaml"
    "$PROJECT_ROOT/deployment/fortinet-argocd-app.yaml"
    "$PROJECT_ROOT/k8s/argocd/fortinet-app.yaml"
    "$PROJECT_ROOT/argocd-apps/base/fortinet-application.yaml"
    "$PROJECT_ROOT/argocd/application.yaml"
)

echo -e "\n${BLUE}Step 1: Backing up and removing duplicate configurations${NC}"
for file in "${DUPLICATE_FILES[@]}"; do
    safe_remove "$file"
done

# Move unified config to main location
UNIFIED_CONFIG="$PROJECT_ROOT/argocd/fortinet-unified.yaml"
MAIN_CONFIG="$PROJECT_ROOT/argocd/application.yaml"

if [[ -f "$UNIFIED_CONFIG" ]]; then
    echo -e "\n${BLUE}Step 2: Installing unified configuration${NC}"
    mv "$UNIFIED_CONFIG" "$MAIN_CONFIG"
    echo -e "${GREEN}✓ Unified configuration installed as $MAIN_CONFIG${NC}"
else
    echo -e "${RED}✗ Unified configuration not found at $UNIFIED_CONFIG${NC}"
    exit 1
fi

# Check if ArgoCD CLI is available
if command -v argocd &> /dev/null; then
    echo -e "\n${BLUE}Step 3: Applying ArgoCD configuration${NC}"
    
    # Delete existing application (if exists)
    if argocd app get fortinet &> /dev/null; then
        echo -e "${YELLOW}Deleting existing ArgoCD application...${NC}"
        argocd app delete fortinet --cascade --yes || true
        sleep 5
    fi
    
    # Apply new configuration
    echo -e "${GREEN}Applying unified ArgoCD configuration...${NC}"
    kubectl apply -f "$MAIN_CONFIG"
    
    echo -e "${GREEN}✓ ArgoCD application registered successfully${NC}"
    
    # Wait for sync
    echo -e "${BLUE}Waiting for initial sync...${NC}"
    sleep 10
    argocd app sync fortinet --prune || true
    
else
    echo -e "\n${YELLOW}ArgoCD CLI not found. Please apply manually:${NC}"
    echo "kubectl apply -f $MAIN_CONFIG"
fi

# Update kustomization if exists
KUSTOMIZATION_FILE="$PROJECT_ROOT/argocd-apps/overlays/prod/kustomization.yaml"
if [[ -f "$KUSTOMIZATION_FILE" ]]; then
    echo -e "\n${BLUE}Step 4: Updating kustomization.yaml${NC}"
    sed -i 's|fortinet-application.yaml|../../../argocd/application.yaml|g' "$KUSTOMIZATION_FILE"
    echo -e "${GREEN}✓ Kustomization updated${NC}"
fi

echo -e "\n${GREEN}=== Cleanup Complete ===${NC}"
echo -e "${BLUE}Summary:${NC}"
echo "• Removed ${#DUPLICATE_FILES[@]} duplicate ArgoCD configurations"
echo "• Installed unified configuration at: $MAIN_CONFIG"
echo "• ArgoCD application: fortinet"
echo "• Namespace: fortinet"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Verify application status: argocd app get fortinet"
echo "2. Check deployment: kubectl get pods -n fortinet"
echo "3. Health check: curl http://192.168.50.110:30777/api/health"
echo ""
echo -e "${BLUE}Backup files created with timestamp for recovery if needed.${NC}"