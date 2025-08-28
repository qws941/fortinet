# MSA + GitOps 완전 통합 환경 (jclee.me)

## 🎯 개요

FortiNet MSA (Microservices Architecture)와 GitOps를 완전 통합한 엔터프라이즈급 배포 환경입니다. jclee.me 인프라와 완벽하게 연동되어 4개의 마이크로서비스를 자동화된 CI/CD 파이프라인으로 관리합니다.

## 🏗️ 아키텍처

### MSA 서비스 구성
- **user-service**: 사용자 관리 및 인증
- **product-service**: 상품 카탈로그 관리
- **order-service**: 주문 처리 및 관리
- **notification-service**: 알림 및 메시징

### 인프라 구성 요소
- **Service Mesh**: Istio (서비스 간 통신 관리)
- **Monitoring**: Prometheus + Grafana + Jaeger
- **GitOps**: ArgoCD (선언적 배포 관리)
- **Container Registry**: Harbor (registry.jclee.me)
- **Helm Repository**: ChartMuseum (charts.jclee.me)

## 🌍 환경 구성

### 환경별 특성

| 환경 | 도메인 | 네임스페이스 | 리플리카 | 리소스 할당 | HPA |
|------|---------|--------------|----------|-------------|-----|
| **Development** | `*-dev.jclee.me` | `microservices-dev` | 1 | 100m/128Mi - 500m/512Mi | ❌ |
| **Staging** | `*-staging.jclee.me` | `microservices-staging` | 2 | 200m/256Mi - 1000m/1Gi | ✅ (2-5) |
| **Production** | `*.jclee.me` | `microservices` | 3 | 500m/512Mi - 2000m/2Gi | ✅ (3-10) |

### 브랜치 배포 전략
- `develop` → Development 환경 자동 배포
- `staging` → Staging 환경 자동 배포
- `main/master` → Production 환경 자동 배포

## 🚀 빠른 시작

### 1. ArgoCD 초기 설정
```bash
# ArgoCD MSA 프로젝트 및 Repository 설정
./msa-gitops/scripts/setup-argocd-msa.sh
```

### 2. MSA 서비스 배포
```bash
# 전체 서비스 배포 (Production)
./msa-gitops/scripts/deploy-msa.sh production all

# 특정 서비스 배포
./msa-gitops/scripts/deploy-msa.sh production user-service

# 개발 환경 배포
./msa-gitops/scripts/deploy-msa.sh development all
```

### 3. 상태 모니터링
```bash
# 전체 MSA 상태 확인
./msa-gitops/scripts/monitor-msa-status.sh

# 특정 환경 상태 확인
./msa-gitops/scripts/monitor-msa-status.sh production

# 특정 서비스 상태 확인
./msa-gitops/scripts/monitor-msa-status.sh production user-service
```

## 📁 디렉토리 구조

```
msa-gitops/
├── applications/              # ArgoCD Application 정의
│   ├── user-service-application.yaml
│   ├── product-service-application.yaml
│   ├── order-service-application.yaml
│   ├── notification-service-application.yaml
│   ├── istio-application.yaml
│   └── monitoring-application.yaml
├── environments/              # 환경별 Helm Values
│   ├── development/           # 개발 환경 설정
│   ├── staging/              # 스테이징 환경 설정
│   └── production/           # 프로덕션 환경 설정
├── configs/                  # ArgoCD 설정
│   ├── argocd-msa-project.yaml
│   └── msa-notifications.yaml
├── scripts/                  # 관리 스크립트
│   ├── setup-argocd-msa.sh   # 초기 설정
│   ├── deploy-msa.sh         # 배포 스크립트
│   └── monitor-msa-status.sh # 상태 모니터링
└── .github/workflows/        # GitHub Actions
    └── msa-gitops-deploy.yaml
```

## 🔄 CI/CD 파이프라인

### GitHub Actions 워크플로우
1. **코드 Push** → 브랜치별 환경 결정
2. **Docker 빌드** → Harbor Registry 업로드
3. **Helm 패키징** → ChartMuseum 업로드
4. **ArgoCD 배포** → 환경별 자동 배포
5. **배포 검증** → Health Check 및 API 테스트

### 배포 트리거
- **자동 배포**: `main/master`, `staging`, `develop` 브랜치 Push
- **수동 배포**: GitHub Actions 워크플로우 디스패치
- **Pull Request**: 빌드 및 테스트만 실행

## 🌐 서비스 접속 정보

### Production 환경
- **user-service**: https://user-service.jclee.me
- **product-service**: https://product-service.jclee.me
- **order-service**: https://order-service.jclee.me
- **notification-service**: https://notification-service.jclee.me

### Staging 환경
- **user-service**: https://user-service-staging.jclee.me
- **product-service**: https://product-service-staging.jclee.me
- **order-service**: https://order-service-staging.jclee.me
- **notification-service**: https://notification-service-staging.jclee.me

### Development 환경
- **user-service**: https://user-service-dev.jclee.me
- **product-service**: https://product-service-dev.jclee.me
- **order-service**: https://order-service-dev.jclee.me
- **notification-service**: https://notification-service-dev.jclee.me

## 📊 모니터링 및 관리

### 관리 도구
- **ArgoCD**: https://argo.jclee.me
- **Grafana**: https://grafana.jclee.me
- **Prometheus**: https://prometheus.jclee.me
- **K8s Dashboard**: https://k8s.jclee.me
- **Harbor Registry**: https://registry.jclee.me
- **ChartMuseum**: https://charts.jclee.me

### 모니터링 대시보드
- **MSA Overview**: https://grafana.jclee.me/d/msa-overview
- **Service Performance**: https://grafana.jclee.me/d/service-performance
- **Infrastructure Metrics**: https://grafana.jclee.me/d/infrastructure

## 🔧 운영 가이드

### 일반적인 작업

#### 1. 새로운 서비스 추가
```bash
# 1. ArgoCD Application 파일 생성
cp msa-gitops/applications/user-service-application.yaml \
   msa-gitops/applications/new-service-application.yaml

# 2. 환경별 Values 파일 생성
for env in development staging production; do
    cp msa-gitops/environments/${env}/values-user-service-${env}.yaml \
       msa-gitops/environments/${env}/values-new-service-${env}.yaml
done

# 3. GitHub Actions 워크플로우에 서비스 추가
# .github/workflows/msa-gitops-deploy.yaml 파일 수정

# 4. ArgoCD에 Application 생성
argocd app create -f msa-gitops/applications/new-service-application.yaml
```

#### 2. 환경별 리소스 조정
```bash
# Values 파일 수정 후 동기화
vim msa-gitops/environments/production/values-user-service-production.yaml
argocd app sync user-service-production
```

#### 3. 롤백 수행
```bash
# 애플리케이션 히스토리 확인
argocd app history user-service-production

# 특정 리비전으로 롤백
argocd app rollback user-service-production <revision>
```

#### 4. 스케일링
```bash
# HPA 활성화
kubectl patch hpa user-service-hpa -n microservices \
  -p '{"spec":{"minReplicas":5,"maxReplicas":20}}'

# 수동 스케일링
kubectl scale deployment user-service -n microservices --replicas=5
```

### 트러블슈팅

#### 1. Application이 Sync되지 않을 때
```bash
# 상태 확인
argocd app get user-service-production

# 강제 동기화
argocd app sync user-service-production --force

# 리소스 정리 후 재동기화
argocd app sync user-service-production --prune
```

#### 2. 서비스 Health Check 실패
```bash
# Pod 상태 확인
kubectl get pods -n microservices -l app=user-service

# Pod 로그 확인
kubectl logs -n microservices -l app=user-service --tail=100

# 서비스 엔드포인트 확인
kubectl get endpoints user-service -n microservices
```

#### 3. Istio 관련 문제
```bash
# Istio 프록시 상태 확인
kubectl exec -n microservices <pod-name> -c istio-proxy -- \
  curl localhost:15000/stats/prometheus | grep envoy_cluster_health

# Istio 설정 확인
istioctl proxy-config cluster <pod-name> -n microservices
```

## 🔐 보안 설정

### RBAC 설정
- **MSA Developers**: Applications 조회/동기화 권한
- **MSA Admins**: 전체 프로젝트 관리 권한
- **jclee Admins**: 클러스터 레벨 관리 권한

### 네트워크 보안
- **Istio Service Mesh**: mTLS 자동 암호화
- **Network Policies**: 네임스페이스 간 통신 제어
- **Ingress Security**: TLS 터미네이션 및 인증서 관리

### 시크릿 관리
- **Harbor Registry**: 컨테이너 이미지 인증
- **Database Credentials**: K8s Secret으로 관리
- **API Keys**: ArgoCD Repository 인증

## 📈 성능 최적화

### 리소스 최적화
- **HPA**: CPU/Memory 기반 자동 스케일링
- **VPA**: 리소스 요청/제한 자동 조정
- **Pod Disruption Budget**: 고가용성 보장

### 캐싱 전략
- **Redis Cluster**: 분산 캐싱 레이어
- **CDN Integration**: 정적 리소스 캐싱
- **Application-level Caching**: 서비스별 캐시 전략

## 🚨 알림 설정

### ArgoCD Notifications
- **Slack Integration**: 배포 상태 알림
- **Email Notifications**: 중요 이벤트 알림
- **Teams Integration**: 팀별 맞춤 알림

### 알림 트리거
- **Sync Failed**: 동기화 실패 시
- **Health Degraded**: 서비스 상태 저하 시
- **Deployment Complete**: 배포 완료 시
- **Resource Limit Exceeded**: 리소스 임계치 초과 시

## 📚 참고 자료

### 공식 문서
- [ArgoCD Documentation](https://argo-cd.readthedocs.io/)
- [Istio Documentation](https://istio.io/latest/docs/)
- [Helm Documentation](https://helm.sh/docs/)

### jclee.me 인프라 문서
- [K8s Cluster Guide](https://k8s.jclee.me/docs)
- [Harbor Registry Guide](https://registry.jclee.me/docs)
- [Monitoring Stack Guide](https://grafana.jclee.me/docs)

## 🤝 기여 가이드

### 코드 기여
1. Feature 브랜치 생성
2. 변경사항 구현 및 테스트
3. Pull Request 생성
4. 코드 리뷰 및 승인
5. Merge 후 자동 배포

### 이슈 리포팅
- **버그 리포트**: GitHub Issues 템플릿 사용
- **기능 요청**: Feature Request 템플릿 사용
- **보안 이슈**: Security Policy 참조

## 📞 지원 및 연락처

### 기술 지원
- **Email**: admin@jclee.me
- **Slack**: #msa-support
- **Teams**: MSA Operations Team

### 긴급 상황
- **On-call**: MSA SRE Team
- **Escalation**: jclee Admin Team

---

**© 2024 jclee.me - MSA GitOps Platform**