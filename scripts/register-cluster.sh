#!/bin/bash

# =============================================================================
# ArgoCD 클러스터 등록 자동화 스크립트
# 192.168.50.110 클러스터 등록 예시
# =============================================================================

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 로그 함수
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_header() { echo -e "${CYAN}=== $1 ===${NC}"; }

# 기본 설정값
CLUSTER_HOST=${1:-"192.168.50.110"}
CLUSTER_USER=${2:-"jclee"}
CLUSTER_PASS=${3:-"bingogo1"}
CLUSTER_NAME="prod-$(echo $CLUSTER_HOST | tr '.' '-')"
CONTEXT_NAME="prod-$CLUSTER_HOST"

# Help 함수
show_help() {
    cat << EOF
ArgoCD 클러스터 등록 스크립트

사용법: $0 [HOST] [USER] [PASSWORD]

예시:
  $0                                    # 기본값 사용 (192.168.50.110)
  $0 192.168.50.111 admin secret       # 사용자 정의

기본값:
  HOST: 192.168.50.110
  USER: jclee
  PASS: bingogo1

옵션:
  -h, --help    이 도움말 표시
EOF
}

# Help 체크
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    show_help
    exit 0
fi

log_header "ArgoCD 클러스터 등록 시작"

log_info "📋 클러스터 정보:"
echo "  - Host: $CLUSTER_HOST"
echo "  - User: $CLUSTER_USER"
echo "  - Name: $CLUSTER_NAME"
echo "  - Context: $CONTEXT_NAME"
echo ""

# =============================================================================
# 1. 사전 요구사항 확인
# =============================================================================
log_header "1. 사전 요구사항 확인"

# ArgoCD CLI 확인
if ! command -v argocd &> /dev/null; then
    log_error "ArgoCD CLI가 설치되지 않았습니다."
    echo "설치 방법:"
    echo "  curl -sSL -o argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64"
    echo "  chmod +x argocd && sudo mv argocd /usr/local/bin/"
    exit 1
fi
log_success "ArgoCD CLI 확인됨"

# kubectl 확인
if ! command -v kubectl &> /dev/null; then
    log_error "kubectl이 설치되지 않았습니다."
    echo "설치 방법:"
    echo "  curl -LO https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
    echo "  sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl"
    exit 1
fi
log_success "kubectl 확인됨"

# =============================================================================
# 2. ArgoCD 로그인
# =============================================================================
log_header "2. ArgoCD 서버 로그인"

# 서버 연결 테스트
if ! curl -k -s --connect-timeout 5 "https://argo.jclee.me/api/version" > /dev/null; then
    log_error "ArgoCD 서버(argo.jclee.me)에 연결할 수 없습니다."
    exit 1
fi
log_success "ArgoCD 서버 연결 확인"

# 로그인
log_info "ArgoCD 로그인 중..."
if argocd login argo.jclee.me \
    --username admin \
    --password bingogo1 \
    --insecure \
    --grpc-web; then
    log_success "ArgoCD 로그인 성공"
else
    log_error "ArgoCD 로그인 실패"
    exit 1
fi

# =============================================================================
# 3. 대상 클러스터 연결 테스트
# =============================================================================
log_header "3. 대상 클러스터 연결 테스트"

log_info "클러스터 연결 테스트: $CLUSTER_HOST"
if curl -k -s --connect-timeout 10 "https://$CLUSTER_HOST:6443/version" > /dev/null; then
    log_success "클러스터 API 서버 연결 확인"
else
    log_warning "클러스터 API 서버에 직접 연결할 수 없습니다."
    echo "Kubernetes가 설치되지 않았을 수 있습니다."
    
    read -p "계속 진행하시겠습니까? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "등록이 취소되었습니다."
        exit 0
    fi
fi

# =============================================================================
# 4. kubectl 컨텍스트 설정
# =============================================================================
log_header "4. kubectl 컨텍스트 설정"

# 기존 컨텍스트 정리
log_info "기존 컨텍스트 정리..."
kubectl config delete-context "$CONTEXT_NAME" 2>/dev/null || true
kubectl config delete-cluster "$CLUSTER_NAME" 2>/dev/null || true
kubectl config delete-user "$CLUSTER_USER@$CLUSTER_NAME" 2>/dev/null || true

# 클러스터 설정
log_info "클러스터 설정 추가..."
kubectl config set-cluster "$CLUSTER_NAME" \
    --server="https://$CLUSTER_HOST:6443" \
    --insecure-skip-tls-verify=true

# 사용자 인증 설정
log_info "사용자 인증 설정..."
kubectl config set-credentials "$CLUSTER_USER@$CLUSTER_NAME" \
    --username="$CLUSTER_USER" \
    --password="$CLUSTER_PASS"

# 컨텍스트 생성
log_info "컨텍스트 생성..."
kubectl config set-context "$CONTEXT_NAME" \
    --cluster="$CLUSTER_NAME" \
    --user="$CLUSTER_USER@$CLUSTER_NAME"

log_success "kubectl 컨텍스트 설정 완료"

# =============================================================================
# 5. 컨텍스트 연결 테스트
# =============================================================================
log_header "5. 컨텍스트 연결 테스트"

log_info "새 컨텍스트로 연결 테스트..."
if kubectl --context="$CONTEXT_NAME" cluster-info --request-timeout=10s > /dev/null 2>&1; then
    log_success "kubectl 컨텍스트 연결 성공"
    
    # 노드 정보 표시
    log_info "클러스터 노드 정보:"
    kubectl --context="$CONTEXT_NAME" get nodes 2>/dev/null || echo "  (노드 정보를 가져올 수 없음)"
else
    log_warning "kubectl 컨텍스트 연결 실패"
    echo "클러스터가 준비되지 않았거나 인증 정보가 잘못되었을 수 있습니다."
fi

# =============================================================================
# 6. ArgoCD에 클러스터 등록
# =============================================================================
log_header "6. ArgoCD에 클러스터 등록"

# 기존 등록 제거
log_info "기존 클러스터 등록 제거..."
argocd cluster rm "https://$CLUSTER_HOST:6443" 2>/dev/null || true

# 새 클러스터 등록
log_info "새 클러스터 등록 중..."
if argocd cluster add "$CONTEXT_NAME" \
    --name "$CLUSTER_NAME" \
    --server-side-apply \
    --yes; then
    log_success "ArgoCD에 클러스터 등록 완료"
else
    log_error "클러스터 등록 실패"
    
    # 수동 등록 시도
    log_info "수동 등록 시도..."
    if argocd cluster add "https://$CLUSTER_HOST:6443" \
        --name "$CLUSTER_NAME" \
        --auth-token "" \
        --insecure; then
        log_success "수동 등록 성공"
    else
        log_error "수동 등록도 실패했습니다."
        exit 1
    fi
fi

# =============================================================================
# 7. 등록 확인 및 상태 체크
# =============================================================================
log_header "7. 등록 확인 및 상태 체크"

log_info "등록된 클러스터 목록:"
argocd cluster list

echo ""
log_info "새로 등록된 클러스터 상세 정보:"
argocd cluster get "https://$CLUSTER_HOST:6443" 2>/dev/null || \
argocd cluster get "$CLUSTER_NAME" 2>/dev/null || \
echo "클러스터 상세 정보를 가져올 수 없습니다."

# =============================================================================
# 8. 완료 및 다음 단계 안내
# =============================================================================
echo ""
log_success "🎉 클러스터 등록이 완료되었습니다!"

echo ""
log_info "📋 등록 정보:"
echo "  - 클러스터: $CLUSTER_HOST:6443"
echo "  - 이름: $CLUSTER_NAME"
echo "  - 컨텍스트: $CONTEXT_NAME"

echo ""
log_info "📚 다음 단계:"
echo "  1. ApplicationSet을 사용하여 다중 클러스터 배포 설정"
echo "  2. 개별 애플리케이션을 이 클러스터에 배포"
echo ""

log_info "🔄 ApplicationSet 사용 예시:"
echo "  kubectl apply -f argocd/applicationset.yaml"
echo ""

log_info "🚀 개별 애플리케이션 생성 예시:"
echo "  argocd app create fortinet-$CLUSTER_NAME \\"
echo "    --repo https://github.com/JCLEE94/fortinet.git \\"
echo "    --path k8s/manifests \\"
echo "    --dest-server https://$CLUSTER_HOST:6443 \\"
echo "    --dest-namespace fortinet \\"
echo "    --sync-policy auto \\"
echo "    --auto-prune \\"
echo "    --self-heal"

exit 0