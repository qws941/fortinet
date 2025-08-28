# GitHub Secrets 설정 가이드

## 🚨 현재 문제
CI/CD 파이프라인이 Docker 레지스트리 로그인 실패로 인해 실패하고 있습니다.

```
X 🔐 Log in to Registry
Username and password required
```

## 🔑 필요한 GitHub Secrets

### 1. Docker 레지스트리 인증 정보
- `DOCKER_USERNAME`: qws941
- `DOCKER_PASSWORD`: bingogo1

## 📝 설정 방법

### 방법 1: GitHub CLI 사용 (권장)
```bash
# Docker 사용자명 설정
gh secret set DOCKER_USERNAME -b "qws941" -R JCLEE94/fortinet

# Docker 비밀번호 설정
gh secret set DOCKER_PASSWORD -b "bingogo1" -R JCLEE94/fortinet
```

### 방법 2: GitHub 웹 인터페이스 사용
1. https://github.com/JCLEE94/fortinet/settings/secrets/actions 접속
2. "New repository secret" 클릭
3. 다음 secrets 추가:
   - Name: `DOCKER_USERNAME`, Value: `qws941`
   - Name: `DOCKER_PASSWORD`, Value: `bingogo1`

### 방법 3: 환경 변수로 설정 (로컬 테스트용)
```bash
export DOCKER_USERNAME="qws941"
export DOCKER_PASSWORD="bingogo1"
```

## 🔍 설정 확인

### Secrets 목록 확인
```bash
gh secret list -R JCLEE94/fortinet
```

### 파이프라인 재실행
```bash
# 최신 실패한 워크플로우 재실행
gh run rerun 15888381064

# 또는 새로운 푸시로 트리거
git commit --allow-empty -m "trigger: CI/CD pipeline test"
git push origin master
```

## 📊 선택적 설정 (권장)

### GitHub Variables 설정
```bash
# Docker 레지스트리 URL
gh variable set DOCKER_REGISTRY -b "registry.jclee.me" -R JCLEE94/fortinet

# Docker 이미지 이름
gh variable set DOCKER_IMAGE_NAME -b "fortinet" -R JCLEE94/fortinet

# Python 버전
gh variable set PYTHON_VERSION -b "3.11" -R JCLEE94/fortinet
```

## 🛡️ 보안 권장사항

### 더 안전한 방법들:
1. **Personal Access Token 사용**
   ```bash
   # Docker Hub에서 PAT 생성 후
   gh secret set DOCKER_TOKEN -b "your-pat-token" -R JCLEE94/fortinet
   ```

2. **GitHub Environments 사용**
   - production 환경 생성
   - 환경별 secrets 설정
   - 보호 규칙 추가

3. **OIDC (OpenID Connect) 설정**
   - 비밀번호 없는 인증
   - 더 안전한 방법

## 🚀 즉시 해결 방법

가장 빠른 해결책:
```bash
# 1. Secrets 설정
gh secret set DOCKER_USERNAME -b "qws941" -R JCLEE94/fortinet
gh secret set DOCKER_PASSWORD -b "bingogo1" -R JCLEE94/fortinet

# 2. 확인
gh secret list -R JCLEE94/fortinet

# 3. 파이프라인 재실행
gh run rerun 15888381064
```

## 📈 예상 결과

설정 완료 후:
- ✅ Docker 레지스트리 로그인 성공
- ✅ 이미지 빌드 및 푸시 성공
- ✅ CI/CD 파이프라인 전체 성공

## 🔗 참고 자료
- [GitHub Secrets 문서](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [Docker Hub Access Tokens](https://docs.docker.com/security/for-developers/access-tokens/)
- [GitHub Actions 보안 강화](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions)