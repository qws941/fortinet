#!/bin/bash

echo "🚀 Applying Flask Application ConfigMap Update..."
echo "================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check command status
check_status() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ $1${NC}"
    else
        echo -e "${RED}✗ $1${NC}"
        exit 1
    fi
}

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}Error: kubectl is not installed${NC}"
    exit 1
fi

# Check if we can connect to the cluster
echo "1️⃣ Checking Kubernetes cluster connection..."
kubectl cluster-info &> /dev/null
check_status "Connected to Kubernetes cluster"

# Apply the complete Flask application ConfigMap
echo -e "\n2️⃣ Applying new Flask application ConfigMap..."
kubectl apply -f k8s/manifests/fortinet-app-complete-configmap.yaml
check_status "ConfigMap 'fortinet-app-complete' created/updated"

# Apply all manifests using kustomize
echo -e "\n3️⃣ Applying all manifests with kustomize..."
kubectl apply -k k8s/manifests/
check_status "All manifests applied successfully"

# Restart the deployment to pick up the new ConfigMap
echo -e "\n4️⃣ Restarting deployment to use new ConfigMap..."
kubectl rollout restart deployment/fortinet-app -n fortinet
check_status "Deployment restart initiated"

# Wait for rollout to complete
echo -e "\n5️⃣ Waiting for rollout to complete..."
kubectl rollout status deployment/fortinet-app -n fortinet --timeout=300s
check_status "Rollout completed successfully"

# Check pod status
echo -e "\n6️⃣ Checking pod status..."
kubectl get pods -n fortinet -l app=fortinet

# Get the service endpoint
echo -e "\n7️⃣ Service Information:"
kubectl get svc -n fortinet fortinet-service

# Test the application
echo -e "\n8️⃣ Testing application health endpoint..."
POD_NAME=$(kubectl get pods -n fortinet -l app=fortinet -o jsonpath="{.items[0].metadata.name}")
if [ ! -z "$POD_NAME" ]; then
    echo "Testing via port-forward to pod: $POD_NAME"
    
    # Start port-forward in background
    kubectl port-forward -n fortinet pod/$POD_NAME 8888:7777 &
    PF_PID=$!
    
    # Wait a moment for port-forward to establish
    sleep 3
    
    # Test the health endpoint
    echo -e "\nHealth check response:"
    curl -s http://localhost:8888/api/health | jq . || echo "Failed to get health response"
    
    # Kill the port-forward
    kill $PF_PID 2>/dev/null
fi

echo -e "\n✅ ${GREEN}Flask application ConfigMap update completed!${NC}"
echo -e "\n📌 Access the application:"
echo "   - NodePort: http://<node-ip>:30777"
echo "   - Via kubectl: kubectl port-forward -n fortinet svc/fortinet-service 7777:7777"
echo "   - Production: https://fortinet.jclee.me"

echo -e "\n💡 To view logs:"
echo "   kubectl logs -n fortinet -l app=fortinet -f"

echo -e "\n🔍 To check ConfigMap content:"
echo "   kubectl describe configmap fortinet-app-complete -n fortinet"