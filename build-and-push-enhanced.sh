#!/bin/bash
# Enhanced Build and Push Script for FortiGate Nextrade
# Supports multi-service builds with Docker registry push
# Version: 2.0

set -e

# =============================================================================
# Configuration
# =============================================================================
REGISTRY="${REGISTRY:-registry.jclee.me}"
PROJECT="${PROJECT:-fortinet}"
TAG="${1:-latest}"
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
VERSION="${VERSION:-1.0.0-${GIT_COMMIT}}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# =============================================================================
# Functions
# =============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "\n${CYAN}========================================${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}========================================${NC}\n"
}

# Docker build with buildkit and caching
build_image() {
    local service=$1
    local dockerfile=$2
    local context=$3
    local image_name=$4
    
    log_info "Building ${service} image..."
    
    # Enable BuildKit for better performance
    export DOCKER_BUILDKIT=1
    
    # Build arguments
    local build_args=(
        --build-arg BUILD_DATE="${BUILD_DATE}"
        --build-arg VERSION="${VERSION}"
        --build-arg VCS_REF="${GIT_COMMIT}"
        --cache-from "${image_name}:latest"
        --cache-from "${image_name}:cache"
        -f "${dockerfile}"
        -t "${image_name}:${TAG}"
    )
    
    # Add platform if specified
    if [ -n "${DOCKER_PLATFORM}" ]; then
        build_args+=(--platform "${DOCKER_PLATFORM}")
    fi
    
    # Build the image
    if docker build "${build_args[@]}" "${context}"; then
        log_success "Successfully built ${image_name}:${TAG}"
        
        # Tag as latest if not already
        if [ "${TAG}" != "latest" ]; then
            docker tag "${image_name}:${TAG}" "${image_name}:latest"
        fi
        
        # Tag for cache
        docker tag "${image_name}:${TAG}" "${image_name}:cache"
        
        return 0
    else
        log_error "Failed to build ${image_name}"
        return 1
    fi
}

# Push image with retry logic
push_image() {
    local image_name=$1
    local max_retries=3
    local retry_count=0
    
    log_info "Pushing ${image_name}:${TAG} to registry..."
    
    while [ $retry_count -lt $max_retries ]; do
        if docker push "${image_name}:${TAG}"; then
            log_success "Successfully pushed ${image_name}:${TAG}"
            
            # Push additional tags
            if [ "${TAG}" != "latest" ]; then
                docker push "${image_name}:latest" || true
            fi
            
            # Push cache tag
            docker push "${image_name}:cache" || true
            
            return 0
        else
            retry_count=$((retry_count + 1))
            log_warning "Push attempt ${retry_count}/${max_retries} failed"
            
            if [ $retry_count -lt $max_retries ]; then
                log_info "Retrying in 5 seconds..."
                sleep 5
            fi
        fi
    done
    
    log_error "Failed to push ${image_name} after ${max_retries} attempts"
    return 1
}

# Scan image for vulnerabilities
scan_image() {
    local image_name=$1
    
    if command -v trivy &> /dev/null; then
        log_info "Scanning ${image_name} for vulnerabilities..."
        trivy image --severity HIGH,CRITICAL "${image_name}:${TAG}" || true
    else
        log_warning "Trivy not installed, skipping security scan"
    fi
}

# =============================================================================
# Main Execution
# =============================================================================

print_header "FortiGate Nextrade Docker Build & Push"

echo -e "${CYAN}Configuration:${NC}"
echo -e "  Registry: ${REGISTRY}"
echo -e "  Project: ${PROJECT}"
echo -e "  Tag: ${TAG}"
echo -e "  Version: ${VERSION}"
echo -e "  Build Date: ${BUILD_DATE}"
echo -e "  Git Commit: ${GIT_COMMIT}"
echo ""

# Check prerequisites
log_info "Checking prerequisites..."

if ! docker version &>/dev/null; then
    log_error "Docker is not running or not installed"
    exit 1
fi

# Login to registry
print_header "Registry Authentication"

if [ -n "${REGISTRY_USERNAME}" ] && [ -n "${REGISTRY_PASSWORD}" ]; then
    log_info "Logging into ${REGISTRY}..."
    echo "${REGISTRY_PASSWORD}" | docker login "${REGISTRY}" \
        --username "${REGISTRY_USERNAME}" --password-stdin
    log_success "Successfully logged into registry"
elif docker system info 2>/dev/null | grep -q "${REGISTRY}"; then
    log_info "Already logged into ${REGISTRY}"
else
    log_warning "No credentials found, attempting interactive login..."
    if ! docker login "${REGISTRY}"; then
        log_error "Registry login failed"
        export SKIP_PUSH=true
        log_warning "Building locally only (push disabled)"
    fi
fi

# Build services
print_header "Building Services"

# Service definitions
declare -A services=(
    ["redis"]="Dockerfile.redis:."
    ["postgresql"]="Dockerfile.postgresql:."
    ["fortinet"]="Dockerfile.all-in-one:."
)

# Alternative Dockerfile paths
declare -A alt_dockerfiles=(
    ["redis"]="docker/redis/Dockerfile"
    ["postgresql"]="docker/postgresql/Dockerfile"
    ["fortinet"]="deployment/dockerfiles/Dockerfile.production"
)

# Build each service
for service in "${!services[@]}"; do
    IFS=':' read -r dockerfile context <<< "${services[$service]}"
    
    # Check if primary Dockerfile exists
    if [ ! -f "${dockerfile}" ]; then
        # Try alternative path
        alt_dockerfile="${alt_dockerfiles[$service]}"
        if [ -f "${alt_dockerfile}" ]; then
            dockerfile="${alt_dockerfile}"
            log_warning "Using alternative Dockerfile: ${alt_dockerfile}"
        else
            # Try the main Dockerfile as last resort for fortinet service
            if [ "${service}" = "fortinet" ] && [ -f "Dockerfile" ]; then
                dockerfile="Dockerfile"
                log_warning "Using main Dockerfile for ${service}"
            else
                log_error "Dockerfile not found for ${service}"
                continue
            fi
        fi
    fi
    
    # Determine image name
    if [ "${service}" = "fortinet" ]; then
        image_name="${REGISTRY}/${PROJECT}"
    else
        image_name="${REGISTRY}/${PROJECT}-${service}"
    fi
    
    # Build the image
    if build_image "${service}" "${dockerfile}" "${context}" "${image_name}"; then
        # Scan for vulnerabilities
        scan_image "${image_name}"
        
        # Push if not skipped
        if [ "${SKIP_PUSH}" != "true" ]; then
            push_image "${image_name}"
        else
            log_warning "Skipping push for ${image_name} (SKIP_PUSH=true)"
        fi
    fi
done

# Generate deployment manifest
print_header "Generating Deployment Information"

cat > deployment-info.json <<EOF
{
  "timestamp": "${BUILD_DATE}",
  "version": "${VERSION}",
  "git_commit": "${GIT_COMMIT}",
  "registry": "${REGISTRY}",
  "project": "${PROJECT}",
  "tag": "${TAG}",
  "images": [
    {
      "service": "redis",
      "image": "${REGISTRY}/${PROJECT}-redis:${TAG}",
      "size": "$(docker images ${REGISTRY}/${PROJECT}-redis:${TAG} --format "{{.Size}}" 2>/dev/null || echo "unknown")"
    },
    {
      "service": "postgresql",
      "image": "${REGISTRY}/${PROJECT}-postgresql:${TAG}",
      "size": "$(docker images ${REGISTRY}/${PROJECT}-postgresql:${TAG} --format "{{.Size}}" 2>/dev/null || echo "unknown")"
    },
    {
      "service": "fortinet",
      "image": "${REGISTRY}/${PROJECT}:${TAG}",
      "size": "$(docker images ${REGISTRY}/${PROJECT}:${TAG} --format "{{.Size}}" 2>/dev/null || echo "unknown")"
    }
  ]
}
EOF

log_success "Deployment information saved to deployment-info.json"

# Summary
print_header "Build & Push Summary"

echo -e "${GREEN}Successfully processed the following images:${NC}"
echo -e "  • ${REGISTRY}/${PROJECT}-redis:${TAG}"
echo -e "  • ${REGISTRY}/${PROJECT}-postgresql:${TAG}"
echo -e "  • ${REGISTRY}/${PROJECT}:${TAG}"
echo ""

if [ "${SKIP_PUSH}" = "true" ]; then
    log_warning "Images built locally but NOT pushed to registry"
else
    log_success "All images pushed to ${REGISTRY}"
fi

# Cleanup old images (optional)
if [ "${CLEANUP_OLD_IMAGES}" = "true" ]; then
    log_info "Cleaning up old images..."
    docker image prune -f --filter "until=24h" || true
fi

log_success "Build and push process completed successfully!"