#!/bin/bash
set -e

echo "🚀 Fortinet GitOps CI/CD Template Setup"
echo "======================================"

# 기존 파일 정리 (선택적)
# rm -rf .github/workflows/* || true
# rm -f docker-compose.yml *.log .env.* || true

# GitHub CLI 로그인 체크
echo "🔐 Checking GitHub CLI authentication..."
if ! gh auth status > /dev/null 2>&1; then
    echo "❌ GitHub CLI not authenticated. Please run: gh auth login"
    exit 1
fi

# Fortinet 프로젝트 특화 설정값
GITHUB_ORG="${GITHUB_ORG:-jclee94}"
APP_NAME="fortinet"
NAMESPACE="fortinet"
NODEPORT="30777"  # 현재 사용 중인 NodePort

# 기존 설정값 사용
REGISTRY_URL="${REGISTRY_URL:-registry.jclee.me}"
REGISTRY_USERNAME="${REGISTRY_USERNAME:-admin}"
REGISTRY_PASSWORD="${REGISTRY_PASSWORD:-bingogo1}"
CHARTMUSEUM_URL="${CHARTMUSEUM_URL:-https://charts.jclee.me}"
CHARTMUSEUM_USERNAME="${CHARTMUSEUM_USERNAME:-admin}"
CHARTMUSEUM_PASSWORD="${CHARTMUSEUM_PASSWORD:-bingogo1}"

echo "📋 Fortinet Configuration:"
echo "  App Name: ${APP_NAME}"
echo "  Namespace: ${NAMESPACE}"
echo "  NodePort: ${NODEPORT}"
echo "  Registry: ${REGISTRY_URL}"
echo "  Chart Museum: ${CHARTMUSEUM_URL}"

# GitHub Secrets 설정 (Variables는 워크플로우에서 하드코딩)
echo "🔑 Setting up GitHub secrets..."
gh secret list | grep -q "REGISTRY_URL" || gh secret set REGISTRY_URL -b "${REGISTRY_URL}"
gh secret list | grep -q "REGISTRY_USERNAME" || gh secret set REGISTRY_USERNAME -b "${REGISTRY_USERNAME}"
gh secret list | grep -q "REGISTRY_PASSWORD" || gh secret set REGISTRY_PASSWORD -b "${REGISTRY_PASSWORD}"
gh secret list | grep -q "CHARTMUSEUM_URL" || gh secret set CHARTMUSEUM_URL -b "${CHARTMUSEUM_URL}"
gh secret list | grep -q "CHARTMUSEUM_USERNAME" || gh secret set CHARTMUSEUM_USERNAME -b "${CHARTMUSEUM_USERNAME}"
gh secret list | grep -q "CHARTMUSEUM_PASSWORD" || gh secret set CHARTMUSEUM_PASSWORD -b "${CHARTMUSEUM_PASSWORD}"

echo "⚠ Note: GitHub Variables not supported in this CLI version - using hardcoded values in workflow"

# 기존 Helm Chart 업데이트 (새로 생성하지 않고 기존 것 사용)
echo "⚙️ Updating existing Helm chart configuration..."
if [ -d "charts/fortinet" ]; then
    # values.yaml에서 NodePort 확인 및 업데이트
    if grep -q "nodePort:" charts/fortinet/values.yaml; then
        sed -i "s/nodePort:.*/nodePort: ${NODEPORT}/" charts/fortinet/values.yaml
        echo "  ✅ NodePort updated to ${NODEPORT}"
    fi
    
    # 현재 차트 버전 확인
    CURRENT_VERSION=$(grep "^version:" charts/fortinet/Chart.yaml | cut -d' ' -f2 | tr -d '"')
    echo "  Current chart version: ${CURRENT_VERSION}"
else
    echo "❌ Helm chart not found at charts/fortinet"
    echo "   Using existing chart structure..."
fi

# 최적화된 GitHub Actions 워크플로우 생성
echo "🔨 Creating optimized GitHub Actions workflows..."
mkdir -p .github/workflows

cat > .github/workflows/fortinet-optimized-pipeline.yaml << 'EOF'
name: Fortinet Optimized CI/CD Pipeline

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
  PYTHON_VERSION: '3.11'
  APP_NAME: fortinet
  NAMESPACE: fortinet
  NODEPORT: 30777

jobs:
  # 1단계: 빠른 검증 - 코드 품질 & 단위 테스트
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
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'
          
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov flake8 black
          
      - name: Quick code quality check
        run: |
          echo "🧹 Running quick quality checks..."
          black --check src/ || echo "⚠ Formatting issues found"
          flake8 src/ --max-line-length=120 --ignore=E203,W503 --max-complexity=10 || echo "⚠ Code complexity issues"
          
      - name: Quick unit tests
        run: |
          echo "🧪 Running quick unit tests..."
          cd src
          pytest ../tests/unit/ -v --tb=short --maxfail=3 -x
          
      - name: Feature validation test
        run: |
          echo "✅ Running feature validation..."
          cd src
          python test_features.py
          
      - name: Check deployment eligibility
        id: check
        run: |
          if [ "${{ github.ref }}" == "refs/heads/master" ] || [ "${{ github.ref }}" == "refs/heads/main" ]; then
            echo "should-deploy=true" >> $GITHUB_OUTPUT
          else
            echo "should-deploy=false" >> $GITHUB_OUTPUT
          fi

  # 2단계: 통합 테스트 (배포가 필요한 경우에만)
  integration-tests:
    runs-on: self-hosted
    needs: quick-validation
    if: needs.quick-validation.outputs.should-deploy == 'true'
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'
          
      - name: Install test dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-xdist
          
      - name: Run integration tests
        run: |
          echo "🔗 Running integration tests..."
          export APP_MODE=test
          export OFFLINE_MODE=true
          export DISABLE_SOCKETIO=true
          cd src
          pytest ../tests/integration/ -v --tb=short --maxfail=5

  # 3단계: 빌드 & 배포
  build-and-deploy:
    runs-on: self-hosted
    needs: [quick-validation, integration-tests]
    if: needs.quick-validation.outputs.should-deploy == 'true'
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
          
      - name: Install Helm
        uses: azure/setup-helm@v3
        with:
          version: 'v3.14.0'
          
      - name: Package and deploy Helm chart
        run: |
          set -e
          
          CHART_VERSION="${{ steps.version.outputs.chart-version }}"
          IMAGE_TAG=$(echo "${{ steps.meta.outputs.tags }}" | head -n1 | cut -d: -f2)
          
          echo "📦 Updating Helm chart..."
          echo "  Chart Version: ${CHART_VERSION}"
          echo "  Image Tag: ${IMAGE_TAG}"
          
          # Chart 버전과 이미지 태그 업데이트
          sed -i "s/^version:.*/version: ${CHART_VERSION}/" ./charts/${APP_NAME}/Chart.yaml
          sed -i "s/^appVersion:.*/appVersion: \"${CHART_VERSION}\"/" ./charts/${APP_NAME}/Chart.yaml
          sed -i "s/tag:.*/tag: \"${IMAGE_TAG}\"/" ./charts/${APP_NAME}/values.yaml
          
          # Helm 차트 패키징
          helm package ./charts/${APP_NAME} --destination ./
          
          # ChartMuseum에 업로드
          CHART_FILE="${APP_NAME}-${CHART_VERSION}.tgz"
          
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
          
      - name: Verify deployment
        run: |
          echo "🔍 Waiting for deployment and verifying..."
          sleep 60  # ArgoCD sync 대기
          
          # 기본 헬스체크
          HEALTH_URL="http://192.168.50.110:${NODEPORT}/api/health"
          echo "Testing health endpoint: ${HEALTH_URL}"
          
          # 최대 5번 재시도
          for i in {1..5}; do
            if curl -f --connect-timeout 10 --max-time 30 "${HEALTH_URL}"; then
              echo "✅ Deployment verification successful"
              exit 0
            else
              echo "⏳ Health check failed, attempt ${i}/5"
              if [ ${i} -eq 5 ]; then
                echo "❌ Health check failed after 5 attempts"
                exit 1
              fi
              sleep 30
            fi
          done
EOF

echo "✅ Optimized GitHub Actions workflow created"

# 업데이트된 ArgoCD Application 설정
echo "🎯 Creating updated ArgoCD Application configuration..."
cat > argocd-fortinet-template-application.yaml << EOF
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: ${APP_NAME}-${NAMESPACE}
  namespace: argocd
  labels:
    app: ${APP_NAME}
    env: ${NAMESPACE}
  annotations:
    argocd.argoproj.io/sync-wave: "1"
spec:
  project: default
  source:
    repoURL: ${CHARTMUSEUM_URL}
    chart: ${APP_NAME}
    targetRevision: "*"
    helm:
      releaseName: ${APP_NAME}
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

echo "✅ ArgoCD Application configuration created"

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
cat > scripts/verify_fortinet_deployment.sh << 'EOF'
#!/bin/bash

APP_NAME="fortinet"
NAMESPACE="fortinet"
NODEPORT="30779"
BASE_URL="http://192.168.50.110:${NODEPORT}"

echo "🔍 Fortinet Template Deployment Verification"
echo "==========================================="

# 1. GitHub Actions 워크플로우 상태 확인
echo "1. GitHub Actions workflow status..."
gh run list --workflow="Fortinet Optimized CI/CD Pipeline" --limit 3

# 2. Docker 이미지 확인
echo -e "\n2. Docker images in registry..."
if command -v curl >/dev/null 2>&1; then
    curl -s -u ${REGISTRY_USERNAME}:${REGISTRY_PASSWORD} \
      https://${REGISTRY_URL}/v2/jclee94/${APP_NAME}/tags/list | \
      python3 -c "import sys,json; print('\n'.join(json.load(sys.stdin).get('tags', [])[:5]))" 2>/dev/null || \
      echo "Registry access failed or jq not available"
fi

# 3. Helm 차트 확인
echo -e "\n3. Helm charts in museum..."
if command -v curl >/dev/null 2>&1; then
    curl -s -u ${CHARTMUSEUM_USERNAME}:${CHARTMUSEUM_PASSWORD} \
      ${CHARTMUSEUM_URL}/api/charts/${APP_NAME} | \
      python3 -c "import sys,json; [print(chart['version']) for chart in json.load(sys.stdin)[:5]]" 2>/dev/null || \
      echo "ChartMuseum access failed"
fi

# 4. Kubernetes 리소스 확인
echo -e "\n4. Kubernetes resources..."
kubectl get pods,svc -n ${NAMESPACE} -l app=${APP_NAME}

# 5. ArgoCD 애플리케이션 상태
echo -e "\n5. ArgoCD application status..."
argocd app get ${APP_NAME}-${NAMESPACE} 2>/dev/null || echo "⚠ ArgoCD not configured or not accessible"

# 6. 애플리케이션 헬스체크
echo -e "\n6. Application health checks..."
echo "Testing: ${BASE_URL}/api/health"
if curl -f --connect-timeout 10 "${BASE_URL}/api/health" 2>/dev/null; then
    echo "✅ Health check passed"
else
    echo "❌ Health check failed"
fi

echo "Testing: ${BASE_URL}/api/system-info"
if curl -f --connect-timeout 10 "${BASE_URL}/api/system-info" 2>/dev/null; then
    echo "✅ System info accessible"
else
    echo "❌ System info failed"
fi

# 7. 로그 확인
echo -e "\n7. Recent application logs..."
kubectl logs -l app=${APP_NAME} -n ${NAMESPACE} --tail=10 --since=5m | head -20

echo -e "\n✅ Deployment verification completed"
EOF

chmod +x scripts/verify_fortinet_deployment.sh

echo "✅ Deployment verification script created: scripts/verify_fortinet_deployment.sh"

echo ""
echo "🎉 Fortinet GitOps CI/CD Template Setup Completed!"
echo "================================================="
echo ""
echo "📋 Files Created/Updated:"
echo "   - .github/workflows/fortinet-optimized-pipeline.yaml"
echo "   - argocd-fortinet-template-application.yaml"
echo "   - scripts/verify_fortinet_deployment.sh"
echo ""
echo "🚀 Next Steps:"
echo "1. Review and commit the generated files:"
echo "   git add ."
echo "   git commit -m 'feat: Add optimized GitOps CI/CD pipeline with template'"
echo "   git push origin master"
echo ""
echo "2. Configure ArgoCD (optional - can be done later):"
echo "   argocd app create -f argocd-fortinet-template-application.yaml --upsert"
echo ""
echo "3. Monitor the deployment:"
echo "   ./scripts/verify_fortinet_deployment.sh"
echo ""
echo "4. Access the application:"
echo "   http://192.168.50.110:${NODEPORT}/"
echo "   http://fortinet.jclee.me/"
echo ""
echo "🔧 Troubleshooting:"
echo "   - Check GitHub Actions: https://github.com/jclee94/fortinet/actions"
echo "   - Check ArgoCD: https://argo.jclee.me/applications"
echo "   - Run verification: ./scripts/verify_fortinet_deployment.sh"