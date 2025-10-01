# 📝 Slack App 설정 - 필요한 토큰 정보

## 🔑 필요한 3가지 토큰

### 1. **Bot User OAuth Token** (필수)
- **형식**: `xoxb-xxxxx-xxxxx-xxxxxx`
- **어디서**: OAuth & Permissions → Bot User OAuth Token
- **용도**: Slack에 메시지 보내고 명령 받기
- **환경변수**: `SLACK_BOT_TOKEN`

### 2. **Signing Secret** (필수)
- **형식**: 32자 문자열 (예: `a1b2c3d4e5f6...`)
- **어디서**: Basic Information → App Credentials → Signing Secret
- **용도**: Slack 요청이 진짜인지 검증
- **환경변수**: `SLACK_SIGNING_SECRET`

### 3. **App-Level Token** (필수)
- **형식**: `xapp-xxxxx-xxxxx-xxxxxx`
- **어디서**: Basic Information → App-Level Tokens
- **용도**: Socket Mode로 실시간 연결
- **환경변수**: `SLACK_APP_TOKEN`

---

## 📋 단계별 가이드

### Step 1: Slack App 생성
```
1. https://api.slack.com/apps 방문
2. "Create New App" 클릭
3. "From scratch" 선택
4. App Name: "Tmux Bridge"
5. Workspace: 본인 워크스페이스 선택
6. "Create App" 클릭
```

### Step 2: Socket Mode 활성화
```
왼쪽 메뉴 → Settings → Socket Mode
1. "Enable Socket Mode" 토글 켜기
2. Token Name: "tmux-bridge-token"
3. Scope: "connections:write" 선택
4. "Generate" 클릭
5. ⚠️ xapp-로 시작하는 토큰 복사 → 이게 APP_TOKEN!
```

### Step 3: Bot Token Scopes 추가
```
왼쪽 메뉴 → Features → OAuth & Permissions → Scopes
1. "Add an OAuth Scope" 클릭
2. 다음 3개 추가:
   - commands (슬래시 명령 사용)
   - chat:write (메시지 전송)
   - app_mentions:read (멘션 읽기)
```

### Step 4: 워크스페이스에 설치
```
OAuth & Permissions 페이지 상단
1. "Install to Workspace" 클릭
2. "Allow" 클릭
3. ⚠️ xoxb-로 시작하는 토큰 복사 → 이게 BOT_TOKEN!
```

### Step 5: Signing Secret 복사
```
왼쪽 메뉴 → Settings → Basic Information
1. App Credentials 섹션 찾기
2. "Signing Secret" → "Show" 클릭
3. ⚠️ 32자 문자열 복사 → 이게 SIGNING_SECRET!
```

### Step 6: Slash Command 생성
```
왼쪽 메뉴 → Features → Slash Commands
1. "Create New Command" 클릭
2. 입력:
   - Command: /tmux
   - Request URL: (비워두기 - Socket Mode 사용)
   - Short Description: Control tmux sessions
   - Usage Hint: [list|create|exec|kill|output] [args]
3. "Save" 클릭
```

---

## 🔐 .env 파일 만들기

모든 토큰을 받았으면:

```bash
cd /home/jclee/app/tmux/slack-tmux-bridge

cat > .env << 'EOF'
# Slack Tokens
SLACK_BOT_TOKEN=xoxb-여기에-봇-토큰
SLACK_SIGNING_SECRET=여기에-시그닝-시크릿
SLACK_APP_TOKEN=xapp-여기에-앱-토큰

# Server Config
PORT=3000
WS_PORT=3001
TMUX_SOCKET_DIR=/home/jclee/.tmux/sockets
EOF

# 실제 토큰으로 교체
nano .env
```

---

## ✅ 체크리스트

완료하면 체크:

- [ ] Slack App 생성됨
- [ ] Socket Mode 활성화
- [ ] App-Level Token 받음 (xapp-...)
- [ ] Bot Token Scopes 3개 추가
- [ ] 워크스페이스에 설치
- [ ] Bot Token 받음 (xoxb-...)
- [ ] Signing Secret 받음
- [ ] /tmux 슬래시 명령 생성
- [ ] .env 파일에 3개 토큰 입력
- [ ] 토큰 검증: `cat .env | grep -E "xoxb|xapp"`

---

## 🧪 테스트

```bash
# 1. 토큰 확인
cat .env

# 2. 서버 시작
npm start

# 3. Slack에서 테스트
/tmux help
```

---

## 🐛 문제 해결

### "Token not found" 에러
→ .env 파일이 있는지 확인: `ls -la .env`

### "Invalid token" 에러
→ 토큰 형식 확인:
- BOT_TOKEN: `xoxb-`로 시작
- APP_TOKEN: `xapp-`로 시작
- SIGNING_SECRET: 32자 문자열

### Bot이 응답 없음
→ Socket Mode 활성화 확인
→ 워크스페이스에 설치 확인
→ 서버 로그 확인: `npm start`

---

## 📸 스크린샷 위치 (참고용)

1. **App Token**: Settings → Socket Mode → Token 생성
2. **Bot Token**: OAuth & Permissions → 상단 "Bot User OAuth Token"
3. **Signing Secret**: Basic Information → App Credentials

---

**완료되면 `npm start` 실행!** 🚀
