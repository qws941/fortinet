#!/bin/bash
# =============================================================================
# FortiGate Nextrade - Docker Independence Test Script
# 완전 독립 컨테이너 실행 검증
# =============================================================================

set -e

# 설정 변수
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_PREFIX="independence-test"
TIMEOUT=300  # 5분 타임아웃
CLEANUP_ON_EXIT=true

# 색상 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 클린업 함수
cleanup() {
    if [ "$CLEANUP_ON_EXIT" = "true" ]; then
        log_info "클린업 시작..."
        
        # 테스트 컨테이너들 정지 및 제거
        docker ps -a --filter "name=${TEST_PREFIX}" --format "{{.Names}}" | while read -r container; do
            if [ -n "$container" ]; then
                log_info "컨테이너 정리: $container"
                docker stop "$container" 2>/dev/null || true
                docker rm "$container" 2>/dev/null || true
            fi
        done
        
        # 테스트 네트워크 제거
        docker network ls --filter "name=${TEST_PREFIX}" --format "{{.Name}}" | while read -r network; do
            if [ -n "$network" ]; then
                log_info "네트워크 정리: $network"
                docker network rm "$network" 2>/dev/null || true
            fi
        done
        
        log_success "클린업 완료"
    fi
}

# 시그널 핸들러 설정
trap cleanup EXIT
trap 'log_error "스크립트가 중단되었습니다"; exit 1' INT TERM

# 도커 이미지 검증
check_images() {
    log_info "=== Docker 이미지 검증 ==="
    
    local images=(
        "registry.jclee.me/fortinet:latest"
        "registry.jclee.me/fortinet-redis:latest"
        "registry.jclee.me/fortinet-postgresql:latest"
    )
    
    local missing_images=()
    
    for image in "${images[@]}"; do
        if docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^${image}$"; then
            log_success "이미지 존재: $image"
        else
            log_error "이미지 없음: $image"
            missing_images+=("$image")
        fi
    done
    
    if [ ${#missing_images[@]} -gt 0 ]; then
        log_error "필수 이미지들이 없습니다. 먼저 빌드하세요:"
        for image in "${missing_images[@]}"; do
            echo "  - $image"
        done
        exit 1
    fi
    
    log_success "모든 이미지 검증 완료"
}

# 헬스체크 함수
wait_for_health() {
    local container_name=$1
    local health_endpoint=${2:-""}
    local timeout=${3:-$TIMEOUT}
    local interval=5
    local elapsed=0
    
    log_info "헬스체크 대기: $container_name"
    
    while [ $elapsed -lt $timeout ]; do
        # Docker 컨테이너 상태 확인
        if ! docker ps --filter "name=$container_name" --format "{{.Names}}" | grep -q "$container_name"; then
            log_error "컨테이너가 실행 중이지 않음: $container_name"
            return 1
        fi
        
        # 헬스체크 엔드포인트가 있으면 HTTP 확인
        if [ -n "$health_endpoint" ]; then
            if docker exec "$container_name" curl -f "$health_endpoint" >/dev/null 2>&1; then
                log_success "헬스체크 통과: $container_name"
                return 0
            fi
        else
            # Docker 헬스체크 상태 확인
            health_status=$(docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null || echo "none")
            if [ "$health_status" = "healthy" ]; then
                log_success "헬스체크 통과: $container_name"
                return 0
            fi
        fi
        
        log_info "헬스체크 대기 중... ($elapsed/${timeout}초)"
        sleep $interval
        elapsed=$((elapsed + interval))
    done
    
    log_error "헬스체크 타임아웃: $container_name"
    return 1
}

# Redis 독립 테스트
test_redis_independence() {
    log_info "=== Redis 독립성 테스트 ==="
    
    local container_name="${TEST_PREFIX}-redis"
    local port="6380"
    
    log_info "Redis 컨테이너 실행..."
    docker run -d \
        --name "$container_name" \
        -p "$port:6379" \
        --restart=no \
        registry.jclee.me/fortinet-redis:latest
    
    if ! wait_for_health "$container_name"; then
        log_error "Redis 헬스체크 실패"
        return 1
    fi
    
    # Redis 연결 테스트
    log_info "Redis 연결 테스트..."
    if docker exec "$container_name" redis-cli ping | grep -q "PONG"; then
        log_success "Redis 연결 성공"
    else
        log_error "Redis 연결 실패"
        return 1
    fi
    
    # 포트 바인딩 테스트
    if netstat -tuln | grep -q ":$port"; then
        log_success "Redis 포트 바인딩 확인: $port"
    else
        log_warning "Redis 포트 바인딩 확인 불가: $port"
    fi
    
    log_success "Redis 독립성 테스트 통과"
    return 0
}

# PostgreSQL 독립 테스트
test_postgresql_independence() {
    log_info "=== PostgreSQL 독립성 테스트 ==="
    
    local container_name="${TEST_PREFIX}-postgresql"
    local port="5434"
    
    log_info "PostgreSQL 컨테이너 실행..."
    docker run -d \
        --name "$container_name" \
        -p "$port:5432" \
        -e POSTGRES_USER=fortinet \
        -e POSTGRES_PASSWORD=fortinet123 \
        -e POSTGRES_DB=fortinet_db \
        --restart=no \
        registry.jclee.me/fortinet-postgresql:latest
    
    if ! wait_for_health "$container_name"; then
        log_error "PostgreSQL 헬스체크 실패"
        return 1
    fi
    
    # PostgreSQL 연결 테스트
    log_info "PostgreSQL 연결 테스트..."
    if docker exec "$container_name" pg_isready -U fortinet -d fortinet_db; then
        log_success "PostgreSQL 연결 성공"
    else
        log_error "PostgreSQL 연결 실패"
        return 1
    fi
    
    # 포트 바인딩 테스트
    if netstat -tuln | grep -q ":$port"; then
        log_success "PostgreSQL 포트 바인딩 확인: $port"
    else
        log_warning "PostgreSQL 포트 바인딩 확인 불가: $port"
    fi
    
    log_success "PostgreSQL 독립성 테스트 통과"
    return 0
}

# FortiGate 애플리케이션 독립 테스트
test_fortinet_independence() {
    log_info "=== FortiGate 애플리케이션 독립성 테스트 ==="
    
    local container_name="${TEST_PREFIX}-fortinet"
    local port="7778"
    
    log_info "FortiGate 컨테이너 실행..."
    docker run -d \
        --name "$container_name" \
        -p "$port:7777" \
        -e APP_MODE=test \
        -e OFFLINE_MODE=true \
        -e WEB_APP_HOST=0.0.0.0 \
        -e WEB_APP_PORT=7777 \
        -e PYTHONPATH=/app/src \
        --restart=no \
        registry.jclee.me/fortinet:latest
    
    if ! wait_for_health "$container_name" "http://localhost:7777/api/health"; then
        log_error "FortiGate 헬스체크 실패"
        return 1
    fi
    
    # HTTP API 테스트
    log_info "FortiGate API 테스트..."
    if curl -f "http://localhost:$port/api/health" >/dev/null 2>&1; then
        log_success "FortiGate API 응답 성공"
    else
        log_error "FortiGate API 응답 실패"
        return 1
    fi
    
    # 포트 바인딩 테스트
    if netstat -tuln | grep -q ":$port"; then
        log_success "FortiGate 포트 바인딩 확인: $port"
    else
        log_warning "FortiGate 포트 바인딩 확인 불가: $port"
    fi
    
    log_success "FortiGate 애플리케이션 독립성 테스트 통과"
    return 0
}

# 네트워크 독립성 테스트
test_network_independence() {
    log_info "=== 네트워크 독립성 테스트 ==="
    
    local network_name="${TEST_PREFIX}-network"
    local redis_container="${TEST_PREFIX}-net-redis"
    local app_container="${TEST_PREFIX}-net-app"
    
    # 전용 네트워크 생성
    log_info "전용 네트워크 생성..."
    docker network create "$network_name"
    
    # Redis 컨테이너 실행 (네트워크 내부)
    log_info "Redis 컨테이너 실행 (네트워크 내부)..."
    docker run -d \
        --name "$redis_container" \
        --network "$network_name" \
        --restart=no \
        registry.jclee.me/fortinet-redis:latest
    
    # 앱 컨테이너 실행 (Redis 연결 포함)
    log_info "FortiGate 컨테이너 실행 (Redis 연결)..."
    docker run -d \
        --name "$app_container" \
        --network "$network_name" \
        -p "7779:7777" \
        -e APP_MODE=test \
        -e OFFLINE_MODE=false \
        -e REDIS_HOST="$redis_container" \
        -e REDIS_PORT=6379 \
        -e WEB_APP_HOST=0.0.0.0 \
        -e WEB_APP_PORT=7777 \
        -e PYTHONPATH=/app/src \
        --restart=no \
        registry.jclee.me/fortinet:latest
    
    if ! wait_for_health "$redis_container"; then
        log_error "네트워크 Redis 헬스체크 실패"
        return 1
    fi
    
    if ! wait_for_health "$app_container" "http://localhost:7777/api/health"; then
        log_error "네트워크 애플리케이션 헬스체크 실패"
        return 1
    fi
    
    # API 연결 테스트
    if curl -f "http://localhost:7779/api/health" >/dev/null 2>&1; then
        log_success "네트워크 내 서비스 통신 성공"
    else
        log_error "네트워크 내 서비스 통신 실패"
        return 1
    fi
    
    log_success "네트워크 독립성 테스트 통과"
    return 0
}

# 환경변수 독립성 테스트
test_environment_independence() {
    log_info "=== 환경변수 독립성 테스트 ==="
    
    local container_name="${TEST_PREFIX}-env-test"
    
    # 최소한의 환경변수로 실행
    log_info "최소 환경변수로 컨테이너 실행..."
    docker run -d \
        --name "$container_name" \
        -p "7780:7777" \
        --restart=no \
        registry.jclee.me/fortinet:latest
    
    if wait_for_health "$container_name" "http://localhost:7777/api/health"; then
        log_success "기본 설정으로 실행 성공"
    else
        log_warning "기본 설정 실행 실패 (예상될 수 있음)"
    fi
    
    # 컨테이너 정리
    docker stop "$container_name" >/dev/null 2>&1 || true
    docker rm "$container_name" >/dev/null 2>&1 || true
    
    # 완전한 환경변수로 재실행
    log_info "완전한 환경변수로 컨테이너 재실행..."
    docker run -d \
        --name "$container_name" \
        -p "7780:7777" \
        -e APP_MODE=test \
        -e OFFLINE_MODE=true \
        -e WEB_APP_HOST=0.0.0.0 \
        -e WEB_APP_PORT=7777 \
        -e PYTHONPATH=/app/src \
        -e SECRET_KEY=test-secret-key \
        --restart=no \
        registry.jclee.me/fortinet:latest
    
    if ! wait_for_health "$container_name" "http://localhost:7777/api/health"; then
        log_error "환경변수 설정 실행 실패"
        return 1
    fi
    
    log_success "환경변수 독립성 테스트 통과"
    return 0
}

# 메인 테스트 실행
main() {
    log_info "=== FortiGate Nextrade Docker 독립성 테스트 시작 ==="
    log_info "타임아웃: ${TIMEOUT}초"
    log_info "테스트 접두사: $TEST_PREFIX"
    
    local test_results=()
    local failed_tests=()
    
    # 이미지 검증
    check_images
    
    # 개별 서비스 독립성 테스트
    log_info "\n=== 개별 서비스 독립성 테스트 ==="
    
    if test_redis_independence; then
        test_results+=("Redis: PASS")
    else
        test_results+=("Redis: FAIL")
        failed_tests+=("Redis")
    fi
    
    if test_postgresql_independence; then
        test_results+=("PostgreSQL: PASS")
    else
        test_results+=("PostgreSQL: FAIL")
        failed_tests+=("PostgreSQL")
    fi
    
    if test_fortinet_independence; then
        test_results+=("FortiGate App: PASS")
    else
        test_results+=("FortiGate App: FAIL")
        failed_tests+=("FortiGate App")
    fi
    
    # 네트워크 독립성 테스트
    if test_network_independence; then
        test_results+=("Network Independence: PASS")
    else
        test_results+=("Network Independence: FAIL")
        failed_tests+=("Network Independence")
    fi
    
    # 환경변수 독립성 테스트
    if test_environment_independence; then
        test_results+=("Environment Independence: PASS")
    else
        test_results+=("Environment Independence: FAIL")
        failed_tests+=("Environment Independence")
    fi
    
    # 결과 출력
    echo
    log_info "=== 테스트 결과 요약 ==="
    for result in "${test_results[@]}"; do
        if [[ "$result" == *"PASS"* ]]; then
            log_success "$result"
        else
            log_error "$result"
        fi
    done
    
    echo
    if [ ${#failed_tests[@]} -eq 0 ]; then
        log_success "🎉 모든 독립성 테스트가 성공했습니다!"
        log_info "Docker 컨테이너들이 완전 독립적으로 실행 가능합니다."
        exit 0
    else
        log_error "❌ ${#failed_tests[@]}개의 테스트가 실패했습니다:"
        for test in "${failed_tests[@]}"; do
            echo "  - $test"
        done
        log_info "실패한 테스트들을 확인하고 수정하세요."
        exit 1
    fi
}

# 옵션 파싱
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-cleanup)
            CLEANUP_ON_EXIT=false
            shift
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --help|-h)
            echo "사용법: $0 [옵션]"
            echo "옵션:"
            echo "  --no-cleanup    테스트 후 컨테이너 정리 안함"
            echo "  --timeout SEC   헬스체크 타임아웃 (기본: 300초)"
            echo "  --help, -h      도움말 출력"
            exit 0
            ;;
        *)
            log_error "알 수 없는 옵션: $1"
            echo "도움말: $0 --help"
            exit 1
            ;;
    esac
done

# 필수 명령어 확인
for cmd in docker curl netstat; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        log_error "필수 명령어가 없습니다: $cmd"
        exit 1
    fi
done

# 메인 실행
main