# Tmux + Claude Code 통합 시스템

이 시스템은 tmux 세션 관리와 Claude Code를 완벽하게 통합합니다.

## 🎯 핵심 기능

### 1. 명령어
- `ts <session>` 또는 `cc <session>` - tmux 세션 생성/접속 (디렉토리 자동 복원)
- `ts` / `cc` - 마지막 세션 재개 또는 세션 목록 표시
- **Note**: `ts`와 `cc` 명령어는 완전히 호환되며 동일한 기능을 제공합니다

### 2. 자동화
- ✅ tmux 세션 접속 시 pwd 자동 복원
- ✅ Claude Code 크리덴셜 자동 로드
- ✅ 환경변수 충돌 제거
- ✅ Bash 프로필 최적화 완료

## 📖 자세한 문서

- [INSTALL-SUMMARY.md](./INSTALL-SUMMARY.md) - 전체 설치 내역 및 사용법
- [CLAUDE.md](./CLAUDE.md) - Claude Code를 위한 프로젝트 가이드

## 🚀 빠른 시작

```bash
# 1. 새 shell 시작하여 설정 로드
bash

# 2. tmux 세션 시작 (ts 또는 cc 사용 가능)
cd /home/jclee/app/blacklist
ts blacklist
# 또는
cc blacklist

# 3. 세션 목록 확인
ts list
# 또는
cc list

# 4. 마지막 세션 재개
ts
# 또는
cc
```

## 🔧 파일 구조

```
/home/jclee/app/tmux/
├── cc                          # Claude Code 실행 스크립트
├── README.md                   # 이 파일
├── INSTALL-SUMMARY.md          # 상세 설치 문서
└── CLAUDE.md                   # 프로젝트 가이드

~/.bashrc → ~/.claude/config/bashrc
~/.bashrc.d/
├── tmux-auto-cc.sh
└── tmux-pwd-restore.sh

/home/jclee/app/tmux/tc         # TC/CC Master 스크립트
~/.claude/bin/
├── tc → /home/jclee/app/tmux/tc
└── cc → tc (symlink)
```

## 📚 주요 명령어

### 세션 관리
```bash
ts <name> [path]      # 세션 생성/접속
cc <name> [path]      # ts와 동일 (별칭)
ts list              # 모든 활성 세션 목록
ts kill <name>       # 특정 세션 종료
ts clean             # 모든 세션 정리
ts resume            # 마지막 세션 재개
```

### 프로젝트 발견
```bash
ts discover          # 대화형 프로젝트 발견 및 등록
ts scan              # discover의 별칭
```

### 백그라운드 작업
```bash
ts bg start <name> <cmd>   # 백그라운드 작업 시작
ts bg list                 # 백그라운드 작업 목록
ts bg stop <name>          # 백그라운드 작업 중지
ts bg attach <name>        # 백그라운드 작업에 연결
```

### IPC (프로세스 간 통신)
```bash
ts ipc send <session> <msg>   # 세션에 메시지 전송
ts ipc broadcast <msg>        # 모든 세션에 브로드캐스트
```

### 시스템
```bash
ts version            # 버전 정보 표시
ts help               # 도움말 표시
```
