#!/bin/bash

# =============================================================================
# Build and Run Standalone FortiGate Nextrade Container
# No external dependencies or volume mounts required
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=== Building Standalone FortiGate Nextrade Container ==="
echo "Project Root: $PROJECT_ROOT"
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
IMAGE_NAME="fortinet-standalone"
IMAGE_TAG="${1:-latest}"
CONTAINER_NAME="fortinet-standalone"
PORT="${2:-7777}"

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Change to project root
cd "$PROJECT_ROOT"

# Step 1: Stop and remove existing container if running
echo "Step 1: Cleaning up existing containers..."
if docker ps -a | grep -q "$CONTAINER_NAME"; then
    print_warning "Stopping existing container: $CONTAINER_NAME"
    docker stop "$CONTAINER_NAME" 2>/dev/null || true
    docker rm "$CONTAINER_NAME" 2>/dev/null || true
    print_status "Existing container removed"
else
    print_status "No existing container found"
fi

# Step 2: Build the standalone image
echo ""
echo "Step 2: Building standalone Docker image..."
if docker build -f Dockerfile.standalone -t "${IMAGE_NAME}:${IMAGE_TAG}" .; then
    print_status "Docker image built successfully: ${IMAGE_NAME}:${IMAGE_TAG}"
else
    print_error "Failed to build Docker image"
    exit 1
fi

# Step 3: Show image size
echo ""
echo "Step 3: Image information..."
IMAGE_SIZE=$(docker images "${IMAGE_NAME}:${IMAGE_TAG}" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" | tail -n 1)
echo "Image details: $IMAGE_SIZE"

# Step 4: Run the container
echo ""
echo "Step 4: Starting standalone container..."
if docker run -d \
    --name "$CONTAINER_NAME" \
    -p "${PORT}:7777" \
    -e APP_MODE=production \
    -e LOG_LEVEL=INFO \
    --restart unless-stopped \
    --memory="1g" \
    --memory-reservation="512m" \
    --security-opt no-new-privileges:true \
    "${IMAGE_NAME}:${IMAGE_TAG}"; then
    print_status "Container started successfully"
else
    print_error "Failed to start container"
    exit 1
fi

# Step 5: Wait for container to be ready
echo ""
echo "Step 5: Waiting for application to be ready..."
MAX_ATTEMPTS=30
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if docker exec "$CONTAINER_NAME" curl -f -s http://localhost:7777/api/health > /dev/null 2>&1; then
        print_status "Application is ready!"
        break
    fi
    
    ATTEMPT=$((ATTEMPT + 1))
    echo -n "."
    sleep 2
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    print_error "Application failed to start within timeout"
    echo "Container logs:"
    docker logs "$CONTAINER_NAME" --tail 50
    exit 1
fi

# Step 6: Display access information
echo ""
echo "=========================================="
print_status "Standalone FortiGate Nextrade is running!"
echo "=========================================="
echo ""
echo "Access Information:"
echo "  - URL: http://localhost:${PORT}"
echo "  - Health Check: http://localhost:${PORT}/api/health"
echo "  - Container: $CONTAINER_NAME"
echo "  - Image: ${IMAGE_NAME}:${IMAGE_TAG}"
echo ""
echo "Useful Commands:"
echo "  - View logs: docker logs -f $CONTAINER_NAME"
echo "  - Enter container: docker exec -it $CONTAINER_NAME /bin/bash"
echo "  - Stop container: docker stop $CONTAINER_NAME"
echo "  - Remove container: docker rm $CONTAINER_NAME"
echo "  - Check status: docker ps | grep $CONTAINER_NAME"
echo ""
echo "No external dependencies required!"
echo "No volume mounts needed!"
echo "Everything is self-contained!"
echo ""

# Step 7: Quick health check
echo "Performing health check..."
HEALTH_RESPONSE=$(docker exec "$CONTAINER_NAME" curl -s http://localhost:7777/api/health)
echo "Health Status: $HEALTH_RESPONSE"
echo ""

print_status "Deployment complete!"