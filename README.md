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

- [CLAUDE.md](./CLAUDE.md) - Claude Code를 위한 프로젝트 가이드
- [docs/](./docs/) - 상세 문서 디렉토리
  - [INSTALL-SUMMARY.md](./docs/INSTALL-SUMMARY.md) - 전체 설치 내역
  - [QUICKSTART-AUTO-DISCOVER.md](./docs/QUICKSTART-AUTO-DISCOVER.md) - 빠른 시작 가이드
  - [TS-QUICK-REFERENCE.md](./docs/TS-QUICK-REFERENCE.md) - TS 명령어 레퍼런스

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

## 🔧 디렉토리 구조

```
/home/jclee/app/tmux/
├── agents/              # AI 에이전트 (Claude, monitoring)
├── scripts/             # 유틸리티 및 설치 스크립트
├── tests/               # 테스트 스크립트
├── docs/                # 상세 문서
├── config/              # 설정 파일 (Grafana, Prometheus)
├── archive/             # 아카이브된 구 버전 스크립트
├── validate/            # TypeScript 검증 모듈
├── list/                # TypeScript 세션 목록 모듈
├── web-interface/       # 웹 인터페이스
├── slack-tmux-bridge/   # Slack 통합
├── README.md            # 메인 문서
├── CLAUDE.md            # Claude Code 가이드
├── docker-compose.yml   # Docker 서비스 정의
├── tc                   # TC/CC Master 스크립트
├── sq                   # SQ 명령어
└── ts.sh                # TS 명령어 메인 스크립트
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
