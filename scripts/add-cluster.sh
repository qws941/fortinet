#!/bin/bash

# =============================================================================
# 새 Kubernetes 클러스터를 ArgoCD에 추가하는 스크립트
# 클러스터: 192.168.50.110 (jclee/bingogo1)
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

log_info "🔗 새 Kubernetes 클러스터 추가 중..."

# =============================================================================
# 1. 새 클러스터 정보
# =============================================================================
CLUSTER_HOST="192.168.50.110"
CLUSTER_USER="jclee"
CLUSTER_PASS="bingogo1"
CLUSTER_NAME="production-secondary"

log_info "📋 클러스터 정보:"
echo "  - Host: $CLUSTER_HOST"
echo "  - User: $CLUSTER_USER"
echo "  - Name: $CLUSTER_NAME"

# =============================================================================
# 2. ArgoCD 로그인 확인
# =============================================================================
log_info "🔐 ArgoCD 로그인 상태 확인..."

if ! argocd cluster list &> /dev/null; then
    log_info "ArgoCD 로그인 중..."
    argocd login argo.jclee.me --username admin --password bingogo1 --insecure --grpc-web
fi
log_success "ArgoCD 로그인 확인됨"

# =============================================================================
# 3. kubectl 컨텍스트 생성
# =============================================================================
log_info "🔧 kubectl 컨텍스트 설정 중..."

# 기존 컨텍스트 삭제 (있다면)
kubectl config delete-context "$CLUSTER_NAME" 2>/dev/null || true
kubectl config delete-cluster "$CLUSTER_NAME" 2>/dev/null || true
kubectl config delete-user "$CLUSTER_USER@$CLUSTER_NAME" 2>/dev/null || true

# 새 클러스터 설정
kubectl config set-cluster "$CLUSTER_NAME" \
    --server="https://$CLUSTER_HOST:6443" \
    --insecure-skip-tls-verify=true

# 사용자 인증 설정
kubectl config set-credentials "$CLUSTER_USER@$CLUSTER_NAME" \
    --username="$CLUSTER_USER" \
    --password="$CLUSTER_PASS"

# 컨텍스트 생성
kubectl config set-context "$CLUSTER_NAME" \
    --cluster="$CLUSTER_NAME" \
    --user="$CLUSTER_USER@$CLUSTER_NAME"

log_success "kubectl 컨텍스트 생성 완료"

# =============================================================================
# 4. 클러스터 연결 테스트
# =============================================================================
log_info "🧪 클러스터 연결 테스트..."

if kubectl --context="$CLUSTER_NAME" cluster-info --request-timeout=10s > /dev/null 2>&1; then
    log_success "클러스터 연결 성공"
else
    log_error "클러스터 연결 실패"
    log_info "다음을 확인하세요:"
    echo "  1. 클러스터가 실행 중인지 확인"
    echo "  2. 네트워크 연결 확인"
    echo "  3. 인증 정보 확인"
    exit 1
fi

# =============================================================================
# 5. ArgoCD에 클러스터 추가
# =============================================================================
log_info "➕ ArgoCD에 클러스터 추가 중..."

# 기존 클러스터 제거 (있다면)
argocd cluster rm "https://$CLUSTER_HOST:6443" 2>/dev/null || true

# 새 클러스터 추가
if argocd cluster add "$CLUSTER_NAME" \
    --name "$CLUSTER_NAME" \
    --server-side-apply \
    --yes; then
    log_success "ArgoCD에 클러스터 추가 완료"
else
    log_error "클러스터 추가 실패"
    exit 1
fi

# =============================================================================
# 6. 등록된 클러스터 확인
# =============================================================================
log_info "📊 등록된 클러스터 목록:"
argocd cluster list

# =============================================================================
# 7. 네임스페이스 생성 (새 클러스터에)
# =============================================================================
log_info "📂 새 클러스터에 네임스페이스 생성..."

kubectl --context="$CLUSTER_NAME" create namespace fortinet --dry-run=client -o yaml | \
kubectl --context="$CLUSTER_NAME" apply -f -

log_success "네임스페이스 'fortinet' 생성 완료"

# =============================================================================
# 8. Registry Secret 생성 (새 클러스터에)
# =============================================================================
log_info "🔑 Registry Secret 생성..."

kubectl --context="$CLUSTER_NAME" create secret docker-registry regcred \
    --docker-server=registry.jclee.me \
    --docker-username=qws9411 \
    --docker-password=bingogo1 \
    --namespace=fortinet \
    --dry-run=client -o yaml | \
kubectl --context="$CLUSTER_NAME" apply -f -

log_success "Registry Secret 생성 완료"

# =============================================================================
# 9. 완료
# =============================================================================
echo ""
log_success "🎉 새 클러스터 추가가 완료되었습니다!"
echo ""
log_info "📋 다음 단계:"
echo "  1. ApplicationSet을 생성하여 다중 클러스터 배포 설정"
echo "  2. 클러스터별 설정 오버레이 구성"
echo "  3. 배포 테스트"
echo ""
log_info "📚 생성된 kubectl 컨텍스트: $CLUSTER_NAME"
echo "  사용법: kubectl --context=$CLUSTER_NAME get nodes"

exit 0