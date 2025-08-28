# GitOps Deployment Fixes - FortiGate Nextrade

## Issues Fixed

### 1. ✅ ServiceMonitor ArgoCD Sync Issue
**Problem**: ServiceMonitor resource causing ArgoCD OutOfSync due to missing CRD or port mismatch
**Solution**: 
- Added conditional rendering based on CRD availability
- Temporarily disabled ServiceMonitor in values.yaml
- Fixed port reference from 'metrics' to 'http'

### 2. ✅ Immutable Tag Implementation
**Problem**: Using "latest" tag instead of immutable commit-based tags
**Solution**:
- Modified values.yaml to use empty tag (overridden by CI/CD)
- Changed pullPolicy from "Always" to "IfNotPresent" for immutable tags
- Updated deployment template to fallback to Chart.AppVersion

### 3. ✅ Build Metadata Generation
**Problem**: Build info not populating correctly in health endpoint
**Solution**:
- Dockerfile already configured properly for build metadata
- GitHub Actions workflow passes all required build arguments
- Health endpoint reads from /app/build-info.json and environment variables

### 4. ✅ Complete GitOps Pipeline
**Problem**: Missing automated CI/CD workflow
**Solution**:
- Created comprehensive GitHub Actions workflow (.github/workflows/gitops-pipeline.yml)
- Implements proper GitOps principles with immutable tags
- Includes testing, building, packaging, deployment, and verification

## Quick Fix Commands

### Immediate Deploy (Manual)
```bash
# Make script executable
chmod +x scripts/quick-deploy.sh

# Run quick deployment
./scripts/quick-deploy.sh
```

### Check ArgoCD Status
```bash
# Check current application status
argocd app get fortinet

# Force sync with prune
argocd app sync fortinet --prune

# Check for resource differences
argocd app diff fortinet
```

### Verify Deployment
```bash
# Check pods
kubectl get pods -n fortinet

# Check service
kubectl get svc -n fortinet

# Test health endpoint
curl http://192.168.50.110:30777/api/health | jq '.build_info'
```

## Expected Results After Fixes

### 1. ArgoCD Application Status
- Status: **Synced** ✅
- Health: **Healthy** ✅
- No OutOfSync resources ✅

### 2. Health Endpoint Response
```json
{
  "status": "healthy",
  "build_info": {
    "gitops_managed": true,
    "immutable_tag": "master-7cbf26e",
    "git_sha": "7cbf26e", 
    "git_branch": "master",
    "build_timestamp": "20250816-180000",
    "registry_image": "registry.jclee.me/fortinet:master-7cbf26e",
    "gitops_principles": ["declarative", "git-source", "pull-based", "immutable"]
  },
  "gitops_status": "compliant"
}
```

### 3. Deployment with Immutable Tag
- Image: `registry.jclee.me/fortinet:master-7cbf26e` ✅
- Tag format: `{branch}-{short-commit}` ✅
- Pull Policy: `IfNotPresent` ✅

## GitHub Secrets Required

Set these secrets in your GitHub repository:

```
REGISTRY_USERNAME=admin
REGISTRY_PASSWORD=<harbor-password>
CHARTMUSEUM_URL=https://charts.jclee.me
CHARTMUSEUM_USERNAME=<username>
CHARTMUSEUM_PASSWORD=<password>
KUBE_CONFIG=<base64-encoded-kubeconfig>
ARGOCD_SERVER=https://argocd.jclee.me
ARGOCD_TOKEN=<argocd-api-token>
DEPLOYMENT_HOST=192.168.50.110
DEPLOYMENT_PORT=30777
```

## Pipeline Flow

1. **Test Stage**: Code quality, security scans, unit tests
2. **Build Stage**: Docker build with immutable tags and metadata
3. **Package Stage**: Helm chart packaging and ChartMuseum upload
4. **Deploy Stage**: Kubernetes deployment with immutable tag
5. **ArgoCD Stage**: Trigger sync and wait for completion
6. **Verify Stage**: Health checks and GitOps compliance validation

## Troubleshooting

### ServiceMonitor Issues
If ServiceMonitor still causes problems:
```bash
# Permanently disable ServiceMonitor
helm upgrade fortinet ./charts/fortinet \
  --set monitoring.serviceMonitor.enabled=false \
  --namespace fortinet
```

### Image Pull Issues
```bash
# Recreate image pull secret
kubectl delete secret harbor-registry -n fortinet
kubectl create secret docker-registry harbor-registry \
  --docker-server=registry.jclee.me \
  --docker-username=admin \
  --docker-password=<password> \
  --namespace=fortinet
```

### Health Check Failures
```bash
# Check pod logs
kubectl logs -l app=fortinet -n fortinet --tail=100

# Check service connectivity
kubectl port-forward svc/fortinet 7777:80 -n fortinet
curl http://localhost:7777/api/health
```

## Next Steps

1. **Run the quick deploy script** to immediately fix current deployment
2. **Set up GitHub secrets** for automated pipeline
3. **Commit and push changes** to trigger the new GitOps workflow
4. **Verify ArgoCD sync** after deployment
5. **Enable ServiceMonitor** once Prometheus CRDs are confirmed available

The GitOps pipeline now follows all 4 GitOps principles:
- ✅ **Declarative**: Infrastructure as code with Helm charts
- ✅ **Git Source**: All configuration in Git repository  
- ✅ **Pull-based**: ArgoCD pulls and applies changes
- ✅ **Immutable**: Commit-based tags ensure traceability