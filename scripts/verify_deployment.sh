#!/bin/bash

APP_NAME="fortinet"
NAMESPACE="fortinet"
NODEPORT="30779"
BASE_URL="http://192.168.50.110:${NODEPORT}"

echo "🔍 Fortinet Deployment Verification"
echo "=================================="

# 1. GitHub Actions 워크플로우 상태 확인
echo "1. GitHub Actions workflow status..."
gh run list --workflow="Fortinet GitOps CI/CD Pipeline" --limit 3

# 2. Docker 이미지 확인
echo -e "\n2. Docker images in registry..."
curl -s -u ${REGISTRY_USERNAME}:${REGISTRY_PASSWORD} \
  https://${REGISTRY_URL}/v2/jclee94/${APP_NAME}/tags/list | jq -r '.tags[]' | head -5

# 3. Helm 차트 확인
echo -e "\n3. Helm charts in museum..."
curl -s -u ${CHARTMUSEUM_USERNAME}:${CHARTMUSEUM_PASSWORD} \
  ${CHARTMUSEUM_URL}/api/charts/${APP_NAME} | jq -r '.[].version' | head -5

# 4. Kubernetes 리소스 확인
echo -e "\n4. Kubernetes resources..."
kubectl get pods,svc -n ${NAMESPACE} -l app=${APP_NAME}

# 5. ArgoCD 애플리케이션 상태
echo -e "\n5. ArgoCD application status..."
argocd app get ${APP_NAME}-production 2>/dev/null || echo "⚠ ArgoCD not configured or not accessible"

# 6. 애플리케이션 헬스체크
echo -e "\n6. Application health checks..."
echo "Testing: ${BASE_URL}/api/health"
curl -f --connect-timeout 10 "${BASE_URL}/api/health" && echo -e "\n✅ Health check passed" || echo -e "\n❌ Health check failed"

echo "Testing: ${BASE_URL}/api/system-info"
curl -f --connect-timeout 10 "${BASE_URL}/api/system-info" && echo -e "\n✅ System info accessible" || echo -e "\n❌ System info failed"

# 7. 로그 확인
echo -e "\n7. Recent application logs..."
kubectl logs -l app=${APP_NAME} -n ${NAMESPACE} --tail=10 --since=5m | head -20

echo -e "\n✅ Deployment verification completed"
