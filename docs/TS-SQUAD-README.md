# TS Squad - Multi-Agent Task Management

Claude Squad 기능을 ts 명령어 시스템에 통합한 멀티 에이전트 작업 관리 도구입니다.

## 🎯 핵심 기능

### 1. **Git Worktrees 기반 에이전트 격리**
- 각 에이전트가 독립된 git worktree에서 작업
- 브랜치별 완전한 격리로 충돌 없는 병렬 작업
- 자동 브랜치 생성 및 관리

### 2. **Tmux 세션 격리**
- Socket 기반 독립적인 tmux 세션
- 각 에이전트는 전용 Claude Code 인스턴스 실행
- 중첩 tmux 세션 자동 처리

### 3. **Grafana 통합 모니터링**
- 실시간 에이전트 상태 추적
- Loki 로그 집계
- Prometheus 메트릭 수집
- 자동 헬스 체크

### 4. **체크포인트 및 재개**
- Git commit 기반 체크포인트
- 일시정지 및 재개 기능
- 작업 상태 보존

## 📦 설치

### 필수 요구사항

```bash
# Ubuntu/Debian
sudo apt install tmux git jq python3 python3-pip

# Python 패키지
pip3 install --user requests
```

### 자동 설치

```bash
cd /home/jclee/app/tmux
./install-ts-squad.sh
```

설치 완료 후 다음 명령어가 사용 가능합니다:
- `ts-squad` - 메인 명령어
- `ts-squad-monitor` - 모니터링 스크립트

## 🚀 사용법

### 1. 에이전트 생성

```bash
# 기본 에이전트 생성
ts-squad spawn fix-auth feature/fix-auth "Fix authentication bug"

# 자동 모드 (프롬프트 자동 승인)
ts-squad spawn add-api feature/add-api "Add REST API" --auto

# 간단한 생성 (자동 브랜치명)
ts-squad spawn optimize-db
```

**실행 결과:**
- Git worktree 생성: `~/.ts-worktrees/agent-fix-auth`
- 독립 브랜치: `feature/fix-auth`
- Tmux 세션: `agent-fix-auth`
- Claude Code 자동 시작

### 2. 에이전트 목록 보기

```bash
ts-squad list
```

**출력 예시:**
```
════════════════════════════════════════════════════
           TS Squad - Active Agents
════════════════════════════════════════════════════

📊 Agent Statistics:
  Active: 3 / 10

🤖 Active Agents:
  AGENT ID             TASK                     BRANCH               STATUS
  ────────────────────────────────────────────────────────────────────────────
  agent-fix-auth       fix-auth                 feature/fix-auth     ● active
  agent-add-api        add-api                  feature/add-api      ● active
  agent-optimize-db    optimize-db              agent/optimize-db    ◐ paused
```

### 3. 에이전트에 연결

```bash
# 특정 에이전트에 연결
ts-squad attach agent-fix-auth

# tmux 내부에서 실행 시 새 윈도우로 열림
# tmux 외부에서 실행 시 attach
```

### 4. 체크포인트 생성

```bash
# 체크포인트 생성 및 일시정지
ts-squad checkpoint agent-fix-auth "Completed authentication refactoring"
```

**실행 결과:**
- Git commit 생성
- 에이전트 상태를 "paused"로 변경
- Grafana에 로그 전송

### 5. 일시정지된 에이전트 재개

```bash
ts-squad resume agent-fix-auth
```

### 6. 에이전트 종료

```bash
# Worktree 포함 완전 삭제
ts-squad kill agent-fix-auth

# Worktree 보존 (코드 유지)
ts-squad kill agent-fix-auth keep-worktree
```

### 7. 작업 자동 위임

```bash
# 작업 설명만으로 에이전트 자동 생성
ts-squad delegate "Optimize database query performance"

# 자동 모드로 위임
ts-squad delegate "Add user authentication" --auto
```

**자동 처리:**
- Task name 자동 생성
- Branch name 자동 생성
- 에이전트 즉시 시작

### 8. 대시보드 보기

```bash
ts-squad dashboard
```

**출력 예시:**
```
════════════════════════════════════════════════════
           TS Squad Dashboard
════════════════════════════════════════════════════

📊 Overall Statistics:
  Total Agents:  5
  Active:        3
  Paused:        2
  Failed:        0

🌿 Git Worktrees:
  /home/jclee/.ts-worktrees/agent-fix-auth     [feature/fix-auth]
  /home/jclee/.ts-worktrees/agent-add-api      [feature/add-api]
  /home/jclee/.ts-worktrees/agent-optimize-db  [agent/optimize-db]

💾 Disk Usage:
  Worktrees: 256 MB
```

## 📊 모니터링

### 수동 실행

```bash
# 한 번 실행
ts-squad-monitor

# 지속 실행 (30초 간격)
ts-squad-monitor continuous 30
```

### Systemd 서비스

```bash
# 서비스 시작
sudo systemctl start ts-squad-monitor

# 부팅 시 자동 시작
sudo systemctl enable ts-squad-monitor

# 상태 확인
sudo systemctl status ts-squad-monitor
```

### Grafana 대시보드

모니터링 데이터는 다음 위치로 전송됩니다:
- **Loki**: `http://localhost:3100` (로그)
- **Prometheus**: `http://localhost:9091` (메트릭)

**수집되는 메트릭:**
- `ts_squad_total_agents` - 총 에이전트 수
- `ts_squad_active_agents` - 활성 에이전트 수
- `ts_squad_paused_agents` - 일시정지된 에이전트 수
- `ts_squad_failed_agents` - 실패한 에이전트 수
- `ts_squad_worktrees` - Git worktree 수
- `ts_squad_disk_usage_mb` - 디스크 사용량 (MB)

**Loki 로그 레이블:**
- `job="ts-squad"` 또는 `job="ts-squad-monitor"`
- `event` - 이벤트 유형 (agent_spawned, agent_killed, etc.)
- `agent_id` - 에이전트 ID
- `branch` - Git 브랜치

## 🏗️ 아키텍처

```
TS Squad
├── Git Worktrees (~/.ts-worktrees/)
│   ├── agent-fix-auth/
│   │   └── [feature/fix-auth 브랜치]
│   ├── agent-add-api/
│   │   └── [feature/add-api 브랜치]
│   └── agent-optimize-db/
│       └── [agent/optimize-db 브랜치]
│
├── Tmux Sessions (~/.tmux/sockets/)
│   ├── agent-fix-auth (socket)
│   ├── agent-add-api (socket)
│   └── agent-optimize-db (socket)
│
├── Agent Registry (~/.config/ts/agents.json)
│   └── {
│         "agents": {
│           "agent-fix-auth": {
│             "task_name": "fix-auth",
│             "branch": "feature/fix-auth",
│             "worktree_path": "~/.ts-worktrees/agent-fix-auth",
│             "socket_path": "~/.tmux/sockets/agent-fix-auth",
│             "status": "active",
│             ...
│           }
│         }
│       }
│
└── Monitoring
    ├── ts-squad-monitor.py → Loki (logs)
    └── ts-squad-monitor.py → Prometheus (metrics)
```

## 🔧 고급 사용법

### 여러 에이전트 병렬 실행

```bash
# 3개의 독립적인 작업 동시 실행
ts-squad spawn frontend feature/ui-update "Update UI components"
ts-squad spawn backend feature/api-refactor "Refactor REST API"
ts-squad spawn testing feature/add-tests "Add integration tests"

# 모든 에이전트 상태 확인
ts-squad list
```

### 에이전트 워크플로우 자동화

```bash
#!/bin/bash
# auto-delegate-tasks.sh

TASKS=(
  "Optimize database indexes"
  "Add user authentication"
  "Implement caching layer"
  "Write API documentation"
)

for task in "${TASKS[@]}"; do
  ts-squad delegate "$task" --auto
  sleep 2
done

echo "All tasks delegated!"
```

### Git Worktree 수동 관리

```bash
# Worktree 목록 보기
git worktree list

# 특정 worktree로 이동
cd ~/.ts-worktrees/agent-fix-auth

# 작업 후 메인 브랜치로 머지
git checkout main
git merge feature/fix-auth
git push origin main

# Worktree 제거
git worktree remove ~/.ts-worktrees/agent-fix-auth
```

### 체크포인트 기반 복구

```bash
# 체크포인트 생성
ts-squad checkpoint agent-fix-auth "Before risky changes"

# 작업 진행...
# 문제 발생 시 git reset으로 복구
cd ~/.ts-worktrees/agent-fix-auth
git log --oneline  # 체크포인트 commit 확인
git reset --hard <commit-hash>

# 에이전트 재개
ts-squad resume agent-fix-auth
```

## 🐛 트러블슈팅

### 에이전트가 시작되지 않음

```bash
# Socket 확인
ls -la ~/.tmux/sockets/

# 죽은 소켓 제거
rm ~/.tmux/sockets/agent-*

# 레지스트리 초기화
ts-squad init
```

### Worktree 충돌

```bash
# 모든 worktree 목록
git worktree list

# 손상된 worktree 제거
git worktree remove -f <path>

# 레지스트리 정리
jq '.agents = {}' ~/.config/ts/agents.json > ~/.config/ts/agents.json.tmp
mv ~/.config/ts/agents.json.tmp ~/.config/ts/agents.json
```

### 디스크 용량 부족

```bash
# Worktree 크기 확인
du -sh ~/.ts-worktrees/*

# 오래된 에이전트 제거
for agent in $(jq -r '.agents | keys[]' ~/.config/ts/agents.json); do
  ts-squad kill $agent
done
```

### Grafana 연결 실패

```bash
# Loki/Prometheus 상태 확인
curl -s http://localhost:3100/ready
curl -s http://localhost:9090/-/ready

# Docker 서비스 재시작
docker-compose restart grafana loki prometheus
```

## 📈 성능 최적화

### 최대 에이전트 수 조정

```bash
# Agent registry 편집
jq '.max_agents = 20' ~/.config/ts/agents.json > ~/.config/ts/agents.json.tmp
mv ~/.config/ts/agents.json.tmp ~/.config/ts/agents.json
```

### 모니터링 주기 조정

```bash
# 더 자주 모니터링 (15초 간격)
ts-squad-monitor continuous 15

# 덜 자주 모니터링 (60초 간격)
ts-squad-monitor continuous 60
```

### Worktree 저장 위치 변경

스크립트에서 `WORKTREE_BASE` 변수 수정:

```bash
# ts-squad-integration.sh 편집
WORKTREE_BASE="/mnt/nvme/.ts-worktrees"  # 더 빠른 디스크
```

## 🔗 기존 ts 명령어와 통합

### 방법 1: Wrapper 사용

```bash
# ts-squad-wrapper.sh를 /usr/local/bin/ts로 복사
sudo cp ts-squad-wrapper.sh /usr/local/bin/ts-new
sudo chmod +x /usr/local/bin/ts-new

# 사용
ts-new squad spawn my-task
```

### 방법 2: 기존 ts 스크립트 수정

기존 `/usr/local/bin/ts` 파일에 다음 코드 추가:

```bash
# TS Squad Integration (맨 위에 추가)
if [[ "$1" == "squad" ]]; then
    shift
    exec /usr/local/bin/ts-squad "$@"
fi
```

이후:
```bash
ts squad spawn my-task        # ts 명령어로 직접 사용
ts squad list
ts squad dashboard
```

## 📚 참고 자료

- **Claude Squad**: https://github.com/smtg-ai/claude-squad
- **Git Worktrees**: https://git-scm.com/docs/git-worktree
- **Tmux**: https://github.com/tmux/tmux
- **Grafana Loki**: https://grafana.com/oss/loki/
- **Prometheus**: https://prometheus.io/

## 🤝 기여

버그 리포트나 기능 제안은 이슈로 등록해주세요.

## 📄 라이선스

MIT License

---

**Happy Multi-Agent Coding! 🚀**
