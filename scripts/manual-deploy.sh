#!/bin/bash
# Manual deployment script for FortiGate Nextrade
# Use this when GitHub Actions is not available

set -e

echo "🚀 FortiGate Nextrade Manual Deployment"
echo "======================================"
echo ""

# Configuration
REGISTRY="registry.jclee.me"
IMAGE_NAME="fortinet"
DOCKERFILE="Dockerfile.production"

# Get current git info
GIT_COMMIT=$(git rev-parse HEAD)
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)
VERSION="latest"

echo "📋 Deployment Information:"
echo "  - Registry: $REGISTRY"
echo "  - Image: $IMAGE_NAME"
echo "  - Branch: $GIT_BRANCH"
echo "  - Commit: $GIT_COMMIT"
echo "  - Build Date: $BUILD_DATE"
echo ""

# Check if we're on main/master branch
if [[ "$GIT_BRANCH" != "main" && "$GIT_BRANCH" != "master" ]]; then
    read -p "⚠️  Not on main/master branch. Continue? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Deployment cancelled"
        exit 1
    fi
fi

# Check Docker daemon
echo "🔍 Checking Docker..."
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running"
    exit 1
fi
echo "✅ Docker is running"

# Login to registry
echo ""
echo "🔐 Logging in to registry..."
if [ -z "$DOCKER_USERNAME" ] || [ -z "$DOCKER_PASSWORD" ]; then
    echo "Please provide Docker registry credentials:"
    read -p "Username: " DOCKER_USERNAME
    read -s -p "Password: " DOCKER_PASSWORD
    echo
fi

docker login $REGISTRY -u "$DOCKER_USERNAME" -p "$DOCKER_PASSWORD" || {
    echo "❌ Failed to login to registry"
    exit 1
}
echo "✅ Successfully logged in to $REGISTRY"

# Build image
echo ""
echo "🏗️  Building Docker image..."
docker build -f $DOCKERFILE \
    --build-arg BUILD_DATE="$BUILD_DATE" \
    --build-arg GIT_COMMIT="$GIT_COMMIT" \
    --build-arg GIT_BRANCH="$GIT_BRANCH" \
    --build-arg VERSION="$VERSION" \
    -t $REGISTRY/$IMAGE_NAME:latest \
    -t $REGISTRY/$IMAGE_NAME:$GIT_COMMIT \
    . || {
    echo "❌ Docker build failed"
    exit 1
}
echo "✅ Docker image built successfully"

# Push to registry
echo ""
echo "📤 Pushing to registry..."
docker push $REGISTRY/$IMAGE_NAME:latest || {
    echo "❌ Failed to push latest tag"
    exit 1
}
docker push $REGISTRY/$IMAGE_NAME:$GIT_COMMIT || {
    echo "❌ Failed to push commit tag"
    exit 1
}
echo "✅ Images pushed successfully"

# Trigger Watchtower
echo ""
echo "🔔 Triggering Watchtower update..."
if [ -z "$WATCHTOWER_TOKEN" ]; then
    read -s -p "Enter Watchtower token: " WATCHTOWER_TOKEN
    echo
fi

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    -H "Authorization: Bearer $WATCHTOWER_TOKEN" \
    -H "Content-Type: application/json" \
    https://watchtower.jclee.me/v1/update)

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "204" ]; then
    echo "✅ Watchtower update triggered successfully"
else
    echo "⚠️  Failed to trigger Watchtower (HTTP $HTTP_CODE)"
    echo "   Containers may need manual update"
fi

# Wait and check deployment
echo ""
echo "⏱️  Waiting for deployment (30s)..."
sleep 30

# Health check
echo ""
echo "🏥 Checking production health..."
HEALTH_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://fortinet.jclee.me/api/health)

if [ "$HEALTH_CODE" = "200" ]; then
    echo "✅ Production health check passed!"
    
    # Get version info
    HEALTH_INFO=$(curl -s https://fortinet.jclee.me/api/health)
    echo ""
    echo "📊 Deployment Summary:"
    echo "$HEALTH_INFO" | python3 -m json.tool | grep -E '"version"|"git_commit"|"uptime_human"' || true
else
    echo "❌ Production health check failed (HTTP $HEALTH_CODE)"
fi

echo ""
echo "🎉 Manual deployment completed!"
echo ""
echo "📝 Next steps:"
echo "   - Monitor logs: docker logs -f fortigate-nextrade"
echo "   - Check metrics: https://fortinet.jclee.me/monitoring"
echo "   - Rollback if needed: docker pull $REGISTRY/$IMAGE_NAME:<previous-commit>"