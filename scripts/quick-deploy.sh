#!/bin/bash

# =============================================================================
# Quick Deploy Script - FortiGate Nextrade
# Fixes ArgoCD issues and deploys with immutable tag
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== FortiGate Nextrade Quick Deploy ===${NC}"

# Get current commit info
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
GIT_SHA=$(git rev-parse --short HEAD)
IMMUTABLE_TAG="${GIT_BRANCH}-${GIT_SHA}"
BUILD_TIMESTAMP=$(date -u +"%Y%m%d-%H%M%S")

echo -e "${YELLOW}Current branch: ${GIT_BRANCH}${NC}"
echo -e "${YELLOW}Current commit: ${GIT_SHA}${NC}"
echo -e "${YELLOW}Immutable tag: ${IMMUTABLE_TAG}${NC}"

# Step 1: Build image with proper build args
echo -e "\n${BLUE}Step 1: Building Docker image...${NC}"
docker build -f Dockerfile.production \
  --build-arg BUILD_DATE="${BUILD_TIMESTAMP}" \
  --build-arg BUILD_TIMESTAMP="${BUILD_TIMESTAMP}" \
  --build-arg GIT_COMMIT="$(git rev-parse HEAD)" \
  --build-arg GIT_SHA="${GIT_SHA}" \
  --build-arg GIT_BRANCH="${GIT_BRANCH}" \
  --build-arg VERSION="manual-${BUILD_TIMESTAMP}" \
  --build-arg IMMUTABLE_TAG="${IMMUTABLE_TAG}" \
  --build-arg REGISTRY_URL="registry.jclee.me" \
  -t "registry.jclee.me/fortinet:${IMMUTABLE_TAG}" \
  -t "registry.jclee.me/fortinet:latest" \
  .

echo -e "${GREEN}✅ Image built successfully${NC}"

# Step 2: Push to registry
echo -e "\n${BLUE}Step 2: Pushing to registry...${NC}"
docker push "registry.jclee.me/fortinet:${IMMUTABLE_TAG}"
docker push "registry.jclee.me/fortinet:latest"

echo -e "${GREEN}✅ Image pushed successfully${NC}"

# Step 3: Deploy with Helm using immutable tag
echo -e "\n${BLUE}Step 3: Deploying with Helm...${NC}"

# Create namespace if it doesn't exist
kubectl create namespace fortinet --dry-run=client -o yaml | kubectl apply -f -

# Create image pull secret (if needed)
kubectl create secret docker-registry harbor-registry \
  --docker-server=registry.jclee.me \
  --docker-username=admin \
  --docker-password="${HARBOR_PASSWORD:-}" \
  --namespace=fortinet \
  --dry-run=client -o yaml | kubectl apply -f - || echo "Secret creation skipped"

# Deploy with Helm
helm upgrade --install fortinet ./charts/fortinet \
  --namespace fortinet \
  --set image.tag="${IMMUTABLE_TAG}" \
  --set image.pullPolicy="IfNotPresent" \
  --set monitoring.serviceMonitor.enabled=false \
  --timeout=5m \
  --wait

echo -e "${GREEN}✅ Helm deployment completed${NC}"

# Step 4: Verify deployment
echo -e "\n${BLUE}Step 4: Verifying deployment...${NC}"

# Wait for pods to be ready
echo "Waiting for pods to be ready..."
kubectl wait --for=condition=ready pod -l app=fortinet -n fortinet --timeout=300s

# Get pod status
echo -e "\n${YELLOW}Pod Status:${NC}"
kubectl get pods -n fortinet -l app=fortinet

# Test health endpoint
echo -e "\n${YELLOW}Testing health endpoint...${NC}"
sleep 10

HEALTH_URL="http://192.168.50.110:30777/api/health"
if curl -s --max-time 10 "${HEALTH_URL}" | jq -e '.status == "healthy"' > /dev/null; then
  echo -e "${GREEN}✅ Health check passed!${NC}"
  
  # Show GitOps metadata
  echo -e "\n${YELLOW}GitOps Metadata:${NC}"
  curl -s "${HEALTH_URL}" | jq '.build_info'
  
  # Verify immutable tag
  DEPLOYED_TAG=$(curl -s "${HEALTH_URL}" | jq -r '.build_info.immutable_tag // "unknown"')
  if [ "${DEPLOYED_TAG}" = "${IMMUTABLE_TAG}" ]; then
    echo -e "${GREEN}✅ Immutable tag verification passed: ${DEPLOYED_TAG}${NC}"
  else
    echo -e "${RED}❌ Tag mismatch - Expected: ${IMMUTABLE_TAG}, Got: ${DEPLOYED_TAG}${NC}"
  fi
  
else
  echo -e "${RED}❌ Health check failed${NC}"
  echo "Pod logs:"
  kubectl logs -l app=fortinet -n fortinet --tail=50
  exit 1
fi

# Step 5: ArgoCD sync (optional)
if command -v argocd &> /dev/null; then
  echo -e "\n${BLUE}Step 5: Syncing ArgoCD...${NC}"
  argocd app sync fortinet --prune || echo "ArgoCD sync failed or app doesn't exist"
else
  echo -e "\n${YELLOW}ArgoCD CLI not found, skipping sync${NC}"
fi

echo -e "\n${GREEN}🎉 Deployment completed successfully!${NC}"
echo -e "${GREEN}📊 Health: ${HEALTH_URL}${NC}"
echo -e "${GREEN}🌐 App: http://192.168.50.110:30777/${NC}"
echo -e "${GREEN}🏷️  Tag: ${IMMUTABLE_TAG}${NC}"