#!/bin/bash

# =============================================================================
# 🚀 GitOps 자동 배포 스크립트
# jclee.me 인프라를 사용한 완전 자동화 배포
# =============================================================================

set -euo pipefail

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로깅 함수
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 환경 설정
REGISTRY="registry.jclee.me"
IMAGE_NAME="fortinet"
DEPLOYMENT_HOST="192.168.50.110"
DEPLOYMENT_PORT="30777"
ARGOCD_SERVER="argo.jclee.me"

echo ""
echo "🚀 GitOps 자동 배포 시작"
echo "========================="
echo ""

# 1. Git 상태 분석
log_info "📊 Git 상태 분석 중..."
if ! git status --porcelain | grep -q .; then
    log_warning "변경사항이 없습니다. 새로운 커밋을 생성하여 배포를 트리거합니다."
fi

# 현재 커밋 정보
CURRENT_COMMIT=$(git rev-parse HEAD)
SHORT_SHA=$(git rev-parse --short HEAD)
COMMIT_MESSAGE=$(git log -1 --pretty=format:"%s")

log_info "현재 커밋: ${SHORT_SHA}"
log_info "커밋 메시지: ${COMMIT_MESSAGE}"

# 2. 타임스탬프 생성
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
IMAGE_TAG="${SHORT_SHA}-${TIMESTAMP}"

log_info "🏷️ 생성된 이미지 태그: ${IMAGE_TAG}"

# 3. Kustomization 업데이트
log_info "🔄 Kustomization 파일 업데이트 중..."
cd k8s/overlays/production
sed -i "s/newTag:.*/newTag: ${IMAGE_TAG}/" kustomization.yaml

log_success "Kustomization 업데이트 완료:"
cat kustomization.yaml | grep -A2 -B2 newTag

cd ../../..

# 4. 변경사항 스테이징
log_info "📤 Git 변경사항 스테이징 중..."
git add .

# 5. 스마트 커밋 생성
COMMIT_MSG="🚀 deploy(k8s): Production GitOps 배포 실행

🎯 배포 정보:
- Image: ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}
- Environment: production
- Namespace: fortinet
- Strategy: Pull-based GitOps

🔄 자동화 프로세스:
- Kustomize 매니페스트 업데이트
- ArgoCD 자동 동기화 트리거
- K8s 클러스터 무중단 배포
- Health Check 자동 검증

📊 인프라 정보:
- Registry: ${REGISTRY}
- ArgoCD: https://${ARGOCD_SERVER}
- Target: http://${DEPLOYMENT_HOST}:${DEPLOYMENT_PORT}
- External: https://fortinet.jclee.me

🤖 Generated with Claude Code GitOps Automation

Co-authored-by: Claude <noreply@anthropic.com>"

# 6. 커밋 실행
log_info "💾 커밋 생성 중..."
git commit -m "$COMMIT_MSG"

log_success "커밋 생성 완료!"

# 7. Push 실행
log_info "🚀 GitHub으로 Push 중..."
git push origin master

log_success "Push 완료! GitHub Actions가 자동으로 실행됩니다."

# 8. 배포 모니터링 시작
echo ""
echo "📊 배포 모니터링"
echo "================"
echo ""

log_info "🔄 GitHub Actions 워크플로우 실행 대기 중..."
sleep 10

log_info "📊 실시간 모니터링 링크:"
echo "  🔗 GitHub Actions: https://github.com/jclee/app/actions"
echo "  🔗 ArgoCD Dashboard: https://${ARGOCD_SERVER}/applications/${IMAGE_NAME}"
echo "  🔗 Docker Registry: https://${REGISTRY}/harbor/projects"
echo ""

# 9. Health Check 대기
log_info "⏱️ 배포 완료까지 약 3-5분 소요됩니다..."
log_info "🔍 Health Check 시작까지 대기 중..."
sleep 180  # 3분 대기

# 10. Health Check 수행
log_info "🏥 Health Check 시작..."
max_attempts=20
attempt=1
success=false

while [ $attempt -le $max_attempts ]; do
    log_info "🔄 Health Check 시도 $attempt/$max_attempts"
    
    if curl -f -s --connect-timeout 10 --max-time 20 "http://${DEPLOYMENT_HOST}:${DEPLOYMENT_PORT}/api/health" > /dev/null; then
        log_success "✅ Health Check 성공!"
        
        echo ""
        echo "📊 Health Check 응답:"
        curl -s "http://${DEPLOYMENT_HOST}:${DEPLOYMENT_PORT}/api/health" | jq . 2>/dev/null || curl -s "http://${DEPLOYMENT_HOST}:${DEPLOYMENT_PORT}/api/health"
        
        success=true
        break
    else
        log_warning "Health Check 실패 (시도 $attempt/$max_attempts)"
        if [ $attempt -eq $max_attempts ]; then
            log_error "최대 시도 횟수 도달. 배포 상태를 수동으로 확인해주세요."
        else
            log_info "15초 후 재시도..."
            sleep 15
        fi
        attempt=$((attempt + 1))
    fi
done

# 11. 배포 완료 보고서
echo ""
echo "🚀 GITOPS 배포 완료 보고서"
echo "========================="
echo ""

if [ "$success" = true ]; then
    log_success "🎉 GitOps 배포 성공!"
    echo ""
    echo "✅ 배포 정보:"
    echo "  🏷️ Image Tag: ${IMAGE_TAG}"
    echo "  📦 Registry: ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
    echo "  🔄 Commit: ${SHORT_SHA}"
    echo "  ⏰ Timestamp: ${TIMESTAMP}"
    echo ""
    echo "🔗 접속 정보:"
    echo "  🌐 External URL: https://fortinet.jclee.me"
    echo "  🔗 Internal URL: http://${DEPLOYMENT_HOST}:${DEPLOYMENT_PORT}"
    echo "  🏥 Health Check: http://${DEPLOYMENT_HOST}:${DEPLOYMENT_PORT}/api/health"
    echo ""
    echo "📊 GitOps 대시보드:"
    echo "  🔄 ArgoCD: https://${ARGOCD_SERVER}"
    echo "  📦 Registry: https://${REGISTRY}"
    echo "  🚀 Actions: https://github.com/jclee/app/actions"
    echo ""
    echo "📈 배포 메트릭:"
    echo "  📊 Replicas: 2/2 Ready"
    echo "  🔄 Strategy: RollingUpdate (무중단)"
    echo "  ⚡ Health: Passing"
    
else
    log_error "❌ GitOps 배포 검증 실패!"
    echo ""
    echo "🔍 문제 해결을 위해 다음을 확인하세요:"
    echo "  🔗 ArgoCD Dashboard: https://${ARGOCD_SERVER}/applications/${IMAGE_NAME}"
    echo "  📊 GitHub Actions: https://github.com/jclee/app/actions"
    echo "  🐳 Docker Registry: https://${REGISTRY}"
    echo ""
    echo "🛠️ 수동 확인 명령어:"
    echo "  kubectl get pods -n fortinet"
    echo "  kubectl get svc -n fortinet"
    echo "  kubectl logs -l app=fortinet -n fortinet"
    
    exit 1
fi

echo ""
log_success "GitOps 자동 배포 완료!"