#!/bin/bash
# =============================================================================
# FortiGate Nextrade - Deployment Verification Script
# Verifies that all components are ready for deployment
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}==============================================================================${NC}"
echo -e "${BLUE}FortiGate Nextrade - Deployment Readiness Verification${NC}"
echo -e "${BLUE}==============================================================================${NC}"

# Function to check status
check_status() {
    local name=$1
    local status=$2
    if [ "$status" = "true" ]; then
        echo -e "${GREEN}✅ $name${NC}"
    else
        echo -e "${RED}❌ $name${NC}"
        return 1
    fi
}

# Function to check Docker image exists
check_image() {
    local image=$1
    if docker image inspect "$image" > /dev/null 2>&1; then
        local size=$(docker image inspect "$image" --format='{{.Size}}' | numfmt --to=iec)
        echo -e "${GREEN}✅ Image: $image ($size)${NC}"
        return 0
    else
        echo -e "${RED}❌ Image: $image (not found)${NC}"
        return 1
    fi
}

# Function to check file exists
check_file() {
    local file=$1
    local desc=$2
    if [ -f "$file" ]; then
        echo -e "${GREEN}✅ $desc: $file${NC}"
        return 0
    else
        echo -e "${RED}❌ $desc: $file (not found)${NC}"
        return 1
    fi
}

# Function to check directory exists
check_directory() {
    local dir=$1
    local desc=$2
    if [ -d "$dir" ]; then
        echo -e "${GREEN}✅ $desc: $dir${NC}"
        return 0
    else
        echo -e "${RED}❌ $desc: $dir (not found)${NC}"
        return 1
    fi
}

all_checks_passed=true

echo -e "\n${YELLOW}1. Docker Images Verification${NC}"
echo "=================================="
check_image "registry.jclee.me/fortinet:latest" || all_checks_passed=false
check_image "registry.jclee.me/fortinet-redis:latest" || all_checks_passed=false
check_image "registry.jclee.me/fortinet-postgresql:latest" || all_checks_passed=false

echo -e "\n${YELLOW}2. Configuration Files${NC}"
echo "======================="
check_file "docker-compose.production.yml" "Docker Compose file" || all_checks_passed=false
check_file "build-and-push.sh" "Build script" || all_checks_passed=false
check_file ".env.example" "Environment template" || all_checks_passed=false
check_file "start.sh" "Startup script" || all_checks_passed=false

echo -e "\n${YELLOW}3. Application Structure${NC}"
echo "========================="
check_directory "src" "Source code" || all_checks_passed=false
check_directory "docker" "Docker configurations" || all_checks_passed=false
check_directory "data" "Data directory" || all_checks_passed=false
check_directory "logs" "Logs directory" || all_checks_passed=false
check_directory "config" "Config directory" || all_checks_passed=false

echo -e "\n${YELLOW}4. Docker Infrastructure${NC}"
echo "=========================="
if docker --version > /dev/null 2>&1; then
    docker_version=$(docker --version)
    echo -e "${GREEN}✅ Docker: $docker_version${NC}"
else
    echo -e "${RED}❌ Docker: not available${NC}"
    all_checks_passed=false
fi

if docker-compose --version > /dev/null 2>&1; then
    compose_version=$(docker-compose --version)
    echo -e "${GREEN}✅ Docker Compose: $compose_version${NC}"
else
    echo -e "${RED}❌ Docker Compose: not available${NC}"
    all_checks_passed=false
fi

echo -e "\n${YELLOW}5. Docker Compose Configuration${NC}"
echo "=================================="
if docker-compose -f docker-compose.production.yml config > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Docker Compose configuration is valid${NC}"
else
    echo -e "${RED}❌ Docker Compose configuration has errors${NC}"
    all_checks_passed=false
fi

echo -e "\n${YELLOW}6. Network Connectivity${NC}"
echo "========================"
if ping -c 1 8.8.8.8 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Internet connectivity${NC}"
else
    echo -e "${YELLOW}⚠️  No internet connectivity (offline mode)${NC}"
fi

echo -e "\n${YELLOW}7. Port Availability${NC}"
echo "===================="
ports_to_check=(7777 5432 6379 80 443 8080)
for port in "${ports_to_check[@]}"; do
    if ! netstat -tuln 2>/dev/null | grep -q ":$port "; then
        echo -e "${GREEN}✅ Port $port is available${NC}"
    else
        echo -e "${YELLOW}⚠️  Port $port is in use${NC}"
    fi
done

echo -e "\n${BLUE}==============================================================================${NC}"

if [ "$all_checks_passed" = "true" ]; then
    echo -e "${GREEN}🎉 DEPLOYMENT READY!${NC}"
    echo -e "${GREEN}All verification checks passed successfully.${NC}"
    echo ""
    echo -e "${BLUE}Next Steps:${NC}"
    echo "1. Create .env file from .env.example"
    echo "2. Configure environment variables as needed"
    echo "3. Run: docker-compose -f docker-compose.production.yml up -d"
    echo "4. Access application at: http://localhost:7777"
    echo "5. Access Traefik dashboard at: http://localhost:8080"
    echo ""
    exit 0
else
    echo -e "${RED}❌ DEPLOYMENT NOT READY!${NC}"
    echo -e "${RED}Some verification checks failed. Please fix the issues above.${NC}"
    echo ""
    exit 1
fi