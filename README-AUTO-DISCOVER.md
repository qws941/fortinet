# TS Auto-Discover Daemon

## 개요

**완전 자동화된 프로젝트 발견 및 등록 시스템**

명령어를 입력하지 않아도 시스템이 자동으로 5분마다 새로운 프로젝트를 발견하고 등록합니다.

## 설치

### 원스텝 설치

```bash
cd /home/jclee/app/tmux
./install-auto-discover.sh
```

설치 스크립트가 자동으로:
1. 데몬 스크립트를 실행 가능하게 설정
2. 로그 디렉토리 생성
3. systemd 서비스 설치
4. 서비스 활성화 및 시작

### 수동 설치

```bash
# 1. 실행 권한 부여
chmod +x ts-auto-discover-daemon.sh
chmod +x ts-discover.sh

# 2. systemd 서비스 설치
sudo cp systemd/ts-auto-discover.service /etc/systemd/system/
sudo systemctl daemon-reload

# 3. 서비스 활성화 및 시작
sudo systemctl enable ts-auto-discover.service
sudo systemctl start ts-auto-discover.service
```

## 동작 방식

### 자동 스캔 주기

- **간격**: 5분마다 자동 실행
- **스캔 대상**:
  - `/home/jclee/app`
  - `/home/jclee/synology`

### 자동 등록 프로세스

```
시작
  ↓
[5분 대기]
  ↓
[프로젝트 스캔]
  ↓
[새 프로젝트 발견?] ─── 아니오 ─→ [5분 대기]
  ↓ 예
[자동 등록]
  ↓
[Grafana 로깅]
  ↓
[5분 대기]
```

### 프로젝트 타입 자동 감지

| 파일 | 프로젝트 타입 | 자동 태그 |
|------|-------------|----------|
| `package.json` | Node.js | `dev,node,app` |
| `go.mod` | Go | `dev,go,app` |
| `requirements.txt` | Python | `dev,python,app` |
| `Cargo.toml` | Rust | `dev,rust,app` |
| `docker-compose.yml` | Docker | `docker,app` |

## 관리 명령어

### 상태 확인

```bash
# 서비스 상태
sudo systemctl status ts-auto-discover

# 간단한 상태
sudo systemctl is-active ts-auto-discover
```

### 로그 확인

```bash
# 앱 로그 (실시간)
tail -f ~/.config/ts/auto-discover.log

# systemd 로그 (실시간)
journalctl -u ts-auto-discover -f

# 최근 100줄
journalctl -u ts-auto-discover -n 100
```

### 서비스 제어

```bash
# 중지
sudo systemctl stop ts-auto-discover

# 시작
sudo systemctl start ts-auto-discover

# 재시작
sudo systemctl restart ts-auto-discover

# 비활성화 (부팅시 자동 시작 안함)
sudo systemctl disable ts-auto-discover

# 활성화 (부팅시 자동 시작)
sudo systemctl enable ts-auto-discover
```

### 완전 제거

```bash
# 서비스 중지 및 비활성화
sudo systemctl stop ts-auto-discover
sudo systemctl disable ts-auto-discover

# 서비스 파일 제거
sudo rm /etc/systemd/system/ts-auto-discover.service
sudo systemctl daemon-reload

# 로그 파일 제거 (선택사항)
rm ~/.config/ts/auto-discover.log
```

## 로그 출력 예시

### 앱 로그 (`~/.config/ts/auto-discover.log`)

```
[2025-10-01T06:30:00Z] === TS Auto-Discover Daemon Started ===
[2025-10-01T06:30:00Z] Starting auto-discovery...
[2025-10-01T06:30:02Z] Discovery completed successfully
[2025-10-01T06:35:00Z] Starting auto-discovery...
[2025-10-01T06:35:01Z] Discovery already running, skipping...
[2025-10-01T06:40:00Z] Starting auto-discovery...
[2025-10-01T06:40:03Z] Discovery completed successfully
```

### Systemd 로그

```bash
$ journalctl -u ts-auto-discover -n 20

Oct 01 06:30:00 hostname systemd[1]: Started TS Auto-Discover Daemon.
Oct 01 06:30:00 hostname ts-auto-discover-daemon.sh[12345]: TS Auto-Discover Daemon Started
Oct 01 06:30:00 hostname ts-auto-discover-daemon.sh[12345]: Interval: 300 seconds (5 minutes)
Oct 01 06:30:02 hostname ts-auto-discover-daemon.sh[12345]: ✓ Registered: new-project
```

## 실전 사용 시나리오

### 시나리오 1: 새 프로젝트 클론

```bash
# 1. 새 프로젝트 클론
cd /home/jclee/app
git clone https://github.com/user/new-project.git

# 2. 아무것도 안해도 됨!
# 최대 5분 후 자동으로 ts 데이터베이스에 등록됨

# 3. 확인
ts list | grep new-project
```

### 시나리오 2: Synology에 새 디렉토리 생성

```bash
# 1. 새 디렉토리 생성
mkdir -p /home/jclee/synology/new-backup
cd /home/jclee/synology/new-backup
# ... 작업 ...

# 2. 자동 등록 대기
# 5분 이내에 자동으로 등록됨

# 3. 확인
ts read new-backup
```

### 시나리오 3: 프로젝트 타입이 변경됨

```bash
# 1. 기존 프로젝트에 package.json 추가
cd /home/jclee/app/my-project
npm init -y

# 2. 다음 스캔 때 자동으로 태그 업데이트
# (현재는 수동 업데이트 필요, 향후 개선 예정)
ts update my-project --tags "dev,node,app"
```

## Grafana 모니터링

모든 자동 발견 작업이 Grafana Loki에 로깅됩니다.

### Grafana 쿼리

```logql
# 모든 자동 발견 작업
{job="ts-discover"}

# 자동 등록 성공
{job="ts-discover", operation="auto_register", status="success"}

# 5분간 발견된 프로젝트 수
sum by (status) (count_over_time({job="ts-discover", operation="register"}[5m]))

# 시간대별 발견 프로젝트 추이
count_over_time({job="ts-discover", operation="register"}[1h])
```

### Grafana 대시보드 예시

**패널 1: 자동 등록 통계**
- 쿼리: `sum(count_over_time({job="ts-discover", operation="auto_register"}[24h]))`
- 타입: Stat
- 표시: 24시간 동안 등록된 프로젝트 수

**패널 2: 발견 프로젝트 로그**
- 쿼리: `{job="ts-discover"} |= "Registered"`
- 타입: Logs
- 표시: 최근 등록된 프로젝트 목록

**패널 3: 데몬 상태**
- 쿼리: `{job="ts-discover"} |= "Daemon Started"`
- 타입: Logs
- 표시: 데몬 시작/재시작 이력

## 성능 및 리소스

### 리소스 사용량

- **CPU**: 거의 0% (스캔시에만 잠깐 사용)
- **메모리**: ~10MB
- **디스크 I/O**: 매우 낮음 (스캔시 디렉토리 읽기만)
- **네트워크**: Grafana 로깅시 소량

### 잠금 메커니즘

동시 실행 방지를 위한 잠금 파일 사용:
- **잠금 파일**: `~/.config/ts/auto-discover.lock`
- **동작**: 이미 스캔 중이면 건너뜀
- **자동 정리**: 스캔 완료 후 자동 삭제

## 문제 해결

### 문제: 데몬이 실행되지 않음

**확인**:
```bash
sudo systemctl status ts-auto-discover
```

**해결**:
```bash
# 로그 확인
journalctl -u ts-auto-discover -n 50

# 재시작
sudo systemctl restart ts-auto-discover
```

### 문제: 새 프로젝트가 등록되지 않음

**확인**:
```bash
# 수동 실행으로 테스트
/home/jclee/app/tmux/ts-discover.sh

# 로그 확인
tail -50 ~/.config/ts/auto-discover.log
```

**해결**:
- 디렉토리 권한 확인
- 데이터베이스 파일 권한 확인: `~/.config/ts/sessions.db`

### 문제: 잠금 파일이 남아있음

**증상**: "Discovery already running, skipping..." 계속 출력

**해결**:
```bash
rm ~/.config/ts/auto-discover.lock
sudo systemctl restart ts-auto-discover
```

## 고급 설정

### 스캔 간격 변경

`ts-auto-discover-daemon.sh` 수정:

```bash
# 기본값: 5분 (300초)
readonly INTERVAL=300

# 1분으로 변경
readonly INTERVAL=60

# 10분으로 변경
readonly INTERVAL=600
```

변경 후:
```bash
sudo systemctl restart ts-auto-discover
```

### 추가 스캔 경로 설정

`ts-discover.sh` 수정:

```bash
readonly SCAN_PATHS=(
    "/home/jclee/app"
    "/home/jclee/synology"
    "/home/jclee/custom-projects"  # 추가
)
```

### 로그 로테이션 설정

`/etc/logrotate.d/ts-auto-discover` 생성:

```
/home/jclee/.config/ts/auto-discover.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 0644 jclee jclee
}
```

## Constitutional Compliance

이 자동화 시스템은 CLAUDE.md v11.0을 준수합니다:

- ✅ **Grafana 통합**: 모든 작업이 Loki에 로깅
- ✅ **자율 실행**: 인간 개입 없이 자동으로 작동
- ✅ **환경 인식**: ENVIRONMENTAL_MAP.md 기반 디렉토리 스캔
- ✅ **Zero 로컬 모니터링**: 모든 관찰은 grafana.jclee.me를 통해서만
- ✅ **지속적 학습**: 새 프로젝트 패턴 자동 감지 및 등록

## 요약

### 설치 후 효과

1. **명령어 불필요**: `ts discover` 명령어 입력 불필요
2. **자동 등록**: 새 프로젝트가 5분 이내에 자동 등록
3. **투명한 관찰**: Grafana에서 모든 활동 추적 가능
4. **Zero 관리**: 한 번 설치하면 영구적으로 작동

### 추천 워크플로우

```bash
# 1. 설치 (한 번만)
./install-auto-discover.sh

# 2. 새 프로젝트 작업 시작
cd /home/jclee/app
git clone <repo-url>
cd <repo-name>
# ... 작업 시작 ...

# 3. 5분 후 자동으로 ts에 등록됨
# 확인만 하면 됨
ts list | grep <repo-name>

# 4. 바로 attach
ts attach <repo-name>
```

**완전 자동화 완성!** 🎉
