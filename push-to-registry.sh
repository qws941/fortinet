#!/bin/bash
# =============================================================================
# Push Images to registry.jclee.me
# =============================================================================

set -e

echo "🚀 Starting image push to registry.jclee.me..."
echo "================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Registry configuration
REGISTRY="registry.jclee.me"
REGISTRY_USER="admin"
REGISTRY_PASS="bingogo1"

# Login to registry
echo -e "${YELLOW}🔐 Logging into registry...${NC}"
echo "$REGISTRY_PASS" | docker login $REGISTRY -u $REGISTRY_USER --password-stdin

# Build and push Redis
echo -e "\n${GREEN}📦 Building and pushing Redis image...${NC}"
docker build -f Dockerfile.redis -t $REGISTRY/fortinet-redis:latest .
docker push $REGISTRY/fortinet-redis:latest
echo -e "${GREEN}✅ Redis image pushed successfully${NC}"

# Build and push PostgreSQL
echo -e "\n${GREEN}📦 Building and pushing PostgreSQL image...${NC}"
docker build -f Dockerfile.postgresql -t $REGISTRY/fortinet-postgresql:latest .
docker push $REGISTRY/fortinet-postgresql:latest
echo -e "${GREEN}✅ PostgreSQL image pushed successfully${NC}"

# Build and push Fortinet App
echo -e "\n${GREEN}📦 Building and pushing Fortinet application image...${NC}"
docker build -f Dockerfile.fortinet -t $REGISTRY/fortinet:latest .
docker push $REGISTRY/fortinet:latest
echo -e "${GREEN}✅ Fortinet application image pushed successfully${NC}"

# List pushed images
echo -e "\n${YELLOW}📋 Pushed images:${NC}"
echo "  - $REGISTRY/fortinet-redis:latest"
echo "  - $REGISTRY/fortinet-postgresql:latest"
echo "  - $REGISTRY/fortinet:latest"

echo -e "\n${GREEN}🎉 All images successfully pushed to registry.jclee.me!${NC}"
echo "================================================"