# Tmux Session Selector (tss)

인터랙티브한 tmux 세션 선택 및 관리 도구

## 🚀 사용법

터미널에서 다음 명령어를 실행하세요:

```bash
tss
```

또는 직접 스크립트 실행:

```bash
/home/jclee/app/tmux/tmux-session-selector.sh
```

## ✨ 주요 기능

### 1️⃣ 세션 연결
- 숫자 키로 세션 선택 후 즉시 연결
- tmux 안에서 실행 시 자동으로 switch-client 사용

### 2️⃣ 새 세션 생성 (N)
- 대화형으로 세션 이름과 작업 디렉토리 입력
- 중복 세션명 자동 확인

### 3️⃣ 세션 종료 (K)
- 개별 세션 선택 종료
- 모든 세션 일괄 종료 (위험!)

### 4️⃣ 목록 새로고침 (L)
- 실시간 세션 상태 업데이트

### 5️⃣ 웹 인터페이스 (W)
- 브라우저에서 http://localhost:3333 자동 오픈
- 서버 미실행 시 자동 시작 옵션

### 6️⃣ 종료 (Q)
- 선택기 종료 (세션은 유지됨)

## 📋 화면 구성

```
╔════════════════════════════════════════════════════════╗
║           🖥️  TMUX 세션 선택기                        ║
╚════════════════════════════════════════════════════════╝

📋 세션 목록:

[1] blacklist
    └─ 윈도우: 2개 | 생성: 2025-10-01 16:48 | 상태: 🟢 연결됨

[2] claude
    └─ 윈도우: 1개 | 생성: 2025-10-01 16:40 | 상태: ⚪ 분리됨

[3] tmux-web
    └─ 윈도우: 1개 | 생성: 2025-10-01 19:37 | 상태: ⚪ 분리됨

════════════════════════════════════════════════════════

[1-3] 세션 연결
[N] 새 세션 생성
[K] 세션 종료
[L] 세션 목록 새로고침
[W] 웹 인터페이스 열기 (http://localhost:3333)
[Q] 종료

선택: _
```

## 🎨 색상 표시

- 🟢 **녹색 점**: 현재 연결된 세션
- ⚪ **흰색 점**: 분리된 세션
- **파란색 숫자**: 선택 가능한 번호
- **빨간색**: 위험한 작업 (종료 등)
- **녹색**: 안전한 작업 (생성, 연결)

## 💡 팁

### 빠른 세션 전환
```bash
# 선택기 실행 후 숫자만 입력
tss
> 1  # blacklist 세션으로 즉시 이동
```

### Alias 설정
`~/.bashrc` 또는 `~/.zshrc`에 추가:

```bash
alias ts='tss'
alias tmux-menu='tss'
```

### tmux 안에서 사용
tmux 세션 안에서 실행하면:
- 새 윈도우 대신 switch-client 사용
- 원활한 세션 전환

### 키보드 단축키
- `Ctrl+C`: 선택기 즉시 종료
- `L`: 목록 새로고침 (세션 추가/삭제 반영)
- `Q`: 정상 종료

## 🔧 통합

### 웹 인터페이스와 함께 사용
```bash
# CLI 선택기
tss

# 웹 인터페이스 (브라우저)
http://localhost:3333
```

둘 다 같은 tmux 세션을 관리하며 실시간 동기화됩니다.

### ts 명령어와 함께 사용
```bash
# ts로 세션 관리
ts list
ts create myproject

# tss로 인터랙티브 선택
tss
```

## 🛠️ 문제 해결

### 세션이 보이지 않음
```bash
# tmux 서버 상태 확인
tmux ls

# 서버가 없으면 새 세션 생성
tmux new -s test
```

### 권한 오류
```bash
# 스크립트 실행 권한 확인
ls -l /home/jclee/app/tmux/tmux-session-selector.sh

# 권한 부여
chmod +x /home/jclee/app/tmux/tmux-session-selector.sh
```

### 웹 인터페이스 연결 실패
```bash
# 웹 서버 실행 확인
curl http://localhost:3333

# 서버 시작
cd /home/jclee/app/tmux/web-tmux-interface
./start.sh
```

## 📦 파일 구조

```
/home/jclee/app/tmux/
├── tmux-session-selector.sh    # 메인 스크립트
├── README-session-selector.md  # 이 문서
└── web-tmux-interface/         # 웹 인터페이스
    ├── server.js
    ├── public/index.html
    └── start.sh

/usr/local/bin/
└── tss                          # 글로벌 명령어 (심볼릭 링크)
```

## 🎯 사용 예시

### 예시 1: 프로젝트 세션 연결
```bash
$ tss
# 메뉴에서 [1] blacklist 선택
# → blacklist 세션으로 즉시 연결
```

### 예시 2: 새 프로젝트 세션 생성
```bash
$ tss
# [N] 입력
# 세션 이름: fortinet
# 작업 디렉토리: /home/jclee/app/fortinet
# → fortinet 세션 생성 및 연결
```

### 예시 3: 불필요한 세션 정리
```bash
$ tss
# [K] 입력
# [1-5] 중 삭제할 세션 번호 선택
# y 입력으로 확인
# → 선택한 세션 종료
```

## 🚀 향후 개선 계획

- [ ] fzf 통합 (더 빠른 검색)
- [ ] 세션 그룹/태그 기능
- [ ] 최근 사용 세션 우선 표시
- [ ] 세션 설명 메모 기능
- [ ] Tmux 플러그인 버전
