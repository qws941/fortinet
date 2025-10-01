#!/bin/bash
# Fix tmux auto-start issue that causes duplicate key input

set -euo pipefail

BASHRC="$HOME/.bashrc"
BACKUP="$HOME/.bashrc.backup.$(date +%Y%m%d_%H%M%S)"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔧 Fixing tmux auto-start issue"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 백업 생성
echo "📦 Creating backup: $BACKUP"
cp "$BASHRC" "$BACKUP"

# tmux 자동 실행 코드 주석 처리
echo "🔧 Disabling auto-tmux in bashrc..."

sed -i '138,167 s/^/# DISABLED: /' "$BASHRC"

# 또는 완전히 삭제하려면:
# sed -i '138,167d' "$BASHRC"

echo ""
echo "✅ Fixed!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 다음 단계:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. 현재 tmux 세션에서 나가기:"
echo "   Ctrl+b d"
echo ""
echo "2. 새 터미널 열기 (tmux 자동 실행 안됨)"
echo ""
echo "3. 원하는 프로젝트에서 수동으로 세션 시작:"
echo "   cd /home/jclee/app/blacklist"
echo "   ts blacklist"
echo ""
echo "4. 키 입력이 정상인지 확인"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "💾 백업 위치: $BACKUP"
echo "🔄 원래대로 되돌리려면: cp $BACKUP $BASHRC"
echo ""
