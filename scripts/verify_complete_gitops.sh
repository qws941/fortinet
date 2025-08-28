#!/bin/bash

APP_NAME="fortinet"
NAMESPACE="fortinet" 
NODEPORT="30777"
BASE_URL="http://192.168.50.110:${NODEPORT}"

echo "🔍 Complete GitOps Deployment Verification"
echo "=========================================="

# 1. GitHub Actions 상태
echo "1. GitHub Actions workflow status..."
gh run list --workflow="Fortinet Complete GitOps CI/CD" --limit 3

# 2. ArgoCD 애플리케이션 상태
echo -e "\n2. ArgoCD application status..."
if command -v argocd >/dev/null 2>&1; then
    argocd app get fortinet-gitops 2>/dev/null || echo "⚠ ArgoCD app not found or not accessible"
else
    echo "⚠ ArgoCD CLI not available"
fi

# 3. Kubernetes 리소스
echo -e "\n3. Kubernetes resources..."
kubectl get pods,svc -n ${NAMESPACE} -l app=${APP_NAME}

# 4. 애플리케이션 헬스체크
echo -e "\n4. Application health check..."
echo "Testing: ${BASE_URL}/api/health"
if curl -f --connect-timeout 10 "${BASE_URL}/api/health" 2>/dev/null; then
    echo "✅ Health check passed"
else
    echo "❌ Health check failed"
fi

# 5. Chart 버전 확인
echo -e "\n5. Current chart version..."
if [ -f "charts/fortinet/Chart.yaml" ]; then
    grep "^version:" charts/fortinet/Chart.yaml
    grep "^appVersion:" charts/fortinet/Chart.yaml
fi

echo -e "\n✅ Complete GitOps verification completed"
