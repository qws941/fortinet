# 🚀 Tmux + Claude Code 통합 완료

## ✅ 설치된 기능

### 1. `cc` 명령어 (Claude Code 실행)
```bash
cc  # 현재 디렉토리에서 Claude Code 실행
```

**특징**:
- 현재 디렉토리(`pwd`)를 working directory로 사용
- 크리덴셜 정보 자동 로드 (`/home/jclee/synology/config/claude/`)
- 환경변수 충돌 없음

**위치**:
- 실제 파일: `/home/jclee/app/tmux/cc`
- 심볼릭 링크: `~/.claude/bin/cc` (PATH 최우선)

### 2. `ts` 명령어 (Tmux Session Manager)
```bash
ts blacklist          # blacklist 세션 생성/접속
ts list               # 모든 세션 목록
ts kill blacklist     # 세션 종료
```

**특징**:
- Socket 기반 세션 격리 (`/home/jclee/.tmux/sockets/`)
- 프로젝트 디렉토리 자동 복원
- Grafana 텔레메트리 통합

**위치**:
- 실제 파일: `/usr/local/bin/ts`
- 심볼릭 링크: `~/.claude/bin/ts` (PATH 최우선)

### 3. Tmux 세션 pwd 자동 복원
- 세션 생성 시 디렉토리 저장: `~/.config/ts/metadata/<session>.path`
- 세션 재접속 시 자동 복원
- PROMPT_COMMAND로 디렉토리 변경 추적

### 4. Bash 프로필 정리
**해결한 문제**:
- ✅ ts 명령어 3중 충돌 해결
- ✅ PATH 중복 제거
- ✅ bashrc.d 중복 로드 제거

**파일**:
- `~/.bashrc` → `~/.claude/config/bashrc` (심볼릭 링크)
- 백업: `~/.claude/config/bashrc.backup-*`

## 📝 사용 예시

```bash
# 1. 프로젝트 세션 시작
cd /home/jclee/app/blacklist
ts blacklist              # blacklist 세션 생성

# 2. tmux 안에서 Claude Code 실행
cc                        # 현재 디렉토리에서 Claude 실행

# 3. 세션 종료 후 다시 접속
ts blacklist              # 자동으로 /app/blacklist로 이동

# 4. 다른 프로젝트로 이동
cd /home/jclee/app/safework
ts safework               # safework 세션 생성
cc                        # safework에서 Claude 실행
```

## 🔧 설정 파일 위치

```
~/.bashrc                              # → ~/.claude/config/bashrc (심볼릭 링크)
~/.bashrc.d/
  ├── tmux-auto-cc.sh                  # Claude Code tmux 통합
  ├── tmux-pwd-restore.sh              # pwd 자동 복원
  └── ts-shortcuts.sh.disabled         # 비활성화됨

~/.tmux.conf                           # Tmux 설정
~/.config/ts/
  ├── config.json                      # TS 설정
  └── metadata/                        # 세션별 디렉토리 정보
      ├── blacklist.path
      └── safework.path

/home/jclee/app/tmux/cc               # Claude Code 실행 스크립트
/usr/local/bin/ts                      # TS 명령어
```

## 🧪 검증 방법

```bash
# 새 shell 시작
bash

# 명령어 위치 확인
which ts  # ~/.claude/bin/ts
which cc  # ~/.claude/bin/cc

# PATH 중복 확인
echo $PATH | tr ':' '\n' | grep -E 'claude|local'

# Tmux 세션 테스트
ts test /tmp
pwd                    # /tmp 확인
exit

ts test
pwd                    # /tmp로 복원 확인
```

## 🎯 주요 환경변수

### 공통
- `CI=true` - Claude CLI raw mode 수정
- `CLAUDE_HOME=/home/jclee/.claude`
- `APP_ROOT=/home/jclee/app`

### Tmux 안에서만
- `CLAUDE_TMUX_SESSION` - 현재 세션 이름
- `CLAUDE_WORKING_DIR` - 현재 작업 디렉토리
- `TMUX_SESSION` - tmux 세션 이름

## 🔄 업데이트 방법

```bash
# Bash 설정 리로드
source ~/.bashrc

# Tmux 설정 리로드 (tmux 안에서)
tmux source-file ~/.tmux.conf
# 또는
<prefix> + r  # Ctrl-b, r

# TS 명령어 업데이트
cd /home/jclee/app/tmux
sudo ./install-advanced-ts.sh
```

## 🐛 문제 해결

### ts 명령어가 작동하지 않음
```bash
# 심볼릭 링크 확인
ls -la ~/.claude/bin/ts

# 재생성
ln -sf /usr/local/bin/ts ~/.claude/bin/ts
```

### cc 명령어가 작동하지 않음
```bash
# Claude binary 확인
ls -la /home/jclee/.claude/local/claude

# 크리덴셜 파일 확인
ls -la /home/jclee/synology/config/claude/
```

### pwd가 복원되지 않음
```bash
# 메타데이터 확인
cat ~/.config/ts/metadata/<session>.path

# bashrc.d 스크립트 확인
source ~/.bashrc.d/tmux-pwd-restore.sh
```
