# TS Master - Unified Tmux Session Manager

**Version:** 4.0.0-master  
**Build Date:** 2025-10-01  
**Constitutional Compliance:** v11.0

## 📋 Overview

TS Master는 모든 ts 관련 스크립트들을 단일 파일로 통합한 통합 Tmux 세션 관리자입니다.

### 통합된 스크립트 (11개 → 1개)

- ✅ ts-unified.sh (593줄)
- ✅ ts-bg-manager.sh (402줄)
- ✅ ts-ipc.sh (528줄)
- ✅ ts-squad-integration.sh (543줄)
- ✅ ts-claude-integration.sh (338줄)
- ✅ ts-advanced.sh, ts-enhanced.sh, ts-interact.sh, ts-alias.sh, ts-compatibility.sh, ts-squad-wrapper.sh

**결과:** `/home/jclee/app/tmux/ts.sh` (516줄)

## 🎯 주요 기능

### 1. 세션 관리 (Session Management)

```bash
ts                    # Resume last or list sessions
ts list               # List all active sessions
ts <name> [path]      # Create/attach to session
ts kill <name>        # Kill specific session
ts clean              # Clean all sessions
ts resume             # Resume last session
```

### 2. 백그라운드 태스크 (Background Tasks)

```bash
ts bg start <name> <cmd>   # Start background task
ts bg list                 # List background tasks
ts bg stop <name>          # Stop background task
ts bg attach <name>        # Attach to background task
```

**예시:**
```bash
# 개발 서버를 백그라운드에서 실행
ts bg start dev-server "npm run dev"

# 테스트 watcher 실행
ts bg start test-watch "npm test -- --watch"

# 실행 중인 태스크 확인
ts bg list

# 태스크 중지
ts bg stop dev-server
```

### 3. IPC (Inter-Process Communication)

```bash
ts ipc send <session> <msg>   # Send message to session
ts ipc broadcast <msg>        # Broadcast to all sessions
```

**예시:**
```bash
# 특정 세션에 명령 전송
ts ipc send blacklist "npm test"

# 모든 세션에 브로드캐스트
ts ipc broadcast "git pull origin main"
```

### 4. 시스템 명령

```bash
ts version            # Show version info
ts help               # Show this help
```

## ✨ 핵심 개선사항

### 1. 중복 세션 자동 방지

- 세션 생성 시 기본 tmux 세션 자동 감지 및 제거
- 소켓 기반 세션으로 자동 마이그레이션

### 2. 소켓 기반 격리

- 각 세션이 독립적인 소켓 사용 (`/home/jclee/.tmux/sockets/`)
- 세션 간 충돌 방지

### 3. Grafana 텔레메트리

- 모든 명령 실행이 Grafana Loki로 자동 로깅
- Job: `ts-command`
- Constitutional Compliance 보장

### 4. 자동 정리

- 죽은 소켓 자동 정리
- 세션 상태 자동 추적

## 📁 파일 구조

```
/home/jclee/app/tmux/
├── ts.sh                      # 마스터 소스 파일 (516줄)
├── test-ts-master.sh          # 종합 테스트 스크립트
├── quick-test.sh              # 빠른 테스트
└── README-TS-MASTER.md        # 이 문서

/usr/local/bin/
└── ts                         # 시스템 전역 배포

/home/jclee/.local/bin/
├── ts-advanced                # 마스터 파일 복사본
└── ts → ts-advanced          # 심볼릭 링크

/home/jclee/.config/ts/
├── config.json                # 설정 파일
├── state/                     # 상태 디렉터리
├── ipc/                       # IPC 메시지
└── bg/                        # 백그라운드 태스크 로그
```

## 🧪 테스트

### 빠른 테스트

```bash
/home/jclee/app/tmux/quick-test.sh
```

### 종합 테스트

```bash
/home/jclee/app/tmux/test-ts-master.sh
```

### 수동 테스트

```bash
# 1. 버전 확인
ts version

# 2. 세션 목록
ts list

# 3. 백그라운드 태스크
ts bg start test "echo 'Hello'; sleep 5"
ts bg list
ts bg stop test

# 4. IPC 테스트
ts ipc send tmux "echo 'Test message'"
```

## 📊 테스트 결과

### ✅ 통과한 테스트

- ✅ 기본 명령 (version, help, list)
- ✅ 세션 관리 (create, attach, kill)
- ✅ 백그라운드 태스크 (start, list, stop)
- ✅ IPC (send, broadcast)
- ✅ 중복 세션 감지 및 제거
- ✅ 설정 및 상태 관리
- ✅ Grafana 텔레메트리

## 🔧 설정

### 기본 설정 (`~/.config/ts/config.json`)

```json
{
  "version": "4.0.0",
  "socket_dir": "/home/jclee/.tmux/sockets",
  "grafana_telemetry": true,
  "auto_dedup": true,
  "background_tasks": true,
  "ipc_enabled": true
}
```

### 환경 변수

```bash
# 소켓 디렉터리 (기본: ~/.tmux/sockets)
export TS_SOCKET_DIR="/custom/socket/dir"

# 설정 디렉터리 (기본: ~/.config/ts)
export TS_CONFIG_DIR="/custom/config/dir"

# Grafana Loki URL
export GRAFANA_LOKI_URL="https://grafana.jclee.me/loki/api/v1/push"
```

## 🚀 배포

### 시스템 전역 설치

```bash
sudo cp /home/jclee/app/tmux/ts.sh /usr/local/bin/ts
sudo chmod +x /usr/local/bin/ts
```

### 로컬 사용자 설치

```bash
cp /home/jclee/app/tmux/ts.sh ~/.local/bin/ts-advanced
chmod +x ~/.local/bin/ts-advanced
ln -sf ~/.local/bin/ts-advanced ~/.local/bin/ts
```

## 📈 Grafana 모니터링

### Loki 쿼리

```promql
# 모든 ts 명령 로그
{job="ts-command"}

# 특정 명령 필터링
{job="ts-command", command="create"}

# 에러 필터링
{job="ts-command"} |= "exit_code" != "0"
```

### 대시보드

- Job: `ts-command`
- Labels: `command`, `user`, `version`
- Metrics: `exit_code`, `duration_ms`

## 🐛 트러블슈팅

### 중복 세션 문제

```bash
# 중복 세션 확인
tmux ls
ts list

# 모든 세션 정리
ts clean
```

### 죽은 소켓 정리

```bash
# 자동 정리 (ts 명령 실행 시 자동)
ts list

# 수동 정리
find ~/.tmux/sockets -type s -exec tmux -S {} has-session \; || rm -f {}
```

### 백그라운드 태스크가 보이지 않음

```bash
# 태스크 로그 확인
cat ~/.config/ts/bg/tasks.log

# 세션 확인
ts list | grep "bg-"
```

## 📝 변경 이력

### v4.0.0-master (2025-10-01)

- ✨ 모든 ts 스크립트 통합 (11개 → 1개)
- ✨ 백그라운드 태스크 관리 추가
- ✨ IPC 기능 통합
- ✨ 중복 세션 자동 방지
- ✨ Grafana 텔레메트리 내장
- 🐛 세션 충돌 문제 해결
- 📚 종합 테스트 스크립트 추가

## 🤝 기여

문제 발견 시:
1. `/home/jclee/app/tmux/test-ts-master.sh` 실행
2. 에러 로그 확인: `{job="ts-command"} |= "error"`
3. GitHub Issue 생성

## 📄 라이선스

Constitutional Compliance v11.0  
Grafana Integration Required

---

**마지막 업데이트:** 2025-10-01  
**테스트 상태:** ✅ 모든 테스트 통과  
**배포 상태:** ✅ 프로덕션 준비 완료
