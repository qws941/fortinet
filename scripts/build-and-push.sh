#!/bin/bash

# =============================================================================
# FortiGate Docker Build and Push Script with Version Verification
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
REGISTRY="registry.jclee.me"
PROJECT="fortinet"
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
VCS_REF=$(git rev-parse --short HEAD 2>/dev/null || echo "no-git")
VERSION=${VERSION:-"v1.0.0-$(date +%Y%m%d-%H%M%S)"}

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}FortiGate Docker Build & Push${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "Registry: ${YELLOW}$REGISTRY${NC}"
echo -e "Project:  ${YELLOW}$PROJECT${NC}"
echo -e "Version:  ${YELLOW}$VERSION${NC}"
echo -e "Git Ref:  ${YELLOW}$VCS_REF${NC}"
echo -e "Date:     ${YELLOW}$BUILD_DATE${NC}"
echo ""

# Function to build and push image
build_and_push() {
    local SERVICE=$1
    local DOCKERFILE=$2
    local IMAGE_NAME="$REGISTRY/$PROJECT/$SERVICE"
    
    echo -e "${GREEN}Building $SERVICE...${NC}"
    
    # Build with version labels
    docker build \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VCS_REF="$VCS_REF" \
        --build-arg VERSION="$VERSION" \
        -f "$DOCKERFILE" \
        -t "$SERVICE:latest" \
        -t "$SERVICE:$VERSION" \
        .
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Build successful${NC}"
    else
        echo -e "${RED}✗ Build failed${NC}"
        exit 1
    fi
    
    # Tag for registry
    docker tag "$SERVICE:latest" "$IMAGE_NAME:latest"
    docker tag "$SERVICE:$VERSION" "$IMAGE_NAME:$VERSION"
    
    # Push to registry
    echo -e "${GREEN}Pushing $SERVICE to registry...${NC}"
    docker push "$IMAGE_NAME:latest"
    docker push "$IMAGE_NAME:$VERSION"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Push successful${NC}"
    else
        echo -e "${RED}✗ Push failed${NC}"
        exit 1
    fi
    
    # Verify image in registry
    echo -e "${GREEN}Verifying $SERVICE in registry...${NC}"
    docker pull "$IMAGE_NAME:$VERSION" > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Verification successful${NC}"
        
        # Get image details
        echo -e "${YELLOW}Image Details:${NC}"
        docker inspect "$IMAGE_NAME:$VERSION" --format='
        Size: {{.Size}} bytes
        Created: {{.Created}}
        Architecture: {{.Architecture}}
        OS: {{.Os}}' | sed 's/^/  /'
        
        # Get labels
        echo -e "${YELLOW}Image Labels:${NC}"
        docker inspect "$IMAGE_NAME:$VERSION" --format='{{range $k, $v := .Config.Labels}}  {{$k}}: {{$v}}
{{end}}' | grep org.opencontainers | head -5
        
    else
        echo -e "${RED}✗ Verification failed${NC}"
        exit 1
    fi
    
    echo ""
}

# Build and push all services
echo -e "${GREEN}Starting build process...${NC}"
echo ""

# Main application
build_and_push "fortinet" "Dockerfile.fortinet"

# Redis service
build_and_push "fortinet-redis" "Dockerfile.redis"

# PostgreSQL service
build_and_push "fortinet-postgresql" "Dockerfile.postgresql"

# Summary
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Build Summary${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ All images built and pushed successfully${NC}"
echo ""
echo -e "${YELLOW}Images available at:${NC}"
echo -e "  • $REGISTRY/$PROJECT/fortinet:$VERSION"
echo -e "  • $REGISTRY/$PROJECT/fortinet-redis:$VERSION"
echo -e "  • $REGISTRY/$PROJECT/fortinet-postgresql:$VERSION"
echo ""
echo -e "${YELLOW}Latest tags:${NC}"
echo -e "  • $REGISTRY/$PROJECT/fortinet:latest"
echo -e "  • $REGISTRY/$PROJECT/fortinet-redis:latest"
echo -e "  • $REGISTRY/$PROJECT/fortinet-postgresql:latest"
echo ""

# Deployment verification
echo -e "${GREEN}Verifying deployment readiness...${NC}"

# Check if fortinet.jclee.me is accessible
if curl -f -s -o /dev/null -w "%{http_code}" https://fortinet.jclee.me/api/health | grep -q "200\|404"; then
    echo -e "${GREEN}✓ fortinet.jclee.me is accessible${NC}"
else
    echo -e "${YELLOW}⚠ fortinet.jclee.me is not accessible${NC}"
fi

# Create deployment manifest
cat > /tmp/fortinet-deployment-verify.yaml <<EOF
# Deployment verification for fortinet.jclee.me
apiVersion: v1
kind: ConfigMap
metadata:
  name: fortinet-version
  namespace: fortinet
data:
  version: "$VERSION"
  build_date: "$BUILD_DATE"
  git_ref: "$VCS_REF"
  images: |
    - $REGISTRY/$PROJECT/fortinet:$VERSION
    - $REGISTRY/$PROJECT/fortinet-redis:$VERSION
    - $REGISTRY/$PROJECT/fortinet-postgresql:$VERSION
EOF

echo -e "${GREEN}✓ Deployment manifest created at /tmp/fortinet-deployment-verify.yaml${NC}"
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Build and Push Complete!${NC}"
echo -e "${GREEN}========================================${NC}"