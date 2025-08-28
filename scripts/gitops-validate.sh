#!/bin/bash
# GitOps 4원칙 준수 검증 스크립트

set -e

echo "======================================"
echo "GitOps 4 Principles Validation Script"
echo "======================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Validation counters
PASSED=0
FAILED=0
WARNINGS=0

# Function to check a condition
check() {
    local description="$1"
    local command="$2"
    
    echo -n "Checking: $description... "
    
    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PASSED${NC}"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAILED${NC}"
        ((FAILED++))
        return 1
    fi
}

# Function to warn
warn() {
    local description="$1"
    echo -e "${YELLOW}⚠ WARNING: $description${NC}"
    ((WARNINGS++))
}

echo ""
echo "1. DECLARATIVE Configuration Check"
echo "-----------------------------------"

check "Kubernetes manifests exist" "test -d k8s/"
check "Kustomization files present" "test -f k8s/overlays/production/kustomization.yaml"
check "ArgoCD application manifest" "test -f argocd-apps/fortinet.yaml"
check "Helm Chart defined" "test -f charts/fortinet/Chart.yaml"
check "Dockerfile present" "test -f Dockerfile.production"

echo ""
echo "2. GIT SOURCE Verification"
echo "---------------------------"

check "Git repository initialized" "git rev-parse --git-dir"
check "Remote origin configured" "git remote get-url origin"
check "Clean working tree" "test -z \"$(git status --porcelain)\""
check "On valid branch" "git symbolic-ref HEAD"

# Get current git info
GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
echo "   Current SHA: $GIT_SHA"
echo "   Current Branch: $GIT_BRANCH"

echo ""
echo "3. PULL-BASED Deployment Check"
echo "-------------------------------"

check "ArgoCD sync policy defined" "grep -q 'syncPolicy:' argocd-apps/fortinet.yaml"
check "Automated sync enabled" "grep -q 'automated:' argocd-apps/fortinet.yaml"
check "Self-heal configured" "grep -q 'selfHeal: true' argocd-apps/fortinet.yaml"
check "Prune enabled" "grep -q 'prune: true' argocd-apps/fortinet.yaml"

echo ""
echo "4. IMMUTABLE Infrastructure Check"
echo "----------------------------------"

check "Image tag specified" "grep -q 'newTag:' k8s/overlays/production/kustomization.yaml"
check "Build metadata in Dockerfile" "grep -q 'ARG BUILD_TIMESTAMP' Dockerfile.production"
check "Git SHA in build args" "grep -q 'ARG GIT_SHA' Dockerfile.production"
check "Immutable tag reference" "grep -q 'IMMUTABLE_TAG' Dockerfile.production"

# Check if running in Kubernetes
if command -v kubectl > /dev/null 2>&1; then
    echo ""
    echo "5. RUNTIME Validation (Kubernetes)"
    echo "-----------------------------------"
    
    if kubectl get ns fortinet > /dev/null 2>&1; then
        check "Namespace exists" "kubectl get ns fortinet"
        check "Deployment exists" "kubectl get deployment fortinet -n fortinet"
        check "Pods running" "kubectl get pods -n fortinet --no-headers | grep -q Running"
        
        # Get deployed image
        DEPLOYED_IMAGE=$(kubectl get deployment fortinet -n fortinet -o jsonpath='{.spec.template.spec.containers[0].image}' 2>/dev/null || echo "unknown")
        echo "   Deployed Image: $DEPLOYED_IMAGE"
        
        # Check health endpoint
        if command -v curl > /dev/null 2>&1; then
            HEALTH_URL="http://192.168.50.110:30777/api/health"
            if curl -s -f --max-time 5 "$HEALTH_URL" > /dev/null 2>&1; then
                echo -e "   Health Check: ${GREEN}✓ HEALTHY${NC}"
                
                # Check GitOps compliance from health endpoint
                GITOPS_STATUS=$(curl -s "$HEALTH_URL" | python3 -c "import json,sys; data=json.load(sys.stdin); print(data.get('gitops_status', 'unknown'))" 2>/dev/null || echo "unknown")
                
                if [ "$GITOPS_STATUS" = "compliant" ]; then
                    echo -e "   GitOps Status: ${GREEN}✓ COMPLIANT${NC}"
                    ((PASSED++))
                else
                    echo -e "   GitOps Status: ${YELLOW}⚠ $GITOPS_STATUS${NC}"
                    ((WARNINGS++))
                fi
            else
                warn "Health endpoint not accessible"
            fi
        fi
    else
        warn "Fortinet namespace not found in cluster"
    fi
else
    warn "kubectl not available - skipping runtime checks"
fi

echo ""
echo "6. CI/CD Pipeline Check"
echo "-----------------------"

check "GitHub Actions workflow" "test -f .github/workflows/main-deploy.yml"
check "Build stage defined" "grep -q 'build-and-push:' .github/workflows/main-deploy.yml"
check "Deploy stage defined" "grep -q 'deploy:' .github/workflows/main-deploy.yml"
check "GitOps metadata in build" "grep -q 'BUILD_TIMESTAMP' .github/workflows/main-deploy.yml"

echo ""
echo "======================================"
echo "VALIDATION SUMMARY"
echo "======================================"
echo -e "Passed:   ${GREEN}$PASSED${NC}"
echo -e "Failed:   ${RED}$FAILED${NC}"
echo -e "Warnings: ${YELLOW}$WARNINGS${NC}"

if [ $FAILED -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ GitOps 4 Principles: COMPLIANT${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}✗ GitOps 4 Principles: NON-COMPLIANT${NC}"
    echo ""
    echo "Recommendations:"
    echo "1. Fix all failed checks above"
    echo "2. Ensure all manifests use declarative configuration"
    echo "3. Verify Git is the single source of truth"
    echo "4. Configure ArgoCD for pull-based deployments"
    echo "5. Use immutable image tags with build metadata"
    exit 1
fi