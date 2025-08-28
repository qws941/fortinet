#!/bin/bash
# K8s deployment script for FortiGate Nextrade

set -e

# Configuration
NAMESPACE="fortinet"
REGISTRY="registry.jclee.me"
IMAGE_NAME="fortinet"
KUBECONFIG_PATH="${KUBECONFIG:-$HOME/.kube/config}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl not found. Please install kubectl first."
        exit 1
    fi
    
    # Check kustomize
    if ! command -v kustomize &> /dev/null; then
        log_warn "kustomize not found. Using kubectl's built-in kustomize."
    fi
    
    # Check kubeconfig
    if [ ! -f "$KUBECONFIG_PATH" ]; then
        log_error "Kubeconfig not found at $KUBECONFIG_PATH"
        exit 1
    fi
    
    # Test cluster connection
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    log_info "Prerequisites check passed ✅"
}

# Create namespace if not exists
create_namespace() {
    if ! kubectl get namespace $NAMESPACE &> /dev/null; then
        log_info "Creating namespace $NAMESPACE..."
        kubectl create namespace $NAMESPACE
    else
        log_info "Namespace $NAMESPACE already exists"
    fi
}

# Create image pull secret
create_image_pull_secret() {
    log_info "Creating image pull secret..."
    
    # Check if secret already exists
    if kubectl get secret regcred -n $NAMESPACE &> /dev/null; then
        log_info "Image pull secret already exists"
        return
    fi
    
    # Prompt for credentials if not in environment
    if [ -z "$DOCKER_USERNAME" ] || [ -z "$DOCKER_PASSWORD" ]; then
        read -p "Docker Registry Username: " DOCKER_USERNAME
        read -sp "Docker Registry Password: " DOCKER_PASSWORD
        echo
    fi
    
    kubectl create secret docker-registry regcred \
        --docker-server=$REGISTRY \
        --docker-username=$DOCKER_USERNAME \
        --docker-password=$DOCKER_PASSWORD \
        --docker-email=admin@jclee.me \
        -n $NAMESPACE
    
    log_info "Image pull secret created"
}

# Deploy with kustomize
deploy_application() {
    log_info "Deploying application..."
    
    cd k8s
    
    # Set build metadata
    export BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    export GIT_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
    export GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
    export VERSION="${VERSION:-latest}"
    
    # Update image tag if provided
    if [ -n "$IMAGE_TAG" ]; then
        log_info "Using image tag: $IMAGE_TAG"
        if command -v kustomize &> /dev/null; then
            kustomize edit set image $REGISTRY/$IMAGE_NAME:$IMAGE_TAG
        else
            # Fallback to sed
            sed -i "s|newTag: .*|newTag: $IMAGE_TAG|" kustomization.yaml
        fi
    fi
    
    # Dry run first
    log_info "Running dry-run..."
    kubectl apply -k . --dry-run=client
    
    # Apply manifests
    log_info "Applying manifests..."
    kubectl apply -k .
    
    # Wait for rollout
    log_info "Waiting for deployment rollout..."
    kubectl rollout status deployment/fortinet -n $NAMESPACE --timeout=300s
    
    log_info "Deployment completed ✅"
}

# Verify deployment
verify_deployment() {
    log_info "Verifying deployment..."
    
    # Check pods
    echo "📦 Pods:"
    kubectl get pods -n $NAMESPACE -l app=fortinet
    echo
    
    # Check services
    echo "🔌 Services:"
    kubectl get svc -n $NAMESPACE
    echo
    
    # Check ingress
    echo "🌐 Ingress:"
    kubectl get ingress -n $NAMESPACE
    echo
    
    # Check HPA
    echo "📈 HPA:"
    kubectl get hpa -n $NAMESPACE
    echo
    
    # Check PVC
    echo "💾 Storage:"
    kubectl get pvc -n $NAMESPACE
    echo
}

# Health check
health_check() {
    log_info "Running health check..."
    
    # Get a pod name
    POD_NAME=$(kubectl get pods -n $NAMESPACE -l app=fortinet -o jsonpath='{.items[0].metadata.name}')
    
    if [ -z "$POD_NAME" ]; then
        log_error "No pods found"
        return 1
    fi
    
    # Internal health check
    log_info "Checking internal health endpoint..."
    kubectl exec -n $NAMESPACE $POD_NAME -- curl -s http://localhost:7777/api/health || log_warn "Internal health check failed"
    
    # External health check
    if [ -n "$EXTERNAL_URL" ]; then
        log_info "Checking external health endpoint at $EXTERNAL_URL..."
        curl -s $EXTERNAL_URL/api/health || log_warn "External health check failed"
    fi
}

# Main deployment flow
main() {
    echo "🚀 FortiGate Nextrade K8s Deployment"
    echo "===================================="
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --image-tag)
                IMAGE_TAG="$2"
                shift 2
                ;;
            --external-url)
                EXTERNAL_URL="$2"
                shift 2
                ;;
            --skip-secret)
                SKIP_SECRET=true
                shift
                ;;
            --help)
                echo "Usage: $0 [options]"
                echo "Options:"
                echo "  --image-tag TAG      Docker image tag to deploy"
                echo "  --external-url URL   External URL for health check"
                echo "  --skip-secret        Skip image pull secret creation"
                echo "  --help               Show this help message"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Execute deployment steps
    check_prerequisites
    create_namespace
    
    if [ "$SKIP_SECRET" != "true" ]; then
        create_image_pull_secret
    fi
    
    deploy_application
    verify_deployment
    health_check
    
    log_info "🎉 Deployment completed successfully!"
    echo
    echo "📊 Summary:"
    echo "- Namespace: $NAMESPACE"
    echo "- Image: $REGISTRY/$IMAGE_NAME:${IMAGE_TAG:-latest}"
    echo "- Cluster: $(kubectl config current-context)"
    echo
    echo "Next steps:"
    echo "- Check logs: kubectl logs -n $NAMESPACE -l app=fortinet -f"
    echo "- Port forward: kubectl port-forward -n $NAMESPACE svc/fortinet 7777:7777"
    echo "- Scale: kubectl scale deployment/fortinet -n $NAMESPACE --replicas=5"
}

# Run main function
main "$@"