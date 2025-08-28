#!/bin/bash

# =============================================================================
# FortiGate Nextrade - 최초 배포 스크립트
# ArgoCD GitOps 환경 초기 설정 및 배포
# =============================================================================

set -e

# 색상 정의
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

# 프로젝트 루트 디렉토리로 이동
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

log_info "🚀 FortiGate Nextrade 최초 배포 스크립트 시작..."
log_info "📂 프로젝트 디렉토리: $PROJECT_DIR"

# =============================================================================
# 1. 사전 요구사항 확인
# =============================================================================
log_info "1️⃣ 사전 요구사항 확인 중..."

# ArgoCD CLI 확인
if ! command -v argocd &> /dev/null; then
    log_error "ArgoCD CLI가 설치되지 않았습니다."
    log_info "설치 방법: https://argo-cd.readthedocs.io/en/stable/cli_installation/"
    exit 1
fi
log_success "ArgoCD CLI 설치됨"

# Git 상태 확인
if [ -n "$(git status --porcelain)" ]; then
    log_warning "커밋되지 않은 변경사항이 있습니다."
    echo "현재 Git 상태:"
    git status --short
    echo ""
    read -p "계속 진행하시겠습니까? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "배포가 취소되었습니다."
        exit 0
    fi
fi

# =============================================================================
# 2. ArgoCD 연결 및 인증
# =============================================================================
log_info "2️⃣ ArgoCD 서버 연결 중..."

ARGOCD_SERVER="${ARGOCD_SERVER:-argo.jclee.me}"
ARGOCD_USER="${ARGOCD_USER:-admin}"
ARGOCD_PASS="${ARGOCD_PASS:-REPLACE_WITH_YOUR_PASSWORD}"

# ArgoCD 서버 연결 테스트
if ! curl -k -s --connect-timeout 5 "https://$ARGOCD_SERVER/api/version" > /dev/null; then
    log_error "ArgoCD 서버($ARGOCD_SERVER)에 연결할 수 없습니다."
    exit 1
fi
log_success "ArgoCD 서버 연결 확인"

# ArgoCD 로그인
log_info "ArgoCD 로그인 중..."
if argocd login "$ARGOCD_SERVER" \
    --username "$ARGOCD_USER" \
    --password "$ARGOCD_PASS" \
    --insecure \
    --grpc-web; then
    log_success "ArgoCD 로그인 성공"
else
    log_error "ArgoCD 로그인 실패"
    exit 1
fi

# =============================================================================
# 3. GitHub Repository 등록
# =============================================================================
log_info "3️⃣ GitHub Repository 등록 중..."

GITHUB_REPO="https://github.com/qws941/fortinet.git"
GITHUB_USER="qws941"
GITHUB_TOKEN="${GITHUB_TOKEN:-ghp_REPLACE_WITH_YOUR_TOKEN}"

if argocd repo add "$GITHUB_REPO" \
    --username "$GITHUB_USER" \
    --password "$GITHUB_TOKEN" \
    --upsert; then
    log_success "GitHub Repository 등록 완료"
else
    log_warning "Repository 등록 실패 (이미 등록되어 있을 수 있음)"
fi

# =============================================================================
# 4. ArgoCD 애플리케이션 생성
# =============================================================================
log_info "4️⃣ ArgoCD 애플리케이션 설정 중..."

APP_NAME="fortinet"
NAMESPACE="fortinet"
MANIFESTS_PATH="k8s/manifests"

# 기존 애플리케이션 확인
if argocd app get "$APP_NAME" &> /dev/null; then
    log_warning "애플리케이션 '$APP_NAME'이 이미 존재합니다."
    read -p "기존 애플리케이션을 삭제하고 재생성하시겠습니까? (y/N): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "기존 애플리케이션 삭제 중..."
        argocd app delete "$APP_NAME" --cascade
        sleep 5
    else
        log_info "기존 애플리케이션을 유지합니다."
    fi
fi

# 애플리케이션 생성 (존재하지 않는 경우)
if ! argocd app get "$APP_NAME" &> /dev/null; then
    log_info "ArgoCD 애플리케이션 생성 중..."
    if argocd app create "$APP_NAME" \
        --repo "$GITHUB_REPO" \
        --path "$MANIFESTS_PATH" \
        --dest-server "https://kubernetes.default.svc" \
        --dest-namespace "$NAMESPACE" \
        --sync-policy auto \
        --auto-prune \
        --self-heal \
        --revision HEAD; then
        log_success "ArgoCD 애플리케이션 생성 완료"
    else
        log_error "ArgoCD 애플리케이션 생성 실패"
        exit 1
    fi
fi

# =============================================================================
# 5. 초기 동기화 및 배포
# =============================================================================
log_info "5️⃣ 초기 동기화 및 배포 중..."

# 수동 동기화 실행
log_info "애플리케이션 동기화 중..."
if argocd app sync "$APP_NAME" --prune; then
    log_success "애플리케이션 동기화 완료"
else
    log_warning "동기화 중 일부 오류 발생 (정상적일 수 있음)"
fi

# 동기화 완료 대기
log_info "배포 완료까지 대기 중... (최대 5분)"
if argocd app wait "$APP_NAME" \
    --timeout 300 \
    --health \
    --sync; then
    log_success "배포 완료!"
else
    log_warning "배포 시간 초과 (수동 확인 필요)"
fi

# =============================================================================
# 6. 배포 상태 확인
# =============================================================================
log_info "6️⃣ 배포 상태 확인 중..."

echo ""
log_info "=== ArgoCD 애플리케이션 상태 ==="
argocd app get "$APP_NAME"

echo ""
log_info "=== 접속 정보 ==="
log_success "🌐 ArgoCD 대시보드: https://argo.jclee.me/applications/fortinet"
log_success "🏥 애플리케이션 헬스체크: https://fortinet.jclee.me/api/health"
log_success "📊 실시간 모니터링: kubectl get pods -n fortinet"

# =============================================================================
# 7. 헬스체크
# =============================================================================
log_info "7️⃣ 애플리케이션 헬스체크 중..."

echo "잠시 후 애플리케이션 시작을 위해 대기 중..."
sleep 30

for i in {1..5}; do
    log_info "헬스체크 시도 $i/5..."
    if curl -f -k -s "https://fortinet.jclee.me/api/health" > /dev/null; then
        log_success "✅ 애플리케이션이 정상적으로 실행 중입니다!"
        break
    else
        if [ $i -eq 5 ]; then
            log_warning "⚠️ 헬스체크 실패 - 수동 확인이 필요할 수 있습니다."
            log_info "다음 명령어로 상태를 확인하세요:"
            echo "  kubectl get pods -n fortinet"
            echo "  kubectl logs -n fortinet -l app=fortinet"
        else
            sleep 30
        fi
    fi
done

# =============================================================================
# 8. 완료 및 안내
# =============================================================================
echo ""
log_success "🎉 FortiGate Nextrade 최초 배포가 완료되었습니다!"
echo ""
log_info "📋 다음 단계:"
echo "  1. ArgoCD 대시보드에서 배포 상태 확인"
echo "  2. 애플리케이션 기능 테스트"
echo "  3. GitHub Actions Secrets 설정 (REGISTRY_USERNAME, REGISTRY_PASSWORD, ARGOCD_AUTH_TOKEN)"
echo ""
log_info "🔄 향후 배포 방법:"
echo "  git push origin master  # 자동 배포"
echo "  argocd app sync fortinet --prune  # 수동 배포"
echo ""
log_info "📚 자세한 정보는 docs/argocd-setup-guide.md를 참조하세요."

exit 0