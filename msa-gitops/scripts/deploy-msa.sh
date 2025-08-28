#!/bin/bash
set -e

# MSA GitOps 배포 스크립트 (jclee.me)
ENVIRONMENT="${1:-production}"
SERVICE="${2:-all}"
CHART_VERSION="${3:-latest}"
IMAGE_TAG="${4:-latest}"

echo "🚀 MSA GitOps 배포 시작..."
echo "  - Environment: ${ENVIRONMENT}"
echo "  - Service: ${SERVICE}"
echo "  - Chart Version: ${CHART_VERSION}"
echo "  - Image Tag: ${IMAGE_TAG}"

# ArgoCD 로그인
argocd login argo.jclee.me --username admin --password bingogo1 --insecure --grpc-web

# 환경별 설정
case ${ENVIRONMENT} in
  "development")
    NAMESPACE="microservices-dev"
    DOMAIN_SUFFIX="-dev.jclee.me"
    REPLICA_COUNT=1
    CPU_LIMIT="500m"
    MEMORY_LIMIT="512Mi"
    CPU_REQUEST="100m"
    MEMORY_REQUEST="128Mi"
    HPA_ENABLED="false"
    MIN_REPLICAS=1
    MAX_REPLICAS=1
    ;;
  "staging")
    NAMESPACE="microservices-staging"
    DOMAIN_SUFFIX="-staging.jclee.me"
    REPLICA_COUNT=2
    CPU_LIMIT="1000m"
    MEMORY_LIMIT="1Gi"
    CPU_REQUEST="200m"
    MEMORY_REQUEST="256Mi"
    HPA_ENABLED="true"
    MIN_REPLICAS=2
    MAX_REPLICAS=5
    ;;
  "production")
    NAMESPACE="microservices"
    DOMAIN_SUFFIX=".jclee.me"
    REPLICA_COUNT=3
    CPU_LIMIT="2000m"
    MEMORY_LIMIT="2Gi"
    CPU_REQUEST="500m"
    MEMORY_REQUEST="512Mi"
    HPA_ENABLED="true"
    MIN_REPLICAS=3
    MAX_REPLICAS=10
    ;;
  *)
    echo "❌ 지원하지 않는 환경: ${ENVIRONMENT}"
    exit 1
    ;;
esac

# MSA 서비스 목록
MSA_SERVICES=("user-service" "product-service" "order-service" "notification-service")

# 인프라 컴포넌트 먼저 배포
echo "🏗️ 인프라 컴포넌트 배포..."

# Istio 배포
envsubst < msa-gitops/applications/istio-application.yaml > /tmp/istio-${ENVIRONMENT}.yaml
argocd app create -f /tmp/istio-${ENVIRONMENT}.yaml --upsert
argocd app sync istio-${ENVIRONMENT} --timeout 300

# Monitoring 배포
envsubst < msa-gitops/applications/monitoring-application.yaml > /tmp/monitoring-${ENVIRONMENT}.yaml
argocd app create -f /tmp/monitoring-${ENVIRONMENT}.yaml --upsert
argocd app sync monitoring-${ENVIRONMENT} --timeout 300

# MSA 서비스 배포
if [ "${SERVICE}" = "all" ]; then
  SERVICES_TO_DEPLOY=("${MSA_SERVICES[@]}")
else
  SERVICES_TO_DEPLOY=("${SERVICE}")
fi

for SVC in "${SERVICES_TO_DEPLOY[@]}"; do
  echo "📱 MSA 서비스 배포: ${SVC}"
  
  # Application YAML 생성
  envsubst < msa-gitops/applications/${SVC}-application.yaml > /tmp/${SVC}-${ENVIRONMENT}.yaml
  
  # ArgoCD Application 생성/업데이트
  argocd app create -f /tmp/${SVC}-${ENVIRONMENT}.yaml --upsert
  
  # 동기화 실행
  echo "🔄 ArgoCD 동기화 실행: ${SVC}-${ENVIRONMENT}"
  argocd app sync ${SVC}-${ENVIRONMENT} --timeout 300
  
  # 배포 완료 대기
  echo "⏳ 배포 완료 대기: ${SVC}-${ENVIRONMENT}"
  argocd app wait ${SVC}-${ENVIRONMENT} --timeout 300
done

# 전체 MSA 상태 확인
echo "📊 MSA 전체 상태 확인..."
for SVC in "${SERVICES_TO_DEPLOY[@]}"; do
  echo "  📱 ${SVC}: $(argocd app get ${SVC}-${ENVIRONMENT} -o json | jq -r '.status.health.status')"
done

echo "🎉 MSA GitOps 배포 완료!"
echo ""
echo "🌐 MSA 서비스 URLs:"
for SVC in "${SERVICES_TO_DEPLOY[@]}"; do
  echo "  - ${SVC}: https://${SVC}${DOMAIN_SUFFIX}"
done
echo ""
echo "📊 모니터링:"
echo "  - ArgoCD: https://argo.jclee.me/applications"
echo "  - Grafana: https://grafana${DOMAIN_SUFFIX}"
echo "  - Prometheus: https://prometheus${DOMAIN_SUFFIX}"
echo "  - K8s Dashboard: https://k8s.jclee.me"