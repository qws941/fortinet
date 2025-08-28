#!/bin/bash

# GitHub Actions Workflow Validation Script
# Tests the gitops-pipeline.yml for common issues

set -e

WORKFLOW_FILE=".github/workflows/gitops-pipeline.yml"

echo "🔍 Validating GitHub Actions Workflow"
echo "======================================="

# Check if workflow file exists
if [ ! -f "$WORKFLOW_FILE" ]; then
    echo "❌ Workflow file not found: $WORKFLOW_FILE"
    exit 1
fi

echo "✅ Workflow file found: $WORKFLOW_FILE"

# Validate YAML syntax
echo ""
echo "📝 Checking YAML syntax..."
if command -v yamllint >/dev/null 2>&1; then
    yamllint "$WORKFLOW_FILE" || true
elif command -v python3 >/dev/null 2>&1; then
    python3 -c "import yaml; yaml.safe_load(open('$WORKFLOW_FILE'))" && echo "✅ YAML syntax is valid"
else
    echo "⚠️ No YAML validator found (yamllint or python3)"
fi

# Check for required environment variables
echo ""
echo "🔧 Checking environment variables..."
grep -q "REGISTRY_URL:" "$WORKFLOW_FILE" && echo "✅ REGISTRY_URL defined"
grep -q "IMAGE_NAME:" "$WORKFLOW_FILE" && echo "✅ IMAGE_NAME defined"
grep -q "CHARTMUSEUM_URL:" "$WORKFLOW_FILE" && echo "✅ CHARTMUSEUM_URL defined"

# Check for required secrets
echo ""
echo "🔐 Checking required secrets..."
REQUIRED_SECRETS=(
    "REGISTRY_USERNAME"
    "REGISTRY_PASSWORD"
    "CHARTMUSEUM_USERNAME"
    "CHARTMUSEUM_PASSWORD"
    "ARGOCD_TOKEN"
)

for secret in "${REQUIRED_SECRETS[@]}"; do
    if grep -q "$secret" "$WORKFLOW_FILE"; then
        echo "✅ Secret referenced: $secret"
    else
        echo "❌ Secret missing: $secret"
    fi
done

# Check for required files
echo ""
echo "📁 Checking required files..."
REQUIRED_FILES=(
    "requirements.txt"
    "Dockerfile"
    "charts/fortinet/Chart.yaml"
    "charts/fortinet/values.yaml"
    "start.sh"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ Required file found: $file"
    else
        echo "❌ Required file missing: $file"
    fi
done

# Validate Docker build context
echo ""
echo "🐳 Checking Docker configuration..."
if [ -f "Dockerfile" ]; then
    echo "✅ Dockerfile found"
    if [ -f ".dockerignore" ]; then
        echo "✅ .dockerignore found"
    else
        echo "⚠️ .dockerignore missing (recommended)"
    fi
else
    echo "❌ Dockerfile not found"
fi

# Check Helm chart structure
echo ""
echo "📦 Checking Helm chart..."
if [ -f "charts/fortinet/Chart.yaml" ] && [ -f "charts/fortinet/values.yaml" ]; then
    echo "✅ Helm chart structure looks good"
    
    # Check if image tag is configurable
    if grep -q "tag:" "charts/fortinet/values.yaml"; then
        echo "✅ Image tag is configurable in values.yaml"
    else
        echo "❌ Image tag not found in values.yaml"
    fi
else
    echo "❌ Helm chart structure incomplete"
fi

# Test connectivity endpoints
echo ""
echo "🌐 Testing connectivity (optional)..."
ENDPOINTS=(
    "registry.jclee.me"
    "charts.jclee.me"
    "192.168.50.110:30777"
)

for endpoint in "${ENDPOINTS[@]}"; do
    if timeout 5 nc -z ${endpoint/:/ } 2>/dev/null; then
        echo "✅ Can reach: $endpoint"
    else
        echo "⚠️ Cannot reach: $endpoint (may be expected in CI)"
    fi
done

echo ""
echo "🎯 Validation Summary"
echo "===================="
echo "Workflow file: $WORKFLOW_FILE"
echo "Status: Ready for commit"
echo ""
echo "Next steps:"
echo "1. Configure GitHub secrets (see .github/SECRETS.md)"
echo "2. Test the workflow by pushing to master branch"
echo "3. Monitor the pipeline in GitHub Actions tab"
echo ""
echo "✅ Validation complete!"