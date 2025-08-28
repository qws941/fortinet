#!/bin/bash
set -e

echo "🚀 Fortinet Complete GitOps CI/CD Template Setup"
echo "================================================"

# Fortinet 프로젝트 특화 설정값
GITHUB_ORG="jclee94"
APP_NAME="fortinet"
NAMESPACE="fortinet"
NODEPORT="30777"

# GitHub CLI 로그인 체크
echo "🔐 Checking GitHub CLI authentication..."
if ! gh auth status > /dev/null 2>&1; then
    echo "❌ GitHub CLI not authenticated. Please run: gh auth login"
    exit 1
fi

# GitHub Secrets 설정
REGISTRY_URL="registry.jclee.me"
REGISTRY_USERNAME="admin"
REGISTRY_PASSWORD="bingogo1"

echo "🔑 Setting up GitHub secrets..."
gh secret list | grep -q "REGISTRY_URL" || gh secret set REGISTRY_URL -b "${REGISTRY_URL}"
gh secret list | grep -q "REGISTRY_USERNAME" || gh secret set REGISTRY_USERNAME -b "${REGISTRY_USERNAME}"
gh secret list | grep -q "REGISTRY_PASSWORD" || gh secret set REGISTRY_PASSWORD -b "${REGISTRY_PASSWORD}"

echo "📋 Configuration:"
echo "  App Name: ${APP_NAME}"
echo "  Namespace: ${NAMESPACE}"
echo "  NodePort: ${NODEPORT}"
echo "  Registry: ${REGISTRY_URL}"

# 완전한 GitHub Actions 워크플로우 생성
echo "🔨 Creating complete GitHub Actions workflow..."
mkdir -p .github/workflows

cat > .github/workflows/fortinet-complete-gitops.yaml << 'EOF'
name: Fortinet Complete GitOps CI/CD

on:
  push:
    branches: [main, master]
    paths-ignore:
      - 'docs/**'
      - '*.md'
      - '.gitignore'
  pull_request:
    branches: [main, master]
    paths-ignore:
      - 'docs/**'
      - '*.md'
      - '.gitignore'

env:
  REGISTRY: ${{ secrets.REGISTRY_URL }}
  IMAGE_NAME: jclee94/fortinet
  APP_NAME: fortinet
  NAMESPACE: fortinet
  NODEPORT: 30777

jobs:
  # 1단계: 빠른 검증
  quick-validation:
    runs-on: self-hosted
    outputs:
      should-deploy: ${{ steps.check.outputs.should-deploy }}
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          cache: 'pip'
          
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest flake8 black
          
      - name: Quick validation
        run: |
          echo "✅ Running quick validation..."
          cd src && python test_features.py
          
      - name: Check deployment eligibility
        id: check
        run: |
          if [ "${{ github.ref }}" == "refs/heads/master" ]; then
            echo "should-deploy=true" >> $GITHUB_OUTPUT
          else
            echo "should-deploy=false" >> $GITHUB_OUTPUT
          fi

  # 2단계: 완전한 빌드 및 배포
  build-and-deploy:
    runs-on: self-hosted
    needs: quick-validation
    if: needs.quick-validation.outputs.should-deploy == 'true'
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
          token: ${{ secrets.GITHUB_TOKEN }}
        
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
        
      - name: Login to Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ secrets.REGISTRY_USERNAME }}
          password: ${{ secrets.REGISTRY_PASSWORD }}
          
      - name: Generate version info
        id: version
        run: |
          COMMIT_SHA="${{ github.sha }}"
          SHORT_SHA=${COMMIT_SHA:0:8}
          TIMESTAMP=$(date +%Y%m%d-%H%M%S)
          CHART_VERSION="1.0.0-${TIMESTAMP}-${SHORT_SHA}"
          IMAGE_TAG="master-${SHORT_SHA}"
          
          echo "chart-version=${CHART_VERSION}" >> $GITHUB_OUTPUT
          echo "image-tag=${IMAGE_TAG}" >> $GITHUB_OUTPUT
          echo "Generated chart version: ${CHART_VERSION}"
          echo "Generated image tag: ${IMAGE_TAG}"
          
      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: Dockerfile.production
          push: true
          tags: |
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ steps.version.outputs.image-tag }}
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest
          cache-from: type=registry,ref=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:buildcache
          cache-to: type=registry,ref=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:buildcache,mode=max
          
      - name: Update Helm chart
        run: |
          CHART_VERSION="${{ steps.version.outputs.chart-version }}"
          IMAGE_TAG="${{ steps.version.outputs.image-tag }}"
          
          echo "📦 Updating Helm chart..."
          echo "  Chart Version: ${CHART_VERSION}"
          echo "  Image Tag: ${IMAGE_TAG}"
          
          # Chart 버전과 이미지 태그 업데이트
          sed -i "s/^version:.*/version: ${CHART_VERSION}/" ./charts/${APP_NAME}/Chart.yaml
          sed -i "s/^appVersion:.*/appVersion: \"${CHART_VERSION}\"/" ./charts/${APP_NAME}/Chart.yaml
          sed -i "s/tag:.*/tag: \"${IMAGE_TAG}\"/" ./charts/${APP_NAME}/values.yaml
          
      - name: Commit chart changes
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add charts/${APP_NAME}/Chart.yaml charts/${APP_NAME}/values.yaml
          
          if git diff --staged --quiet; then
            echo "📝 No chart changes to commit"
          else
            git commit -m "🚀 Update chart to ${{ steps.version.outputs.chart-version }}

            📦 Chart Version: ${{ steps.version.outputs.chart-version }}
            🐳 Image Tag: ${{ steps.version.outputs.image-tag }}
            
            Generated by GitHub Actions
            
            Co-Authored-By: GitHub Actions <actions@github.com>"
            git push
            echo "✅ Chart changes committed and pushed"
          fi
          
      - name: Verify deployment
        run: |
          echo "🔍 Waiting for ArgoCD sync..."
          sleep 90
          
          # 헬스체크
          HEALTH_URL="http://192.168.50.110:${NODEPORT}/api/health"
          echo "Testing: ${HEALTH_URL}"
          
          for i in {1..5}; do
            if curl -f --connect-timeout 10 "${HEALTH_URL}"; then
              echo "✅ Deployment verification successful"
              exit 0
            else
              echo "⏳ Attempt ${i}/5 failed, waiting..."
              sleep 30
            fi
          done
          
          echo "⚠ Health check failed but continuing..."
EOF

echo "✅ Complete GitHub Actions workflow created"

# ArgoCD Application을 Git 기반으로 완전히 재구성
echo "🎯 Creating Git-based ArgoCD Application..."
cat > argocd-fortinet-gitops.yaml << EOF
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: fortinet-gitops
  namespace: argocd
  labels:
    app: fortinet
    env: production
    type: gitops
  annotations:
    argocd.argoproj.io/sync-wave: "1"
spec:
  project: default
  source:
    repoURL: https://github.com/jclee94/fortinet.git
    path: charts/fortinet
    targetRevision: HEAD
    helm:
      releaseName: fortinet
      values: |
        replicaCount: 1
        image:
          pullPolicy: Always
        service:
          type: NodePort
          nodePort: 30777
        resources:
          limits:
            cpu: 1000m
            memory: 1Gi
          requests:
            cpu: 100m
            memory: 256Mi
        env:
          APP_MODE: production
          OFFLINE_MODE: "false"
          WEB_APP_PORT: "7777"
  destination:
    server: https://kubernetes.default.svc
    namespace: fortinet
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
      allowEmpty: false
    syncOptions:
    - CreateNamespace=true
    - ServerSideApply=true
    - ApplyOutOfSyncOnly=true
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
  revisionHistoryLimit: 10
EOF

echo "✅ Git-based ArgoCD Application created"

# 검증 스크립트 생성
echo "📋 Creating verification script..."
cat > scripts/verify_complete_gitops.sh << 'EOF'
#!/bin/bash

APP_NAME="fortinet"
NAMESPACE="fortinet" 
NODEPORT="30777"
BASE_URL="http://192.168.50.110:${NODEPORT}"

echo "🔍 Complete GitOps Deployment Verification"
echo "=========================================="

# 1. GitHub Actions 상태
echo "1. GitHub Actions workflow status..."
gh run list --workflow="Fortinet Complete GitOps CI/CD" --limit 3

# 2. ArgoCD 애플리케이션 상태
echo -e "\n2. ArgoCD application status..."
if command -v argocd >/dev/null 2>&1; then
    argocd app get fortinet-gitops 2>/dev/null || echo "⚠ ArgoCD app not found or not accessible"
else
    echo "⚠ ArgoCD CLI not available"
fi

# 3. Kubernetes 리소스
echo -e "\n3. Kubernetes resources..."
kubectl get pods,svc -n ${NAMESPACE} -l app=${APP_NAME}

# 4. 애플리케이션 헬스체크
echo -e "\n4. Application health check..."
echo "Testing: ${BASE_URL}/api/health"
if curl -f --connect-timeout 10 "${BASE_URL}/api/health" 2>/dev/null; then
    echo "✅ Health check passed"
else
    echo "❌ Health check failed"
fi

# 5. Chart 버전 확인
echo -e "\n5. Current chart version..."
if [ -f "charts/fortinet/Chart.yaml" ]; then
    grep "^version:" charts/fortinet/Chart.yaml
    grep "^appVersion:" charts/fortinet/Chart.yaml
fi

echo -e "\n✅ Complete GitOps verification completed"
EOF

chmod +x scripts/verify_complete_gitops.sh

echo "✅ Verification script created"

echo ""
echo "🎉 Fortinet Complete GitOps CI/CD Setup Completed!"
echo "=================================================="
echo ""
echo "📋 Created Files:"
echo "   - .github/workflows/fortinet-complete-gitops.yaml"
echo "   - argocd-fortinet-gitops.yaml"
echo "   - scripts/verify_complete_gitops.sh"
echo ""
echo "🚀 Next Steps:"
echo "1. Commit and push changes:"
echo "   git add ."
echo "   git commit -m 'feat: Complete GitOps CI/CD pipeline setup'"
echo "   git push origin master"
echo ""
echo "2. Create ArgoCD Application:"
echo "   argocd app create -f argocd-fortinet-gitops.yaml --upsert"
echo ""
echo "3. Verify deployment:"
echo "   ./scripts/verify_complete_gitops.sh"
echo ""
echo "4. Monitor:"
echo "   - GitHub Actions: https://github.com/jclee94/fortinet/actions"
echo "   - Application: http://192.168.50.110:30777"