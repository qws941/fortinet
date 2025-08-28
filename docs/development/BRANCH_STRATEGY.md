# FortiGate Nextrade - 고급 브랜치 전략 가이드

## 📋 개요

FortiGate Nextrade 프로젝트는 Git Flow를 기반으로 한 고급 브랜치 전략을 채택하여 안정적인 개발 및 배포 환경을 제공합니다.

## 🌿 브랜치 구조

### 영구 브랜치 (Permanent Branches)

#### 1. `main` (Production Branch)
- **목적**: 프로덕션 릴리스 브랜치
- **배포**: 프로덕션 환경 (fortinet.jclee.me)
- **보호 수준**: 최고 (Direct push 금지, PR만 허용)
- **자동화**: 릴리스 태그 시 자동 배포

```bash
# 프로덕션 배포 확인
curl https://fortinet.jclee.me/api/health
```

#### 2. `develop` (Integration Branch)
- **목적**: 개발 통합 브랜치
- **배포**: 개발 환경 (dev-fortinet.jclee.me)
- **보호 수준**: 높음 (PR 리뷰 필수, CI 통과 필수)
- **자동화**: 푸시 시 자동 통합 테스트

### 임시 브랜치 (Temporary Branches)

#### 3. `feature/*` (Feature Branches)
- **네이밍**: `feature/FORT-123-new-monitoring-system`
- **소스**: `develop`에서 분기
- **병합 대상**: `develop`
- **라이프사이클**: 기능 완성 후 삭제

```bash
# Feature 브랜치 생성
git checkout develop
git checkout -b feature/FORT-123-advanced-analytics
```

#### 4. `release/*` (Release Branches)
- **네이밍**: `release/v1.2.0`
- **소스**: `develop`에서 분기
- **병합 대상**: `main` 및 `develop`
- **라이프사이클**: 릴리스 후 삭제

```bash
# Release 브랜치 생성
git checkout develop
git checkout -b release/v1.2.0
```

#### 5. `hotfix/*` (Hotfix Branches)
- **네이밍**: `hotfix/v1.1.1-critical-security-fix`
- **소스**: `main`에서 분기
- **병합 대상**: `main` 및 `develop`
- **라이프사이클**: 핫픽스 배포 후 삭제

```bash
# Hotfix 브랜치 생성
git checkout main
git checkout -b hotfix/v1.1.1-security-patch
```

## 🔒 브랜치 보호 규칙

### Main Branch Protection
```yaml
required_status_checks:
  strict: true
  contexts:
    - "ci/security-scan"
    - "ci/unit-tests"
    - "ci/integration-tests"
    - "ci/performance-tests"
    - "ci/compliance-check"

enforce_admins: true
required_pull_request_reviews:
  required_approving_review_count: 2
  dismiss_stale_reviews: true
  require_code_owner_reviews: true
  require_last_push_approval: true

restrictions:
  users: []
  teams: ["senior-developers"]
  apps: ["github-actions"]

allow_force_pushes: false
allow_deletions: false
```

### Develop Branch Protection
```yaml
required_status_checks:
  strict: true
  contexts:
    - "ci/unit-tests"
    - "ci/integration-tests"
    - "ci/code-quality"

required_pull_request_reviews:
  required_approving_review_count: 1
  dismiss_stale_reviews: true

allow_force_pushes: false
allow_deletions: false
```

## 🚀 CI/CD 파이프라인 통합

### Branch-Based Deployment Strategy

| 브랜치 | 환경 | 트리거 | 배포 방식 | 승인 |
|--------|------|--------|-----------|------|
| `main` | Production | Tag push | GitOps (ArgoCD) | Manual |
| `develop` | Development | Push | Auto-deploy | None |
| `feature/*` | Feature Env | Push | Preview deploy | None |
| `release/*` | Staging | Push | Auto-deploy | QA Team |
| `hotfix/*` | Hotfix Staging | Push | Auto-deploy | Emergency |

### Pipeline Configuration

#### Main Branch Pipeline
```yaml
name: Production Deployment
on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Security Scan
        run: |
          bandit -r src/
          safety check
          trivy fs .

  compliance-check:
    runs-on: ubuntu-latest
    steps:
      - name: GDPR Compliance
        run: ./scripts/compliance-check.sh
      - name: Security Standards
        run: ./scripts/security-audit.sh

  deploy-production:
    needs: [security-scan, compliance-check]
    if: startsWith(github.ref, 'refs/tags/v')
    runs-on: ubuntu-latest
    environment: production
    steps:
      - name: Deploy to Production
        run: |
          argocd app sync fortinet-prod
          ./scripts/verify-deployment.sh production
```

#### Develop Branch Pipeline
```yaml
name: Development Integration
on:
  push:
    branches: [develop]
  pull_request:
    branches: [develop]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Unit Tests
        run: |
          pytest tests/unit/ -v --cov=src
          
  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - name: Run Integration Tests
        run: |
          pytest tests/integration/ -v
          pytest tests/msa/ -v

  auto-deploy:
    needs: [unit-tests, integration-tests]
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Development
        run: |
          kubectl apply -f k8s/environments/development/
          kubectl rollout status deployment/fortinet-dev
```

## 🔄 워크플로우 가이드

### Feature Development Workflow

1. **Feature 브랜치 생성**
```bash
git checkout develop
git pull origin develop
git checkout -b feature/FORT-123-new-dashboard
```

2. **개발 및 커밋**
```bash
git add .
git commit -m "feat(dashboard): add real-time metrics visualization

- Implement ApexCharts integration
- Add responsive design support
- Include dark mode compatibility
- Add unit tests for chart components

Closes #123"
```

3. **PR 생성 및 리뷰**
```bash
gh pr create --title "feat: Advanced Dashboard with Real-time Metrics" \
  --body "## 변경사항
- 실시간 메트릭 시각화 추가
- ApexCharts 라이브러리 통합
- 반응형 디자인 지원

## 테스트
- [x] 단위 테스트 추가
- [x] 통합 테스트 통과
- [x] 성능 테스트 완료

## 체크리스트
- [x] 코드 리뷰 완료
- [x] CI 파이프라인 통과
- [x] 문서 업데이트"
```

### Release Workflow

1. **Release 브랜치 생성**
```bash
git checkout develop
git pull origin develop
git checkout -b release/v1.2.0
```

2. **버전 업데이트**
```bash
echo "1.2.0" > VERSION
sed -i 's/version: .*/version: 1.2.0/' charts/fortinet/Chart.yaml
git add VERSION charts/fortinet/Chart.yaml
git commit -m "chore: bump version to 1.2.0"
```

3. **릴리스 노트 작성**
```bash
cat > CHANGELOG.md << 'EOF'
# Changelog

## [1.2.0] - 2025-08-28

### Added
- Advanced real-time dashboard with ApexCharts
- Enhanced security monitoring system
- MSA service mesh integration
- Automated compliance checking

### Changed
- Improved API response times by 25%
- Enhanced Docker image optimization
- Updated Kubernetes manifests for v1.28

### Fixed
- Resolved memory leak in packet sniffer
- Fixed FortiManager authentication issues
- Corrected timezone handling in logs

### Security
- Updated all dependencies to latest versions
- Added additional input validation
- Implemented rate limiting on API endpoints
EOF
```

4. **Release 완료**
```bash
# Release branch를 main에 병합
gh pr create --base main --title "chore: Release v1.2.0"

# 병합 후 태그 생성
git checkout main
git pull origin main
git tag -a v1.2.0 -m "Release version 1.2.0"
git push origin v1.2.0
```

### Hotfix Workflow

1. **긴급 수정 브랜치 생성**
```bash
git checkout main
git pull origin main
git checkout -b hotfix/v1.1.1-security-patch
```

2. **수정 및 테스트**
```bash
# 보안 취약점 수정
git add .
git commit -m "security: fix SQL injection vulnerability in API endpoint

- Sanitize input parameters in /api/fortimanager/policies
- Add input validation middleware
- Update security tests

CVE-2025-XXXX"
```

3. **긴급 배포**
```bash
# Main 및 Develop에 병합
gh pr create --base main --title "security: Critical security patch v1.1.1"
gh pr create --base develop --title "security: Backport security patch to develop"

# 태그 생성 및 배포
git checkout main
git tag -a v1.1.1 -m "Security patch v1.1.1"
git push origin v1.1.1
```

## 📊 브랜치 모니터링 및 분석

### Branch Health Metrics
```bash
# 브랜치 상태 체크 스크립트
#!/bin/bash
echo "=== Branch Health Report ==="
echo "Main branch commits ahead: $(git rev-list develop..main --count)"
echo "Develop branch commits ahead: $(git rev-list main..develop --count)"
echo "Active feature branches: $(git branch -r | grep feature | wc -l)"
echo "Stale branches (>30 days): $(git for-each-ref --format='%(refname:short) %(committerdate)' refs/remotes | awk '$2 < "'$(date -d '30 days ago' '+%Y-%m-%d')'"' | wc -l)"
```

### Automated Branch Cleanup
```yaml
name: Branch Cleanup
on:
  schedule:
    - cron: '0 2 * * 0'  # Weekly on Sunday at 2 AM

jobs:
  cleanup-merged-branches:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0
      - name: Delete merged branches
        run: |
          git branch -r --merged main | 
          grep -v main | 
          grep -v develop | 
          sed 's/origin\///' | 
          xargs -n 1 git push --delete origin
```

## 🛡️ 보안 및 컴플라이언스

### Commit Message Standards
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: 새로운 기능
- `fix`: 버그 수정
- `docs`: 문서 변경
- `style`: 코드 스타일 (formatting, semi colons, etc)
- `refactor`: 코드 리팩토링
- `test`: 테스트 추가/수정
- `chore`: 빌드 관련 작업
- `security`: 보안 관련 수정
- `perf`: 성능 개선

### Pre-commit Hooks
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=120]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.3.0
    hooks:
      - id: mypy

  - repo: local
    hooks:
      - id: security-scan
        name: Security Scan
        entry: bandit -r src/
        language: system
        pass_filenames: false
```

## 🎯 모범 사례

### DO's
- ✅ 브랜치명은 항상 이슈 번호와 함께 사용
- ✅ 커밋 메시지는 컨벤션을 준수
- ✅ Feature 브랜치는 작고 집중된 기능으로 제한
- ✅ PR은 리뷰 전에 CI가 통과해야 함
- ✅ Merge 전에 브랜치를 최신 상태로 유지
- ✅ 완료된 브랜치는 즉시 삭제

### DON'Ts
- ❌ Main/Develop 브랜치에 직접 푸시 금지
- ❌ Force push 사용 금지 (특별한 경우 제외)
- ❌ 장기간 유지되는 Feature 브랜치
- ❌ 리뷰 없는 코드 병합
- ❌ CI 실패 시 강제 병합
- ❌ 커밋 메시지 컨벤션 무시

## 🔧 도구 및 자동화

### GitHub CLI 활용
```bash
# 자주 사용하는 명령어들
alias gh-feature="gh pr create --draft --base develop"
alias gh-release="gh pr create --base main --title 'chore: Release'"
alias gh-hotfix="gh pr create --base main --title 'hotfix:'"

# 브랜치 상태 확인
gh pr status
gh pr list --state open
gh repo view --branch main
```

### IDE 통합
```json
// VSCode settings.json
{
  "git.branchProtection": ["main", "develop"],
  "git.confirmForcePush": true,
  "git.showPushSuccessNotification": true,
  "gitlens.advanced.messages": {
    "suppressCommitHasNoPreviousCommitWarning": false
  }
}
```

## 📈 성과 측정

### KPI Metrics
- **Lead Time**: Feature 개발 시작부터 프로덕션 배포까지 시간
- **Deployment Frequency**: 프로덕션 배포 빈도
- **Change Failure Rate**: 배포 실패율
- **Mean Time to Recovery**: 장애 복구 평균 시간

### 모니터링 대시보드
```bash
# GitHub API를 활용한 메트릭 수집
curl -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/qws941/fortinet/pulls?state=closed&per_page=100" \
  | jq '.[] | {number: .number, merged_at: .merged_at, created_at: .created_at}'
```

---

이 브랜치 전략을 통해 FortiGate Nextrade 프로젝트는 안정적이고 예측 가능한 개발 프로세스를 유지하며, 고품질의 소프트웨어를 지속적으로 배포할 수 있습니다.