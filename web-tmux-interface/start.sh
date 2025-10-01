#!/bin/bash
# Tmux Web Interface - 시작 스크립트

cd /home/jclee/app/tmux/web-tmux-interface

echo "🚀 Tmux Web Interface 시작 중..."

# 기존 세션이 있으면 종료
tmux kill-session -t tmux-web 2>/dev/null

# 백그라운드에서 서버 시작
tmux new-session -d -s tmux-web "npm start"

# 서버가 준비될 때까지 대기
sleep 3

# 상태 확인
if curl -s http://localhost:3333/ > /dev/null; then
    echo "✅ 서버가 성공적으로 시작되었습니다!"
    echo ""
    echo "📍 웹 브라우저에서 접속하세요:"
    echo "   http://localhost:3333"
    echo ""
    echo "🔧 서버 로그 확인:"
    echo "   tmux attach -t tmux-web"
    echo ""
    echo "🛑 서버 종료:"
    echo "   tmux kill-session -t tmux-web"
else
    echo "❌ 서버 시작 실패"
    echo "   로그 확인: tmux attach -t tmux-web"
    exit 1
fi
