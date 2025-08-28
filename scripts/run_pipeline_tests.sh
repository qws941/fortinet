#!/bin/bash

# GitOps CI/CD 파이프라인 통합 테스트 실행 스크립트

set -e

echo "🚀 Fortinet GitOps Pipeline Integration Test Suite"
echo "================================================="

# 스크립트 디렉토리 설정
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 환경 확인 함수
check_requirements() {
    log_info "Checking requirements..."
    
    # Python 확인
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required but not installed"
        exit 1
    fi
    
    # Docker 확인 (선택적)
    if command -v docker &> /dev/null; then
        if docker info &> /dev/null; then
            log_success "Docker is available and running"
        else
            log_warning "Docker is installed but not running"
        fi
    else
        log_warning "Docker is not available - some tests will be skipped"
    fi
    
    # kubectl 확인 (선택적)
    if command -v kubectl &> /dev/null; then
        if kubectl cluster-info &> /dev/null; then
            log_success "kubectl is available and cluster is accessible"
        else
            log_warning "kubectl is available but cluster is not accessible"
        fi
    else
        log_warning "kubectl is not available - some tests will be skipped"
    fi
    
    # ArgoCD CLI 확인 (선택적)
    if command -v argocd &> /dev/null; then
        log_success "ArgoCD CLI is available"
    else
        log_warning "ArgoCD CLI is not available - some tests will be skipped"
    fi
}

# 테스트 환경 설정
setup_test_environment() {
    log_info "Setting up test environment..."
    
    cd "${PROJECT_ROOT}"
    
    # 환경 변수 설정
    export APP_MODE=test
    export OFFLINE_MODE=true
    export DISABLE_SOCKETIO=true
    export PYTHONPATH="${PROJECT_ROOT}/src"
    
    # 테스트용 임시 디렉토리 생성
    export TEST_TEMP_DIR="${PROJECT_ROOT}/tmp/test_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "${TEST_TEMP_DIR}"
    
    log_success "Test environment ready"
    log_info "Test temp directory: ${TEST_TEMP_DIR}"
}

# 의존성 설치
install_dependencies() {
    log_info "Installing Python dependencies..."
    
    cd "${PROJECT_ROOT}"
    
    # 기본 의존성
    if [ -f "requirements.txt" ]; then
        pip install -q -r requirements.txt
        log_success "Basic dependencies installed"
    fi
    
    # 테스트 의존성
    pip install -q pytest pytest-xdist requests docker pyyaml
    log_success "Test dependencies installed"
}

# GitOps 파이프라인 통합 테스트 실행
run_gitops_tests() {
    log_info "Running GitOps CI/CD Pipeline Integration Tests..."
    
    cd "${PROJECT_ROOT}/src"
    
    if python3 ../tests/integration/test_gitops_pipeline_integration.py; then
        log_success "GitOps pipeline tests passed"
        return 0
    else
        log_error "GitOps pipeline tests failed"
        return 1
    fi
}

# Docker 컨테이너 통합 테스트 실행
run_docker_tests() {
    log_info "Running Docker Container Integration Tests..."
    
    cd "${PROJECT_ROOT}/src"
    
    # Docker가 사용 가능한 경우에만 실행
    if command -v docker &> /dev/null && docker info &> /dev/null; then
        if python3 ../tests/integration/test_docker_container_integration.py; then
            log_success "Docker container tests passed"
            return 0
        else
            log_error "Docker container tests failed"
            return 1
        fi
    else
        log_warning "Skipping Docker tests - Docker not available"
        return 0
    fi
}

# 기존 통합 테스트 실행
run_existing_integration_tests() {
    log_info "Running existing integration tests..."
    
    cd "${PROJECT_ROOT}/src"
    
    # pytest를 사용한 통합 테스트 실행
    if pytest ../tests/integration/ -v --tb=short --maxfail=3 -x; then
        log_success "Existing integration tests passed"
        return 0
    else
        log_error "Existing integration tests failed"
        return 1
    fi
}

# 피처 검증 테스트 실행
run_feature_tests() {
    log_info "Running feature validation tests..."
    
    cd "${PROJECT_ROOT}/src"
    
    if python3 test_features.py; then
        log_success "Feature validation tests passed"
        return 0
    else
        log_error "Feature validation tests failed"
        return 1
    fi
}

# 테스트 결과 리포트 생성
generate_report() {
    local total_tests=$1
    local passed_tests=$2
    local failed_tests=$3
    
    log_info "Generating test report..."
    
    cat > "${TEST_TEMP_DIR}/test_report.md" << EOF
# GitOps CI/CD Pipeline Integration Test Report

**Generated:** $(date)
**Project:** Fortinet GitOps Pipeline
**Environment:** ${APP_MODE:-production}

## Test Summary

- **Total Test Suites:** ${total_tests}
- **Passed:** ${passed_tests}
- **Failed:** ${failed_tests}
- **Success Rate:** $(echo "scale=1; ${passed_tests} * 100 / ${total_tests}" | bc -l)%

## Test Suites

### 1. GitOps Pipeline Integration Tests
- Registry connectivity
- ChartMuseum integration  
- Kubernetes deployment verification
- Application health checks
- ArgoCD synchronization

### 2. Docker Container Integration Tests
- Image build and analysis
- Container startup and health
- API endpoint accessibility
- Log analysis and monitoring

### 3. Existing Integration Tests
- API client integration
- Monitoring system integration
- ITSM workflow integration

### 4. Feature Validation Tests
- Core system features
- API endpoints
- Monitoring capabilities

## Environment Information

- **Python Version:** $(python3 --version)
- **Docker Available:** $(command -v docker >/dev/null && echo "Yes" || echo "No")
- **Kubernetes Available:** $(command -v kubectl >/dev/null && echo "Yes" || echo "No")
- **ArgoCD CLI Available:** $(command -v argocd >/dev/null && echo "Yes" || echo "No")

## Test Artifacts

Test artifacts and logs are available in: \`${TEST_TEMP_DIR}\`

EOF

    log_success "Test report generated: ${TEST_TEMP_DIR}/test_report.md"
}

# 정리 함수
cleanup() {
    log_info "Cleaning up test environment..."
    
    # 임시 파일 정리는 선택적으로 수행
    if [ "${KEEP_TEMP_FILES}" != "true" ]; then
        rm -rf "${TEST_TEMP_DIR}" 2>/dev/null || true
    else
        log_info "Temporary files kept at: ${TEST_TEMP_DIR}"
    fi
}

# 메인 실행 함수
main() {
    local test_suites=()
    local total_tests=0
    local passed_tests=0
    local failed_tests=0
    
    # 명령행 인수 처리
    while [[ $# -gt 0 ]]; do
        case $1 in
            --gitops)
                test_suites+=("gitops")
                shift
                ;;
            --docker)
                test_suites+=("docker")
                shift
                ;;
            --integration)
                test_suites+=("integration")
                shift
                ;;
            --features)
                test_suites+=("features")
                shift
                ;;
            --all)
                test_suites=("gitops" "docker" "integration" "features")
                shift
                ;;
            --keep-temp)
                export KEEP_TEMP_FILES=true
                shift
                ;;
            --help)
                echo "Usage: $0 [options]"
                echo "Options:"
                echo "  --gitops      Run GitOps pipeline tests only"
                echo "  --docker      Run Docker container tests only"
                echo "  --integration Run existing integration tests only"
                echo "  --features    Run feature validation tests only"
                echo "  --all         Run all test suites (default)"
                echo "  --keep-temp   Keep temporary files after testing"
                echo "  --help        Show this help message"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # 기본적으로 모든 테스트 실행
    if [ ${#test_suites[@]} -eq 0 ]; then
        test_suites=("gitops" "docker" "integration" "features")
    fi
    
    # 트랩 설정 (스크립트 종료 시 정리)
    trap cleanup EXIT
    
    # 초기 설정
    check_requirements
    setup_test_environment
    install_dependencies
    
    echo ""
    log_info "Starting test execution..."
    echo ""
    
    # 테스트 스위트 실행
    for suite in "${test_suites[@]}"; do
        total_tests=$((total_tests + 1))
        
        case $suite in
            "gitops")
                if run_gitops_tests; then
                    passed_tests=$((passed_tests + 1))
                else
                    failed_tests=$((failed_tests + 1))
                fi
                ;;
            "docker")
                if run_docker_tests; then
                    passed_tests=$((passed_tests + 1))
                else
                    failed_tests=$((failed_tests + 1))
                fi
                ;;
            "integration")
                if run_existing_integration_tests; then
                    passed_tests=$((passed_tests + 1))
                else
                    failed_tests=$((failed_tests + 1))
                fi
                ;;
            "features")
                if run_feature_tests; then
                    passed_tests=$((passed_tests + 1))
                else
                    failed_tests=$((failed_tests + 1))
                fi
                ;;
        esac
        
        echo ""
    done
    
    # 테스트 결과 요약
    echo "=" * 60
    log_info "Test Execution Complete"
    echo "=" * 60
    
    if [ $failed_tests -eq 0 ]; then
        log_success "All test suites passed! (${passed_tests}/${total_tests})"
    else
        log_error "${failed_tests} test suite(s) failed out of ${total_tests}"
    fi
    
    # 리포트 생성
    generate_report $total_tests $passed_tests $failed_tests
    
    # 종료 코드 설정
    if [ $failed_tests -eq 0 ]; then
        exit 0
    else
        exit 1
    fi
}

# 스크립트 실행
main "$@"