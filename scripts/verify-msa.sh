#!/bin/bash
# MSA 인프라 상태 종합 확인 (jclee.me)

echo "🔍 jclee.me MSA 인프라 상태 확인..."

APP_NAME="${APP_NAME:-fortinet}"
NAMESPACE="${NAMESPACE:-microservices}"

# 1. Docker Registry 상태
echo "🐳 Docker Registry (registry.jclee.me):"
curl -s -u admin:bingogo1 https://registry.jclee.me/v2/jclee/${APP_NAME}/tags/list 2>/dev/null | jq . || echo "Registry 연결 실패"

# 2. Helm Charts 상태  
echo "📊 Helm Charts (charts.jclee.me):"
curl -s -u admin:bingogo1 https://charts.jclee.me/api/charts/${APP_NAME} 2>/dev/null | jq . || echo "Charts 연결 실패"

# 3. ArgoCD Application 상태
echo "🚀 ArgoCD (argo.jclee.me):"
if command -v argocd &> /dev/null; then
  argocd login argo.jclee.me --username admin --password bingogo1 --insecure --grpc-web 2>/dev/null
  argocd app get ${APP_NAME}-${NAMESPACE} 2>/dev/null || echo "ArgoCD 애플리케이션 없음"
else
  echo "⚠ ArgoCD CLI가 설치되지 않음"
  echo "   https://argo.jclee.me/applications/${APP_NAME}-${NAMESPACE}"
fi

# 4. Kubernetes 클러스터 상태 (k8s.jclee.me)
echo "☸️ Kubernetes (k8s.jclee.me):"
if kubectl get pods,svc,ingress,hpa -n ${NAMESPACE} -l app=${APP_NAME} 2>/dev/null; then
  echo "✅ Kubernetes 리소스 확인됨"
else
  echo "⚠ Kubernetes 연결 실패 또는 리소스 없음"
fi

# 5. 서비스 Health Check
echo "🌐 Service Health Check:"
if curl -f -s https://${APP_NAME}.jclee.me/api/health 2>/dev/null; then
  echo "✅ Health Check 성공"
else
  echo "⚠ Health check endpoint 응답 없음"
fi

# 6. NodePort 확인
echo "🔌 NodePort 확인:"
if kubectl get svc ${APP_NAME} -n ${NAMESPACE} -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null; then
  NODEPORT=$(kubectl get svc ${APP_NAME} -n ${NAMESPACE} -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null)
  echo "NodePort: ${NODEPORT}"
  curl -f -s http://192.168.50.110:${NODEPORT}/api/health 2>/dev/null && echo " - NodePort Health Check 성공" || echo " - NodePort 연결 실패"
else
  echo "⚠ NodePort 정보 없음"
fi

echo ""
echo "📊 MSA 인프라 요약:"
echo "  🌐 Public URL: https://${APP_NAME}.jclee.me"
echo "  🔌 NodePort: http://192.168.50.110:30777"  
echo "  📊 ArgoCD: https://argo.jclee.me/applications/${APP_NAME}-${NAMESPACE}"
echo "  ☸️ Kubernetes: https://k8s.jclee.me"
echo "  🐳 Registry: https://registry.jclee.me"
echo "  📦 Charts: https://charts.jclee.me"
echo ""
echo "✅ MSA 인프라 상태 확인 완료"