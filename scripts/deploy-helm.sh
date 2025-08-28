#!/bin/bash

# Deploy FortiGate Nextrade using Helm Chart
# This script deploys the application from ChartMuseum

set -e

# Configuration
NAMESPACE="fortinet"
RELEASE_NAME="fortinet-nextrade"
CHART_REPO="chartmuseum"
CHART_NAME="fortinet-nextrade"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Helm is installed
check_helm() {
    if ! command -v helm &> /dev/null; then
        print_error "Helm is not installed. Please install Helm first."
        exit 1
    fi
    print_success "Helm is installed: $(helm version --short)"
}

# Check if kubectl is configured
check_kubectl() {
    if ! kubectl cluster-info &> /dev/null; then
        print_error "kubectl is not configured or cluster is not accessible."
        exit 1
    fi
    print_success "Kubernetes cluster is accessible"
}

# Add ChartMuseum repository
setup_chart_repo() {
    print_status "Setting up ChartMuseum repository..."
    
    # Check if repo already exists
    if helm repo list | grep -q "^${CHART_REPO}"; then
        print_status "ChartMuseum repository already exists, updating..."
        helm repo update ${CHART_REPO}
    else
        print_status "Adding ChartMuseum repository..."
        helm repo add ${CHART_REPO} https://charts.jclee.me --username admin --password bingogo1
        helm repo update
    fi
    
    # Verify chart is available
    if helm search repo ${CHART_REPO}/${CHART_NAME} | grep -q ${CHART_NAME}; then
        print_success "FortiGate Nextrade chart found in repository"
    else
        print_error "FortiGate Nextrade chart not found in repository"
        exit 1
    fi
}

# Deploy the application
deploy_application() {
    print_status "Deploying FortiGate Nextrade..."
    
    # Create namespace if it doesn't exist
    kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
    
    # Check if release already exists
    if helm list -n ${NAMESPACE} | grep -q ${RELEASE_NAME}; then
        print_warning "Release ${RELEASE_NAME} already exists. Upgrading..."
        helm upgrade ${RELEASE_NAME} ${CHART_REPO}/${CHART_NAME} \
            --namespace ${NAMESPACE} \
            --wait \
            --timeout 10m
        print_success "Application upgraded successfully"
    else
        print_status "Installing new release..."
        helm install ${RELEASE_NAME} ${CHART_REPO}/${CHART_NAME} \
            --namespace ${NAMESPACE} \
            --create-namespace \
            --wait \
            --timeout 10m
        print_success "Application installed successfully"
    fi
}

# Verify deployment
verify_deployment() {
    print_status "Verifying deployment..."
    
    # Wait for pods to be ready
    print_status "Waiting for pods to be ready..."
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=fortinet-nextrade -n ${NAMESPACE} --timeout=300s
    
    # Check deployment status
    kubectl get deployments -n ${NAMESPACE}
    kubectl get pods -n ${NAMESPACE}
    kubectl get services -n ${NAMESPACE}
    
    # Test health endpoint
    print_status "Testing application health..."
    kubectl port-forward svc/${RELEASE_NAME} 8080:80 -n ${NAMESPACE} &
    PORT_FORWARD_PID=$!
    
    sleep 5
    
    if curl -s http://localhost:8080/api/health | grep -q "status"; then
        print_success "Application health check passed"
    else
        print_warning "Application health check failed, but deployment is complete"
    fi
    
    # Clean up port forward
    kill $PORT_FORWARD_PID 2>/dev/null || true
}

# Show access information
show_access_info() {
    print_success "Deployment completed successfully!"
    echo
    echo "Access Information:"
    echo "=================="
    
    # NodePort access
    NODEPORT=$(kubectl get svc ${RELEASE_NAME}-nodeport -n ${NAMESPACE} -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "N/A")
    if [ "$NODEPORT" != "N/A" ]; then
        echo "NodePort Access: http://<node-ip>:${NODEPORT}"
    fi
    
    # Ingress access
    INGRESS_HOST=$(kubectl get ingress ${RELEASE_NAME} -n ${NAMESPACE} -o jsonpath='{.spec.rules[0].host}' 2>/dev/null || echo "N/A")
    if [ "$INGRESS_HOST" != "N/A" ]; then
        echo "Ingress Access: https://${INGRESS_HOST}"
    fi
    
    # Port forward access
    echo "Port Forward: kubectl port-forward svc/${RELEASE_NAME} 8080:80 -n ${NAMESPACE}"
    echo "Then access: http://localhost:8080"
    
    echo
    echo "Useful Commands:"
    echo "==============="
    echo "View pods: kubectl get pods -n ${NAMESPACE}"
    echo "View logs: kubectl logs -f deployment/${RELEASE_NAME} -n ${NAMESPACE}"
    echo "Delete app: helm uninstall ${RELEASE_NAME} -n ${NAMESPACE}"
}

# Main execution
main() {
    print_status "Starting FortiGate Nextrade Helm deployment..."
    
    check_helm
    check_kubectl
    setup_chart_repo
    deploy_application
    verify_deployment
    show_access_info
    
    print_success "Deployment script completed!"
}

# Parse command line arguments
case "${1:-}" in
    "--help"|"-h")
        echo "Usage: $0 [options]"
        echo "Options:"
        echo "  -h, --help     Show this help message"
        echo "  --dry-run      Perform a dry run without actual deployment"
        echo "  --uninstall    Uninstall the application"
        echo
        echo "Environment Variables:"
        echo "  NAMESPACE      Kubernetes namespace (default: fortinet)"
        echo "  RELEASE_NAME   Helm release name (default: fortinet-nextrade)"
        exit 0
        ;;
    "--dry-run")
        print_status "Performing dry run..."
        helm template ${RELEASE_NAME} ${CHART_REPO}/${CHART_NAME} --namespace ${NAMESPACE}
        exit 0
        ;;
    "--uninstall")
        print_status "Uninstalling FortiGate Nextrade..."
        helm uninstall ${RELEASE_NAME} -n ${NAMESPACE}
        print_success "Application uninstalled"
        exit 0
        ;;
esac

# Run main function
main "$@"