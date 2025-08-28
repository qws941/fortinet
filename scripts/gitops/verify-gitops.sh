#!/bin/bash

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🔍 GitOps Deployment Verification${NC}"
echo "=================================="

# Load configuration
source <(grep -E '^(GITHUB_ORG|APP_NAME|NAMESPACE)=' scripts/setup-gitops-template.sh)

echo -e "\n${YELLOW}1. GitHub Actions Status${NC}"
gh run list --limit 3

echo -e "\n${YELLOW}2. ArgoCD Application Status${NC}"
argocd app get ${APP_NAME}-${NAMESPACE} || echo "ArgoCD app not found"

echo -e "\n${YELLOW}3. Kubernetes Resources${NC}"
kubectl get all -n ${NAMESPACE}

echo -e "\n${YELLOW}4. Pod Status and Images${NC}"
kubectl get pods -n ${NAMESPACE} -o wide
echo ""
kubectl get pods -n ${NAMESPACE} -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[0].image}{"\n"}{end}'

echo -e "\n${YELLOW}5. Health Check${NC}"
echo -n "Local health check (NodePort): "
if curl -f -s http://192.168.50.110:30779/api/health > /dev/null; then
    echo -e "${GREEN}✅ Healthy${NC}"
    curl -s http://192.168.50.110:30779/api/health | jq . || curl -s http://192.168.50.110:30779/api/health
else
    echo -e "${RED}❌ Failed${NC}"
fi

echo -e "\n${YELLOW}6. Recent Logs${NC}"
kubectl logs -n ${NAMESPACE} -l app=${APP_NAME} --tail=20 || echo "No logs available"

echo -e "\n${GREEN}✅ Verification complete${NC}"
