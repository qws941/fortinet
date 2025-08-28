#!/bin/bash

# =============================================================================
# FortiGate Nextrade - 통합 배포 테스트 스크립트
# 의존성 없는 독립 서비스 테스트
# =============================================================================

set -e  # 에러 발생 시 스크립트 중단

# 색상 설정
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

# 테스트 결과 저장
TEST_RESULTS=()
TOTAL_TESTS=0
PASSED_TESTS=0

add_test_result() {
    local test_name="$1"
    local result="$2"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    if [[ "$result" == "PASS" ]]; then
        PASSED_TESTS=$((PASSED_TESTS + 1))
        log_success "✅ $test_name"
        TEST_RESULTS+=("✅ $test_name: PASS")
    else
        log_error "❌ $test_name"
        TEST_RESULTS+=("❌ $test_name: FAIL - $result")
    fi
}

# 서비스 상태 확인 함수
check_service_status() {
    local service_name="$1"
    local container_name="$2"
    
    log_info "🔍 $service_name 서비스 상태 확인 중..."
    
    if docker ps | grep -q "$container_name"; then
        log_success "$service_name 컨테이너가 실행 중입니다"
        return 0
    else
        log_error "$service_name 컨테이너가 실행되지 않았습니다"
        return 1
    fi
}

# 헬스체크 함수
wait_for_health() {
    local container_name="$1"
    local max_attempts="$2"
    local attempt=1
    
    log_info "⏳ $container_name 헬스체크 대기 중... (최대 ${max_attempts}회 시도)"
    
    while [ $attempt -le $max_attempts ]; do
        local health_status=$(docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null || echo "no-health")
        
        if [[ "$health_status" == "healthy" ]]; then
            log_success "$container_name이 건강 상태입니다"
            return 0
        elif [[ "$health_status" == "no-health" ]]; then
            log_info "$container_name에 헬스체크가 설정되지 않았습니다 (정상)"
            return 0
        fi
        
        log_info "시도 $attempt/$max_attempts: $container_name 상태 = $health_status"
        sleep 5
        attempt=$((attempt + 1))
    done
    
    log_error "$container_name 헬스체크 실패"
    return 1
}

# 연결성 테스트 함수
test_connectivity() {
    local service_name="$1"
    local test_command="$2"
    
    log_info "🔗 $service_name 연결성 테스트 중..."
    
    if eval "$test_command" >/dev/null 2>&1; then
        add_test_result "$service_name 연결성 테스트" "PASS"
        return 0
    else
        add_test_result "$service_name 연결성 테스트" "연결 실패"
        return 1
    fi
}

# 메인 테스트 실행
main() {
    echo "🧪 ===== FortiGate Nextrade 통합 테스트 시작 ====="
    echo "📅 테스트 시작 시간: $(date)"
    echo ""
    
    # 1. 기존 컨테이너 정리
    log_info "🧹 기존 컨테이너 정리 중..."
    docker-compose -f docker-compose-independent.yml down --remove-orphans || true
    sleep 2
    
    # 2. 독립 서비스 시작
    log_info "🚀 독립 서비스 스택 시작 중..."
    if docker-compose -f docker-compose-independent.yml up -d; then
        log_success "서비스 스택이 시작되었습니다"
        add_test_result "독립 서비스 스택 시작" "PASS"
    else
        add_test_result "독립 서비스 스택 시작" "Docker Compose 실행 실패"
        return 1
    fi
    
    # 3. 서비스 시작 대기
    log_info "⏳ 서비스 시작 대기 중... (10초)"
    sleep 10
    
    # 4. 개별 서비스 상태 확인
    log_info "🔍 서비스 상태 확인 중..."
    
    # Redis 상태 확인
    if check_service_status "Redis" "fortinet-redis"; then
        add_test_result "Redis 서비스 상태" "PASS"
    else
        add_test_result "Redis 서비스 상태" "컨테이너 실행 안됨"
    fi
    
    # PostgreSQL 상태 확인
    if check_service_status "PostgreSQL" "fortinet-postgresql"; then
        add_test_result "PostgreSQL 서비스 상태" "PASS"
    else
        add_test_result "PostgreSQL 서비스 상태" "컨테이너 실행 안됨"
    fi
    
    # Fortinet App 상태 확인
    if check_service_status "Fortinet App" "fortinet"; then
        add_test_result "Fortinet App 서비스 상태" "PASS"
    else
        add_test_result "Fortinet App 서비스 상태" "컨테이너 실행 안됨"
    fi
    
    # 5. 헬스체크 대기
    log_info "🏥 헬스체크 대기 중..."
    wait_for_health "fortinet-redis" 12
    wait_for_health "fortinet-postgresql" 20
    wait_for_health "fortinet" 30
    
    # 6. 연결성 테스트
    log_info "🔗 개별 서비스 연결성 테스트..."
    
    # Redis 연결 테스트
    test_connectivity "Redis" "docker exec fortinet-redis redis-cli ping"
    
    # PostgreSQL 연결 테스트  
    test_connectivity "PostgreSQL" "docker exec fortinet-postgresql pg_isready -U fortinet -d fortinet_db"
    
    # Fortinet App 기본 테스트 (포트 7777)
    log_info "🌐 Fortinet 앱 기본 연결 테스트 (포트 7777)..."
    sleep 5  # 앱 완전 시작 대기
    
    if curl -f --max-time 10 http://localhost:7777/api/health 2>/dev/null; then
        add_test_result "Fortinet App HTTP 연결 (포트 7777)" "PASS"
    else
        add_test_result "Fortinet App HTTP 연결 (포트 7777)" "HTTP 요청 실패"
    fi
    
    # 7. 통합 연결 테스트
    log_info "🔗 통합 연결 테스트..."
    
    # DB 연결 테스트 API 호출 (애플리케이션 내부에서)
    if docker exec fortinet curl -X POST http://localhost:7777/api/test-db-connection 2>/dev/null; then
        add_test_result "앱-DB 통합 연결 테스트" "PASS"
    else
        add_test_result "앱-DB 통합 연결 테스트" "내부 API 호출 실패"
    fi
    
    # Redis 연결 테스트 API 호출
    if docker exec fortinet curl -X POST http://localhost:7777/api/test-redis-connection 2>/dev/null; then
        add_test_result "앱-Redis 통합 연결 테스트" "PASS"
    else
        add_test_result "앱-Redis 통합 연결 테스트" "내부 API 호출 실패"
    fi
    
    # 8. 네트워크 연결성 테스트
    log_info "🌐 네트워크 연결성 테스트..."
    
    # 컨테이너 간 핑 테스트
    if docker exec fortinet ping -c 3 fortinet-redis >/dev/null 2>&1; then
        add_test_result "Fortinet -> Redis 네트워크 연결" "PASS"
    else
        add_test_result "Fortinet -> Redis 네트워크 연결" "핑 실패"
    fi
    
    if docker exec fortinet ping -c 3 fortinet-postgresql >/dev/null 2>&1; then
        add_test_result "Fortinet -> PostgreSQL 네트워크 연결" "PASS"
    else
        add_test_result "Fortinet -> PostgreSQL 네트워크 연결" "핑 실패"
    fi
    
    # 9. 로그 확인
    log_info "📋 서비스 로그 상태 확인..."
    
    # 각 서비스의 최근 로그 확인 (에러 검사)
    if docker logs fortinet-redis --tail=20 2>&1 | grep -qi "error" || docker logs fortinet-redis --tail=20 2>&1 | grep -qi "fatal"; then
        add_test_result "Redis 로그 상태" "에러 로그 발견"
    else
        add_test_result "Redis 로그 상태" "PASS"
    fi
    
    if docker logs fortinet-postgresql --tail=20 2>&1 | grep -qi "error" || docker logs fortinet-postgresql --tail=20 2>&1 | grep -qi "fatal"; then
        add_test_result "PostgreSQL 로그 상태" "에러 로그 발견"
    else
        add_test_result "PostgreSQL 로그 상태" "PASS"
    fi
    
    if docker logs fortinet --tail=20 2>&1 | grep -qi "error" || docker logs fortinet --tail=20 2>&1 | grep -qi "fatal"; then
        add_test_result "Fortinet App 로그 상태" "에러 로그 발견"
    else
        add_test_result "Fortinet App 로그 상태" "PASS"
    fi
    
    # 10. 결과 출력
    echo ""
    echo "🏁 ===== 통합 테스트 완료 ====="
    echo "📅 테스트 완료 시간: $(date)"
    echo ""
    
    log_info "📊 테스트 결과 요약:"
    echo "총 테스트: $TOTAL_TESTS"
    echo "성공: $PASSED_TESTS"
    echo "실패: $((TOTAL_TESTS - PASSED_TESTS))"
    echo "성공률: $(( (PASSED_TESTS * 100) / TOTAL_TESTS ))%"
    echo ""
    
    log_info "📝 상세 테스트 결과:"
    for result in "${TEST_RESULTS[@]}"; do
        echo "  $result"
    done
    
    # 11. 최종 판정
    if [[ $PASSED_TESTS -eq $TOTAL_TESTS ]]; then
        echo ""
        log_success "🎉 모든 테스트가 성공했습니다!"
        log_success "독립 실행 배포가 정상적으로 작동합니다."
        
        # 서비스 접근 정보 출력
        echo ""
        log_info "🌐 서비스 접근 정보:"
        echo "  • Fortinet Web UI: http://localhost:7777"
        echo "  • Redis: localhost:6380"
        echo "  • PostgreSQL: localhost:5433"
        echo "  • Watchtower: http://localhost:8080"
        echo ""
        echo "컨테이너를 종료하려면: docker-compose -f docker-compose-independent.yml down"
        
        return 0
    else
        echo ""
        log_error "❌ 일부 테스트가 실패했습니다."
        log_warning "로그를 확인하여 문제를 해결하세요:"
        echo "  docker logs fortinet-redis"
        echo "  docker logs fortinet-postgresql"
        echo "  docker logs fortinet"
        
        return 1
    fi
}

# 트랩 설정 (스크립트 중단 시 정리)
cleanup() {
    log_warning "테스트가 중단되었습니다. 정리 중..."
    docker-compose -f docker-compose-independent.yml down --remove-orphans 2>/dev/null || true
}

trap cleanup EXIT INT TERM

# 메인 함수 실행
main "$@"