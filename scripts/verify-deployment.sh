#!/bin/bash
set -euo pipefail

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 로깅 함수
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 환경 변수
APP_NAME="${APP_NAME:-fortinet}"
NAMESPACE="${NAMESPACE:-fortinet}"
NODEPORT="${NODEPORT:-30777}"
REGISTRY_URL="registry.jclee.me"
REGISTRY_USERNAME="admin"
REGISTRY_PASSWORD="bingogo1"
CHARTMUSEUM_URL="https://charts.jclee.me"
CHARTMUSEUM_USERNAME="admin"
CHARTMUSEUM_PASSWORD="bingogo1"

log_info "🔍 배포 검증 시작..."

# 1. Docker 이미지 확인
log_info "Docker 이미지 확인 중..."
IMAGE_TAGS=$(curl -s -u ${REGISTRY_USERNAME}:${REGISTRY_PASSWORD} \
  https://${REGISTRY_URL}/v2/${APP_NAME}/tags/list 2>/dev/null | jq -r '.tags[]' | tail -5) || {
  log_warn "레지스트리 접근 실패"
  IMAGE_TAGS="Unknown"
}
echo "최근 이미지 태그: ${IMAGE_TAGS}"

# 2. Helm 차트 확인
log_info "Helm 차트 확인 중..."
CHART_VERSIONS=$(curl -s -u ${CHARTMUSEUM_USERNAME}:${CHARTMUSEUM_PASSWORD} \
  ${CHARTMUSEUM_URL}/api/charts/${APP_NAME} 2>/dev/null | jq -r '.[].version' | head -5) || {
  log_warn "ChartMuseum 접근 실패"
  CHART_VERSIONS="Unknown"
}
echo "최근 차트 버전: ${CHART_VERSIONS}"

# 3. Kubernetes 리소스 확인
log_info "Kubernetes 리소스 확인 중..."
kubectl get all -n ${NAMESPACE} -l app=${APP_NAME} || log_warn "리소스 조회 실패"

# 4. Pod 상태 확인
log_info "Pod 상태 확인 중..."
POD_STATUS=$(kubectl get pods -n ${NAMESPACE} -l app=${APP_NAME} -o json 2>/dev/null | \
  jq -r '.items[0].status.phase' || echo "Unknown")
echo "Pod 상태: ${POD_STATUS}"

# 5. Service 확인
log_info "Service 확인 중..."
SVC_INFO=$(kubectl get svc -n ${NAMESPACE} ${APP_NAME} -o json 2>/dev/null | \
  jq -r '.spec.ports[0].nodePort' || echo "Unknown")
echo "NodePort: ${SVC_INFO}"

# 6. 헬스체크
log_info "애플리케이션 헬스체크 중..."
HEALTH_URL="http://192.168.50.110:${NODEPORT}/api/health"
if curl -f ${HEALTH_URL} --connect-timeout 5 >/dev/null 2>&1; then
  log_info "✅ 헬스체크 성공"
  curl -s ${HEALTH_URL} | jq . || true
else
  log_error "❌ 헬스체크 실패: ${HEALTH_URL}"
fi

# 7. ArgoCD 앱 상태 (선택사항)
log_info "ArgoCD 애플리케이션 상태 확인 중..."
argocd app get ${APP_NAME} --grpc-web 2>/dev/null || log_warn "ArgoCD 접근 실패 (정상일 수 있음)"

# 결과 요약
echo ""
log_info "📊 배포 검증 요약"
echo "================================="
echo "앱 이름: ${APP_NAME}"
echo "네임스페이스: ${NAMESPACE}"
echo "NodePort: ${NODEPORT}"
echo "Pod 상태: ${POD_STATUS}"
echo "서비스 접근: http://192.168.50.110:${NODEPORT}"
echo "도메인: http://fortinet.jclee.me (외부 설정 필요)"
echo "================================="

if [ "${POD_STATUS}" = "Running" ]; then
  log_info "✅ 배포 검증 완료 - 애플리케이션이 정상 실행 중입니다"
else
  log_warn "⚠️ 배포 검증 필요 - Pod 상태를 확인하세요"
fi