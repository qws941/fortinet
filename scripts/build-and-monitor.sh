#!/bin/bash
# =============================================================================
# FortiGate Nextrade - 각 이미지 빌드 후 컨테이너 로그 모니터링
# =============================================================================

set -e

# Configuration
REGISTRY="registry.jclee.me"
VERSION="${VERSION:-latest}"
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
VCS_REF=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

# Service ports
REDIS_PORT=7777
POSTGRESQL_PORT=7778
FORTINET_PORT=7779

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

echo_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
echo_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
echo_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
echo_error() { echo -e "${RED}[ERROR]${NC} $1"; }
echo_build() { echo -e "${CYAN}[BUILD]${NC} $1"; }
echo_monitor() { echo -e "${MAGENTA}[MONITOR]${NC} $1"; }

# 빌드 및 실행 상태 추적
declare -A BUILD_STATUS
declare -A CONTAINER_STATUS
declare -A CONTAINER_NAMES

# 이미지별 빌드 함수
build_redis_image() {
    echo_build "🔴 Redis 이미지 빌드 시작..."
    
    if docker build \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VCS_REF="$VCS_REF" \
        --build-arg VERSION="$VERSION" \
        -f Dockerfile.redis \
        -t $REGISTRY/fortinet-redis:$VERSION \
        -t $REGISTRY/fortinet-redis:$(date +%Y%m%d-%H%M%S) \
        . > build_logs/redis_build.log 2>&1; then
        
        BUILD_STATUS[redis]="SUCCESS"
        echo_success "✅ Redis 이미지 빌드 완료"
        
        # Registry 푸시
        echo_info "📤 Redis 이미지 Registry 푸시 중..."
        if docker push $REGISTRY/fortinet-redis:$VERSION >> build_logs/redis_push.log 2>&1; then
            echo_success "✅ Redis 이미지 푸시 완료"
        else
            echo_warning "⚠️  Redis 이미지 푸시 실패 (로그: build_logs/redis_push.log)"
        fi
    else
        BUILD_STATUS[redis]="FAILED"
        echo_error "❌ Redis 이미지 빌드 실패 (로그: build_logs/redis_build.log)"
        return 1
    fi
}

build_postgresql_image() {
    echo_build "🟢 PostgreSQL 이미지 빌드 시작..."
    
    if docker build \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VCS_REF="$VCS_REF" \
        --build-arg VERSION="$VERSION" \
        -f Dockerfile.postgresql \
        -t $REGISTRY/fortinet-postgresql:$VERSION \
        -t $REGISTRY/fortinet-postgresql:$(date +%Y%m%d-%H%M%S) \
        . > build_logs/postgresql_build.log 2>&1; then
        
        BUILD_STATUS[postgresql]="SUCCESS"
        echo_success "✅ PostgreSQL 이미지 빌드 완료"
        
        # Registry 푸시
        echo_info "📤 PostgreSQL 이미지 Registry 푸시 중..."
        if docker push $REGISTRY/fortinet-postgresql:$VERSION >> build_logs/postgresql_push.log 2>&1; then
            echo_success "✅ PostgreSQL 이미지 푸시 완료"
        else
            echo_warning "⚠️  PostgreSQL 이미지 푸시 실패 (로그: build_logs/postgresql_push.log)"
        fi
    else
        BUILD_STATUS[postgresql]="FAILED"
        echo_error "❌ PostgreSQL 이미지 빌드 실패 (로그: build_logs/postgresql_build.log)"
        return 1
    fi
}

build_fortinet_image() {
    echo_build "🔵 Fortinet 애플리케이션 이미지 빌드 시작..."
    
    if docker build \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VCS_REF="$VCS_REF" \
        --build-arg VERSION="$VERSION" \
        -f Dockerfile.fortinet \
        -t $REGISTRY/fortinet:$VERSION \
        -t $REGISTRY/fortinet:$(date +%Y%m%d-%H%M%S) \
        . > build_logs/fortinet_build.log 2>&1; then
        
        BUILD_STATUS[fortinet]="SUCCESS"
        echo_success "✅ Fortinet 이미지 빌드 완료"
        
        # Registry 푸시
        echo_info "📤 Fortinet 이미지 Registry 푸시 중..."
        if docker push $REGISTRY/fortinet:$VERSION >> build_logs/fortinet_push.log 2>&1; then
            echo_success "✅ Fortinet 이미지 푸시 완료"
        else
            echo_warning "⚠️  Fortinet 이미지 푸시 실패 (로그: build_logs/fortinet_push.log)"
        fi
    else
        BUILD_STATUS[fortinet]="FAILED"
        echo_error "❌ Fortinet 이미지 빌드 실패 (로그: build_logs/fortinet_build.log)"
        return 1
    fi
}

# 컨테이너 실행 함수
run_redis_container() {
    if [ "${BUILD_STATUS[redis]}" != "SUCCESS" ]; then
        echo_warning "⚠️  Redis 이미지 빌드가 실패하여 컨테이너를 실행할 수 없습니다"
        return 1
    fi
    
    echo_info "🔴 Redis 컨테이너 실행 중..."
    
    # 기존 컨테이너 정리
    docker stop fortinet-redis-$REDIS_PORT 2>/dev/null || true
    docker rm fortinet-redis-$REDIS_PORT 2>/dev/null || true
    
    # 새 컨테이너 실행
    if docker run -d \
        --name fortinet-redis-$REDIS_PORT \
        --restart unless-stopped \
        -p $REDIS_PORT:6379 \
        -v redis-data-$REDIS_PORT:/data \
        -e REDIS_PORT=6379 \
        -e REDIS_MAXMEMORY=256mb \
        --label "com.centurylinklabs.watchtower.enable=true" \
        --label "fortinet.service.type=redis" \
        --label "fortinet.service.port=$REDIS_PORT" \
        $REGISTRY/fortinet-redis:$VERSION; then
        
        CONTAINER_STATUS[redis]="RUNNING"
        CONTAINER_NAMES[redis]="fortinet-redis-$REDIS_PORT"
        echo_success "✅ Redis 컨테이너 실행 완료"
        return 0
    else
        CONTAINER_STATUS[redis]="FAILED"
        echo_error "❌ Redis 컨테이너 실행 실패"
        return 1
    fi
}

run_postgresql_container() {
    if [ "${BUILD_STATUS[postgresql]}" != "SUCCESS" ]; then
        echo_warning "⚠️  PostgreSQL 이미지 빌드가 실패하여 컨테이너를 실행할 수 없습니다"
        return 1
    fi
    
    echo_info "🟢 PostgreSQL 컨테이너 실행 중..."
    
    # 기존 컨테이너 정리
    docker stop fortinet-postgresql-$POSTGRESQL_PORT 2>/dev/null || true
    docker rm fortinet-postgresql-$POSTGRESQL_PORT 2>/dev/null || true
    
    # 새 컨테이너 실행
    if docker run -d \
        --name fortinet-postgresql-$POSTGRESQL_PORT \
        --restart unless-stopped \
        -p $POSTGRESQL_PORT:5432 \
        -v postgresql-data-$POSTGRESQL_PORT:/var/lib/postgresql/data \
        -e POSTGRES_USER=fortinet \
        -e POSTGRES_PASSWORD=fortinet123 \
        -e POSTGRES_DB=fortinet_db \
        --label "com.centurylinklabs.watchtower.enable=true" \
        --label "fortinet.service.type=postgresql" \
        --label "fortinet.service.port=$POSTGRESQL_PORT" \
        $REGISTRY/fortinet-postgresql:$VERSION; then
        
        CONTAINER_STATUS[postgresql]="RUNNING"
        CONTAINER_NAMES[postgresql]="fortinet-postgresql-$POSTGRESQL_PORT"
        echo_success "✅ PostgreSQL 컨테이너 실행 완료"
        return 0
    else
        CONTAINER_STATUS[postgresql]="FAILED"
        echo_error "❌ PostgreSQL 컨테이너 실행 실패"
        return 1
    fi
}

run_fortinet_container() {
    if [ "${BUILD_STATUS[fortinet]}" != "SUCCESS" ]; then
        echo_warning "⚠️  Fortinet 이미지 빌드가 실패하여 컨테이너를 실행할 수 없습니다"
        return 1
    fi
    
    echo_info "🔵 Fortinet 애플리케이션 컨테이너 실행 중..."
    
    # 기존 컨테이너 정리
    docker stop fortinet-app-$FORTINET_PORT 2>/dev/null || true
    docker rm fortinet-app-$FORTINET_PORT 2>/dev/null || true
    
    # 새 컨테이너 실행
    if docker run -d \
        --name fortinet-app-$FORTINET_PORT \
        --restart unless-stopped \
        -p $FORTINET_PORT:7777 \
        -v fortinet-logs-$FORTINET_PORT:/app/logs \
        -v $(pwd)/data:/app/data:ro \
        -e APP_MODE=production \
        -e WEB_APP_HOST=0.0.0.0 \
        -e WEB_APP_PORT=7777 \
        -e DATABASE_URL=postgresql://fortinet:fortinet123@host.docker.internal:$POSTGRESQL_PORT/fortinet_db \
        -e REDIS_URL=redis://host.docker.internal:$REDIS_PORT/0 \
        -e SECRET_KEY=fortinet-secret-key-2024 \
        --add-host=host.docker.internal:host-gateway \
        --label "com.centurylinklabs.watchtower.enable=true" \
        --label "fortinet.service.type=application" \
        --label "fortinet.service.port=$FORTINET_PORT" \
        $REGISTRY/fortinet:$VERSION; then
        
        CONTAINER_STATUS[fortinet]="RUNNING"
        CONTAINER_NAMES[fortinet]="fortinet-app-$FORTINET_PORT"
        echo_success "✅ Fortinet 컨테이너 실행 완료"
        return 0
    else
        CONTAINER_STATUS[fortinet]="FAILED"
        echo_error "❌ Fortinet 컨테이너 실행 실패"
        return 1
    fi
}

# 컨테이너 로그 모니터링 함수
monitor_container_logs() {
    local service=$1
    local container_name="${CONTAINER_NAMES[$service]}"
    
    if [ -z "$container_name" ] || [ "${CONTAINER_STATUS[$service]}" != "RUNNING" ]; then
        echo_warning "⚠️  $service 컨테이너가 실행 중이지 않습니다"
        return 1
    fi
    
    echo_monitor "📋 $service 컨테이너 로그 모니터링 시작..."
    echo_info "컨테이너 이름: $container_name"
    echo_info "Press Ctrl+C to stop monitoring"
    echo "================================================"
    
    # 실시간 로그 출력
    docker logs -f "$container_name" 2>&1 | while IFS= read -r line; do
        timestamp=$(date '+%H:%M:%S')
        echo "[$timestamp][$service] $line"
    done
}

# 모든 컨테이너 로그 동시 모니터링
monitor_all_logs() {
    echo_monitor "📊 모든 컨테이너 로그 동시 모니터링 시작..."
    
    # 로그 디렉토리 생성
    mkdir -p container_logs
    
    # 각 서비스별 로그 파일에 저장하면서 동시에 출력
    for service in redis postgresql fortinet; do
        local container_name="${CONTAINER_NAMES[$service]}"
        if [ -n "$container_name" ] && [ "${CONTAINER_STATUS[$service]}" = "RUNNING" ]; then
            echo_info "📋 $service 로그 모니터링 시작..."
            
            # 백그라운드에서 로그를 파일과 화면에 동시 출력
            docker logs -f "$container_name" 2>&1 | while IFS= read -r line; do
                timestamp=$(date '+%H:%M:%S')
                formatted_line="[$timestamp][$service] $line"
                echo "$formatted_line"
                echo "$formatted_line" >> "container_logs/${service}_$(date +%Y%m%d_%H%M%S).log"
            done &
        fi
    done
    
    echo_info "모든 로그 모니터링이 백그라운드에서 실행 중입니다."
    echo_info "로그 파일 위치: container_logs/"
    echo_info "모니터링 중단: Ctrl+C"
    
    # 메인 프로세스는 사용자 입력 대기
    wait
}

# 로그 분석 함수
analyze_container_logs() {
    echo_monitor "🔍 컨테이너 로그 분석 시작..."
    
    local analysis_report="reports/container_log_analysis_$(date +%Y%m%d_%H%M%S).txt"
    mkdir -p reports
    
    cat > "$analysis_report" << EOF
FortiGate 컨테이너 로그 분석 리포트
=====================================
분석 시간: $(date)
빌드 커밋: $VCS_REF

빌드 상태:
----------
EOF

    # 빌드 상태 요약
    for service in redis postgresql fortinet; do
        echo "  $service: ${BUILD_STATUS[$service]:-UNKNOWN}" >> "$analysis_report"
    done
    
    cat >> "$analysis_report" << EOF

컨테이너 상태:
------------
EOF

    # 컨테이너 상태 요약
    for service in redis postgresql fortinet; do
        local container_name="${CONTAINER_NAMES[$service]}"
        if [ -n "$container_name" ]; then
            local status=$(docker inspect --format '{{.State.Status}}' "$container_name" 2>/dev/null || echo "NOT_FOUND")
            echo "  $service ($container_name): $status" >> "$analysis_report"
        else
            echo "  $service: NOT_CREATED" >> "$analysis_report"
        fi
    done
    
    cat >> "$analysis_report" << EOF

최근 로그 (각 서비스별 마지막 10줄):
================================
EOF

    # 각 컨테이너별 최근 로그 추출
    for service in redis postgresql fortinet; do
        local container_name="${CONTAINER_NAMES[$service]}"
        if [ -n "$container_name" ] && docker ps -q --filter "name=$container_name" > /dev/null; then
            echo "" >> "$analysis_report"
            echo "--- $service 서비스 로그 ---" >> "$analysis_report"
            docker logs --tail 10 "$container_name" 2>&1 >> "$analysis_report"
        fi
    done
    
    echo_success "✅ 로그 분석 완료: $analysis_report"
    
    # 에러 패턴 검사
    echo_info "🔍 에러 패턴 검사 중..."
    local error_count=0
    
    for service in redis postgresql fortinet; do
        local container_name="${CONTAINER_NAMES[$service]}"
        if [ -n "$container_name" ] && docker ps -q --filter "name=$container_name" > /dev/null; then
            local service_errors=$(docker logs "$container_name" 2>&1 | grep -i -c "error\|exception\|failed" || echo "0")
            if [ "$service_errors" -gt 0 ]; then
                echo_warning "⚠️  $service: $service_errors 개의 에러 메시지 발견"
                error_count=$((error_count + service_errors))
            else
                echo_success "✅ $service: 에러 없음"
            fi
        fi
    done
    
    if [ "$error_count" -gt 0 ]; then
        echo_warning "⚠️  총 $error_count 개의 에러 발견 - 로그를 확인하세요"
    else
        echo_success "🎉 모든 컨테이너가 정상 동작 중입니다"
    fi
}

# 메인 실행 함수
main_build_and_monitor() {
    echo_info "🚀 FortiGate 이미지 빌드 및 로그 모니터링 시작..."
    echo "빌드 버전: $VERSION"
    echo "Git 커밋: $VCS_REF"
    echo "빌드 시간: $BUILD_DATE"
    echo
    
    # 로그 디렉토리 생성
    mkdir -p build_logs container_logs reports
    
    # 단계별 빌드 및 실행
    echo_info "=== 1단계: 이미지 빌드 ==="
    build_redis_image || true
    sleep 2
    build_postgresql_image || true  
    sleep 2
    build_fortinet_image || true
    echo
    
    echo_info "=== 2단계: 컨테이너 실행 ==="
    run_redis_container || true
    sleep 10  # Redis 시작 대기
    
    run_postgresql_container || true
    sleep 20  # PostgreSQL 시작 대기
    
    run_fortinet_container || true
    sleep 15  # Fortinet App 시작 대기
    echo
    
    echo_info "=== 3단계: 초기 상태 확인 ==="
    echo "컨테이너 상태:"
    docker ps --filter "label=fortinet.service.type" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    echo
    
    echo_info "=== 4단계: 로그 모니터링 선택 ==="
    echo "로그 모니터링 옵션을 선택하세요:"
    echo "  1) Redis 로그만 보기"
    echo "  2) PostgreSQL 로그만 보기" 
    echo "  3) Fortinet App 로그만 보기"
    echo "  4) 모든 로그 동시 보기"
    echo "  5) 로그 분석만 실행"
    echo "  6) 종료"
    
    read -p "선택 (1-6): " choice
    
    case $choice in
        1)
            monitor_container_logs redis
            ;;
        2)
            monitor_container_logs postgresql
            ;;
        3)
            monitor_container_logs fortinet
            ;;
        4)
            monitor_all_logs
            ;;
        5)
            analyze_container_logs
            ;;
        6)
            echo_info "종료합니다."
            ;;
        *)
            echo_warning "잘못된 선택입니다. 로그 분석을 실행합니다."
            analyze_container_logs
            ;;
    esac
    
    echo
    echo_success "🎉 빌드 및 모니터링 완료!"
    echo_info "💡 추가 명령어:"
    echo "  컨테이너 상태: docker ps --filter 'label=fortinet.service.type'"
    echo "  개별 로그: docker logs -f fortinet-[service]-[port]"
    echo "  로그 분석: ./scripts/pipeline-test-analyzer.sh"
}

# 실행
main_build_and_monitor