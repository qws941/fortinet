# Docker Compose 운영 가이드

## 📋 개요

FortiGate Nextrade는 단일 컨테이너로 통합되어 Docker Compose를 통해 관리됩니다.
모든 데이터는 Docker 명명된 볼륨을 사용하여 영구 저장됩니다.

## 🚀 빠른 시작

### 1. 환경 초기화
```bash
# 환경 설정 및 볼륨 생성
./scripts/docker-manage.sh init

# 환경 변수 설정
cp .env.example .env
# .env 파일을 편집하여 필요한 설정 입력
```

### 2. 컨테이너 시작
```bash
# 기본 시작
docker-compose up -d

# 또는 관리 스크립트 사용
./scripts/docker-manage.sh up
```

### 3. 상태 확인
```bash
# 컨테이너 상태
./scripts/docker-manage.sh status

# 로그 확인
./scripts/docker-manage.sh logs --follow
```

## 📂 볼륨 구조

### 명명된 볼륨 목록
| 볼륨 이름 | 용도 | 마운트 경로 | 백업 주기 |
|-----------|------|------------|-----------|
| fortinet-data | 애플리케이션 데이터 | /app/data | 일일 |
| fortinet-logs | 로그 파일 | /app/logs | 30일 보관 |
| fortinet-temp | 임시 파일 | /app/temp | 주간 정리 |
| fortinet-config | 설정 파일 | /app/config | 일일 |
| fortinet-cache | 캐시 데이터 | /app/cache | 월간 정리 |
| fortinet-static | 정적 파일 | /app/static | 읽기 전용 |
| fortinet-uploads | 업로드 파일 | /app/uploads | 일일 |

### 볼륨 관리 명령
```bash
# 볼륨 목록 확인
./scripts/docker-manage.sh volumes

# 볼륨 백업
./scripts/docker-manage.sh volume-backup fortinet-data

# 볼륨 복원
./scripts/docker-manage.sh volume-restore fortinet-data ./backups/fortinet-data_20240320_120000.tar.gz
```

## 🔄 마이그레이션

### 바인드 마운트에서 볼륨으로 전환
기존 바인드 마운트를 사용하는 경우:

```bash
# 1. 컨테이너 중지
docker-compose -f docker-compose.production.yml down

# 2. 마이그레이션 실행 (백업 포함)
./scripts/migrate-to-volumes.sh --backup

# 3. 새 구성으로 시작
docker-compose up -d
```

## 🛠️ 일반 운영

### 컨테이너 관리
```bash
# 시작
./scripts/docker-manage.sh up

# 중지
./scripts/docker-manage.sh down

# 재시작
./scripts/docker-manage.sh restart

# 업데이트 (새 이미지 풀 및 재시작)
./scripts/docker-manage.sh update
```

### 디버깅
```bash
# 컨테이너 쉘 접속
./scripts/docker-manage.sh shell

# 명령 실행
./scripts/docker-manage.sh exec python -m pytest

# 헬스체크 상태
./scripts/docker-manage.sh health

# 리소스 사용량
./scripts/docker-manage.sh stats
```

### 로그 관리
```bash
# 실시간 로그
./scripts/docker-manage.sh logs --follow

# 특정 서비스 로그
docker-compose logs fortinet

# 로그 파일 직접 확인
docker run --rm -v fortinet-logs:/logs alpine cat /logs/app.log
```

## 🔧 환경 설정

### 필수 환경 변수
```bash
# FortiGate 연결
FORTIGATE_HOST=192.168.1.100
FORTIGATE_API_TOKEN=your-api-token

# FortiManager 연결
FORTIMANAGER_HOST=192.168.1.200
FORTIMANAGER_USERNAME=admin
FORTIMANAGER_PASSWORD=password

# 애플리케이션 설정
APP_MODE=production
WEB_APP_PORT=7777
```

### 성능 튜닝
```bash
# 리소스 제한 조정
MEMORY_LIMIT=8G
CPU_LIMIT=4.0
WORKERS=8
WORKER_CONNECTIONS=2000
```

## 📊 모니터링

### 헬스체크
- 엔드포인트: `http://localhost:7777/api/health`
- 주기: 30초
- 타임아웃: 10초

### 메트릭스
- Prometheus 엔드포인트: `http://localhost:9090/metrics`
- 수집 가능한 메트릭:
  - 요청 수 및 응답 시간
  - 리소스 사용량
  - 애플리케이션 상태

## 🔒 보안

### 볼륨 권한
- 모든 볼륨은 `fortinet:fortinet` 사용자로 실행
- 민감한 데이터는 암호화된 볼륨 사용 권장

### 네트워크 격리
```yaml
# 내부 전용 네트워크
networks:
  fortinet-network:
    internal: true
```

### 시크릿 관리
```bash
# Docker secrets 사용 (Swarm 모드)
echo "password" | docker secret create fortigate_api_token -

# 또는 환경 파일 암호화
gpg -c .env
```

## 🆘 문제 해결

### 컨테이너가 시작되지 않을 때
```bash
# 설정 검증
./scripts/docker-manage.sh config

# 상세 로그 확인
docker-compose logs --tail=100

# 수동 시작 (디버그 모드)
docker-compose up
```

### 볼륨 문제
```bash
# 볼륨 검사
docker volume inspect fortinet-data

# 권한 확인
docker run --rm -v fortinet-data:/data alpine ls -la /data

# 볼륨 재생성 (주의: 데이터 손실)
docker volume rm fortinet-data
docker volume create fortinet-data
```

### 포트 충돌
```bash
# 사용 중인 포트 확인
sudo lsof -i :7777

# 포트 변경
WEB_APP_PORT=8080 docker-compose up -d
```

## 📝 백업 및 복구

### 전체 백업
```bash
# 모든 볼륨 백업
for vol in data logs config uploads; do
  ./scripts/docker-manage.sh volume-backup fortinet-$vol
done
```

### 재해 복구
```bash
# 1. 새 환경에서 볼륨 생성
./scripts/docker-manage.sh init

# 2. 백업 복원
for vol in data logs config uploads; do
  ./scripts/docker-manage.sh volume-restore fortinet-$vol ./backups/fortinet-${vol}_*.tar.gz
done

# 3. 컨테이너 시작
./scripts/docker-manage.sh up
```

## 🔄 CI/CD 통합

### GitHub Actions 배포
```yaml
- name: Deploy to Production
  run: |
    ssh ${{ secrets.DEPLOY_USER }}@${{ secrets.DEPLOY_HOST }} << 'EOF'
      cd /opt/fortinet
      docker-compose pull
      docker-compose up -d
    EOF
```

### Watchtower 자동 업데이트
```bash
docker run -d \
  --name watchtower \
  -v /var/run/docker.sock:/var/run/docker.sock \
  containrrr/watchtower \
  --label-enable \
  --interval 300
```

## 📞 지원

문제가 발생하면:
1. 로그 확인: `./scripts/docker-manage.sh logs`
2. 상태 점검: `./scripts/docker-manage.sh status`
3. 문제 해결 스크립트: `./scripts/docker-manage.sh troubleshoot`