#!/bin/bash

echo "Setting up ArgoCD Image Updater for GitOps automation..."

# Apply the Image Updater ConfigMap
echo "Applying Image Updater configuration..."
kubectl apply -f argocd/image-updater-configmap.yaml

# Update ArgoCD application
echo "Updating ArgoCD application with Image Updater annotations..."
kubectl apply -f argocd/applications/fortinet.yaml

# Restart Image Updater to pick up new config
echo "Restarting ArgoCD Image Updater..."
kubectl -n argocd rollout restart deployment argocd-image-updater

# Check status
echo "Checking Image Updater status..."
kubectl -n argocd get pods -l app.kubernetes.io/name=argocd-image-updater

echo ""
echo "ArgoCD Image Updater configured!"
echo "The updater will now automatically:"
echo "1. Check registry.jclee.me for new fortinet images"
echo "2. Update the application when new tags matching the pattern are found"
echo "3. Tags allowed: master, main, latest, v1.0.0, etc."
echo ""
echo "Monitor logs with:"
echo "kubectl -n argocd logs -l app.kubernetes.io/name=argocd-image-updater -f"