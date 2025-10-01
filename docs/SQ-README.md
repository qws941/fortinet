# SQ - Multi-Agent Squad Management

**간단하고 강력한 멀티 에이전트 작업 관리 도구**

## 🚀 빠른 시작

```bash
# 설치
./install-sq.sh

# 첫 에이전트 생성
sq spawn my-task

# 목록 보기
sq list

# 대시보드
sq dashboard
```

## 📖 주요 명령어

### 에이전트 생성
```bash
sq spawn <task_name> [branch] [description] [--auto]
```

**예시:**
```bash
sq spawn fix-auth feature/fix-auth "Fix authentication bug"
sq spawn add-api  # 간단한 생성 (자동 브랜치명)
sq spawn optimize-db feature/optimize "Optimize queries" --auto
```

### 에이전트 목록
```bash
sq list      # 또는 sq ls
```

### 에이전트 연결
```bash
sq attach agent-fix-auth
```

### 체크포인트
```bash
sq checkpoint agent-fix-auth "Phase 1 complete"
sq resume agent-fix-auth
```

### 종료
```bash
sq kill agent-fix-auth              # Worktree 포함 삭제
sq kill agent-fix-auth keep-worktree  # 코드 보존
```

### 작업 위임
```bash
sq delegate "Add user profile feature"
sq delegate "Optimize API performance" --auto
```

### 대시보드
```bash
sq dashboard  # 또는 sq dash
```

## 🏗️ 아키텍처

```
SQ System
├── Git Worktrees (~/.ts-worktrees/)
│   ├── agent-fix-auth/     [feature/fix-auth]
│   └── agent-add-api/      [feature/add-api]
│
├── Tmux Sessions (~/.tmux/sockets/)
│   ├── agent-fix-auth (Claude Code)
│   └── agent-add-api (Claude Code)
│
├── Registry (~/.config/ts/agents.json)
│   └── { agents: {...}, active_count: 2 }
│
└── Monitoring
    └── sq-monitor → Grafana (Loki + Prometheus)
```

## 📊 모니터링

```bash
# 한 번 실행
sq-monitor

# 지속 실행 (30초 간격)
sq-monitor continuous 30

# Systemd 서비스
sudo systemctl start sq-monitor
sudo systemctl enable sq-monitor
```

## 💡 사용 시나리오

### 시나리오 1: 병렬 기능 개발
```bash
# 3개의 독립적인 기능을 동시에 개발
sq spawn frontend feature/ui-update "Update UI components"
sq spawn backend feature/api-refactor "Refactor REST API"
sq spawn testing feature/add-tests "Add integration tests"

# 모든 에이전트 상태 확인
sq list
```

### 시나리오 2: 안전한 실험
```bash
# 에이전트 생성
sq spawn experiment feature/new-algo "Test new algorithm"

# 체크포인트 생성
sq checkpoint agent-experiment "Before risky changes"

# 실험 진행...
# 문제 발생 시 Git으로 되돌리기
cd ~/.ts-worktrees/agent-experiment
git reset --hard HEAD~1

# 에이전트 재개
sq resume agent-experiment
```

### 시나리오 3: 작업 자동 분산
```bash
# 여러 작업을 빠르게 위임
sq delegate "Fix login authentication bug"
sq delegate "Add user profile management"
sq delegate "Optimize database queries"
sq delegate "Write API documentation"

# 자동 모드로 위임 (프롬프트 자동 승인)
sq delegate "Add caching layer" --auto
```

## 🔧 고급 기능

### Bash Completion
```bash
# Tab 자동완성 사용
sq at<TAB>       # → sq attach
sq attach ag<TAB>  # → agent 목록 표시
```

### Git Worktree 수동 관리
```bash
# Worktree 목록
git worktree list

# 특정 worktree로 이동
cd ~/.ts-worktrees/agent-fix-auth

# 메인 브랜치로 머지
git checkout main
git merge feature/fix-auth
git push

# Worktree 제거
git worktree remove ~/.ts-worktrees/agent-fix-auth
```

### 리소스 제한 설정
```bash
# Agent registry에서 최대 에이전트 수 조정
jq '.max_agents = 20' ~/.config/ts/agents.json > ~/.config/ts/agents.json.tmp
mv ~/.config/ts/agents.json.tmp ~/.config/ts/agents.json
```

## 🐛 트러블슈팅

### 문제: sq 명령어를 찾을 수 없음
```bash
# 설치 확인
which sq

# 재설치
./install-sq.sh
```

### 문제: 에이전트가 시작되지 않음
```bash
# Socket 정리
rm ~/.tmux/sockets/agent-*

# Registry 초기화
sq init
```

### 문제: Worktree 충돌
```bash
# 모든 worktree 확인
git worktree list

# 손상된 worktree 제거
git worktree remove -f <path>

# Registry 정리
jq '.agents = {}' ~/.config/ts/agents.json > ~/.config/ts/agents.json.tmp
mv ~/.config/ts/agents.json.tmp ~/.config/ts/agents.json
```

## 📚 명령어 레퍼런스

| 명령어 | 별칭 | 설명 |
|--------|------|------|
| `sq spawn` | `create` | 새 에이전트 생성 |
| `sq list` | `ls` | 에이전트 목록 |
| `sq attach` | - | 에이전트 연결 |
| `sq checkpoint` | `save` | 체크포인트 생성 |
| `sq resume` | `continue` | 에이전트 재개 |
| `sq kill` | `stop`, `terminate` | 에이전트 종료 |
| `sq delegate` | `assign` | 작업 자동 위임 |
| `sq dashboard` | `dash`, `status` | 대시보드 |
| `sq init` | - | 초기화 |
| `sq help` | - | 도움말 |

## 🔗 통합

### 기존 ts 명령어와 통합
```bash
# ts 명령어에서 sq 사용
ts squad spawn my-task   # sq spawn my-task와 동일
```

### CI/CD 파이프라인 통합
```bash
# .github/workflows/multi-agent-test.yml
- name: Run multi-agent tests
  run: |
    sq spawn test-unit feature/test-unit "Run unit tests" --auto
    sq spawn test-integration feature/test-int "Run integration tests" --auto
    sq list
```

## 📈 Grafana 메트릭

- `sq_total_agents` - 총 에이전트 수
- `sq_active_agents` - 활성 에이전트
- `sq_paused_agents` - 일시정지
- `sq_failed_agents` - 실패
- `sq_worktrees` - Worktree 수
- `sq_disk_usage_mb` - 디스크 사용량

**Loki 쿼리:**
```
{job="ts-squad"} |= "agent_spawned"
{job="ts-squad", agent_id="agent-fix-auth"}
```

## 🎯 Best Practices

1. **명확한 Task 이름 사용**
   ```bash
   # Good
   sq spawn fix-auth-bug
   sq spawn add-profile-api

   # Bad
   sq spawn task1
   sq spawn test
   ```

2. **주기적인 체크포인트**
   ```bash
   # 중요한 단계마다 체크포인트
   sq checkpoint agent-my-task "Phase 1: Database schema"
   sq checkpoint agent-my-task "Phase 2: API endpoints"
   ```

3. **작업 완료 후 정리**
   ```bash
   # 머지 후 에이전트 제거
   cd ~/.ts-worktrees/agent-my-task
   git checkout main
   git merge feature/my-task
   sq kill agent-my-task
   ```

4. **모니터링 활용**
   ```bash
   # 백그라운드 모니터링 실행
   sudo systemctl enable sq-monitor
   sudo systemctl start sq-monitor
   ```

## 🤝 기여

이슈나 기능 제안은 GitHub에 등록해주세요.

## 📄 라이선스

MIT License

---

**SQ - Simple, Quick, Squad Management** 🚀
