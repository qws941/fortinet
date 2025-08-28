#!/bin/bash
# K8s manifest application script

set -e

NAMESPACE=${NAMESPACE:-fortinet}

echo "🚀 Applying Fortinet K8s manifests..."
echo "   Namespace: $NAMESPACE"

# Apply manifests
echo "📦 Applying manifests..."
kubectl apply -k k8s/manifests/

echo "✅ Application complete!"
echo ""
echo "🔍 Check deployment status:"
echo "   kubectl get pods -n $NAMESPACE"
echo "   kubectl get svc -n $NAMESPACE"
echo "   kubectl get ingress -n $NAMESPACE"