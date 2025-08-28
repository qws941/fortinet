#!/bin/bash
set -e

# MSA 상태 모니터링 스크립트 (jclee.me)
ENVIRONMENT="${1:-all}"
SERVICE="${2:-all}"
ARGOCD_URL="argo.jclee.me"

echo "📊 MSA 상태 모니터링 시작..."
echo "  - Environment: ${ENVIRONMENT}"
echo "  - Service: ${SERVICE}"
echo ""

# ArgoCD 로그인 (자동)
argocd login ${ARGOCD_URL} --username admin --password bingogo1 --insecure --grpc-web > /dev/null 2>&1

# 환경 목록
if [ "${ENVIRONMENT}" = "all" ]; then
    ENVIRONMENTS=("production" "staging" "development")
else
    ENVIRONMENTS=("${ENVIRONMENT}")
fi

# 서비스 목록
if [ "${SERVICE}" = "all" ]; then
    SERVICES=("user-service" "product-service" "order-service" "notification-service")
else
    SERVICES=("${SERVICE}")
fi

# 인프라 컴포넌트 목록
INFRA_COMPONENTS=("istio" "monitoring")

# 색상 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Health Status 색상 함수
get_health_color() {
    case "$1" in
        "Healthy") echo -e "${GREEN}$1${NC}" ;;
        "Progressing") echo -e "${YELLOW}$1${NC}" ;;
        "Degraded"|"Suspended") echo -e "${RED}$1${NC}" ;;
        "Unknown"|"Missing") echo -e "${BLUE}$1${NC}" ;;
        *) echo "$1" ;;
    esac
}

# Sync Status 색상 함수
get_sync_color() {
    case "$1" in
        "Synced") echo -e "${GREEN}$1${NC}" ;;
        "OutOfSync") echo -e "${YELLOW}$1${NC}" ;;
        "Unknown") echo -e "${BLUE}$1${NC}" ;;
        *) echo "$1" ;;
    esac
}

# 전체 MSA 상태 요약
echo "🎯=== MSA 전체 상태 요약 ==="
TOTAL_APPS=0
HEALTHY_APPS=0
SYNCED_APPS=0

for ENV in "${ENVIRONMENTS[@]}"; do
    echo ""
    echo "🌍 Environment: ${ENV}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # 인프라 컴포넌트 상태
    echo "🏗️ Infrastructure Components:"
    for INFRA in "${INFRA_COMPONENTS[@]}"; do
        APP_NAME="${INFRA}-${ENV}"
        if argocd app get ${APP_NAME} --output json > /dev/null 2>&1; then
            HEALTH=$(argocd app get ${APP_NAME} --output json | jq -r '.status.health.status // "Unknown"')
            SYNC=$(argocd app get ${APP_NAME} --output json | jq -r '.status.sync.status // "Unknown"')
            TOTAL_APPS=$((TOTAL_APPS + 1))
            [ "$HEALTH" = "Healthy" ] && HEALTHY_APPS=$((HEALTHY_APPS + 1))
            [ "$SYNC" = "Synced" ] && SYNCED_APPS=$((SYNCED_APPS + 1))
            printf "  📦 %-20s Health: %-20s Sync: %s\n" "${INFRA}" "$(get_health_color "$HEALTH")" "$(get_sync_color "$SYNC")"
        else
            printf "  📦 %-20s %s\n" "${INFRA}" "${RED}Not Found${NC}"
        fi
    done
    
    echo ""
    echo "📱 MSA Services:"
    for SVC in "${SERVICES[@]}"; do
        APP_NAME="${SVC}-${ENV}"
        if argocd app get ${APP_NAME} --output json > /dev/null 2>&1; then
            APP_JSON=$(argocd app get ${APP_NAME} --output json)
            HEALTH=$(echo "$APP_JSON" | jq -r '.status.health.status // "Unknown"')
            SYNC=$(echo "$APP_JSON" | jq -r '.status.sync.status // "Unknown"')
            REVISION=$(echo "$APP_JSON" | jq -r '.status.sync.revision // "Unknown"' | cut -c1-8)
            REPLICAS=$(echo "$APP_JSON" | jq -r '.status.resources[] | select(.kind=="Deployment") | .status // "0/0"')
            
            TOTAL_APPS=$((TOTAL_APPS + 1))
            [ "$HEALTH" = "Healthy" ] && HEALTHY_APPS=$((HEALTHY_APPS + 1))
            [ "$SYNC" = "Synced" ] && SYNCED_APPS=$((SYNCED_APPS + 1))
            
            printf "  🔧 %-20s Health: %-20s Sync: %-15s Rev: %-8s Replicas: %s\n" \
                "${SVC}" "$(get_health_color "$HEALTH")" "$(get_sync_color "$SYNC")" "${REVISION}" "${REPLICAS}"
        else
            printf "  🔧 %-20s %s\n" "${SVC}" "${RED}Not Found${NC}"
        fi
    done
done

echo ""
echo "📈=== MSA 상태 통계 ==="
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
printf "📊 Total Applications: %d\n" ${TOTAL_APPS}
printf "💚 Healthy: %d (%.1f%%)\n" ${HEALTHY_APPS} $(echo "scale=1; ${HEALTHY_APPS}*100/${TOTAL_APPS}" | bc -l 2>/dev/null || echo "0")
printf "🔄 Synced: %d (%.1f%%)\n" ${SYNCED_APPS} $(echo "scale=1; ${SYNCED_APPS}*100/${TOTAL_APPS}" | bc -l 2>/dev/null || echo "0")

# 환경별 서비스 URL 정보
echo ""
echo "🌐=== MSA 서비스 접속 정보 ==="
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

for ENV in "${ENVIRONMENTS[@]}"; do
    case ${ENV} in
        "production")
            DOMAIN_SUFFIX=".jclee.me"
            ;;
        "staging") 
            DOMAIN_SUFFIX="-staging.jclee.me"
            ;;
        "development")
            DOMAIN_SUFFIX="-dev.jclee.me"
            ;;
    esac
    
    echo "🌍 ${ENV^} Environment:"
    for SVC in "${SERVICES[@]}"; do
        APP_NAME="${SVC}-${ENV}"
        if argocd app get ${APP_NAME} --output json > /dev/null 2>&1; then
            HEALTH=$(argocd app get ${APP_NAME} --output json | jq -r '.status.health.status // "Unknown"')
            if [ "$HEALTH" = "Healthy" ]; then
                STATUS_ICON="✅"
            else
                STATUS_ICON="❌"
            fi
            echo "  ${STATUS_ICON} ${SVC}: https://${SVC}${DOMAIN_SUFFIX}"
        fi
    done
    echo ""
done

# 모니터링 링크
echo "🔍=== 모니터링 및 관리 도구 ==="
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎛️ ArgoCD: https://argo.jclee.me/applications"
echo "📊 Grafana: https://grafana.jclee.me/d/msa-overview"
echo "🔍 Prometheus: https://prometheus.jclee.me"
echo "☸️ K8s Dashboard: https://k8s.jclee.me"
echo "📦 Harbor Registry: https://registry.jclee.me"
echo "⛵ ChartMuseum: https://charts.jclee.me"

# 문제가 있는 애플리케이션 요약
echo ""
echo "⚠️=== 문제가 있는 애플리케이션 ==="
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ISSUES_FOUND=false

for ENV in "${ENVIRONMENTS[@]}"; do
    # 인프라 컴포넌트 체크
    for INFRA in "${INFRA_COMPONENTS[@]}"; do
        APP_NAME="${INFRA}-${ENV}"
        if argocd app get ${APP_NAME} --output json > /dev/null 2>&1; then
            HEALTH=$(argocd app get ${APP_NAME} --output json | jq -r '.status.health.status // "Unknown"')
            SYNC=$(argocd app get ${APP_NAME} --output json | jq -r '.status.sync.status // "Unknown"')
            if [ "$HEALTH" != "Healthy" ] || [ "$SYNC" != "Synced" ]; then
                printf "🚨 %-30s Health: %-10s Sync: %s\n" "${APP_NAME}" "${HEALTH}" "${SYNC}"
                ISSUES_FOUND=true
            fi
        fi
    done
    
    # MSA 서비스 체크
    for SVC in "${SERVICES[@]}"; do
        APP_NAME="${SVC}-${ENV}"
        if argocd app get ${APP_NAME} --output json > /dev/null 2>&1; then
            HEALTH=$(argocd app get ${APP_NAME} --output json | jq -r '.status.health.status // "Unknown"')
            SYNC=$(argocd app get ${APP_NAME} --output json | jq -r '.status.sync.status // "Unknown"')
            if [ "$HEALTH" != "Healthy" ] || [ "$SYNC" != "Synced" ]; then
                printf "🚨 %-30s Health: %-10s Sync: %s\n" "${APP_NAME}" "${HEALTH}" "${SYNC}"
                ISSUES_FOUND=true
            fi
        fi
    done
done

if [ "$ISSUES_FOUND" = false ]; then
    echo "✅ 모든 애플리케이션이 정상 상태입니다!"
fi

echo ""
echo "🔄=== 유용한 명령어 ==="
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "# 특정 애플리케이션 동기화"
echo "argocd app sync <app-name>"
echo ""
echo "# 애플리케이션 세부 정보 확인"
echo "argocd app get <app-name>"
echo ""
echo "# 애플리케이션 히스토리 확인"
echo "argocd app history <app-name>"
echo ""
echo "# MSA 전체 배포"
echo "./msa-gitops/scripts/deploy-msa.sh production all"
echo ""
echo "# 특정 서비스만 배포"
echo "./msa-gitops/scripts/deploy-msa.sh production user-service"

echo ""
echo "📊 MSA 상태 모니터링 완료!"