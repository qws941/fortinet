# FortiGate Nextrade Claude Code Commands

Claude Code 슬래시 커맨드 시스템 - MCP 서버 기반 완전 자동화

## 🚀 핵심 커맨드

### `/main` - 완전 자동화 파이프라인 (v9.1.0)
가장 강력한 자동화 커맨드. 개발부터 배포까지 모든 과정을 자동화합니다.

```bash
/main                    # 전체 자동화 실행
/main verify            # 검증 모드
/main issues            # GitHub Issues 해결
/main monitor           # 실시간 모니터링
```

**실행 과정**:
1. 🔌 MCP 서버 초기화 (serena, filesystem, github 등)
2. 🔍 프로젝트 헬스 분석
3. 🧹 자동 코드 품질 개선 (black, isort, flake8)
4. 🧪 병렬 테스트 실행 (unit, integration, functional)
5. 🔒 보안 스캔 (bandit, safety)
6. 📤 자동 Git 커밋 및 푸시
7. 🏗️ CI/CD 파이프라인 트리거
8. 🏥 배포 검증 및 헬스 체크

### `/test` - 통합 테스트 자동화
```bash
/test                   # 전체 테스트 스위트
/test --unit           # 유닛 테스트만
/test --integration    # 통합 테스트만
/test --coverage       # 커버리지 리포트
```

### `/clean` - 코드 품질 자동화
```bash
/clean                 # 코드 정리 및 최적화
/clean --lint          # 린팅만
/clean --format        # 포맷팅만
/clean --security      # 보안 스캔만
```

### `/deploy` - GitOps 배포 자동화
```bash
/deploy                # 프로덕션 배포
/deploy --staging      # 스테이징 배포
/deploy --dry-run      # 배포 시뮬레이션
```

## 🔌 MCP 서버 통합

### 등록된 MCP 서버들
- **serena**: 프로젝트 관리 및 코드 분석
- **filesystem**: 파일 시스템 접근 및 관리
- **github**: GitHub 저장소 및 Actions 관리
- **brave-search**: 웹 검색 및 최신 정보
- **memory**: 지식 그래프 및 학습 데이터
- **puppeteer**: 웹 자동화 및 스크린샷
- **playwright**: 고급 웹 테스팅
- **eslint**: 코드 린팅 (JS/TS)
- **code-runner**: 코드 실행 및 테스트

### 자동화 워크플로우
```json
{
  "automated_development": {
    "servers": ["serena", "filesystem", "github"],
    "description": "개발 프로세스 완전 자동화"
  },
  "ci_cd_pipeline": {
    "servers": ["github", "serena"],
    "description": "CI/CD 파이프라인 자동화"
  },
  "research_optimization": {
    "servers": ["brave-search", "memory"],
    "description": "연구 및 최적화"
  }
}
```

## 🤖 자동화 규칙

### 자동 커밋
- 조건: 코드 품질 통과 + 테스트 통과
- 액션: 의미있는 커밋 메시지로 자동 커밋

### 자동 배포
- 조건: 메인 브랜치 + 모든 검사 통과
- 액션: GitHub Actions 트리거 → Docker 빌드 → ArgoCD 배포

### 자동 최적화
- 조건: 성능 문제 감지
- 액션: 최적화 제안 자동 적용

## 📊 모니터링 및 알림

### 헬스 체크
- **간격**: 5분마다
- **엔드포인트**: http://192.168.50.110:30777/api/health
- **자동 복구**: 서비스 다운 시 재시작

### 알림 시스템
- 배포 실패 알림
- 성능 저하 감지
- 보안 이슈 경고
- 테스트 실패 리포트

## 🔒 보안 및 권한

### API 키 관리
```bash
# 환경 변수를 통한 안전한 관리
GITHUB_TOKEN="${GITHUB_TOKEN}"
BRAVE_API_KEY="${BRAVE_API_KEY}"
```

### 접근 제어
- 허용 경로: `/home/jclee/app/fortinet`
- 금지 작업: 시스템 명령, 네트워크 접근
- 파일 접근 권한 제한

## 🎯 실제 사용 예시

### 1. 일반적인 개발 워크플로우
```bash
# 코드 변경 후
/main

# 결과:
# ✅ 코드 자동 정리됨
# ✅ 테스트 67/67 통과
# ✅ 자동 커밋 및 푸시 완료
# ✅ CI/CD 파이프라인 실행됨
# ✅ 배포 검증 완료
```

### 2. 긴급 수정 사항
```bash
# 빠른 수정 후
/main verify

# 검증 모드로 안전하게 확인 후 배포
```

### 3. GitHub Issues 자동 해결
```bash
/main issues

# GitHub Issues를 분석하고 해결 가능한 것들 자동 처리
```

## ⚙️ 고급 설정

### 환경 변수 설정
```bash
# ~/.bashrc 또는 ~/.zshrc
export MCP_CONFIG_PATH=".claude/mcp-integration-config.json"
export AUTO_COMMIT_ENABLED="true"
export AUTO_DEPLOY_ENABLED="true"
export HEALTH_CHECK_INTERVAL="5m"
```

### 커스텀 워크플로우 추가
```json
// .claude/custom-workflows.json
{
  "my_custom_flow": {
    "description": "나만의 워크플로우",
    "servers": ["serena", "github"],
    "steps": [
      {"action": "custom_validation", "server": "serena"}
    ]
  }
}
```

## 🛠️ 문제 해결

### 자주 발생하는 문제

#### 1. MCP 서버 연결 실패
```bash
# 서버 상태 확인
python .claude/automation-manager.py --check-servers

# 수동 재시작
/main --restart-mcp
```

#### 2. 테스트 실패
```bash
# 상세 로그 확인
/test --verbose

# 특정 테스트만 실행
/test --filter="test_api"
```

#### 3. 배포 실패
```bash
# 배포 상태 확인
kubectl get pods -n fortinet

# 수동 롤백
argocd app rollback fortinet
```

### 디버그 모드
```bash
# 상세 로그 활성화
DEBUG=true /main

# 단계별 실행
/main --step=test --verbose
```

## 📈 성능 최적화

### 병렬 처리
- 테스트: CPU 코어 수만큼 병렬 실행
- 빌드: Docker 이미지 동시 빌드
- MCP: 비동기 서버 통신

### 캐싱 전략
- Docker 레이어 캐싱
- Python 패키지 캐싱  
- 테스트 의존성 캐싱
- Git 객체 캐싱

## 📝 로그 및 리포팅

### 자동 리포트 생성
```bash
# 품질 리포트
cat quality-report.md

# 배포 요약
cat deployment-summary.md

# 자동화 로그
tail -f automation.log
```

### GitHub Actions Artifacts
- 품질 리포트
- 테스트 결과
- 보안 스캔 결과
- 배포 요약

## 🔄 업데이트 및 유지보수

### 자동 업데이트
- MCP 서버 자동 업데이트
- 의존성 보안 패치
- 설정 파일 검증

### 수동 유지보수
```bash
# 설정 검증
python .claude/automation-manager.py --validate-config

# 서버 상태 점검
python .claude/automation-manager.py --health-check

# 캐시 정리
/clean --cache
```

---

## 🎉 시작하기

1. **기본 실행**: `/main` 명령어로 모든 것이 자동화됩니다
2. **모니터링**: 실행 중 로그를 통해 진행 상황 확인
3. **결과 확인**: 자동 생성된 리포트로 결과 검토
4. **지속 개발**: 코드 변경 후 다시 `/main` 실행

**🚀 이제 개발-테스트-배포가 완전히 자동화되었습니다!**