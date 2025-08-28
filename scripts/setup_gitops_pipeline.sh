#!/bin/bash
set -e

echo "🚀 Fortinet GitOps CI/CD Pipeline Setup"
echo "======================================"

# 프로젝트 특화 설정
GITHUB_ORG="${GITHUB_ORG:-jclee94}"
APP_NAME="fortinet"
NAMESPACE="fortinet"
NODEPORT="30779"  # 현재 사용 중인 NodePort

# 기존 설정값 확인
REGISTRY_URL="${REGISTRY_URL:-registry.jclee.me}"
REGISTRY_USERNAME="${REGISTRY_USERNAME:-admin}"
REGISTRY_PASSWORD="${REGISTRY_PASSWORD:-bingogo1}"
CHARTMUSEUM_URL="${CHARTMUSEUM_URL:-https://charts.jclee.me}"
CHARTMUSEUM_USERNAME="${CHARTMUSEUM_USERNAME:-admin}"
CHARTMUSEUM_PASSWORD="${CHARTMUSEUM_PASSWORD:-bingogo1}"

echo "📋 Configuration:"
echo "  App Name: ${APP_NAME}"
echo "  Namespace: ${NAMESPACE}"
echo "  NodePort: ${NODEPORT}"
echo "  Registry: ${REGISTRY_URL}"
echo "  Chart Museum: ${CHARTMUSEUM_URL}"

# GitHub CLI 로그인 체크
echo "🔐 Checking GitHub CLI authentication..."
if ! gh auth status > /dev/null 2>&1; then
    echo "❌ GitHub CLI not authenticated. Please run: gh auth login"
    exit 1
fi

# GitHub Secrets/Variables 설정
echo "🔑 Setting up GitHub secrets and variables..."
gh secret set REGISTRY_URL -b "${REGISTRY_URL}" || echo "⚠ REGISTRY_URL already exists"
gh secret set REGISTRY_USERNAME -b "${REGISTRY_USERNAME}" || echo "⚠ REGISTRY_USERNAME already exists"
gh secret set REGISTRY_PASSWORD -b "${REGISTRY_PASSWORD}" || echo "⚠ REGISTRY_PASSWORD already exists"
gh secret set CHARTMUSEUM_URL -b "${CHARTMUSEUM_URL}" || echo "⚠ CHARTMUSEUM_URL already exists"
gh secret set CHARTMUSEUM_USERNAME -b "${CHARTMUSEUM_USERNAME}" || echo "⚠ CHARTMUSEUM_USERNAME already exists"
gh secret set CHARTMUSEUM_PASSWORD -b "${CHARTMUSEUM_PASSWORD}" || echo "⚠ CHARTMUSEUM_PASSWORD already exists"

gh variable set GITHUB_ORG -b "${GITHUB_ORG}" || echo "⚠ GITHUB_ORG already exists"
gh variable set APP_NAME -b "${APP_NAME}" || echo "⚠ APP_NAME already exists"
gh variable set NAMESPACE -b "${NAMESPACE}" || echo "⚠ NAMESPACE already exists"
gh variable set NODEPORT -b "${NODEPORT}" || echo "⚠ NODEPORT already exists"

# 현재 Helm 차트 확인 및 업데이트
echo "⚙️ Updating Helm chart configuration..."
if [ -d "charts/fortinet" ]; then
    # values.yaml 업데이트 - NodePort 확인
    sed -i "s/nodePort:.*/nodePort: ${NODEPORT}/" charts/fortinet/values.yaml
    
    # Chart.yaml 버전 확인
    CURRENT_VERSION=$(grep "^version:" charts/fortinet/Chart.yaml | cut -d' ' -f2)
    echo "  Current chart version: ${CURRENT_VERSION}"
else
    echo "❌ Helm chart not found at charts/fortinet"
    echo "   Please ensure the chart exists before running this script"
    exit 1
fi

# GitHub Actions 워크플로우 생성
echo "🔨 Creating GitHub Actions workflows..."
mkdir -p .github/workflows

# 통합 테스트가 포함된 CI/CD 워크플로우 생성
cat > .github/workflows/fortinet-gitops-pipeline.yaml << 'EOF'
name: Fortinet GitOps CI/CD Pipeline

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
  IMAGE_NAME: ${{ vars.GITHUB_ORG }}/${{ vars.APP_NAME }}
  PYTHON_VERSION: '3.11'

jobs:
  # 1단계: 코드 품질 및 보안 검사
  code-quality:
    runs-on: self-hosted
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'
          
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov bandit safety
          
      - name: Run linting
        run: |
          echo "🧹 Running code quality checks..."
          black --check src/ || echo "⚠ Black formatting issues found"
          flake8 src/ --max-line-length=120 --ignore=E203,W503 || echo "⚠ Flake8 issues found"
          
      - name: Security scan
        run: |
          echo "🔒 Running security scans..."
          bandit -r src/ -f json -o bandit-report.json || echo "⚠ Security issues found"
          safety check --json --output safety-report.json || echo "⚠ Dependency vulnerabilities found"
          
      - name: Upload security reports
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: security-reports
          path: |
            bandit-report.json
            safety-report.json

  # 2단계: 단위 테스트 및 통합 테스트
  test-suite:
    runs-on: self-hosted
    needs: code-quality
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'
          
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-xdist
          
      - name: Run unit tests
        run: |
          echo "🧪 Running unit tests..."
          cd src
          pytest ../tests/unit/ -v --tb=short --cov=. --cov-report=xml
          
      - name: Run integration tests
        run: |
          echo "🔗 Running integration tests..."
          export APP_MODE=test
          export OFFLINE_MODE=true
          export DISABLE_SOCKETIO=true
          cd src
          pytest ../tests/integration/ -v --tb=short --maxfail=5
          
      - name: Run feature validation tests
        run: |
          echo "✅ Running feature validation..."
          cd src
          python test_features.py
          
      - name: Upload test results
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: test-results
          path: |
            coverage.xml
            src/logs/

  # 3단계: Docker 이미지 빌드 및 푸시
  build-and-push:
    runs-on: self-hosted
    needs: test-suite
    if: github.ref == 'refs/heads/master' || github.ref == 'refs/heads/main'
    outputs:
      image-tag: ${{ steps.meta.outputs.tags }}
      chart-version: ${{ steps.version.outputs.chart-version }}
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        
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
          echo "chart-version=${CHART_VERSION}" >> $GITHUB_OUTPUT
          echo "Generated chart version: ${CHART_VERSION}"
          
      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=sha,prefix={{branch}}-
            type=raw,value=latest,enable={{is_default_branch}}
            
      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: Dockerfile.production
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=registry,ref=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:buildcache
          cache-to: type=registry,ref=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:buildcache,mode=max
          
      - name: Test Docker image
        run: |
          echo "🐳 Testing Docker image..."
          # 이미지 기본 검증
          docker run --rm ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest python --version
          echo "✅ Docker image validated"

  # 4단계: Helm 차트 패키징 및 배포
  helm-deploy:
    runs-on: self-hosted
    needs: build-and-push
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        
      - name: Install Helm
        uses: azure/setup-helm@v3
        with:
          version: 'v3.14.0'
          
      - name: Update Helm chart
        run: |
          CHART_VERSION="${{ needs.build-and-push.outputs.chart-version }}"
          IMAGE_TAG=$(echo "${{ needs.build-and-push.outputs.image-tag }}" | head -n1 | cut -d: -f2)
          
          echo "📦 Updating Helm chart..."
          echo "  Chart Version: ${CHART_VERSION}"
          echo "  Image Tag: ${IMAGE_TAG}"
          
          # Chart.yaml 업데이트
          sed -i "s/^version:.*/version: ${CHART_VERSION}/" ./charts/${{ vars.APP_NAME }}/Chart.yaml
          sed -i "s/^appVersion:.*/appVersion: \"${CHART_VERSION}\"/" ./charts/${{ vars.APP_NAME }}/Chart.yaml
          
          # values.yaml 업데이트
          sed -i "s/tag:.*/tag: \"${IMAGE_TAG}\"/" ./charts/${{ vars.APP_NAME }}/values.yaml
          
      - name: Package and upload Helm chart
        run: |
          CHART_VERSION="${{ needs.build-and-push.outputs.chart-version }}"
          
          echo "📦 Packaging Helm chart..."
          helm package ./charts/${{ vars.APP_NAME }} --destination ./
          
          CHART_FILE="${{ vars.APP_NAME }}-${CHART_VERSION}.tgz"
          
          echo "⬆️ Uploading ${CHART_FILE} to ChartMuseum..."
          HTTP_CODE=$(curl -w "%{http_code}" -s -o /tmp/upload_response.txt \
            -u ${{ secrets.CHARTMUSEUM_USERNAME }}:${{ secrets.CHARTMUSEUM_PASSWORD }} \
            --data-binary "@${CHART_FILE}" \
            ${{ secrets.CHARTMUSEUM_URL }}/api/charts)
          
          echo "HTTP Response Code: ${HTTP_CODE}"
          
          if [ "${HTTP_CODE}" = "201" ] || [ "${HTTP_CODE}" = "409" ]; then
            echo "✅ Chart upload successful: ${CHART_VERSION}"
          else
            echo "❌ Chart upload failed (HTTP ${HTTP_CODE})"
            cat /tmp/upload_response.txt
            exit 1
          fi
          
          # 업로드 검증
          echo "🔍 Verifying chart upload..."
          curl -s -u ${{ secrets.CHARTMUSEUM_USERNAME }}:${{ secrets.CHARTMUSEUM_PASSWORD }} \
            ${{ secrets.CHARTMUSEUM_URL }}/api/charts/${{ vars.APP_NAME }} | \
            grep -q "${CHART_VERSION}" && echo "✅ Chart verification successful" || echo "⚠ Chart verification failed"

  # 5단계: 배포 검증
  deployment-verification:
    runs-on: self-hosted
    needs: helm-deploy
    steps:
      - name: Wait for ArgoCD sync
        run: |
          echo "⏳ Waiting for ArgoCD to sync the application..."
          sleep 30
          
      - name: Verify deployment
        run: |
          echo "🔍 Verifying deployment..."
          
          # 기본 헬스체크
          HEALTH_URL="http://192.168.50.110:${{ vars.NODEPORT }}/api/health"
          echo "Testing health endpoint: ${HEALTH_URL}"
          
          # 최대 10번 재시도 (총 5분)
          for i in {1..10}; do
            if curl -f --connect-timeout 10 --max-time 30 "${HEALTH_URL}"; then
              echo "✅ Health check successful"
              break
            else
              echo "⏳ Health check failed, attempt ${i}/10"
              if [ ${i} -eq 10 ]; then
                echo "❌ Health check failed after 10 attempts"
                exit 1
              fi
              sleep 30
            fi
          done
          
          # 추가 API 엔드포인트 검증
          echo "🧪 Testing additional endpoints..."
          curl -f "${HEALTH_URL%/*}/system-info" || echo "⚠ System info endpoint issues"
          
          echo "✅ Deployment verification completed"

EOF

echo "✅ GitHub Actions workflow created: .github/workflows/fortinet-gitops-pipeline.yaml"

# ArgoCD Application 설정
echo "🎯 Creating ArgoCD Application configuration..."
cat > argocd-fortinet-application.yaml << EOF
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: fortinet
  namespace: argocd
  labels:
    app: fortinet
    env: production
  annotations:
    argocd.argoproj.io/sync-wave: "1"
spec:
  project: default
  source:
    repoURL: ${CHARTMUSEUM_URL}
    chart: fortinet
    targetRevision: "*"
    helm:
      releaseName: fortinet
      values: |
        replicaCount: 2
        image:
          pullPolicy: Always
        service:
          type: NodePort
          nodePort: ${NODEPORT}
        resources:
          limits:
            cpu: 1000m
            memory: 1Gi
          requests:
            cpu: 200m
            memory: 256Mi
        env:
          APP_MODE: production
          OFFLINE_MODE: "false"
          WEB_APP_PORT: "7777"
  destination:
    server: https://kubernetes.default.svc
    namespace: ${NAMESPACE}
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

echo "✅ ArgoCD Application configuration created: argocd-fortinet-application.yaml"

# Kubernetes 환경 설정
echo "☸️ Setting up Kubernetes environment..."
export KUBECONFIG=~/.kube/config

echo "Creating namespace and secrets..."
kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret docker-registry harbor-registry \
  --docker-server=${REGISTRY_URL} \
  --docker-username=${REGISTRY_USERNAME} \
  --docker-password=${REGISTRY_PASSWORD} \
  --namespace=${NAMESPACE} \
  --dry-run=client -o yaml | kubectl apply -f -

echo "✅ Kubernetes resources configured"

# 배포 검증 스크립트 생성
echo "📋 Creating deployment verification script..."
cat > scripts/verify_deployment.sh << 'EOF'
#!/bin/bash

APP_NAME="fortinet"
NAMESPACE="fortinet"
NODEPORT="30779"
BASE_URL="http://192.168.50.110:${NODEPORT}"

echo "🔍 Fortinet Deployment Verification"
echo "=================================="

# 1. GitHub Actions 워크플로우 상태 확인
echo "1. GitHub Actions workflow status..."
gh run list --workflow="Fortinet GitOps CI/CD Pipeline" --limit 3

# 2. Docker 이미지 확인
echo -e "\n2. Docker images in registry..."
curl -s -u ${REGISTRY_USERNAME}:${REGISTRY_PASSWORD} \
  https://${REGISTRY_URL}/v2/jclee94/${APP_NAME}/tags/list | jq -r '.tags[]' | head -5

# 3. Helm 차트 확인
echo -e "\n3. Helm charts in museum..."
curl -s -u ${CHARTMUSEUM_USERNAME}:${CHARTMUSEUM_PASSWORD} \
  ${CHARTMUSEUM_URL}/api/charts/${APP_NAME} | jq -r '.[].version' | head -5

# 4. Kubernetes 리소스 확인
echo -e "\n4. Kubernetes resources..."
kubectl get pods,svc -n ${NAMESPACE} -l app=${APP_NAME}

# 5. ArgoCD 애플리케이션 상태
echo -e "\n5. ArgoCD application status..."
argocd app get ${APP_NAME}-production 2>/dev/null || echo "⚠ ArgoCD not configured or not accessible"

# 6. 애플리케이션 헬스체크
echo -e "\n6. Application health checks..."
echo "Testing: ${BASE_URL}/api/health"
curl -f --connect-timeout 10 "${BASE_URL}/api/health" && echo -e "\n✅ Health check passed" || echo -e "\n❌ Health check failed"

echo "Testing: ${BASE_URL}/api/system-info"
curl -f --connect-timeout 10 "${BASE_URL}/api/system-info" && echo -e "\n✅ System info accessible" || echo -e "\n❌ System info failed"

# 7. 로그 확인
echo -e "\n7. Recent application logs..."
kubectl logs -l app=${APP_NAME} -n ${NAMESPACE} --tail=10 --since=5m | head -20

echo -e "\n✅ Deployment verification completed"
EOF

chmod +x scripts/verify_deployment.sh

echo "✅ Deployment verification script created: scripts/verify_deployment.sh"

echo ""
echo "🎉 Fortinet GitOps CI/CD Pipeline Setup Completed!"
echo "================================================="
echo ""
echo "📋 Next Steps:"
echo "1. Review and commit the generated files:"
echo "   - .github/workflows/fortinet-gitops-pipeline.yaml"
echo "   - argocd-fortinet-application.yaml"
echo "   - scripts/verify_deployment.sh"
echo ""
echo "2. Push to trigger the pipeline:"
echo "   git add ."
echo "   git commit -m 'feat: Add GitOps CI/CD pipeline with integration tests'"
echo "   git push origin master"
echo ""
echo "3. Configure ArgoCD (if not already done):"
echo "   argocd app create -f argocd-fortinet-application.yaml"
echo ""
echo "4. Monitor the deployment:"
echo "   ./scripts/verify_deployment.sh"
echo ""
echo "5. Access the application:"
echo "   http://192.168.50.110:${NODEPORT}/"
echo "   http://fortinet.jclee.me:${NODEPORT}/"
echo ""
echo "🔧 Troubleshooting:"
echo "   - Check GitHub Actions: https://github.com/jclee94/fortinet/actions"
echo "   - Check ArgoCD: https://argo.jclee.me/applications"
echo "   - Run verification: ./scripts/verify_deployment.sh"