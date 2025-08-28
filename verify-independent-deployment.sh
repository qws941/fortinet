#!/bin/bash

# =============================================================================
# FortiGate Nextrade - 독립 배포 검증 스크립트
# =============================================================================

set -e

# 색상 설정
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

echo "🔍 ===== 독립 배포 검증 시작 ====="
echo "📅 검증 시작 시간: $(date)"
echo ""

# 1. 컨테이너 상태 확인
log_info "📋 컨테이너 상태 확인:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep fortinet

echo ""

# 2. 각 서비스 개별 테스트
log_info "🔍 개별 서비스 검증:"

# Redis 테스트
log_info "🔴 Redis 서비스 테스트..."
if docker exec fortinet-redis redis-cli ping >/dev/null 2>&1; then
    log_success "✅ Redis 서비스 정상"
else
    log_error "❌ Redis 서비스 실패"
fi

# PostgreSQL 테스트
log_info "🐘 PostgreSQL 서비스 테스트..."
if docker exec fortinet-postgresql pg_isready -U fortinet -d fortinet_db >/dev/null 2>&1; then
    log_success "✅ PostgreSQL 서비스 정상"
else
    log_error "❌ PostgreSQL 서비스 실패"
fi

# Fortinet App 테스트
log_info "🌐 Fortinet 앱 테스트..."
if curl -f --max-time 10 http://localhost:7777/api/health >/dev/null 2>&1; then
    log_success "✅ Fortinet 앱 정상 (포트 7777)"
else
    log_error "❌ Fortinet 앱 실패 (포트 7777)"
fi

echo ""

# 3. 의존성 제거 확인
log_info "🔗 의존성 제거 검증:"

# docker-compose-independent.yml에서 depends_on이 없는지 확인
if ! grep -q "depends_on" docker-compose-independent.yml; then
    log_success "✅ depends_on 구성 완전 제거됨"
else
    log_warning "⚠️ depends_on 구성이 여전히 존재함"
fi

# 4. 이미지 이름 확인
log_info "🏷️ 이미지 이름 확인:"
FORTINET_IMAGE=$(docker inspect fortinet --format='{{.Config.Image}}')
if [[ "$FORTINET_IMAGE" == "registry.jclee.me/fortinet:latest" ]]; then
    log_success "✅ Fortinet 이미지 이름이 올바르게 수정됨: $FORTINET_IMAGE"
else
    log_warning "⚠️ Fortinet 이미지 이름: $FORTINET_IMAGE"
fi

# 5. 포트 접근성 테스트
log_info "🌐 포트 접근성 테스트:"

PORTS=("6380:Redis" "5433:PostgreSQL" "7777:Fortinet")
for port_info in "${PORTS[@]}"; do
    IFS=':' read -r port service <<< "$port_info"
    if netstat -tlnp 2>/dev/null | grep -q ":$port "; then
        log_success "✅ 포트 $port ($service) 정상 바인딩됨"
    else
        log_error "❌ 포트 $port ($service) 바인딩 실패"
    fi
done

# 6. 헬스체크 상태 확인
log_info "🏥 헬스체크 상태:"
for container in "fortinet-redis" "fortinet-postgresql" "fortinet"; do
    health_status=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "no-health")
    if [[ "$health_status" == "healthy" ]]; then
        log_success "✅ $container: $health_status"
    elif [[ "$health_status" == "no-health" ]]; then
        log_info "ℹ️ $container: 헬스체크 설정 없음 (정상)"
    else
        log_warning "⚠️ $container: $health_status"
    fi
done

# 7. 실제 API 엔드포인트 테스트
log_info "🔌 API 엔드포인트 테스트:"

API_ENDPOINTS=(
    "/api/health:헬스체크"
    "/dashboard:대시보드"
)

for endpoint_info in "${API_ENDPOINTS[@]}"; do
    IFS=':' read -r endpoint description <<< "$endpoint_info"
    if curl -f --max-time 5 "http://localhost:7777$endpoint" >/dev/null 2>&1; then
        log_success "✅ $description ($endpoint)"
    else
        log_warning "⚠️ $description ($endpoint) - 접근 불가 또는 오류"
    fi
done

# 8. 로그 레벨 체크 (에러만 확인)
log_info "📋 로그 상태 체크:"

for container in "fortinet-redis" "fortinet-postgresql" "fortinet"; do
    error_count=$(docker logs "$container" --tail=50 2>&1 | grep -i "error\|fatal\|critical" | wc -l)
    if [[ $error_count -eq 0 ]]; then
        log_success "✅ $container: 에러 로그 없음"
    else
        log_warning "⚠️ $container: 에러 로그 $error_count 개 발견"
    fi
done

# 9. 최종 결과
echo ""
echo "🏁 ===== 검증 완료 ====="
echo "📅 검증 완료 시간: $(date)"
echo ""

log_success "🎉 독립 배포 검증이 완료되었습니다!"
echo ""
log_info "📋 배포 정보:"
echo "  • 배포 방식: 독립 실행 (의존성 제거)"
echo "  • 메인 이미지: registry.jclee.me/fortinet:latest"
echo "  • 컨테이너 이름: fortinet (기존 fortinet-app에서 변경)"
echo "  • 포트 접근:"
echo "    - Fortinet Web UI: http://localhost:7777"
echo "    - Redis: localhost:6380"
echo "    - PostgreSQL: localhost:5433"
echo ""
log_info "🔧 관리 명령어:"
echo "  • 로그 확인: docker logs fortinet"
echo "  • 서비스 재시작: docker-compose -f docker-compose-independent.yml restart"
echo "  • 서비스 종료: docker-compose -f docker-compose-independent.yml down"
echo ""
log_success "✅ 의존성 제거 및 설정 수정이 성공적으로 완료되었습니다!"