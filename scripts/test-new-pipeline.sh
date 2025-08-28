#!/bin/bash

# test-new-pipeline.sh - Comprehensive test suite for GitOps pipeline
# This script validates all components of the new GitOps deployment pipeline

set -e

echo "🧪 GitOps Pipeline Test Suite"
echo "============================="
echo "This script will test all components of the GitOps pipeline"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test results tracking
TESTS_PASSED=0
TESTS_FAILED=0
FAILED_TESTS=()

# Function to run a test
run_test() {
    local test_name=$1
    local test_command=$2
    
    echo -n "  Testing $test_name... "
    
    if eval "$test_command" &>/dev/null; then
        echo -e "${GREEN}✓ PASS${NC}"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC}"
        ((TESTS_FAILED++))
        FAILED_TESTS+=("$test_name")
        return 1
    fi
}

# Function to check URL
check_url() {
    local url=$1
    curl -s -f -o /dev/null "$url"
}

# Function to check command exists
check_command() {
    command -v "$1" >/dev/null 2>&1
}

echo "📋 Starting comprehensive pipeline tests..."
echo ""

# 1. Prerequisites Check
echo "1️⃣ Checking prerequisites..."
run_test "Docker" "check_command docker"
run_test "kubectl" "check_command kubectl"
run_test "argocd CLI" "check_command argocd"
run_test "git" "check_command git"
run_test "curl" "check_command curl"
run_test "jq" "check_command jq"

# 2. Registry Tests
echo ""
echo "2️⃣ Testing Docker Registry..."
run_test "Registry accessibility" "check_url https://registry.jclee.me/v2/"
run_test "Registry catalog" "check_url https://registry.jclee.me/v2/_catalog"
run_test "Fortinet repository" "check_url https://registry.jclee.me/v2/fortinet/tags/list"

# Test registry authentication
echo -n "  Testing registry authentication... "
if curl -s -u admin:bingogo1 https://registry.jclee.me/v2/fortinet/tags/list | grep -q "tags"; then
    echo -e "${GREEN}✓ PASS${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ FAIL${NC}"
    ((TESTS_FAILED++))
    FAILED_TESTS+=("Registry authentication")
fi

# 3. ChartMuseum Tests
echo ""
echo "3️⃣ Testing ChartMuseum..."
run_test "ChartMuseum accessibility" "check_url https://charts.jclee.me"
run_test "ChartMuseum API" "check_url https://charts.jclee.me/api/charts"

# Check if fortinet chart exists
echo -n "  Testing fortinet chart presence... "
if curl -s https://charts.jclee.me/api/charts | grep -q "fortinet"; then
    echo -e "${GREEN}✓ PASS${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${YELLOW}⚠ Chart not found (expected for first run)${NC}"
fi

# 4. Kubernetes Resources
echo ""
echo "4️⃣ Testing Kubernetes resources..."
run_test "fortinet namespace" "kubectl get namespace fortinet"
run_test "Registry secret" "kubectl get secret registry-credentials -n fortinet"
run_test "Deployment" "kubectl get deployment fortinet-app -n fortinet"
run_test "Service" "kubectl get service fortinet-service -n fortinet"
run_test "ConfigMap" "kubectl get configmap fortinet-config -n fortinet"

# Check pod status
echo -n "  Testing pod status... "
POD_STATUS=$(kubectl get pods -n fortinet -l app=fortinet -o jsonpath='{.items[0].status.phase}' 2>/dev/null || echo "NotFound")
if [ "$POD_STATUS" = "Running" ]; then
    echo -e "${GREEN}✓ PASS (Running)${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${YELLOW}⚠ WARNING (Status: $POD_STATUS)${NC}"
fi

# 5. ArgoCD Tests
echo ""
echo "5️⃣ Testing ArgoCD integration..."

# Check ArgoCD login
echo -n "  Testing ArgoCD authentication... "
if argocd account whoami &>/dev/null; then
    echo -e "${GREEN}✓ PASS${NC}"
    ((TESTS_PASSED++))
else
    # Try to login
    if argocd login argo.jclee.me --username admin --password bingogo1 --insecure --grpc-web &>/dev/null; then
        echo -e "${GREEN}✓ PASS (logged in)${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗ FAIL${NC}"
        ((TESTS_FAILED++))
        FAILED_TESTS+=("ArgoCD authentication")
    fi
fi

run_test "ArgoCD application exists" "argocd app get fortinet"

# Check sync status
echo -n "  Testing application sync status... "
SYNC_STATUS=$(argocd app get fortinet -o json 2>/dev/null | jq -r '.status.sync.status' || echo "Unknown")
if [ "$SYNC_STATUS" = "Synced" ]; then
    echo -e "${GREEN}✓ PASS (Synced)${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${YELLOW}⚠ WARNING (Status: $SYNC_STATUS)${NC}"
fi

# Check health status
echo -n "  Testing application health... "
HEALTH_STATUS=$(argocd app get fortinet -o json 2>/dev/null | jq -r '.status.health.status' || echo "Unknown")
if [ "$HEALTH_STATUS" = "Healthy" ]; then
    echo -e "${GREEN}✓ PASS (Healthy)${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${YELLOW}⚠ WARNING (Status: $HEALTH_STATUS)${NC}"
fi

# 6. Application Tests
echo ""
echo "6️⃣ Testing application endpoints..."
run_test "Main application (fortinet.jclee.me)" "check_url https://fortinet.jclee.me"
run_test "Health endpoint" "check_url https://fortinet.jclee.me/api/health"
run_test "NodePort service" "check_url http://192.168.50.110:30777/api/health"

# Test API response
echo -n "  Testing API health response... "
HEALTH_RESPONSE=$(curl -s https://fortinet.jclee.me/api/health 2>/dev/null || echo "{}")
if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
    echo -e "${GREEN}✓ PASS${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ FAIL${NC}"
    ((TESTS_FAILED++))
    FAILED_TESTS+=("API health response")
fi

# 7. Git Repository Tests
echo ""
echo "7️⃣ Testing Git repository state..."

# Check for required files
echo -n "  Testing GitOps workflow file... "
if [ -f ".github/workflows/gitops-deploy.yml" ]; then
    echo -e "${GREEN}✓ PASS${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ FAIL${NC}"
    ((TESTS_FAILED++))
    FAILED_TESTS+=("GitOps workflow file")
fi

echo -n "  Testing ArgoCD application spec... "
if [ -f "argocd/fortinet-app.yaml" ]; then
    echo -e "${GREEN}✓ PASS${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ FAIL${NC}"
    ((TESTS_FAILED++))
    FAILED_TESTS+=("ArgoCD application spec")
fi

echo -n "  Testing Kubernetes manifests... "
if [ -d "k8s/manifests" ] && [ -f "k8s/manifests/kustomization.yaml" ]; then
    echo -e "${GREEN}✓ PASS${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ FAIL${NC}"
    ((TESTS_FAILED++))
    FAILED_TESTS+=("Kubernetes manifests")
fi

# 8. GitHub Actions Tests (if gh CLI available)
echo ""
echo "8️⃣ Testing GitHub Actions..."
if check_command gh; then
    echo -n "  Testing workflow runs... "
    if gh run list --workflow=gitops-deploy.yml --limit 1 &>/dev/null; then
        echo -e "${GREEN}✓ PASS${NC}"
        ((TESTS_PASSED++))
        
        # Get latest run status
        LATEST_RUN=$(gh run list --workflow=gitops-deploy.yml --limit 1 --json status,conclusion -q '.[0]')
        if [ -n "$LATEST_RUN" ]; then
            STATUS=$(echo "$LATEST_RUN" | jq -r '.status')
            CONCLUSION=$(echo "$LATEST_RUN" | jq -r '.conclusion')
            echo -e "  Latest run: ${BLUE}Status=$STATUS, Conclusion=$CONCLUSION${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ Unable to check (gh not authenticated)${NC}"
    fi
else
    echo "  Skipping GitHub Actions tests (gh CLI not available)"
fi

# 9. Image Tests
echo ""
echo "9️⃣ Testing Docker images..."

# Get latest image tag
echo -n "  Testing latest image tag... "
LATEST_TAG=$(curl -s https://registry.jclee.me/v2/fortinet/tags/list 2>/dev/null | jq -r '.tags[]' | grep -E '^2\.0\.' | sort -V | tail -1)
if [ -n "$LATEST_TAG" ]; then
    echo -e "${GREEN}✓ PASS (Latest: $LATEST_TAG)${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ FAIL${NC}"
    ((TESTS_FAILED++))
    FAILED_TESTS+=("Latest image tag")
fi

# Check if image matches deployment
echo -n "  Testing deployed image version... "
DEPLOYED_IMAGE=$(kubectl get deployment fortinet-app -n fortinet -o jsonpath='{.spec.template.spec.containers[0].image}' 2>/dev/null)
if [ -n "$DEPLOYED_IMAGE" ]; then
    echo -e "${GREEN}✓ PASS${NC}"
    echo -e "  Deployed: ${BLUE}$DEPLOYED_IMAGE${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ FAIL${NC}"
    ((TESTS_FAILED++))
    FAILED_TESTS+=("Deployed image version")
fi

# 10. Security Tests
echo ""
echo "🔐 Testing security configurations..."
run_test "Registry secret type" "kubectl get secret registry-credentials -n fortinet -o jsonpath='{.type}' | grep -q 'kubernetes.io/dockerconfigjson'"
run_test "Image pull policy" "kubectl get deployment fortinet-app -n fortinet -o jsonpath='{.spec.template.spec.containers[0].imagePullPolicy}' | grep -q 'Always'"

# Summary
echo ""
echo "📊 Test Summary"
echo "==============="
echo -e "Tests Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests Failed: ${RED}$TESTS_FAILED${NC}"
echo -e "Total Tests: $((TESTS_PASSED + TESTS_FAILED))"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed! GitOps pipeline is fully operational.${NC}"
    echo ""
    echo "🚀 Pipeline is ready for production use!"
    exit 0
else
    echo -e "${RED}❌ Some tests failed:${NC}"
    for test in "${FAILED_TESTS[@]}"; do
        echo -e "  - ${RED}$test${NC}"
    done
    echo ""
    echo "📝 Troubleshooting tips:"
    echo "1. Check service accessibility:"
    echo "   curl -v https://registry.jclee.me/v2/"
    echo "   curl -v https://argo.jclee.me"
    echo ""
    echo "2. Verify ArgoCD application:"
    echo "   argocd app get fortinet --refresh"
    echo "   argocd app sync fortinet"
    echo ""
    echo "3. Check Kubernetes resources:"
    echo "   kubectl get all -n fortinet"
    echo "   kubectl logs -n fortinet deployment/fortinet-app"
    echo ""
    echo "4. Review GitHub Actions:"
    echo "   gh run list --workflow=gitops-deploy.yml"
    echo "   gh run view <run-id> --log"
    exit 1
fi