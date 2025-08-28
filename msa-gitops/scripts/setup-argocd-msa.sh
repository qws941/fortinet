#!/bin/bash
set -e

# ArgoCD MSA 초기 설정 스크립트 (jclee.me)
ARGOCD_URL="argo.jclee.me"
ARGOCD_USERNAME="admin"
ARGOCD_PASSWORD="bingogo1"
CHARTMUSEUM_URL="https://charts.jclee.me"
GITHUB_REPO="https://github.com/jclee94/fortinet.git"

echo "🚀 ArgoCD MSA 초기 설정 시작..."

# ArgoCD CLI 설치 확인
if ! command -v argocd &> /dev/null; then
    echo "📦 ArgoCD CLI 설치 중..."
    curl -sSL -o argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
    sudo install -m 555 argocd /usr/local/bin/argocd
    rm argocd
fi

# ArgoCD 로그인
echo "🔐 ArgoCD 로그인..."
argocd login ${ARGOCD_URL} --username ${ARGOCD_USERNAME} --password ${ARGOCD_PASSWORD} --insecure --grpc-web

# ChartMuseum Repository 추가
echo "📊 Helm Repository 등록..."
argocd repo add ${CHARTMUSEUM_URL} --type helm --name chartmuseum-jclee --username admin --password bingogo1 --insecure-skip-server-verification

# GitHub Repository 추가
echo "📚 GitHub Repository 등록..."
argocd repo add ${GITHUB_REPO} --name fortinet-github

# MSA Project 생성
echo "🏗️ ArgoCD MSA Project 생성..."
argocd proj create -f msa-gitops/configs/argocd-msa-project.yaml

# Kubernetes Namespaces 생성
echo "🌐 Kubernetes Namespaces 생성..."
kubectl create namespace microservices --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace microservices-staging --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace microservices-dev --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace istio-system --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace istio-system-staging --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace istio-system-dev --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace monitoring-staging --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace monitoring-dev --dry-run=client -o yaml | kubectl apply -f -

# Namespace Labels 설정
echo "🏷️ Namespace Labels 설정..."
kubectl label namespace microservices environment=production --overwrite
kubectl label namespace microservices-staging environment=staging --overwrite
kubectl label namespace microservices-dev environment=development --overwrite
kubectl label namespace istio-system environment=production --overwrite
kubectl label namespace istio-system-staging environment=staging --overwrite
kubectl label namespace istio-system-dev environment=development --overwrite
kubectl label namespace monitoring environment=production --overwrite
kubectl label namespace monitoring-staging environment=staging --overwrite
kubectl label namespace monitoring-dev environment=development --overwrite

# Istio Labels for Service Mesh
kubectl label namespace microservices istio-injection=enabled --overwrite
kubectl label namespace microservices-staging istio-injection=enabled --overwrite
kubectl label namespace microservices-dev istio-injection=enabled --overwrite

# Harbor Registry Secret 생성
echo "🔐 Harbor Registry Secret 생성..."
for NS in microservices microservices-staging microservices-dev; do
    kubectl create secret docker-registry harbor-registry-secret \
        --docker-server=registry.jclee.me \
        --docker-username=admin \
        --docker-password=bingogo1 \
        --namespace=${NS} \
        --dry-run=client -o yaml | kubectl apply -f -
done

# MSA Notifications 설정
echo "📢 MSA Notifications 설정..."
kubectl apply -f msa-gitops/configs/msa-notifications.yaml

# ArgoCD Notifications Controller 재시작
echo "🔄 ArgoCD Notifications Controller 재시작..."
kubectl rollout restart deployment argocd-notifications-controller -n argocd

# 인프라 컴포넌트 Applications 생성 (Production)
echo "🏗️ 인프라 컴포넌트 배포 (Production)..."

# Istio Production
export ENVIRONMENT=production
export DOMAIN_SUFFIX=.jclee.me
export NAMESPACE=istio-system
export HPA_ENABLED=true
export MIN_REPLICAS=3
export MAX_REPLICAS=10
export CPU_LIMIT=2000m
export MEMORY_LIMIT=2Gi
export CPU_REQUEST=500m
export MEMORY_REQUEST=512Mi

envsubst < msa-gitops/applications/istio-application.yaml > /tmp/istio-production.yaml
argocd app create -f /tmp/istio-production.yaml --upsert

# Monitoring Production
export NAMESPACE=monitoring
envsubst < msa-gitops/applications/monitoring-application.yaml > /tmp/monitoring-production.yaml
argocd app create -f /tmp/monitoring-production.yaml --upsert

# MSA Services Applications 생성 (Production)
echo "📱 MSA Services Applications 생성 (Production)..."
MSA_SERVICES=("user-service" "product-service" "order-service" "notification-service")

for SVC in "${MSA_SERVICES[@]}"; do
    echo "  📱 생성 중: ${SVC}-production"
    export SERVICE_NAME=${SVC}
    export ENVIRONMENT=production
    export NAMESPACE=microservices
    export DOMAIN_SUFFIX=.jclee.me
    export REPLICA_COUNT=3
    export HPA_ENABLED=true
    export MIN_REPLICAS=3
    export MAX_REPLICAS=10
    export CPU_LIMIT=2000m
    export MEMORY_LIMIT=2Gi
    export CPU_REQUEST=500m
    export MEMORY_REQUEST=512Mi
    
    envsubst < msa-gitops/applications/${SVC}-application.yaml > /tmp/${SVC}-production.yaml
    argocd app create -f /tmp/${SVC}-production.yaml --upsert
done

# 프로젝트 상태 확인
echo "📊 ArgoCD 프로젝트 상태 확인..."
argocd proj get fortinet-msa-project

echo "📋 등록된 Repository 목록:"
argocd repo list

echo "📱 생성된 Applications 목록:"
argocd app list --project fortinet-msa-project

echo "🎉 ArgoCD MSA 초기 설정 완료!"
echo ""
echo "🌐 접속 정보:"
echo "  - ArgoCD UI: https://argo.jclee.me"
echo "  - Username: admin"
echo "  - Password: bingogo1"
echo ""
echo "📊 MSA 배포 명령어:"
echo "  - 전체 배포: ./msa-gitops/scripts/deploy-msa.sh production all"
echo "  - 특정 서비스: ./msa-gitops/scripts/deploy-msa.sh production user-service"
echo "  - 개발 환경: ./msa-gitops/scripts/deploy-msa.sh development all"
echo ""
echo "🔍 모니터링 상태 확인:"
echo "  ./msa-gitops/scripts/monitor-msa-status.sh"