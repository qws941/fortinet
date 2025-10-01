# SQ - Squad Queue (Multi-Agent Manager)

**짧고 기억하기 쉬운 멀티 에이전트 관리 도구**

## 🚀 빠른 시작

```bash
# 1. 초기화
sq init

# 2. 에이전트 생성
sq spawn my-task

# 3. 목록 확인
sq list

# 4. 대시보드
sq dashboard
```

## 📖 주요 명령어

### 에이전트 관리

```bash
# 에이전트 생성 (간단)
sq spawn fix-bug

# 에이전트 생성 (상세)
sq spawn fix-auth feature/fix-auth "Fix authentication bug"

# 자동 모드로 생성
sq spawn optimize-api feature/optimize "Optimize API" --auto

# 작업 자동 위임
sq delegate "Add REST API endpoints"
```

### 상태 확인

```bash
# 에이전트 목록
sq list

# 대시보드
sq dashboard

# 도움말
sq help
```

### 에이전트 제어

```bash
# 연결
sq attach agent-fix-bug

# 체크포인트 (작업 저장)
sq checkpoint agent-fix-bug "Completed phase 1"

# 재개
sq resume agent-fix-bug

# 종료
sq kill agent-fix-bug
```

## 🎯 작동 원리

1. **Git Worktrees** - 각 에이전트가 독립된 브랜치에서 작업
2. **Tmux 세션** - 격리된 Claude Code 인스턴스
3. **Grafana 모니터링** - 모든 활동 추적

## 📊 구조

```
~/.config/ts/agents.json    # 에이전트 레지스트리
~/.ts-worktrees/             # Git worktrees
~/.tmux/sockets/             # Tmux 세션 소켓
```

## 🔧 설치 확인

```bash
# sq 설치 확인
which sq

# 버전 확인
sq help

# 테스트 실행
./test-sq.sh
```

## 💡 사용 예시

### 병렬 작업

```bash
# 3개의 독립적인 작업 동시 진행
sq spawn frontend feature/ui "Update UI"
sq spawn backend feature/api "Refactor API"
sq spawn testing feature/tests "Add tests"

# 모든 에이전트 확인
sq list
```

### 체크포인트 워크플로우

```bash
# 작업 시작
sq spawn risky-change feature/experiment "Experimental feature"

# 중요한 지점에서 저장
sq checkpoint agent-risky-change "Before major refactor"

# 문제 발생 시 롤백 (Git reset 사용)
cd ~/.ts-worktrees/agent-risky-change
git log --oneline
git reset --hard <commit-hash>

# 재개
sq resume agent-risky-change
```

## 🐛 트러블슈팅

### 에이전트가 시작되지 않음

```bash
# 죽은 소켓 제거
rm ~/.tmux/sockets/agent-*

# 레지스트리 초기화
sq init
```

### Git worktree 충돌

```bash
# 모든 worktree 확인
git worktree list

# 손상된 worktree 제거
git worktree remove -f ~/.ts-worktrees/agent-*
```

## 📚 추가 리소스

- **전체 문서**: `TS-SQUAD-README.md`
- **통합 보고서**: `TS-SQUAD-INTEGRATION-SUMMARY.md`
- **테스트**: `./test-sq.sh`

## 🎉 Happy Coding!

```bash
sq spawn awesome-feature
```
