#!/bin/bash
# =============================================================================
# FortiGate Nextrade - Build and Push Separated Docker Images
# =============================================================================

set -e

# Configuration
REGISTRY="registry.jclee.me"
VERSION="latest"
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
VCS_REF=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

echo_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

echo_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
echo_info "🔍 Checking prerequisites..."

# Check Docker
if ! command -v docker &> /dev/null; then
    echo_error "Docker is not installed or not in PATH"
    exit 1
fi

# Check Docker daemon
if ! docker info &> /dev/null; then
    echo_error "Docker daemon is not running"
    exit 1
fi

# Check registry login
echo_info "🔐 Checking registry authentication..."
if ! docker login $REGISTRY --username admin --password-stdin <<< "$REGISTRY_PASSWORD" 2>/dev/null; then
    echo_warning "Registry authentication failed. Attempting with interactive login..."
    docker login $REGISTRY
fi

echo_success "Prerequisites check passed"

# Build and push Redis image
echo_info "🏗️ Building Redis image..."
docker build \
    --build-arg BUILD_DATE="$BUILD_DATE" \
    --build-arg VCS_REF="$VCS_REF" \
    --build-arg VERSION="$VERSION" \
    -f Dockerfile.redis \
    -t $REGISTRY/fortinet-redis:$VERSION \
    -t $REGISTRY/fortinet-redis:$(date +%Y%m%d-%H%M%S) \
    .

if [ $? -eq 0 ]; then
    echo_success "✅ Redis image built successfully"
    
    echo_info "📤 Pushing Redis image to registry..."
    docker push $REGISTRY/fortinet-redis:$VERSION
    docker push $REGISTRY/fortinet-redis:$(date +%Y%m%d-%H%M%S)
    echo_success "✅ Redis image pushed to registry"
else
    echo_error "❌ Redis image build failed"
    exit 1
fi

# Build and push PostgreSQL image
echo_info "🏗️ Building PostgreSQL image..."
docker build \
    --build-arg BUILD_DATE="$BUILD_DATE" \
    --build-arg VCS_REF="$VCS_REF" \
    --build-arg VERSION="$VERSION" \
    -f Dockerfile.postgresql \
    -t $REGISTRY/fortinet-postgresql:$VERSION \
    -t $REGISTRY/fortinet-postgresql:$(date +%Y%m%d-%H%M%S) \
    .

if [ $? -eq 0 ]; then
    echo_success "✅ PostgreSQL image built successfully"
    
    echo_info "📤 Pushing PostgreSQL image to registry..."
    docker push $REGISTRY/fortinet-postgresql:$VERSION
    docker push $REGISTRY/fortinet-postgresql:$(date +%Y%m%d-%H%M%S)
    echo_success "✅ PostgreSQL image pushed to registry"
else
    echo_error "❌ PostgreSQL image build failed"
    exit 1
fi

# Build and push Fortinet app image
echo_info "🏗️ Building Fortinet application image..."
docker build \
    --build-arg BUILD_DATE="$BUILD_DATE" \
    --build-arg VCS_REF="$VCS_REF" \
    --build-arg VERSION="$VERSION" \
    -f Dockerfile.fortinet \
    -t $REGISTRY/fortinet-app:$VERSION \
    -t $REGISTRY/fortinet-app:$(date +%Y%m%d-%H%M%S) \
    .

if [ $? -eq 0 ]; then
    echo_success "✅ Fortinet application image built successfully"
    
    echo_info "📤 Pushing Fortinet application image to registry..."
    docker push $REGISTRY/fortinet-app:$VERSION
    docker push $REGISTRY/fortinet-app:$(date +%Y%m%d-%H%M%S)
    echo_success "✅ Fortinet application image pushed to registry"
else
    echo_error "❌ Fortinet application image build failed"
    exit 1
fi

# Verify images in registry
echo_info "🔍 Verifying images in registry..."
for image in fortinet-redis fortinet-postgresql fortinet-app; do
    if docker manifest inspect $REGISTRY/$image:$VERSION > /dev/null 2>&1; then
        echo_success "✅ $image:$VERSION verified in registry"
    else
        echo_warning "⚠️ $image:$VERSION verification failed"
    fi
done

# Display image information
echo_info "📋 Image Information Summary:"
echo "┌─────────────────────────────┬────────────────────────────┬─────────────────────────────────┐"
echo "│ Image                       │ Tag                        │ Registry                        │"
echo "├─────────────────────────────┼────────────────────────────┼─────────────────────────────────┤"
echo "│ fortinet-redis              │ $VERSION                   │ $REGISTRY             │"
echo "│ fortinet-postgresql         │ $VERSION                   │ $REGISTRY             │"
echo "│ fortinet-app                │ $VERSION                   │ $REGISTRY             │"
echo "└─────────────────────────────┴────────────────────────────┴─────────────────────────────────┘"

echo_info "📄 Build Information:"
echo "  Build Date: $BUILD_DATE"
echo "  VCS Ref: $VCS_REF"
echo "  Version: $VERSION"

echo_success "🎉 All images built and pushed successfully!"
echo_info "💡 Next steps:"
echo "  1. Deploy using: docker-compose -f docker-compose-separated.yml up -d"
echo "  2. Test health: curl http://localhost:7777/api/health"
echo "  3. Monitor logs: docker-compose -f docker-compose-separated.yml logs -f"

# Clean up local images to save space (optional)
read -p "🧹 Clean up local build images? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo_info "🧹 Cleaning up local images..."
    docker image prune -f
    echo_success "✅ Local images cleaned up"
fi

echo_success "🚀 Build and deployment preparation completed!"