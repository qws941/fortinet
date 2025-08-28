#!/bin/bash
# Monitor GitOps Compliance Status
# This script monitors the deployment and verifies GitOps compliance

set -e

echo "🔍 GitOps Compliance Monitor"
echo "============================"

HEALTH_URL="http://192.168.50.110:30777/api/health"
MAX_WAIT=300  # 5 minutes
WAIT_INTERVAL=10

echo "📋 Monitoring GitOps deployment compliance..."
echo "Health endpoint: ${HEALTH_URL}"
echo ""

# Function to check GitOps compliance
check_gitops_compliance() {
    local response=$(curl -s --max-time 10 "${HEALTH_URL}" 2>/dev/null)
    
    if [ $? -eq 0 ] && [ -n "$response" ]; then
        local status=$(echo "$response" | jq -r '.status // "unknown"')
        local gitops_status=$(echo "$response" | jq -r '.gitops_status // "unknown"')
        local immutable_tag=$(echo "$response" | jq -r '.build_info.immutable_tag // "unknown"')
        local git_sha=$(echo "$response" | jq -r '.build_info.git_sha // "unknown"')
        local build_timestamp=$(echo "$response" | jq -r '.build_info.build_timestamp // "unknown"')
        
        echo "🏥 Health Status: ${status}"
        echo "🔧 GitOps Status: ${gitops_status}"
        echo "🏷️  Immutable Tag: ${immutable_tag}"
        echo "📝 Git SHA: ${git_sha}"
        echo "⏰ Build Timestamp: ${build_timestamp}"
        
        if [ "$gitops_status" = "compliant" ]; then
            echo ""
            echo "✅ SUCCESS: GitOps compliance achieved!"
            echo "🎉 All GitOps principles are being followed:"
            echo "   - Declarative: Kubernetes manifests"
            echo "   - Git Source: GitHub repository"
            echo "   - Pull-based: ArgoCD deployment"
            echo "   - Immutable: Immutable container tags"
            echo ""
            echo "📊 Full GitOps Metadata:"
            echo "$response" | jq '.build_info'
            return 0
        elif [ "$gitops_status" = "non-compliant" ]; then
            echo "❌ GitOps non-compliant - checking metadata..."
            return 1
        else
            echo "⚠️  Unknown GitOps status - service may be starting..."
            return 2
        fi
    else
        echo "❌ Failed to connect to health endpoint"
        return 3
    fi
}

# Initial status check
echo "🔄 Initial GitOps compliance check..."
if check_gitops_compliance; then
    exit 0
fi

echo ""
echo "⏳ Waiting for GitOps deployment to complete..."
echo "   This may take a few minutes for the new image to be pulled and deployed"

# Wait loop
elapsed=0
while [ $elapsed -lt $MAX_WAIT ]; do
    sleep $WAIT_INTERVAL
    elapsed=$((elapsed + WAIT_INTERVAL))
    
    echo ""
    echo "🔄 Checking compliance... (${elapsed}s/${MAX_WAIT}s)"
    
    if check_gitops_compliance; then
        echo ""
        echo "🚀 GitOps Deployment Complete!"
        echo "⏱️  Total time: ${elapsed} seconds"
        exit 0
    fi
    
    if [ $elapsed -lt $MAX_WAIT ]; then
        echo "   Retrying in ${WAIT_INTERVAL} seconds..."
    fi
done

echo ""
echo "⏰ Timeout reached after ${MAX_WAIT} seconds"
echo "❌ GitOps compliance not achieved within timeout"
echo ""
echo "🔍 Final status check:"
check_gitops_compliance || true

echo ""
echo "💡 Troubleshooting tips:"
echo "   - Check if the new image is being pulled: kubectl get pods -n fortinet"
echo "   - Check deployment status: kubectl rollout status deployment/fortinet -n fortinet"
echo "   - Check ArgoCD sync: argocd app get fortinet"
echo "   - Manual health check: curl -s ${HEALTH_URL} | jq '.'"

exit 1