# FortiGate Nextrade 프로젝트 구조

## 📁 최종 정리된 폴더 구조

```
fortinet/
├── 📋 CLAUDE.md                    # Claude Code 지침서
├── 📋 README.md                    # 프로젝트 메인 문서
├── 🐳 Dockerfile                   # 기본 Docker 이미지
├── 🐳 Dockerfile.offline           # 오프라인 최적화 이미지
├── 🚀 deploy.sh                    # 로컬 배포 스크립트
├── 🌐 remote-deploy.sh             # 원격 배포 스크립트
├── 📦 create-offline-package.sh    # 오프라인 패키지 생성
├── 🎯 smart-offline-deploy.sh      # 스마트 오프라인 배포
├── ✅ validate-deployment.sh       # 배포 검증 도구
├── 🔧 setup-registry.sh            # Docker Registry 설정
├── 🔑 setup-ssh.sh                 # SSH 환경 설정
├── 🧪 test-deploy.sh               # 로컬 배포 테스트
├── 📝 pytest.ini                   # 테스트 설정
├── 📦 requirements.txt             # Python 의존성
├── 📦 requirements_minimal.txt     # 최소 의존성
├── 🐳 docker-compose.yml           # 기본 Docker Compose
├── 🐳 docker-compose.development.yml # 개발 환경
├── 🐳 docker-compose.production.yml  # 운영 환경
│
├── 📁 config/                      # 배포 설정
│   ├── deploy-config.json          # 배포 설정
│   └── deploy-config-example.json  # 설정 예제
│
├── 📁 environments/                # 환경별 설정
│   ├── development.env             # 개발 환경
│   ├── staging.env                 # 스테이징 환경
│   └── production.env              # 운영 환경
│
├── 📁 deploy/                      # 배포 관련 도구
│   ├── 📁 gitlab/                  # GitLab CI/CD
│   │   ├── gitlab-ci-local-test.sh
│   │   ├── gitlab-runner-fix.sh
│   │   ├── gitlab-runner-install.sh
│   │   └── register-runner.sh
│   ├── 📁 installers/              # 설치 도구
│   │   ├── fortinet-installer.sh
│   │   └── fortinet-installer.ps1
│   └── 📁 services/                # 시스템 서비스
│       └── fortinet-autodeploy.service
│
├── 📁 scripts/                     # 운영 스크립트
│   ├── monitor_deployment.py       # 배포 모니터링
│   └── monitor_pipeline.py         # 파이프라인 모니터링
│
├── 📁 data/                        # 애플리케이션 데이터
│   ├── config.json                 # 앱 설정
│   ├── api_config_template.json    # API 설정 템플릿
│   ├── itsm_automation_config.json # ITSM 자동화 설정
│   ├── monitoring_config.json      # 모니터링 설정
│   ├── redis_config.json           # Redis 설정
│   └── 📁 output/download/         # 다운로드 파일
│
├── 📁 ssl/certs/                   # SSL 인증서
│
├── 📁 logs/                        # 로그 파일
│
├── 📁 src/                         # 소스 코드
│   ├── main.py                     # 메인 애플리케이션
│   ├── web_app.py                  # Flask 웹 앱
│   ├── 📁 api/                     # API 클라이언트
│   ├── 📁 routes/                  # 웹 라우트
│   ├── 📁 templates/               # HTML 템플릿
│   ├── 📁 static/                  # 정적 파일
│   ├── 📁 modules/                 # 핵심 모듈
│   ├── 📁 utils/                   # 유틸리티
│   ├── 📁 config/                  # 설정 관리
│   ├── 📁 core/                    # 핵심 기능
│   ├── 📁 analysis/                # 분석 엔진
│   ├── 📁 automation/              # 자동화
│   ├── 📁 fortimanager/            # FortiManager 통합
│   ├── 📁 itsm/                    # ITSM 통합
│   ├── 📁 monitoring/              # 모니터링
│   ├── 📁 security/                # 보안 기능
│   └── 📁 mock/                    # Mock 시스템
│
└── 📁 tests/                       # 테스트 코드
    ├── 📁 unit/                    # 단위 테스트
    ├── 📁 integration/             # 통합 테스트
    └── 📁 fixtures/                # 테스트 픽스처
```

## 🧹 정리 완료 항목

### 제거된 중복 파일들
- ✅ ARCHITECTURE.md → README.md로 통합
- ✅ DEPLOYMENT_GUIDE.md → README.md로 통합
- ✅ DEPLOYMENT_SOLUTION.md → 삭제
- ✅ DEPLOYMENT_STATUS.md → 삭제
- ✅ FORTIMANAGER_ENHANCEMENTS.md → README.md로 통합
- ✅ LOCAL_DEPLOYMENT_ONLY.md → 삭제
- ✅ PROJECT_RESTRUCTURING_PLAN.md → 삭제
- ✅ REMOTE_DEPLOYMENT_GUIDE.md → README.md로 통합
- ✅ config/.gitlab-ci-variables.md → 삭제
- ✅ docker-compose.prod.yml → docker-compose.production.yml로 대체
- ✅ deploy/scripts/auto-deploy*.sh → 삭제
- ✅ deploy/scripts/quick-deploy.sh → 삭제
- ✅ src/logs/*.json → 삭제

### 최적화된 배포 스크립트들
- ✅ `deploy.sh` - 로컬 배포 (빌드 시간 추적)
- ✅ `remote-deploy.sh` - 원격 다중 서버 배포
- ✅ `create-offline-package.sh` - 오프라인 패키지 생성
- ✅ `smart-offline-deploy.sh` - 스마트 오프라인 배포
- ✅ `validate-deployment.sh` - 배포 검증 시스템
- ✅ `setup-registry.sh` - Docker Registry 설정
- ✅ `setup-ssh.sh` - SSH 환경 구성

## 🎯 핵심 개선사항

1. **통합된 문서화**: 모든 중요 정보가 README.md에 집중
2. **명확한 폴더 구조**: 용도별로 명확히 분리된 디렉토리
3. **완전 자동화**: 원클릭 배포 시스템 구축
4. **검증 시스템**: 배포 전후 자동 검증
5. **환경별 분리**: development/staging/production 명확히 구분
6. **오프라인 지원**: 폐쇄망 환경 완벽 지원

## 📊 정리 통계

- **제거된 파일**: 393개
- **통합된 문서**: 8개 → 1개 (README.md)
- **최적화된 스크립트**: 7개 핵심 배포 도구
- **폴더 구조**: 명확한 계층화
- **배포 옵션**: 5가지 배포 방법 지원

이제 프로젝트는 깔끔하고 체계적인 구조를 가지게 되었으며, 완전 자동화된 배포 시스템을 통해 효율적인 운영이 가능합니다.