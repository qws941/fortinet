#!/bin/bash
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🚀 Deploying GitOps Application${NC}"
echo "================================"

# Load configuration
source <(grep -E '^(GITHUB_ORG|APP_NAME|NAMESPACE)=' scripts/setup-gitops-template.sh)

# Check prerequisites
echo -e "\n${YELLOW}Checking prerequisites...${NC}"

# Check kubectl
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}❌ kubectl not found${NC}"
    exit 1
fi

# Check argocd CLI
if ! command -v argocd &> /dev/null; then
    echo -e "${RED}❌ argocd CLI not found${NC}"
    echo "Install with: brew install argocd"
    exit 1
fi

# Check helm
if ! command -v helm &> /dev/null; then
    echo -e "${RED}❌ helm not found${NC}"
    exit 1
fi

echo -e "${GREEN}✅ All prerequisites met${NC}"

# 1. Setup Kubernetes
echo -e "
${YELLOW}1. Setting up Kubernetes namespace and secrets...${NC}"

# Set the correct kubeconfig
export KUBECONFIG=~/.kube/config
if [ -f ~/.kube/config-k8s-jclee ]; then
    export KUBECONFIG=~/.kube/config-k8s-jclee
    echo "   Using kubeconfig: $KUBECONFIG"
fi

# Test kubectl connection
if ! kubectl cluster-info &>/dev/null; then
    echo -e "   ${RED}❌ Cannot connect to Kubernetes cluster${NC}"
    echo "   Please ensure kubectl is configured correctly"
    exit 1
fi

kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
echo -e "   ${GREEN}✅ Namespace ${NAMESPACE} ready${NC}"

kubectl create secret docker-registry harbor-registry \
  --docker-server=registry.jclee.me \
  --docker-username=admin \
  --docker-password=bingogo1 \
  --namespace=${NAMESPACE} \
  --dry-run=client -o yaml | kubectl apply -f -
echo -e "   ${GREEN}✅ Harbor registry secret created${NC}"

# 2. Setup ArgoCD
echo -e "\n${YELLOW}2. Configuring ArgoCD...${NC}"

# Login to ArgoCD
if ! argocd account whoami &> /dev/null; then
    echo "Logging into ArgoCD..."
    argocd login argo.jclee.me --username admin --password bingogo1 --insecure --grpc-web
fi

# Add ChartMuseum repository
if ! argocd repo list | grep -q "https://charts.jclee.me"; then
    echo "Adding ChartMuseum repository..."
    argocd repo add https://charts.jclee.me \
      --type helm \
      --name chartmuseum-${APP_NAME} \
      --username admin \
      --password bingogo1 \
      --insecure-skip-server-verification
    echo -e "   ${GREEN}✅ ChartMuseum repository added${NC}"
else
    echo -e "   ${YELLOW}⏭️  ChartMuseum repository already exists${NC}"
fi

# 3. Create ArgoCD Application
echo -e "\n${YELLOW}3. Creating ArgoCD application...${NC}"

if argocd app get ${APP_NAME}-${NAMESPACE} &> /dev/null; then
    echo -e "   ${YELLOW}⏭️  Application already exists, updating...${NC}"
    argocd app delete ${APP_NAME}-${NAMESPACE} --yes
    sleep 5
fi

kubectl apply -f argocd-application-${APP_NAME}.yaml
echo -e "   ${GREEN}✅ ArgoCD application created${NC}"

# 4. Initial sync
echo -e "\n${YELLOW}4. Triggering initial sync...${NC}"
sleep 5
argocd app sync ${APP_NAME}-${NAMESPACE}
echo -e "   ${GREEN}✅ Initial sync triggered${NC}"

# 5. Wait and verify
echo -e "\n${YELLOW}5. Waiting for deployment...${NC}"
echo "This may take a few minutes..."

# Watch the sync status
timeout 300 argocd app wait ${APP_NAME}-${NAMESPACE} --health || true

# Final status
echo -e "\n${GREEN}📊 Deployment Status:${NC}"
argocd app get ${APP_NAME}-${NAMESPACE}

echo -e "\n${GREEN}🎉 GitOps deployment complete!${NC}"
echo -e "\n${YELLOW}Access points:${NC}"
echo -e "  - Application: http://192.168.50.110:30779"
echo -e "  - Public URL: https://${APP_NAME}-gitops.jclee.me"
echo -e "  - ArgoCD: https://argo.jclee.me/applications/${APP_NAME}-${NAMESPACE}"
echo -e "  - Logs: kubectl logs -n ${NAMESPACE} -l app=${APP_NAME} -f"
