#!/bin/bash
set -e

echo "🚀 MSA 수동 배포 스크립트 (jclee.me 인프라)"

# 환경변수 확인
APP_NAME="${APP_NAME:-fortinet}"
NAMESPACE="${NAMESPACE:-microservices}"
REGISTRY_URL="${REGISTRY_URL:-registry.jclee.me}"
CHARTMUSEUM_URL="${CHARTMUSEUM_URL:-charts.jclee.me}"

echo "📋 배포 정보:"
echo "  - APP_NAME: ${APP_NAME}"
echo "  - NAMESPACE: ${NAMESPACE}"
echo "  - REGISTRY: ${REGISTRY_URL}"
echo "  - CHARTMUSEUM: ${CHARTMUSEUM_URL}"

# 1. 이미지 빌드 및 푸시
echo "🐳 Docker 이미지 빌드 및 푸시..."
docker build -f Dockerfile.production -t ${REGISTRY_URL}/jclee/${APP_NAME}:latest .
docker push ${REGISTRY_URL}/jclee/${APP_NAME}:latest

# 2. Helm Chart 패키징 및 업로드
echo "📊 Helm Chart 업로드..."
helm package ./charts/${APP_NAME} --destination ./
CHART_FILE=$(ls ${APP_NAME}-*.tgz | head -n1)

echo "📤 ${CHART_FILE}을 ChartMuseum에 업로드 중..."
curl -u admin:bingogo1 --data-binary "@${CHART_FILE}" \
  https://${CHARTMUSEUM_URL}/api/charts

# 3. ArgoCD 동기화
echo "🔄 ArgoCD 동기화..."
if command -v argocd &> /dev/null; then
  argocd login argo.jclee.me --username admin --password bingogo1 --insecure --grpc-web
  argocd app sync ${APP_NAME}-${NAMESPACE}
else
  echo "⚠ ArgoCD CLI가 설치되지 않음 - 수동 동기화 필요"
  echo "   https://argo.jclee.me/applications/${APP_NAME}-${NAMESPACE}"
fi

echo ""
echo "✅ MSA 배포 완료!"
echo "🌐 서비스 URL: https://${APP_NAME}.jclee.me"
echo "📊 ArgoCD: https://argo.jclee.me/applications/${APP_NAME}-${NAMESPACE}"
echo "☸️ Kubernetes: https://k8s.jclee.me"
echo "🐳 Registry: https://${REGISTRY_URL}"
echo "📦 Charts: https://${CHARTMUSEUM_URL}"