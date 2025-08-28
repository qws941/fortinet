#!/bin/bash
# =============================================================================
# FortiGate Unified Setup Testing Script
# Tests all-in-one container and unified configuration
# =============================================================================

set -e

echo "🧪 Testing FortiGate Unified All-in-One Setup"
echo "=============================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test results tracking
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0

# Function to print test results
print_test_result() {
    local test_name="$1"
    local result="$2"
    local message="$3"
    
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    
    if [ "$result" == "PASS" ]; then
        echo -e "${GREEN}✅ $test_name: PASSED${NC} - $message"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}❌ $test_name: FAILED${NC} - $message"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

# Function to run test with timeout
run_test_with_timeout() {
    local timeout_duration="$1"
    local test_command="$2"
    local test_name="$3"
    
    if timeout "$timeout_duration" bash -c "$test_command" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

echo -e "${BLUE}🔍 Phase 1: Configuration File Validation${NC}"
echo "-------------------------------------------"

# Test 1: Check Dockerfile.all-in-one exists
if [ -f "Dockerfile.all-in-one" ]; then
    print_test_result "Dockerfile Validation" "PASS" "Dockerfile.all-in-one exists"
else
    print_test_result "Dockerfile Validation" "FAIL" "Dockerfile.all-in-one not found"
fi

# Test 2: Check unified docker-compose.yml
if [ -f "docker-compose.yml" ]; then
    if grep -q "Dockerfile.all-in-one" docker-compose.yml; then
        print_test_result "Docker Compose Config" "PASS" "Uses all-in-one dockerfile"
    else
        print_test_result "Docker Compose Config" "FAIL" "Does not reference all-in-one dockerfile"
    fi
else
    print_test_result "Docker Compose Config" "FAIL" "docker-compose.yml not found"
fi

# Test 3: Check unified CI/CD pipeline
if [ -f ".github/workflows/unified-pipeline.yml" ]; then
    print_test_result "Unified CI/CD Pipeline" "PASS" "Unified pipeline configuration exists"
else
    print_test_result "Unified CI/CD Pipeline" "FAIL" "Unified pipeline not found"
fi

# Test 4: Check for removed duplicate files
DUPLICATE_FILES=0
for file in docker-simple.yml gitops-pipeline.yml docker-build-verify.yml; do
    if [ -f ".github/workflows/$file" ]; then
        DUPLICATE_FILES=$((DUPLICATE_FILES + 1))
    fi
done

if [ $DUPLICATE_FILES -eq 0 ]; then
    print_test_result "Duplicate File Cleanup" "PASS" "No duplicate CI/CD files found"
else
    print_test_result "Duplicate File Cleanup" "FAIL" "$DUPLICATE_FILES duplicate files still exist"
fi

echo ""
echo -e "${BLUE}🔨 Phase 2: Docker Build Testing${NC}"
echo "--------------------------------"

# Test 5: Docker build test
echo "Building all-in-one container (this may take a few minutes)..."
if run_test_with_timeout "600s" "docker build -f Dockerfile.all-in-one -t fortinet-test:latest ." "Docker Build"; then
    print_test_result "Docker Build" "PASS" "All-in-one container built successfully"
    
    # Test 6: Container startup test
    echo "Testing container startup..."
    if run_test_with_timeout "60s" "docker run -d --name fortinet-test-container -p 7778:7777 fortinet-test:latest" "Container Startup"; then
        print_test_result "Container Startup" "PASS" "Container started successfully"
        
        # Wait for services to initialize
        echo "Waiting for services to initialize..."
        sleep 30
        
        # Test 7: Health check test
        if run_test_with_timeout "30s" "curl -f http://localhost:7778/api/health" "Health Check"; then
            print_test_result "Health Check" "PASS" "Application health check passed"
        else
            print_test_result "Health Check" "FAIL" "Application health check failed"
        fi
        
        # Cleanup test container
        docker stop fortinet-test-container >/dev/null 2>&1 || true
        docker rm fortinet-test-container >/dev/null 2>&1 || true
    else
        print_test_result "Container Startup" "FAIL" "Container failed to start"
    fi
    
    # Cleanup test image
    docker rmi fortinet-test:latest >/dev/null 2>&1 || true
else
    print_test_result "Docker Build" "FAIL" "Container build failed"
fi

echo ""
echo -e "${BLUE}🔍 Phase 3: Configuration Validation${NC}"
echo "--------------------------------------"

# Test 8: Self-contained configuration check
if grep -q "SELF_CONTAINED=true" docker-compose.yml; then
    print_test_result "Self-Contained Config" "PASS" "Self-contained mode enabled"
else
    print_test_result "Self-Contained Config" "FAIL" "Self-contained mode not configured"
fi

# Test 9: No external dependencies check
if grep -q "NO_EXTERNAL_DEPS=true" docker-compose.yml; then
    print_test_result "No External Dependencies" "PASS" "External dependencies disabled"
else
    print_test_result "No External Dependencies" "FAIL" "External dependencies not disabled"
fi

# Test 10: Internal service connections check
if grep -q "localhost:5432" docker-compose.yml && grep -q "localhost:6379" docker-compose.yml; then
    print_test_result "Internal Service Connections" "PASS" "Using localhost connections"
else
    print_test_result "Internal Service Connections" "FAIL" "Not using localhost connections"
fi

echo ""
echo -e "${BLUE}📊 Test Summary${NC}"
echo "==============="

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 ALL TESTS PASSED! ($TESTS_PASSED/$TESTS_TOTAL)${NC}"
    echo ""
    echo "✅ FortiGate Unified All-in-One Setup is ready for deployment!"
    echo ""
    echo "Next steps:"
    echo "1. Push changes to trigger unified CI/CD pipeline"
    echo "2. Monitor deployment at http://192.168.50.110:30777"
    echo "3. Access application at http://fortinet.jclee.me"
    exit 0
else
    echo -e "${RED}❌ TESTS FAILED: $TESTS_FAILED/$TESTS_TOTAL${NC}"
    echo -e "${GREEN}✅ TESTS PASSED: $TESTS_PASSED/$TESTS_TOTAL${NC}"
    echo ""
    echo "Please review and fix the failed tests before proceeding."
    exit 1
fi