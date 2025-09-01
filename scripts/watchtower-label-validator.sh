#!/bin/bash
# =============================================================================
# FortiGate Nextrade - Watchtower 라벨 검증 및 설정 확인
# =============================================================================

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
echo_success() { echo -e "${GREEN}[✅]${NC} $1"; }
echo_warning() { echo -e "${YELLOW}[⚠️]${NC} $1"; }
echo_error() { echo -e "${RED}[❌]${NC} $1"; }
echo_check() { echo -e "${CYAN}[🔍]${NC} $1"; }

# Watchtower 필수 라벨 정의
declare -A REQUIRED_LABELS=(
    ["com.centurylinklabs.watchtower.enable"]="true"
    ["com.centurylinklabs.watchtower.scope"]="fortinet"
    ["com.centurylinklabs.watchtower.stop-signal"]="SIGTERM"
    ["com.centurylinklabs.watchtower.monitor-only"]="false"
)

declare -A RECOMMENDED_LABELS=(
    ["com.centurylinklabs.watchtower.poll-interval"]="300"
    ["com.centurylinklabs.watchtower.stop-timeout"]="30s|45s|60s"
    ["com.centurylinklabs.watchtower.rollback.enable"]="true"
    ["fortinet.service.type"]="redis|postgresql|application"
    ["fortinet.service.port"]="7777|7778|7779"
)

# 현재 실행 중인 컨테이너 확인
check_running_containers() {
    echo_info "🔍 현재 실행 중인 FortiGate 컨테이너 확인..."
    
    local containers=$(docker ps --format "{{.Names}}" --filter "name=fortinet-")
    
    if [ -z "$containers" ]; then
        echo_warning "실행 중인 FortiGate 컨테이너가 없습니다."
        return 1
    fi
    
    echo_success "발견된 컨테이너:"
    for container in $containers; do
        echo "  📦 $container"
    done
    
    return 0
}

# 개별 컨테이너 라벨 검증
validate_container_labels() {
    local container_name=$1
    local validation_passed=true
    
    echo_check "🏷️  $container_name 라벨 검증 중..."
    
    # 컨테이너가 존재하는지 확인
    if ! docker inspect "$container_name" > /dev/null 2>&1; then
        echo_error "컨테이너 '$container_name'을 찾을 수 없습니다."
        return 1
    fi
    
    # 모든 라벨 추출
    local labels=$(docker inspect --format '{{json .Config.Labels}}' "$container_name" | jq -r '. // {}')
    
    echo "    📋 현재 설정된 라벨:"
    docker inspect --format '{{range $key, $value := .Config.Labels}}{{if or (hasPrefix $key "com.centurylinklabs.watchtower") (hasPrefix $key "fortinet.")}}  {{$key}}={{$value}}{{"\n"}}{{end}}{{end}}' "$container_name"
    
    # 필수 라벨 검증
    echo "    🔍 필수 라벨 검증:"
    for label in "${!REQUIRED_LABELS[@]}"; do
        local expected_value="${REQUIRED_LABELS[$label]}"
        local actual_value=$(echo "$labels" | jq -r ".\"$label\" // \"NOT_FOUND\"")
        
        if [ "$actual_value" = "NOT_FOUND" ]; then
            echo_error "    ❌ 누락된 라벨: $label"
            validation_passed=false
        elif [ "$actual_value" = "$expected_value" ]; then
            echo_success "    ✅ $label=$actual_value"
        else
            echo_warning "    ⚠️  $label=$actual_value (예상: $expected_value)"
        fi
    done
    
    # 권장 라벨 검증
    echo "    💡 권장 라벨 검증:"
    for label in "${!RECOMMENDED_LABELS[@]}"; do
        local expected_pattern="${RECOMMENDED_LABELS[$label]}"
        local actual_value=$(echo "$labels" | jq -r ".\"$label\" // \"NOT_SET\"")
        
        if [ "$actual_value" = "NOT_SET" ]; then
            echo_warning "    ⚠️  권장 라벨 미설정: $label"
        else
            echo_success "    ✅ $label=$actual_value"
        fi
    done
    
    if [ "$validation_passed" = true ]; then
        echo_success "  ✅ $container_name 라벨 검증 통과"
    else
        echo_error "  ❌ $container_name 라벨 검증 실패"
    fi
    
    return $($validation_passed)
}

# Watchtower 호환성 테스트
test_watchtower_compatibility() {
    echo_info "🧪 Watchtower 호환성 테스트..."
    
    # Watchtower가 인식할 수 있는 컨테이너 목록
    local managed_containers=$(docker ps --filter "label=com.centurylinklabs.watchtower.enable=true" --format "{{.Names}}")
    
    if [ -z "$managed_containers" ]; then
        echo_error "Watchtower가 관리할 수 있는 컨테이너가 없습니다!"
        return 1
    fi
    
    echo_success "Watchtower 관리 대상 컨테이너:"
    for container in $managed_containers; do
        echo "  🎯 $container"
        
        # 각 컨테이너의 스코프 확인
        local scope=$(docker inspect --format '{{index .Config.Labels "com.centurylinklabs.watchtower.scope"}}' "$container" 2>/dev/null || echo "none")
        if [ "$scope" = "fortinet" ]; then
            echo_success "    ✅ 올바른 스코프: $scope"
        else
            echo_warning "    ⚠️  스코프 확인 필요: $scope"
        fi
    done
    
    return 0
}

# Docker Compose 파일 라벨 검증
validate_compose_labels() {
    echo_info "📄 Docker Compose 파일 라벨 검증..."
    
    local compose_files=("docker-compose-separated.yml" "docker-compose.watchtower-enhanced.yml")
    
    for compose_file in "${compose_files[@]}"; do
        if [ -f "$compose_file" ]; then
            echo_check "검증 중: $compose_file"
            
            # Watchtower 라벨이 포함되어 있는지 확인
            if grep -q "com.centurylinklabs.watchtower.enable" "$compose_file"; then
                echo_success "  ✅ Watchtower 라벨 발견"
                
                # 각 서비스별 라벨 카운트
                local redis_labels=$(grep -A 20 "# Redis\|redis:" "$compose_file" | grep -c "com.centurylinklabs.watchtower" || echo "0")
                local pg_labels=$(grep -A 20 "# PostgreSQL\|postgresql:" "$compose_file" | grep -c "com.centurylinklabs.watchtower" || echo "0")
                local app_labels=$(grep -A 20 "# FortiGate\|fortinet:" "$compose_file" | grep -c "com.centurylinklabs.watchtower" || echo "0")
                
                echo "    📊 라벨 개수:"
                echo "      🔴 Redis: $redis_labels"
                echo "      🟢 PostgreSQL: $pg_labels"
                echo "      🔵 Fortinet App: $app_labels"
                
            else
                echo_warning "  ⚠️  Watchtower 라벨이 없습니다"
            fi
        else
            echo_warning "$compose_file 파일을 찾을 수 없습니다"
        fi
    done
}

# 라벨 수정 제안 생성
generate_label_fixes() {
    echo_info "🔧 라벨 수정 제안 생성..."
    
    cat > fix-watchtower-labels.sh << 'EOF'
#!/bin/bash
# Watchtower 라벨 자동 수정 스크립트

echo "🔧 Watchtower 라벨 자동 수정 시작..."

# Redis 라벨 추가/수정
if docker ps -q --filter "name=fortinet-redis" > /dev/null; then
    echo "🔴 Redis 라벨 수정 중..."
    docker label fortinet-redis \
        com.centurylinklabs.watchtower.enable=true \
        com.centurylinklabs.watchtower.scope=fortinet \
        com.centurylinklabs.watchtower.stop-signal=SIGTERM \
        com.centurylinklabs.watchtower.poll-interval=300 \
        fortinet.service.type=redis \
        fortinet.service.port=7777 \
        fortinet.service.priority=1
fi

# PostgreSQL 라벨 추가/수정  
if docker ps -q --filter "name=fortinet-postgresql" > /dev/null; then
    echo "🟢 PostgreSQL 라벨 수정 중..."
    docker label fortinet-postgresql \
        com.centurylinklabs.watchtower.enable=true \
        com.centurylinklabs.watchtower.scope=fortinet \
        com.centurylinklabs.watchtower.stop-signal=SIGTERM \
        com.centurylinklabs.watchtower.poll-interval=300 \
        fortinet.service.type=postgresql \
        fortinet.service.port=7778 \
        fortinet.service.priority=2
fi

# Fortinet App 라벨 추가/수정
if docker ps -q --filter "name=fortinet-app" > /dev/null; then
    echo "🔵 Fortinet App 라벨 수정 중..."
    docker label fortinet-app \
        com.centurylinklabs.watchtower.enable=true \
        com.centurylinklabs.watchtower.scope=fortinet \
        com.centurylinklabs.watchtower.stop-signal=SIGTERM \
        com.centurylinklabs.watchtower.poll-interval=300 \
        fortinet.service.type=application \
        fortinet.service.port=7779 \
        fortinet.service.priority=3
fi

echo "✅ 라벨 수정 완료!"
EOF
    
    chmod +x fix-watchtower-labels.sh
    echo_success "수정 스크립트 생성됨: fix-watchtower-labels.sh"
}

# Watchtower 설정 리포트 생성
generate_watchtower_report() {
    echo_info "📊 Watchtower 설정 리포트 생성..."
    
    local report_file="reports/watchtower_config_report_$(date +%Y%m%d_%H%M%S).json"
    mkdir -p reports
    
    cat > "$report_file" << EOF
{
    "watchtower_configuration_report": {
        "timestamp": "$(date -Iseconds)",
        "validation_results": {
EOF

    # 관리 대상 컨테이너 정보
    local containers=$(docker ps --filter "label=com.centurylinklabs.watchtower.enable=true" --format "{{.Names}}")
    local container_count=0
    
    for container in $containers; do
        if [ $container_count -gt 0 ]; then
            echo "," >> "$report_file"
        fi
        
        cat >> "$report_file" << EOF
            "$container": {
                "image": "$(docker inspect --format '{{.Config.Image}}' "$container")",
                "status": "$(docker inspect --format '{{.State.Status}}' "$container")",
                "watchtower_labels": $(docker inspect --format '{{json .Config.Labels}}' "$container" | jq 'to_entries | map(select(.key | startswith("com.centurylinklabs.watchtower"))) | from_entries'),
                "fortinet_labels": $(docker inspect --format '{{json .Config.Labels}}' "$container" | jq 'to_entries | map(select(.key | startswith("fortinet."))) | from_entries'),
                "ports": $(docker inspect --format '{{json .NetworkSettings.Ports}}' "$container")
            }
EOF
        container_count=$((container_count + 1))
    done

    cat >> "$report_file" << EOF
        },
        "summary": {
            "total_managed_containers": $container_count,
            "watchtower_container_exists": $(docker ps --filter "name=watchtower" -q > /dev/null && echo "true" || echo "false"),
            "scope_configured": "fortinet",
            "poll_interval": "300s"
        }
    }
}
EOF

    echo_success "리포트 생성 완료: $report_file"
}

# 메인 실행 함수
main_validation() {
    echo_info "🎯 FortiGate Watchtower 라벨 검증 시작..."
    echo
    
    # 실행 중인 컨테이너 확인
    if ! check_running_containers; then
        echo_warning "컨테이너를 먼저 시작하세요: ./scripts/run-all-separated.sh"
        exit 1
    fi
    
    echo
    
    # Docker Compose 파일 검증
    validate_compose_labels
    echo
    
    # 개별 컨테이너 라벨 검증
    local containers=$(docker ps --format "{{.Names}}" --filter "name=fortinet-")
    local overall_passed=true
    
    for container in $containers; do
        if ! validate_container_labels "$container"; then
            overall_passed=false
        fi
        echo
    done
    
    # Watchtower 호환성 테스트
    test_watchtower_compatibility
    echo
    
    # 수정 제안 생성
    if [ "$overall_passed" = false ]; then
        generate_label_fixes
        echo
    fi
    
    # 리포트 생성
    generate_watchtower_report
    echo
    
    if [ "$overall_passed" = true ]; then
        echo_success "🎉 모든 Watchtower 라벨 검증 통과!"
    else
        echo_warning "⚠️  일부 라벨 설정 개선이 필요합니다."
        echo_info "💡 수정 방법:"
        echo "  1. ./fix-watchtower-labels.sh 실행"
        echo "  2. docker-compose.watchtower-enhanced.yml 사용"
        echo "  3. 수동 라벨 수정"
    fi
    
    echo
    echo_info "📊 추가 정보:"
    echo "  라벨 검증 재실행: $0"
    echo "  강화된 설정 적용: docker-compose -f docker-compose.watchtower-enhanced.yml up -d"
    echo "  Watchtower 실행: docker run -d --name watchtower -v /var/run/docker.sock:/var/run/docker.sock containrrr/watchtower --scope fortinet"
}

# 실행
main_validation