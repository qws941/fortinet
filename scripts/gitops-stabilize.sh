#!/bin/bash

# GitOps 파이프라인 안정화 스크립트
# ArgoCD, Kustomize, Helm 통합 검증 및 안정화

set -e

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# 설정
NAMESPACE="fortinet"
APP_NAME="fortinet"
REGISTRY="registry.jclee.me"
ARGOCD_SERVER="argo.jclee.me"
DEPLOYMENT_HOST="192.168.50.110"
DEPLOYMENT_PORT="30777"

echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        GitOps 파이프라인 안정화            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo ""

# 1. Kubernetes 클러스터 연결 확인
echo -e "${GREEN}1. Kubernetes 클러스터 연결 확인...${NC}"
if kubectl cluster-info &> /dev/null; then
    echo "✅ Kubernetes 클러스터 연결 성공"
    kubectl version --client=true -o yaml | grep gitVersion | head -1 || echo "  Kubernetes 클라이언트 연결됨"
else
    echo -e "${RED}❌ Kubernetes 클러스터 연결 실패${NC}"
    exit 1
fi

# 2. ArgoCD 상태 확인
echo -e "${GREEN}2. ArgoCD 상태 확인...${NC}"
if kubectl get namespace argocd &> /dev/null; then
    echo "✅ ArgoCD 네임스페이스 존재"
    
    # ArgoCD 서버 상태
    ARGOCD_STATUS=$(kubectl get deployment argocd-server -n argocd -o jsonpath='{.status.conditions[?(@.type=="Available")].status}' 2>/dev/null || echo "False")
    if [ "$ARGOCD_STATUS" = "True" ]; then
        echo "✅ ArgoCD 서버 실행 중"
    else
        echo -e "${YELLOW}⚠️ ArgoCD 서버가 준비되지 않았습니다${NC}"
    fi
else
    echo -e "${RED}❌ ArgoCD가 설치되지 않았습니다${NC}"
    echo "설치 명령: kubectl create namespace argocd && kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml"
fi

# 3. Helm 차트 검증
echo -e "${GREEN}3. Helm 차트 검증...${NC}"
if [ -d "charts/fortinet" ]; then
    echo "✅ Helm 차트 디렉토리 존재"
    
    # Chart.yaml 버전 확인
    if [ -f "charts/fortinet/Chart.yaml" ]; then
        CHART_VERSION=$(grep "^version:" charts/fortinet/Chart.yaml | awk '{print $2}')
        echo "  📊 차트 버전: $CHART_VERSION"
    fi
    
    # Helm 차트 린트
    echo "  🔍 Helm 차트 검증 중..."
    if helm lint charts/fortinet/ 2>/dev/null; then
        echo "  ✅ Helm 차트 검증 통과"
    else
        echo -e "  ${YELLOW}⚠️ Helm 차트에 경고사항이 있습니다${NC}"
    fi
else
    echo -e "${YELLOW}⚠️ Helm 차트가 없습니다${NC}"
fi

# 4. Kustomize 설정 검증
echo -e "${GREEN}4. Kustomize 설정 검증...${NC}"
if [ -d "k8s/overlays/production" ]; then
    echo "✅ Kustomize overlay 디렉토리 존재"
    
    # kustomization.yaml 검증
    if [ -f "k8s/overlays/production/kustomization.yaml" ]; then
        echo "  ✅ kustomization.yaml 파일 존재"
        
        # 현재 이미지 태그 확인
        CURRENT_TAG=$(grep "newTag:" k8s/overlays/production/kustomization.yaml | awk '{print $2}')
        echo "  🏷️ 현재 이미지 태그: $CURRENT_TAG"
        
        # Kustomize 빌드 테스트
        echo "  🔍 Kustomize 빌드 테스트..."
        if kubectl kustomize k8s/overlays/production > /dev/null 2>&1; then
            echo "  ✅ Kustomize 빌드 성공"
        else
            echo -e "  ${RED}❌ Kustomize 빌드 실패${NC}"
        fi
    fi
else
    echo -e "${YELLOW}⚠️ Kustomize overlay가 없습니다${NC}"
fi

# 5. Docker Registry 연결 테스트
echo -e "${GREEN}5. Docker Registry 연결 테스트...${NC}"
if curl -s -o /dev/null -w "%{http_code}" https://$REGISTRY/v2/ | grep -q "200\|401"; then
    echo "✅ Registry 접속 가능: https://$REGISTRY"
    
    # 최신 이미지 태그 확인
    echo "  🔍 최신 이미지 태그 확인 중..."
    LATEST_TAGS=$(curl -s https://$REGISTRY/v2/fortinet/tags/list 2>/dev/null | jq -r '.tags[]' 2>/dev/null | tail -5)
    if [ -n "$LATEST_TAGS" ]; then
        echo "  📦 최근 이미지 태그:"
        echo "$LATEST_TAGS" | while read tag; do
            echo "    - $tag"
        done
    fi
else
    echo -e "${YELLOW}⚠️ Registry 접속 불가: https://$REGISTRY${NC}"
fi

# 6. ArgoCD Application 상태
echo -e "${GREEN}6. ArgoCD Application 상태 확인...${NC}"
if command -v argocd &> /dev/null; then
    # ArgoCD 로그인 시도
    if [ -n "$ARGOCD_TOKEN" ]; then
        echo "  🔐 ArgoCD 로그인 중..."
        if argocd login $ARGOCD_SERVER --grpc-web --auth-token $ARGOCD_TOKEN &> /dev/null; then
            echo "  ✅ ArgoCD 로그인 성공"
            
            # 애플리케이션 상태 확인
            if argocd app get $APP_NAME &> /dev/null; then
                echo "  ✅ ArgoCD 애플리케이션 존재: $APP_NAME"
                
                # 동기화 상태
                SYNC_STATUS=$(argocd app get $APP_NAME -o json | jq -r '.status.sync.status' 2>/dev/null)
                HEALTH_STATUS=$(argocd app get $APP_NAME -o json | jq -r '.status.health.status' 2>/dev/null)
                
                echo "  📊 동기화 상태: $SYNC_STATUS"
                echo "  🏥 헬스 상태: $HEALTH_STATUS"
                
                if [ "$SYNC_STATUS" != "Synced" ]; then
                    echo -e "  ${YELLOW}⚠️ 애플리케이션이 동기화되지 않았습니다${NC}"
                    echo "  동기화 명령: argocd app sync $APP_NAME"
                fi
            else
                echo -e "  ${YELLOW}⚠️ ArgoCD 애플리케이션이 없습니다${NC}"
                echo "  생성 명령: kubectl apply -f k8s/argocd/fortinet-app.yaml"
            fi
        else
            echo -e "  ${YELLOW}⚠️ ArgoCD 로그인 실패${NC}"
        fi
    else
        echo -e "  ${YELLOW}⚠️ ARGOCD_TOKEN이 설정되지 않았습니다${NC}"
    fi
else
    echo -e "  ${YELLOW}⚠️ ArgoCD CLI가 설치되지 않았습니다${NC}"
fi

# 7. 배포 상태 확인
echo -e "${GREEN}7. 현재 배포 상태 확인...${NC}"
if kubectl get namespace $NAMESPACE &> /dev/null; then
    echo "✅ 애플리케이션 네임스페이스 존재: $NAMESPACE"
    
    # Deployment 상태
    DEPLOYMENT_STATUS=$(kubectl get deployment -n $NAMESPACE -o json 2>/dev/null | jq -r '.items[0].status.conditions[?(@.type=="Available")].status' 2>/dev/null)
    if [ "$DEPLOYMENT_STATUS" = "True" ]; then
        echo "  ✅ Deployment 실행 중"
        
        # Pod 상태
        RUNNING_PODS=$(kubectl get pods -n $NAMESPACE --field-selector=status.phase=Running -o json | jq '.items | length')
        TOTAL_PODS=$(kubectl get pods -n $NAMESPACE -o json | jq '.items | length')
        echo "  📊 Pod 상태: $RUNNING_PODS/$TOTAL_PODS Running"
        
        # Service 상태
        SERVICE_COUNT=$(kubectl get svc -n $NAMESPACE -o json | jq '.items | length')
        echo "  🔗 Service 개수: $SERVICE_COUNT"
    else
        echo -e "  ${YELLOW}⚠️ Deployment가 준비되지 않았습니다${NC}"
    fi
else
    echo -e "  ${YELLOW}⚠️ 네임스페이스가 없습니다: $NAMESPACE${NC}"
fi

# 8. 헬스체크
echo -e "${GREEN}8. 애플리케이션 헬스체크...${NC}"
HEALTH_URL="http://$DEPLOYMENT_HOST:$DEPLOYMENT_PORT/api/health"
echo "  🔍 헬스체크 URL: $HEALTH_URL"

if curl -f -s --connect-timeout 5 --max-time 10 "$HEALTH_URL" > /dev/null; then
    echo "  ✅ 헬스체크 성공"
    HEALTH_RESPONSE=$(curl -s "$HEALTH_URL")
    echo "  📊 응답:"
    echo "$HEALTH_RESPONSE" | jq '.' 2>/dev/null || echo "$HEALTH_RESPONSE"
else
    echo -e "  ${YELLOW}⚠️ 헬스체크 실패${NC}"
fi

# 9. GitOps 워크플로우 검증
echo -e "${GREEN}9. GitOps 워크플로우 검증...${NC}"

# Git 상태 확인
GIT_BRANCH=$(git branch --show-current 2>/dev/null)
GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null)
echo "  📌 현재 브랜치: $GIT_BRANCH"
echo "  📌 현재 커밋: $GIT_COMMIT"

# GitHub Actions 워크플로우 확인
if [ -f ".github/workflows/gitops-pipeline.yml" ]; then
    echo "  ✅ GitOps 파이프라인 워크플로우 존재"
else
    echo -e "  ${YELLOW}⚠️ GitOps 파이프라인 워크플로우가 없습니다${NC}"
fi

# 10. 개선 제안
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           GitOps 안정화 리포트             ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo ""

ISSUES=0

# 문제점 수집 및 해결 방안 제시
if [ "$ARGOCD_STATUS" != "True" ]; then
    ((ISSUES++))
    echo -e "${YELLOW}문제 $ISSUES: ArgoCD 서버가 준비되지 않았습니다${NC}"
    echo "  해결: kubectl rollout restart deployment argocd-server -n argocd"
    echo ""
fi

if [ "$SYNC_STATUS" != "Synced" ] && [ -n "$SYNC_STATUS" ]; then
    ((ISSUES++))
    echo -e "${YELLOW}문제 $ISSUES: ArgoCD 애플리케이션이 동기화되지 않았습니다${NC}"
    echo "  해결: argocd app sync $APP_NAME --prune"
    echo ""
fi

if [ "$DEPLOYMENT_STATUS" != "True" ]; then
    ((ISSUES++))
    echo -e "${YELLOW}문제 $ISSUES: Deployment가 준비되지 않았습니다${NC}"
    echo "  해결: kubectl describe deployment -n $NAMESPACE"
    echo "       kubectl logs -n $NAMESPACE -l app=$APP_NAME --tail=50"
    echo ""
fi

if [ $ISSUES -eq 0 ]; then
    echo -e "${GREEN}✅ GitOps 파이프라인이 정상적으로 작동 중입니다!${NC}"
    echo ""
    echo "📋 권장 사항:"
    echo "  1. 정기적인 이미지 태그 업데이트"
    echo "  2. ArgoCD 자동 동기화 정책 검토"
    echo "  3. 모니터링 대시보드 설정"
    echo "  4. 백업 정책 수립"
else
    echo -e "${YELLOW}⚠️ $ISSUES개의 문제가 발견되었습니다${NC}"
    echo ""
    echo "📋 다음 단계:"
    echo "  1. 위의 해결 방안 실행"
    echo "  2. ./scripts/argocd-setup.sh 실행"
    echo "  3. git push로 GitOps 파이프라인 트리거"
fi

echo ""
echo "🔗 유용한 링크:"
echo "  - ArgoCD UI: https://$ARGOCD_SERVER"
echo "  - Registry: https://$REGISTRY"
echo "  - Application: http://$DEPLOYMENT_HOST:$DEPLOYMENT_PORT"
echo ""
echo "✅ GitOps 안정화 검증 완료!"