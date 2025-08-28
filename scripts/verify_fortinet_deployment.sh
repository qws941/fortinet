#!/bin/bash

APP_NAME="fortinet"
NAMESPACE="fortinet"
NODEPORT="30777"
BASE_URL="http://192.168.50.110:${NODEPORT}"

echo "🔍 Fortinet Template Deployment Verification"
echo "==========================================="

# 1. GitHub Actions 워크플로우 상태 확인
echo "1. GitHub Actions workflow status..."
gh run list --workflow="Fortinet Optimized CI/CD Pipeline" --limit 3

# 2. Docker 이미지 확인
echo -e "\n2. Docker images in registry..."
if command -v curl >/dev/null 2>&1; then
    curl -s -u ${REGISTRY_USERNAME}:${REGISTRY_PASSWORD} \
      https://${REGISTRY_URL}/v2/jclee94/${APP_NAME}/tags/list | \
      python3 -c "import sys,json; print('\n'.join(json.load(sys.stdin).get('tags', [])[:5]))" 2>/dev/null || \
      echo "Registry access failed or jq not available"
fi

# 3. Helm 차트 확인
echo -e "\n3. Helm charts in museum..."
if command -v curl >/dev/null 2>&1; then
    curl -s -u ${CHARTMUSEUM_USERNAME}:${CHARTMUSEUM_PASSWORD} \
      ${CHARTMUSEUM_URL}/api/charts/${APP_NAME} | \
      python3 -c "import sys,json; [print(chart['version']) for chart in json.load(sys.stdin)[:5]]" 2>/dev/null || \
      echo "ChartMuseum access failed"
fi

# 4. Kubernetes 리소스 확인
echo -e "\n4. Kubernetes resources..."
kubectl get pods,svc -n ${NAMESPACE} -l app=${APP_NAME}

# 5. ArgoCD 애플리케이션 상태
echo -e "\n5. ArgoCD application status..."
argocd app get ${APP_NAME}-${NAMESPACE} 2>/dev/null || echo "⚠ ArgoCD not configured or not accessible"

# 6. 애플리케이션 헬스체크
echo -e "\n6. Application health checks..."
echo "Testing: ${BASE_URL}/api/health"
if curl -f --connect-timeout 10 "${BASE_URL}/api/health" 2>/dev/null; then
    echo "✅ Health check passed"
else
    echo "❌ Health check failed"
fi

echo "Testing: ${BASE_URL}/api/system-info"
if curl -f --connect-timeout 10 "${BASE_URL}/api/system-info" 2>/dev/null; then
    echo "✅ System info accessible"
else
    echo "❌ System info failed"
fi

# 7. 로그 확인
echo -e "\n7. Recent application logs..."
kubectl logs -l app=${APP_NAME} -n ${NAMESPACE} --tail=10 --since=5m | head -20

echo -e "\n✅ Deployment verification completed"
