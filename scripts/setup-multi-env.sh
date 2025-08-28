#!/bin/bash
# setup-multi-env.sh - 다중 환경 설정 스크립트

set -euo pipefail

# 색깔 출력을 위한 함수
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# 환경 설정
REGISTRY_URL="registry.jclee.me"
REGISTRY_USER="admin"
REGISTRY_PASS="bingogo1"
CHARTMUSEUM_URL="https://charts.jclee.me"

# 환경별 네임스페이스와 포트 설정
declare -A ENV_NAMESPACES=(
    ["production"]="fortinet"
    ["staging"]="fortinet-staging"
    ["development"]="fortinet-dev"
)

declare -A ENV_NODEPORTS=(
    ["production"]="30777"
    ["staging"]="30779"
    ["development"]="30778"
)

# 함수: 네임스페이스 생성
create_namespaces() {
    log_info "Creating namespaces for all environments..."
    
    for env in "${!ENV_NAMESPACES[@]}"; do
        namespace=${ENV_NAMESPACES[$env]}
        log_info "Creating namespace: $namespace"
        
        kubectl create namespace "$namespace" --dry-run=client -o yaml | kubectl apply -f -
        
        # 네임스페이스 라벨 추가
        kubectl label namespace "$namespace" environment="$env" --overwrite
        kubectl label namespace "$namespace" managed-by="fortinet-cicd" --overwrite
        
        log_success "Namespace $namespace created/updated"
    done
}

# 함수: Registry Secret 생성
create_registry_secrets() {
    log_info "Creating registry secrets for all environments..."
    
    for env in "${!ENV_NAMESPACES[@]}"; do
        namespace=${ENV_NAMESPACES[$env]}
        log_info "Creating registry secret in namespace: $namespace"
        
        kubectl create secret docker-registry registry-credentials \
            --docker-server="$REGISTRY_URL" \
            --docker-username="$REGISTRY_USER" \
            --docker-password="$REGISTRY_PASS" \
            --namespace="$namespace" \
            --dry-run=client -o yaml | kubectl apply -f -
        
        log_success "Registry secret created in $namespace"
    done
    
    # ArgoCD 네임스페이스에도 생성
    log_info "Creating registry secret in argocd namespace..."
    kubectl create secret docker-registry registry-credentials \
        --docker-server="$REGISTRY_URL" \
        --docker-username="$REGISTRY_USER" \
        --docker-password="$REGISTRY_PASS" \
        --namespace="argocd" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    log_success "Registry secret created in argocd namespace"
}

# 함수: 환경별 ConfigMap 생성
create_configmaps() {
    log_info "Creating environment-specific ConfigMaps..."
    
    for env in "${!ENV_NAMESPACES[@]}"; do
        namespace=${ENV_NAMESPACES[$env]}
        nodeport=${ENV_NODEPORTS[$env]}
        
        log_info "Creating ConfigMap for environment: $env"
        
        kubectl create configmap fortinet-config \
            --from-literal=APP_MODE="$env" \
            --from-literal=ENVIRONMENT="$env" \
            --from-literal=NODE_PORT="$nodeport" \
            --from-literal=LOG_LEVEL=$([ "$env" = "production" ] && echo "warning" || echo "info") \
            --from-literal=DEBUG=$([ "$env" = "production" ] && echo "false" || echo "true") \
            --namespace="$namespace" \
            --dry-run=client -o yaml | kubectl apply -f -
        
        log_success "ConfigMap created for $env environment"
    done
}

# 함수: ArgoCD 애플리케이션 배포
deploy_argocd_applications() {
    log_info "Deploying ArgoCD applications for all environments..."
    
    # Production (기존 유지)
    log_info "Applying production ArgoCD application..."
    kubectl apply -f argocd/fortinet-app.yaml
    
    # Staging
    log_info "Applying staging ArgoCD application..."
    kubectl apply -f argocd/fortinet-staging.yaml
    
    # Development
    log_info "Applying development ArgoCD application..."
    kubectl apply -f argocd/fortinet-development.yaml
    
    log_success "All ArgoCD applications deployed"
}

# 함수: 환경별 Service 생성 (NodePort)
create_services() {
    log_info "Creating environment-specific services..."
    
    for env in "${!ENV_NAMESPACES[@]}"; do
        namespace=${ENV_NAMESPACES[$env]}
        nodeport=${ENV_NODEPORTS[$env]}
        
        log_info "Creating service for environment: $env (NodePort: $nodeport)"
        
        # Check if service already exists or if NodePort is already in use
        if kubectl get service fortinet-service -n "$namespace" >/dev/null 2>&1; then
            log_warning "Service already exists in $namespace namespace, skipping creation"
            continue
        fi
        
        # Check if NodePort is already allocated
        if kubectl get svc -A -o jsonpath='{.items[*].spec.ports[*].nodePort}' | grep -q "$nodeport"; then
            log_warning "NodePort $nodeport already in use, skipping service creation for $env"
            continue
        fi
        
        cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: fortinet-service
  namespace: $namespace
  labels:
    app: fortinet
    environment: $env
spec:
  selector:
    app: fortinet
  ports:
  - port: 80
    targetPort: 7777
    nodePort: $nodeport
    protocol: TCP
    name: http
  type: NodePort
EOF
        
        log_success "Service created for $env environment (NodePort: $nodeport)"
    done
}

# 함수: RBAC 설정
setup_rbac() {
    log_info "Setting up RBAC for multi-environment..."
    
    # ServiceAccount 생성
    for env in "${!ENV_NAMESPACES[@]}"; do
        namespace=${ENV_NAMESPACES[$env]}
        
        kubectl create serviceaccount fortinet-sa --namespace="$namespace" --dry-run=client -o yaml | kubectl apply -f -
        
        # Role 생성
        cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: $namespace
  name: fortinet-role
rules:
- apiGroups: [""]
  resources: ["pods", "services", "configmaps", "secrets"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["apps"]
  resources: ["deployments", "replicasets"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
EOF
        
        # RoleBinding 생성
        cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: fortinet-rolebinding
  namespace: $namespace
subjects:
- kind: ServiceAccount
  name: fortinet-sa
  namespace: $namespace
roleRef:
  kind: Role
  name: fortinet-role
  apiGroup: rbac.authorization.k8s.io
EOF
        
        log_success "RBAC setup completed for $env environment"
    done
}

# 함수: 네트워크 정책 설정 (선택사항)
setup_network_policies() {
    if [ "${SETUP_NETWORK_POLICIES:-false}" = "true" ]; then
        log_info "Setting up network policies..."
        
        for env in "${!ENV_NAMESPACES[@]}"; do
            namespace=${ENV_NAMESPACES[$env]}
            
            cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: fortinet-network-policy
  namespace: $namespace
spec:
  podSelector:
    matchLabels:
      app: fortinet
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: argocd
    - namespaceSelector:
        matchLabels:
          name: nginx-ingress
    ports:
    - protocol: TCP
      port: 7777
  egress:
  - {} # Allow all outbound traffic
EOF
            
            log_success "Network policy created for $env environment"
        done
    else
        log_info "Network policies setup skipped (set SETUP_NETWORK_POLICIES=true to enable)"
    fi
}

# 함수: 상태 확인
check_status() {
    log_info "Checking deployment status..."
    
    echo -e "\n📊 Namespace Status:"
    kubectl get namespaces -l managed-by=fortinet-cicd
    
    echo -e "\n🔐 Registry Secrets:"
    for env in "${!ENV_NAMESPACES[@]}"; do
        namespace=${ENV_NAMESPACES[$env]}
        echo "  $env ($namespace): $(kubectl get secret registry-credentials -n "$namespace" --no-headers 2>/dev/null | wc -l) secret(s)"
    done
    
    echo -e "\n📱 ArgoCD Applications:"
    kubectl get applications -n argocd -l app.kubernetes.io/instance=fortinet 2>/dev/null || echo "  No applications found (ArgoCD may not be installed)"
    
    echo -e "\n🌐 Services:"
    for env in "${!ENV_NAMESPACES[@]}"; do
        namespace=${ENV_NAMESPACES[$env]}
        nodeport=${ENV_NODEPORTS[$env]}
        echo "  $env: http://192.168.50.110:$nodeport"
    done
    
    echo -e "\n📋 ConfigMaps:"
    for env in "${!ENV_NAMESPACES[@]}"; do
        namespace=${ENV_NAMESPACES[$env]}
        echo "  $env ($namespace): $(kubectl get configmap fortinet-config -n "$namespace" --no-headers 2>/dev/null | wc -l) configmap(s)"
    done
}

# 메인 실행 함수
main() {
    log_info "🚀 Setting up multi-environment deployment for Fortinet"
    log_info "Environments: ${!ENV_NAMESPACES[*]}"
    
    # 단계별 실행
    create_namespaces
    create_registry_secrets
    create_configmaps
    create_services
    setup_rbac
    setup_network_policies
    deploy_argocd_applications
    
    log_success "🎉 Multi-environment setup completed successfully!"
    
    # 상태 확인
    check_status
    
    echo -e "\n🔗 Quick Access URLs:"
    echo "  📈 ArgoCD: https://argo.jclee.me"
    echo "  🐳 Registry: https://registry.jclee.me"
    echo "  📊 Charts: https://charts.jclee.me"
    echo ""
    echo "🚀 Environment URLs:"
    echo "  Production: https://fortinet.jclee.me (NodePort: 30777)"
    echo "  Staging: https://fortinet-staging.jclee.me (NodePort: 30779)"
    echo "  Development: https://fortinet-development.jclee.me (NodePort: 30778)"
    echo ""
    log_info "Setup complete! You can now deploy to any environment using:"
    echo "  GitHub Actions: Push to master/main (production) or develop (development)"
    echo "  Manual Deploy: gh workflow run deploy-manual.yml"
}

# 스크립트 실행
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi