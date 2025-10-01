#!/bin/bash
# Tmux 웹 인터페이스 배포 스크립트

set -euo pipefail

echo "🚀 Tmux WebSocket 웹 인터페이스 배포 시작"

# 색상 정의
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 배포 모드 선택
echo ""
echo "배포 모드를 선택하세요:"
echo "1) 로컬 Node.js 서버"
echo "2) Systemd 서비스"
echo "3) Docker 컨테이너"
read -p "선택 (1-3): " MODE

case $MODE in
  1)
    echo -e "${BLUE}📦 로컬 Node.js 서버 모드${NC}"

    # 의존성 설치
    if [ ! -d "node_modules" ]; then
      echo "📥 의존성 설치 중..."
      npm install
    fi

    # 기존 프로세스 종료
    pkill -f "node.*server.js" || true

    # 서버 시작
    echo "🚀 서버 시작 중..."
    nohup node server.js > /tmp/tmux-web.log 2>&1 &
    sleep 2

    if pgrep -f "node.*server.js" > /dev/null; then
      echo -e "${GREEN}✅ 서버 시작 성공${NC}"
      echo "📊 로그: tail -f /tmp/tmux-web.log"
    else
      echo -e "${RED}❌ 서버 시작 실패${NC}"
      exit 1
    fi
    ;;

  2)
    echo -e "${BLUE}⚙️ Systemd 서비스 모드${NC}"

    # 서비스 파일 복사
    echo "📝 서비스 파일 설치 중..."
    sudo cp tmux-web.service /etc/systemd/system/

    # Systemd 리로드
    sudo systemctl daemon-reload

    # 서비스 시작 및 활성화
    sudo systemctl enable tmux-web
    sudo systemctl restart tmux-web

    sleep 2

    if sudo systemctl is-active --quiet tmux-web; then
      echo -e "${GREEN}✅ Systemd 서비스 시작 성공${NC}"
      echo "📊 상태: sudo systemctl status tmux-web"
      echo "📊 로그: sudo journalctl -u tmux-web -f"
    else
      echo -e "${RED}❌ 서비스 시작 실패${NC}"
      sudo systemctl status tmux-web
      exit 1
    fi
    ;;

  3)
    echo -e "${BLUE}🐳 Docker 컨테이너 모드${NC}"

    # Docker 이미지 빌드
    echo "🔨 Docker 이미지 빌드 중..."
    docker build -t tmux-web-interface:latest .

    # 기존 컨테이너 중지 및 제거
    docker stop tmux-web-interface 2>/dev/null || true
    docker rm tmux-web-interface 2>/dev/null || true

    # 컨테이너 실행
    echo "🚀 컨테이너 시작 중..."
    docker-compose up -d

    sleep 3

    if docker ps | grep -q tmux-web-interface; then
      echo -e "${GREEN}✅ Docker 컨테이너 시작 성공${NC}"
      echo "📊 로그: docker logs -f tmux-web-interface"
      echo "📊 상태: docker ps | grep tmux-web-interface"
    else
      echo -e "${RED}❌ 컨테이너 시작 실패${NC}"
      docker logs tmux-web-interface
      exit 1
    fi
    ;;

  *)
    echo -e "${RED}❌ 잘못된 선택입니다${NC}"
    exit 1
    ;;
esac

# 헬스 체크
echo ""
echo "🏥 헬스 체크 중..."
sleep 2

HEALTH=$(curl -s http://localhost:3030/health | jq -r '.status' || echo "error")

if [ "$HEALTH" == "ok" ]; then
  echo -e "${GREEN}✅ 헬스 체크 통과${NC}"
else
  echo -e "${RED}❌ 헬스 체크 실패${NC}"
  exit 1
fi

# 세션 목록 테스트
echo ""
echo "🧪 API 테스트 중..."
SESSIONS=$(curl -s http://localhost:3030/api/sessions | jq -r '.success')

if [ "$SESSIONS" == "true" ]; then
  echo -e "${GREEN}✅ API 테스트 통과${NC}"
else
  echo -e "${RED}❌ API 테스트 실패${NC}"
  exit 1
fi

# 완료 메시지
echo ""
echo -e "${GREEN}🎉 배포 완료!${NC}"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${BLUE}📍 접속 정보${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌐 웹 UI:       http://localhost:3030"
echo "🔌 WebSocket:   ws://localhost:3030"
echo "📡 REST API:    http://localhost:3030/api"
echo "🏥 Health:      http://localhost:3030/health"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 실시간 세션 모니터링이 활성화되었습니다!"
echo "📈 Grafana 통합: {job=\"ts-command\"} |~ \"web-interface\""
