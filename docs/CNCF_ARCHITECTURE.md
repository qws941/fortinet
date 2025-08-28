# CNCF Cloud Native Architecture

FortiGate Nextrade 프로젝트의 CNCF(Cloud Native Computing Foundation) 표준 아키텍처 문서입니다.

## 📋 목차

- [아키텍처 개요](#아키텍처-개요)
- [디렉토리 구조](#디렉토리-구조)
- [12-Factor App 준수](#12-factor-app-준수)
- [컨테이너 전략](#컨테이너-전략)
- [Kubernetes 통합](#kubernetes-통합)
- [관찰가능성](#관찰가능성)
- [보안 모델](#보안-모델)
- [확장성 및 성능](#확장성-및-성능)

## 🏗️ 아키텍처 개요

FortiGate Nextrade는 CNCF 표준을 준수하는 클라우드 네이티브 애플리케이션으로 설계되었습니다.

### 핵심 원칙

1. **마이크로서비스 아키텍처**: 느슨하게 결합된 서비스들
2. **컨테이너 우선**: Docker 기반 배포 및 실행
3. **선언적 관리**: Kubernetes 매니페스트 및 Helm 차트
4. **관찰가능성**: 구조화된 로깅, 메트릭, 추적
5. **복원력**: 장애 허용 및 자동 복구

### 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────────────────┐
│                      CNCF Cloud Native Stack                   │
├─────────────────────────────────────────────────────────────────┤
│ Frontend: Browser → Ingress Controller → Service Mesh          │
├─────────────────────────────────────────────────────────────────┤
│ Application Layer                                               │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐               │
│ │ Web Gateway │ │   API       │ │ Background  │               │
│ │   Service   │ │  Services   │ │   Workers   │               │
│ └─────────────┘ └─────────────┘ └─────────────┘               │
├─────────────────────────────────────────────────────────────────┤
│ Infrastructure Layer                                            │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐               │
│ │   Redis     │ │ PostgreSQL  │ │   Message   │               │
│ │   Cache     │ │  Database   │ │    Queue    │               │
│ └─────────────┘ └─────────────┘ └─────────────┘               │
├─────────────────────────────────────────────────────────────────┤
│ Platform Layer: Kubernetes + Helm + ArgoCD                     │
├─────────────────────────────────────────────────────────────────┤
│ Observability: Prometheus + Grafana + Jaeger                   │
└─────────────────────────────────────────────────────────────────┘
```

## 📁 디렉토리 구조

CNCF 표준 Go 프로젝트 레이아웃을 Python 프로젝트에 적용:

```
fortinet/
├── cmd/                    # 애플리케이션 진입점
│   └── fortinet/
│       └── main.py        # 메인 엔트리 포인트
├── pkg/                    # 공개 라이브러리
│   ├── api/               # 공개 API 클라이언트
│   ├── config/            # 설정 관리
│   ├── monitoring/        # 모니터링 유틸리티
│   └── security/          # 보안 라이브러리
├── internal/              # 내부 애플리케이션 코드
│   ├── app/              # 애플리케이션 로직
│   ├── handlers/         # HTTP 핸들러
│   ├── middleware/       # 미들웨어
│   ├── service/          # 비즈니스 로직
│   └── repository/       # 데이터 액세스
├── build/                 # 빌드 및 CI/CD
│   ├── docker/           # Docker 설정
│   ├── ci/               # CI/CD 파이프라인
│   └── helm/             # Helm 차트
├── deployments/           # 배포 매니페스트
│   ├── k8s/              # Kubernetes YAML
│   └── helm/             # Helm 차트
├── test/                  # 테스트 (CNCF 표준)
│   ├── unit/             # 단위 테스트
│   ├── integration/      # 통합 테스트
│   └── e2e/              # End-to-End 테스트
├── docs/                  # 문서
├── scripts/               # 유틸리티 스크립트
├── Makefile              # 빌드 자동화
└── go.mod                # Go 호환성 (툴링용)
```

## 📏 12-Factor App 준수

### I. Codebase
- 단일 Git 저장소에서 버전 관리
- 여러 환경에 동일한 코드베이스 배포

### II. Dependencies
- `requirements.txt`와 `pyproject.toml`로 의존성 명시
- 가상 환경으로 의존성 격리

### III. Config
- 환경 변수로 설정 분리
- `pkg/config/settings.py`에서 설정 관리

```python
# 환경별 설정 예시
config = {
    'app_mode': os.getenv('APP_MODE', 'production'),
    'database_url': os.getenv('DATABASE_URL'),
    'redis_url': os.getenv('REDIS_URL')
}
```

### IV. Backing Services
- 외부 서비스를 첨부된 리소스로 취급
- 설정을 통해 서비스 교체 가능

### V. Build, Release, Run
- 빌드, 릴리스, 실행 단계 명확히 분리
- CI/CD 파이프라인으로 자동화

### VI. Processes
- 무상태 프로세스로 실행
- 상태는 외부 데이터 저장소에 저장

### VII. Port Binding
- HTTP 서비스를 포트로 바인딩해서 외부 노출
- 컨테이너 포트 7777로 서비스 제공

### VIII. Concurrency
- 프로세스 모델로 확장
- Kubernetes HPA로 수평 확장

### IX. Disposability
- 빠른 시작과 우아한 종료
- 신호 핸들러로 graceful shutdown 구현

### X. Dev/Prod Parity
- 개발, 스테이징, 프로덕션 환경 최대한 유사하게 유지
- 컨테이너로 환경 일관성 보장

### XI. Logs
- 로그를 이벤트 스트림으로 취급
- 구조화된 JSON 로깅

### XII. Admin Processes
- 관리 태스크를 일회성 프로세스로 실행
- `python cmd/fortinet/main.py --analyze` 등

## 🐳 컨테이너 전략

### Multi-stage Dockerfile

```dockerfile
# 빌드 스테이지
FROM python:3.11-slim as builder
# 의존성 설치 및 애플리케이션 빌드

# 런타임 스테이지  
FROM python:3.11-slim as runtime
# 최소한의 런타임 환경
# 비루트 사용자로 실행
# 보안 강화 설정
```

### 보안 강화
- 비루트 사용자로 컨테이너 실행
- 최소 권한 원칙 적용
- 취약점 스캔 통합 (Trivy)
- 이미지 서명 및 검증

### 최적화
- Layer 캐싱 최적화
- Multi-platform 빌드 (amd64, arm64)
- 이미지 크기 최소화

## ⚓ Kubernetes 통합

### Health Checks

```yaml
# Liveness Probe
livenessProbe:
  httpGet:
    path: /health
    port: 7777
  initialDelaySeconds: 30
  periodSeconds: 10

# Readiness Probe  
readinessProbe:
  httpGet:
    path: /ready
    port: 7777
  initialDelaySeconds: 5
  periodSeconds: 5
```

### Resource Management

```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "100m"
  limits:
    memory: "512Mi" 
    cpu: "500m"
```

### Horizontal Pod Autoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
spec:
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

## 📊 관찰가능성

### 구조화된 로깅
- JSON 형태의 구조화된 로그
- 분산 추적 ID 포함
- 중앙 집중식 로그 수집

### 메트릭 수집
- Prometheus 형식 메트릭 제공
- 애플리케이션 성능 지표
- 비즈니스 메트릭

### 분산 추적
- 요청 추적 ID 생성
- Jaeger 호환 추적 데이터
- 서비스 간 호출 추적

### 모니터링 엔드포인트

```python
@app.route('/health')     # 헬스 체크
@app.route('/ready')      # 준비 상태 확인  
@app.route('/metrics')    # Prometheus 메트릭
@app.route('/version')    # 버전 정보
```

## 🔒 보안 모델

### 컨테이너 보안
- 비루트 사용자 실행
- 읽기 전용 루트 파일시스템
- 최소 권한 Linux capabilities

### 네트워크 보안
- Service Mesh (Istio) 지원
- mTLS 암호화
- Network Policies

### 시크릿 관리
- Kubernetes Secrets 사용
- 외부 시크릿 관리 시스템 연동
- 환경 변수로 민감 정보 주입 금지

### API 보안
- API 키 기반 인증
- Rate limiting
- CORS 정책 적용

## 📈 확장성 및 성능

### 수평 확장
- Stateless 애플리케이션 설계
- Kubernetes HPA 활용
- 로드 밸런싱

### 성능 최적화
- 연결 풀링
- 캐싱 전략
- 비동기 처리

### 데이터베이스 확장
- Redis 클러스터링
- 읽기 복제본 활용
- 샤딩 지원

## 🔄 GitOps 및 CI/CD

### GitOps 워크플로우
1. 코드 변경 → Git Push
2. GitHub Actions → 이미지 빌드
3. Harbor Registry → 이미지 저장
4. ArgoCD → 자동 배포
5. Kubernetes → 애플리케이션 실행

### 배포 전략
- Rolling Update (기본)
- Blue-Green 배포
- Canary 배포

### 파이프라인 단계
1. **Code Quality**: Linting, Security Scan
2. **Testing**: Unit, Integration, E2E
3. **Build**: Container Image Build
4. **Security**: Container Vulnerability Scan
5. **Deploy**: Helm Chart Deploy
6. **Verify**: Health Check, Smoke Test

## 🎯 Best Practices

### 개발
- 코드 리뷰 필수
- 자동화된 테스트
- 지속적 통합

### 운영
- 모니터링 및 알림
- 장애 대응 절차
- 정기적 보안 업데이트

### 문서화
- API 문서 자동 생성
- 아키텍처 다이어그램 유지
- 운영 가이드 작성

## 📚 참고 자료

- [CNCF Cloud Native Definition](https://github.com/cncf/toc/blob/main/DEFINITION.md)
- [12-Factor App](https://12factor.net/)
- [Kubernetes Best Practices](https://kubernetes.io/docs/concepts/configuration/overview/)
- [Container Security Best Practices](https://kubernetes.io/docs/concepts/security/)
- [Prometheus Monitoring](https://prometheus.io/docs/practices/)

---

이 문서는 프로젝트의 CNCF 표준 준수 현황과 클라우드 네이티브 아키텍처를 설명합니다.
지속적으로 업데이트하여 최신 CNCF 표준을 반영하겠습니다.