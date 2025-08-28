#!/bin/bash
# FortiGate Nextrade 헬스체크 스크립트
# 크론잡으로 실행되는 자동 모니터링 시스템

set -euo pipefail

# 설정
EXTERNAL_ENDPOINT="https://fortinet.jclee.me/api/health"
INTERNAL_ENDPOINT="http://192.168.50.110:30777/api/health"
LOG_FILE="/var/log/fortinet-health.log"
SLACK_WEBHOOK="${SLACK_WEBHOOK:-}"
DISCORD_WEBHOOK="${DISCORD_WEBHOOK:-}"
MAX_RETRIES=3
TIMEOUT=10

# 로깅 함수
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# 알림 전송 함수
send_notification() {
    local message="$1"
    local severity="$2"  # info, warning, critical
    
    # Slack 알림
    if [[ -n "$SLACK_WEBHOOK" ]]; then
        local emoji
        case $severity in
            "info") emoji="✅" ;;
            "warning") emoji="⚠️" ;;
            "critical") emoji="🚨" ;;
        esac
        
        curl -X POST "$SLACK_WEBHOOK" \
            -H 'Content-type: application/json' \
            --data "{\"text\":\"${emoji} FortiGate Nextrade\\n${message}\"}" \
            --max-time 5 --silent >/dev/null || true
    fi
    
    # Discord 알림 (선택적)
    if [[ -n "$DISCORD_WEBHOOK" ]]; then
        curl -X POST "$DISCORD_WEBHOOK" \
            -H 'Content-type: application/json' \
            --data "{\"content\":\"🔍 **FortiGate Health Check**\\n\`\`\`${message}\`\`\`\"}" \
            --max-time 5 --silent >/dev/null || true
    fi
}

# 헬스체크 함수
check_endpoint() {
    local endpoint="$1"
    local name="$2"
    local retries=0
    
    while [[ $retries -lt $MAX_RETRIES ]]; do
        if response=$(curl -f -s -w "%{http_code}:%{time_total}" --max-time $TIMEOUT "$endpoint" 2>/dev/null); then
            http_code="${response%:*}"
            response_time="${response#*:}"
            
            if [[ "$http_code" == "200" ]]; then
                response_time_ms=$(echo "$response_time * 1000" | bc)
                log "✅ $name: HTTP $http_code, ${response_time_ms}ms"
                return 0
            else
                log "❌ $name: HTTP $http_code (시도 $((retries + 1))/$MAX_RETRIES)"
            fi
        else
            log "❌ $name: 연결 실패 (시도 $((retries + 1))/$MAX_RETRIES)"
        fi
        
        retries=$((retries + 1))
        [[ $retries -lt $MAX_RETRIES ]] && sleep 2
    done
    
    return 1
}

# K8s 상태 체크
check_k8s_status() {
    log "🔍 Kubernetes 상태 확인 중..."
    
    # Pod 상태 확인
    if pod_status=$(kubectl get pods -n fortinet -l app=fortinet -o jsonpath='{.items[*].status.phase}' 2>/dev/null); then
        if [[ "$pod_status" == *"Running"* ]]; then
            pod_count=$(echo "$pod_status" | wc -w)
            log "✅ K8s Pods: $pod_count개 실행 중"
        else
            log "❌ K8s Pods: 비정상 상태 ($pod_status)"
            return 1
        fi
    else
        log "❌ K8s Pods: 상태 확인 실패"
        return 1
    fi
    
    # Service 상태 확인
    if service_status=$(kubectl get svc -n fortinet -l app=fortinet -o jsonpath='{.items[*].metadata.name}' 2>/dev/null); then
        if [[ -n "$service_status" ]]; then
            log "✅ K8s Services: $service_status 활성화"
        else
            log "❌ K8s Services: 서비스 없음"
            return 1
        fi
    else
        log "❌ K8s Services: 상태 확인 실패"
        return 1
    fi
    
    return 0
}

# 메인 헬스체크 실행
main() {
    log "🚀 FortiGate Nextrade 헬스체크 시작"
    
    local external_ok=false
    local internal_ok=false
    local k8s_ok=false
    
    # 외부 엔드포인트 체크
    if check_endpoint "$EXTERNAL_ENDPOINT" "External (fortinet.jclee.me)"; then
        external_ok=true
    fi
    
    # 내부 엔드포인트 체크
    if check_endpoint "$INTERNAL_ENDPOINT" "Internal (192.168.50.110:30777)"; then
        internal_ok=true
    fi
    
    # K8s 상태 체크
    if check_k8s_status; then
        k8s_ok=true
    fi
    
    # 종합 상태 판정
    if $external_ok && $internal_ok && $k8s_ok; then
        log "🎉 전체 헬스체크 통과"
        send_notification "모든 엔드포인트 정상 동작 중" "info"
        exit 0
    elif $internal_ok && $k8s_ok; then
        log "⚠️ 내부 서비스는 정상, 외부 접근 문제 발생"
        send_notification "내부 서비스 정상, 외부 도메인 확인 필요" "warning"
        exit 1
    elif $k8s_ok; then
        log "⚠️ K8s는 정상, 서비스 엔드포인트 문제 발생"
        send_notification "Pod는 실행 중, 서비스/인그레스 확인 필요" "warning"
        exit 1
    else
        log "🚨 전체 시스템 장애 발생"
        send_notification "FortiGate Nextrade 시스템 다운 - 즉시 확인 필요" "critical"
        exit 2
    fi
}

# 실행
main "$@"