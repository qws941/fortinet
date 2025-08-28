#!/bin/bash
# =============================================================================
# Pipeline Verification Script
# Comprehensive verification of CI/CD pipeline components
# =============================================================================

set -e

# Configuration
REGISTRY="${REGISTRY:-registry.jclee.me}"
PROJECT="${PROJECT:-fortinet}"
DEPLOYMENT_HOST="${DEPLOYMENT_HOST:-192.168.50.110}"
DEPLOYMENT_PORT="${DEPLOYMENT_PORT:-30777}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Test results
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
WARNINGS=0

# =============================================================================
# Functions
# =============================================================================

log_test() {
    echo -e "${CYAN}[TEST]${NC} $1"
    ((TOTAL_TESTS++))
}

log_pass() {
    echo -e "${GREEN}  ✓${NC} $1"
    ((PASSED_TESTS++))
}

log_fail() {
    echo -e "${RED}  ✗${NC} $1"
    ((FAILED_TESTS++))
}

log_warning() {
    echo -e "${YELLOW}  ⚠${NC} $1"
    ((WARNINGS++))
}

log_info() {
    echo -e "${BLUE}  ℹ${NC} $1"
}

print_header() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# =============================================================================
# Test Functions
# =============================================================================

test_docker_installation() {
    log_test "Docker Installation"
    
    if command -v docker &> /dev/null; then
        local version=$(docker --version)
        log_pass "Docker installed: $version"
        
        # Check Docker daemon
        if docker info &> /dev/null; then
            log_pass "Docker daemon is running"
        else
            log_fail "Docker daemon is not running"
        fi
        
        # Check Docker Compose
        if command -v docker-compose &> /dev/null; then
            local compose_version=$(docker-compose --version)
            log_pass "Docker Compose installed: $compose_version"
        else
            log_warning "Docker Compose not installed"
        fi
    else
        log_fail "Docker is not installed"
    fi
}

test_github_actions_runner() {
    log_test "GitHub Actions Runner"
    
    # Check if runner service exists
    if systemctl list-units --all | grep -q github-runner; then
        log_pass "GitHub runner service found"
        
        # Check if running
        if systemctl is-active --quiet github-runner; then
            log_pass "GitHub runner is active"
        else
            log_warning "GitHub runner is not active"
        fi
    else
        log_warning "GitHub runner service not found"
    fi
    
    # Check runner directory
    if [ -d "/home/runner/actions-runner" ]; then
        log_pass "Runner directory exists"
    else
        log_info "Runner might be in different location"
    fi
}

test_registry_access() {
    log_test "Docker Registry Access"
    
    # Test registry connectivity
    if curl -s -f "https://${REGISTRY}/v2/" -o /dev/null 2>&1 || \
       curl -s -f "http://${REGISTRY}/v2/" -o /dev/null 2>&1; then
        log_pass "Registry ${REGISTRY} is accessible"
        
        # Try to list repositories
        if curl -s -u "admin:bingogo1" "https://${REGISTRY}/v2/_catalog" | grep -q "repositories"; then
            log_pass "Can list repositories in registry"
        else
            log_warning "Cannot list repositories (authentication may be required)"
        fi
    else
        log_fail "Cannot access registry ${REGISTRY}"
    fi
    
    # Check Docker login status
    if docker system info 2>/dev/null | grep -q "${REGISTRY}"; then
        log_pass "Docker is logged into ${REGISTRY}"
    else
        log_warning "Docker not logged into registry"
    fi
}

test_docker_images() {
    log_test "Docker Images"
    
    local images=("${PROJECT}" "${PROJECT}-redis" "${PROJECT}-postgresql")
    
    for image in "${images[@]}"; do
        local full_image="${REGISTRY}/${image}:latest"
        
        # Check if image exists locally
        if docker images | grep -q "${REGISTRY}/${image}"; then
            log_pass "Image ${image} exists locally"
        else
            log_warning "Image ${image} not found locally"
        fi
        
        # Try to pull from registry
        if docker pull "${full_image}" &> /dev/null; then
            log_pass "Successfully pulled ${image} from registry"
            
            # Get image details
            local size=$(docker images "${full_image}" --format "{{.Size}}" 2>/dev/null)
            local created=$(docker images "${full_image}" --format "{{.CreatedAt}}" 2>/dev/null)
            log_info "Image size: ${size}, Created: ${created}"
        else
            log_warning "Cannot pull ${image} from registry"
        fi
    done
}

test_helm_setup() {
    log_test "Helm Configuration"
    
    # Check Helm installation
    if command -v helm &> /dev/null; then
        local helm_version=$(helm version --short)
        log_pass "Helm installed: $helm_version"
        
        # Check for Helm chart
        if [ -f "charts/fortinet/Chart.yaml" ]; then
            log_pass "Helm chart found"
            
            # Validate chart
            if helm lint charts/fortinet &> /dev/null; then
                log_pass "Helm chart is valid"
            else
                log_warning "Helm chart has issues"
            fi
        else
            log_warning "Helm chart not found"
        fi
        
        # Check ChartMuseum connectivity
        if curl -s -f "https://charts.jclee.me/health" -o /dev/null 2>&1; then
            log_pass "ChartMuseum is accessible"
        else
            log_warning "Cannot access ChartMuseum"
        fi
    else
        log_fail "Helm is not installed"
    fi
}

test_application_health() {
    log_test "Application Health"
    
    local health_url="http://${DEPLOYMENT_HOST}:${DEPLOYMENT_PORT}/api/health"
    local app_url="http://${DEPLOYMENT_HOST}:${DEPLOYMENT_PORT}"
    
    # Test health endpoint
    local http_code=$(curl -s -o /dev/null -w "%{http_code}" "${health_url}" 2>/dev/null)
    
    if [ "$http_code" = "200" ]; then
        log_pass "Health endpoint responding (HTTP ${http_code})"
        
        # Get response time
        local response_time=$(curl -s -o /dev/null -w "%{time_total}" "${health_url}")
        log_info "Response time: ${response_time}s"
        
        # Check response content
        local health_response=$(curl -s "${health_url}" 2>/dev/null)
        if echo "$health_response" | grep -q "healthy\|ok\|UP"; then
            log_pass "Application reports healthy status"
        else
            log_warning "Health status unclear"
        fi
    elif [ "$http_code" = "000" ]; then
        log_fail "Cannot connect to application"
    else
        log_warning "Health endpoint returned HTTP ${http_code}"
    fi
    
    # Test main application
    local main_code=$(curl -s -o /dev/null -w "%{http_code}" "${app_url}" 2>/dev/null)
    if [[ "$main_code" =~ ^[23] ]]; then
        log_pass "Main application accessible (HTTP ${main_code})"
    else
        log_warning "Main application returned HTTP ${main_code}"
    fi
}

test_github_workflow() {
    log_test "GitHub Workflow Files"
    
    # Check workflow directory
    if [ -d ".github/workflows" ]; then
        log_pass "Workflow directory exists"
        
        # Count workflow files
        local workflow_count=$(find .github/workflows -name "*.yml" -o -name "*.yaml" | wc -l)
        log_info "Found ${workflow_count} workflow files"
        
        # Check specific workflows
        local workflows=("main-deploy.yml" "enhanced-pipeline.yml")
        for workflow in "${workflows[@]}"; do
            if [ -f ".github/workflows/${workflow}" ]; then
                log_pass "Workflow ${workflow} exists"
                
                # Basic YAML validation
                if command -v yamllint &> /dev/null; then
                    if yamllint -d relaxed ".github/workflows/${workflow}" &> /dev/null; then
                        log_pass "Workflow ${workflow} is valid YAML"
                    else
                        log_warning "Workflow ${workflow} has YAML issues"
                    fi
                fi
            else
                log_info "Workflow ${workflow} not found"
            fi
        done
    else
        log_fail "Workflow directory not found"
    fi
}

test_security_scanning() {
    log_test "Security Scanning Tools"
    
    # Check Trivy
    if command -v trivy &> /dev/null; then
        local trivy_version=$(trivy --version 2>/dev/null | head -1)
        log_pass "Trivy installed: $trivy_version"
        
        # Quick vulnerability database update check
        if trivy image --download-db-only &> /dev/null; then
            log_pass "Trivy database is accessible"
        else
            log_warning "Cannot update Trivy database"
        fi
    else
        log_warning "Trivy not installed"
    fi
    
    # Check other security tools
    local security_tools=("bandit" "safety" "semgrep")
    for tool in "${security_tools[@]}"; do
        if command -v "$tool" &> /dev/null; then
            log_pass "$tool is installed"
        else
            log_info "$tool not installed"
        fi
    done
}

test_build_artifacts() {
    log_test "Build Artifacts"
    
    # Check for build scripts
    local build_scripts=("build-and-push.sh" "build-and-push-enhanced.sh")
    for script in "${build_scripts[@]}"; do
        if [ -f "$script" ]; then
            log_pass "Build script $script exists"
            
            if [ -x "$script" ]; then
                log_pass "Build script $script is executable"
            else
                log_warning "Build script $script is not executable"
            fi
        else
            log_info "Build script $script not found"
        fi
    done
    
    # Check for Dockerfiles
    local dockerfile_count=$(find . -name "Dockerfile*" -type f | wc -l)
    log_info "Found ${dockerfile_count} Dockerfiles"
    
    # Check for deployment info
    if [ -f "deployment-info.json" ]; then
        log_pass "Deployment info file exists"
        
        # Parse deployment info
        if command -v jq &> /dev/null && [ -f "deployment-info.json" ]; then
            local version=$(jq -r '.version' deployment-info.json 2>/dev/null)
            local timestamp=$(jq -r '.timestamp' deployment-info.json 2>/dev/null)
            log_info "Last deployment: version ${version} at ${timestamp}"
        fi
    else
        log_info "No deployment info file found"
    fi
}

test_network_connectivity() {
    log_test "Network Connectivity"
    
    # Test DNS resolution
    if nslookup github.com &> /dev/null; then
        log_pass "DNS resolution working"
    else
        log_fail "DNS resolution failed"
    fi
    
    # Test GitHub connectivity
    if curl -s -f "https://api.github.com" -o /dev/null; then
        log_pass "GitHub API accessible"
    else
        log_fail "Cannot access GitHub API"
    fi
    
    # Test registry connectivity
    if ping -c 1 "${REGISTRY%%:*}" &> /dev/null; then
        log_pass "Can ping registry host"
    else
        log_warning "Cannot ping registry host"
    fi
    
    # Test deployment host connectivity
    if ping -c 1 "${DEPLOYMENT_HOST}" &> /dev/null; then
        log_pass "Can ping deployment host"
    else
        log_warning "Cannot ping deployment host"
    fi
}

# =============================================================================
# Summary Function
# =============================================================================

print_summary() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}                  TEST SUMMARY                    ${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    echo -e "Total Tests:     ${TOTAL_TESTS}"
    echo -e "${GREEN}Passed:          ${PASSED_TESTS}${NC}"
    echo -e "${RED}Failed:          ${FAILED_TESTS}${NC}"
    echo -e "${YELLOW}Warnings:        ${WARNINGS}${NC}"
    echo ""
    
    local pass_rate=0
    if [ $TOTAL_TESTS -gt 0 ]; then
        pass_rate=$(( PASSED_TESTS * 100 / TOTAL_TESTS ))
    fi
    
    echo -e "Pass Rate:       ${pass_rate}%"
    echo ""
    
    if [ $FAILED_TESTS -eq 0 ]; then
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${GREEN}       ✅ PIPELINE VERIFICATION PASSED           ${NC}"
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    elif [ $FAILED_TESTS -le 3 ]; then
        echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${YELLOW}    ⚠️  PIPELINE VERIFICATION PARTIAL PASS        ${NC}"
        echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    else
        echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${RED}       ❌ PIPELINE VERIFICATION FAILED            ${NC}"
        echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    fi
    
    # Generate report file
    cat > pipeline-verification-report.md << EOF
# Pipeline Verification Report

## Test Results
- **Date**: $(date -u +'%Y-%m-%d %H:%M:%S UTC')
- **Total Tests**: ${TOTAL_TESTS}
- **Passed**: ${PASSED_TESTS}
- **Failed**: ${FAILED_TESTS}
- **Warnings**: ${WARNINGS}
- **Pass Rate**: ${pass_rate}%

## Configuration
- **Registry**: ${REGISTRY}
- **Project**: ${PROJECT}
- **Deployment Host**: ${DEPLOYMENT_HOST}:${DEPLOYMENT_PORT}

## Component Status
- Docker: $([ $FAILED_TESTS -eq 0 ] && echo "✅ Operational" || echo "⚠️ Issues detected")
- Registry: $(docker system info 2>/dev/null | grep -q "${REGISTRY}" && echo "✅ Connected" || echo "⚠️ Not connected")
- GitHub Runner: $(systemctl is-active --quiet github-runner && echo "✅ Active" || echo "⚠️ Inactive")
- Application: $(curl -s "http://${DEPLOYMENT_HOST}:${DEPLOYMENT_PORT}/api/health" | grep -q "healthy" && echo "✅ Healthy" || echo "⚠️ Unhealthy")

## Recommendations
EOF
    
    if [ $WARNINGS -gt 0 ]; then
        echo "- Review and address warning messages" >> pipeline-verification-report.md
    fi
    
    if [ $FAILED_TESTS -gt 0 ]; then
        echo "- Fix failed tests before production deployment" >> pipeline-verification-report.md
    fi
    
    echo "" >> pipeline-verification-report.md
    echo "Report generated: $(date)" >> pipeline-verification-report.md
    
    echo ""
    echo -e "${BLUE}Report saved to: pipeline-verification-report.md${NC}"
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    echo -e "${CYAN}╔══════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║     FORTINET CI/CD PIPELINE VERIFICATION        ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════╝${NC}"
    
    print_header "1. Docker & Container Platform"
    test_docker_installation
    
    print_header "2. GitHub Actions Runner"
    test_github_actions_runner
    
    print_header "3. Docker Registry"
    test_registry_access
    test_docker_images
    
    print_header "4. Helm & Kubernetes"
    test_helm_setup
    
    print_header "5. Application Status"
    test_application_health
    
    print_header "6. GitHub Workflows"
    test_github_workflow
    
    print_header "7. Security Scanning"
    test_security_scanning
    
    print_header "8. Build Artifacts"
    test_build_artifacts
    
    print_header "9. Network Connectivity"
    test_network_connectivity
    
    print_summary
}

# Run verification
main "$@"