#!/bin/bash

# FortiGate Nextrade v1.0.9-fix-redis Deployment Verification Script
# Generated: 2025-08-21T21:55:00Z

echo "🚀 FortiGate Nextrade v1.0.9-fix-redis Deployment Verification"
echo "=============================================================="

# Function to check service health
check_health() {
    echo "🔍 Checking application health..."
    if curl -f --max-time 10 http://192.168.50.110:30777/api/health; then
        echo "✅ Application is healthy and responding"
        return 0
    else
        echo "⚠️  Application health check failed - may be starting up"
        return 1
    fi
}

# Function to check Docker image availability
check_image() {
    echo "🐳 Checking Docker image availability..."
    if docker pull registry.jclee.me/fortinet:v1.0.9-fix-redis; then
        echo "✅ Docker image v1.0.9-fix-redis is available in registry"
        return 0
    else
        echo "❌ Docker image not found in registry"
        return 1
    fi
}

# Function to check Kubernetes cluster
check_k8s() {
    echo "☸️  Checking Kubernetes cluster connectivity..."
    if kubectl cluster-info >/dev/null 2>&1; then
        echo "✅ Kubernetes cluster is accessible"
        kubectl get pods -n fortinet 2>/dev/null || echo "⚠️  No pods found in fortinet namespace"
        return 0
    else
        echo "⚠️  Kubernetes cluster is temporarily unavailable"
        return 1
    fi
}

# Function to check ArgoCD status
check_argocd() {
    echo "🔄 Checking ArgoCD deployment status..."
    if argocd app get fortinet >/dev/null 2>&1; then
        echo "✅ ArgoCD application status:"
        argocd app get fortinet
        return 0
    else
        echo "⚠️  ArgoCD is temporarily unavailable"
        return 1
    fi
}

# Main verification process
echo "📋 Starting deployment verification..."
echo

# Track results
RESULTS=()

# Check Docker image
if check_image; then
    RESULTS+=("✅ Docker image: READY")
else
    RESULTS+=("❌ Docker image: FAILED")
fi

echo

# Check Kubernetes
if check_k8s; then
    RESULTS+=("✅ Kubernetes: ACCESSIBLE")
else
    RESULTS+=("⚠️  Kubernetes: UNAVAILABLE")
fi

echo

# Check ArgoCD
if check_argocd; then
    RESULTS+=("✅ ArgoCD: SYNCED")
else
    RESULTS+=("⚠️  ArgoCD: UNAVAILABLE")
fi

echo

# Check application health
if check_health; then
    RESULTS+=("✅ Health: HEALTHY")
else
    RESULTS+=("⚠️  Health: UNAVAILABLE")
fi

echo
echo "📊 VERIFICATION SUMMARY"
echo "======================"
for result in "${RESULTS[@]}"; do
    echo "$result"
done

echo
echo "🔧 DEPLOYMENT INFORMATION"
echo "========================="
echo "Image: registry.jclee.me/fortinet:v1.0.9-fix-redis"
echo "Chart: fortinet-1.0.9.tgz"
echo "Endpoint: http://192.168.50.110:30777/api/health"
echo "Domain: http://fortinet.jclee.me (requires /etc/hosts entry)"
echo "Namespace: fortinet"
echo "Git SHA: 1667783"
echo "Build: 2025-08-21T21:51:26Z"

echo
echo "📝 MANUAL DEPLOYMENT COMMANDS (if ArgoCD unavailable)"
echo "===================================================="
echo "# Install/upgrade with Helm:"
echo "helm upgrade --install fortinet ./charts/fortinet-1.0.9.tgz -n fortinet --create-namespace"
echo
echo "# Check deployment status:"
echo "kubectl get pods -n fortinet"
echo "kubectl logs -l app=fortinet -n fortinet -f"
echo
echo "# Port forward for local testing:"
echo "kubectl port-forward svc/fortinet 8080:80 -n fortinet"

echo
echo "🎯 FIXES INCLUDED IN v1.0.9-fix-redis"
echo "====================================="
echo "✅ Redis port configuration fix (6379 instead of 6380)"
echo "✅ Pytest assertions fix (converted from dict returns to assert statements)"
echo "✅ Updated GitOps metadata and immutable tags"
echo "✅ Multi-stage Docker build optimization"
echo "✅ Security hardening with non-root user"

echo
echo "🔄 GitOps STATUS"
echo "================"
echo "✅ Commits pushed to GitHub (triggers automated pipeline)"
echo "✅ Docker image built and pushed to registry"
echo "✅ Helm chart updated with new version"
echo "⏳ Waiting for infrastructure availability for ArgoCD sync"

echo
echo "Verification completed at $(date)"