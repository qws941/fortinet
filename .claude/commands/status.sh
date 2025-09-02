#!/bin/bash
# Claude Code 자동화 시스템 상태 확인

echo "🎯 FortiGate Nextrade - Claude Code 자동화 시스템 상태"
echo "=========================================="
echo ""

# Git 상태
echo "📋 Git 상태:"
git status --short | head -10
if [ $? -eq 0 ] && [ -z "$(git status --porcelain)" ]; then
    echo "  ✅ 작업 트리 깨끗함"
else
    echo "  📝 $(git status --porcelain | wc -l)개 변경사항 있음"
fi
echo ""

# 브랜치 정보
echo "🌿 현재 브랜치: $(git branch --show-current)"
echo "🔗 원격 브랜치 상태:"
git status -uno | grep "Your branch" || echo "  ✅ 원격과 동기화됨"
echo ""

# MCP 설정 확인
echo "🔌 MCP 서버 설정:"
if [ -f ".claude/mcp-integration-config.json" ]; then
    echo "  ✅ MCP 통합 설정 파일 존재"
    echo "  📊 등록된 서버 수: $(cat .claude/mcp-integration-config.json | jq '.servers | keys | length')"
    echo "  🚀 자동 시작 서버들:"
    cat .claude/mcp-integration-config.json | jq -r '.servers | to_entries[] | select(.value.auto_start == true) | "    • \(.key)"'
else
    echo "  ❌ MCP 설정 파일 없음"
fi
echo ""

# GitHub Actions 워크플로우
echo "🏗️ GitHub Actions 워크플로우:"
if [ -f ".github/workflows/claude-code-action.yml" ]; then
    echo "  ✅ Claude Code 통합 워크플로우 존재"
else
    echo "  ❌ Claude Code 워크플로우 없음"
fi

if [ -f ".github/workflows/main-deploy.yml" ]; then
    echo "  ✅ 메인 배포 워크플로우 존재"
else
    echo "  ❌ 메인 배포 워크플로우 없음"
fi
echo ""

# Docker 및 배포 상태
echo "🐳 배포 상태:"
# ArgoCD 애플리케이션 확인 (선택적)
if command -v argocd >/dev/null 2>&1; then
    echo "  📊 ArgoCD 상태: $(argocd app get fortinet -o json 2>/dev/null | jq -r '.status.health.status // "확인 불가"')"
else
    echo "  ⚠️ ArgoCD CLI 없음"
fi

# 애플리케이션 헬스 체크
echo "  🏥 애플리케이션 헬스 체크..."
if curl -f --max-time 5 "http://192.168.50.110:30777/api/health" >/dev/null 2>&1; then
    echo "  ✅ 애플리케이션 정상 동작 중"
else
    echo "  ❌ 애플리케이션 접근 불가 또는 다운"
fi
echo ""

# 자동화 스크립트 상태
echo "🤖 자동화 스크립트:"
SCRIPTS=(".claude/automation-manager.py" "scripts/live-log-viewer.sh")
for script in "${SCRIPTS[@]}"; do
    if [ -f "$script" ]; then
        if [ -x "$script" ]; then
            echo "  ✅ $script (실행 가능)"
        else
            echo "  ⚠️ $script (실행 권한 없음)"
        fi
    else
        echo "  ❌ $script (없음)"
    fi
done
echo ""

# Python 환경 확인
echo "🐍 Python 환경:"
if command -v python3 >/dev/null 2>&1; then
    echo "  ✅ Python3: $(python3 --version)"
else
    echo "  ❌ Python3 없음"
fi

if [ -f "config/requirements.txt" ]; then
    echo "  📋 Requirements 파일 존재"
else
    echo "  ❌ Requirements 파일 없음"
fi
echo ""

# 최근 커밋 정보
echo "📝 최근 커밋:"
git log --oneline -3
echo ""

# 유용한 명령어들
echo "⚡ 유용한 명령어:"
echo "  /main                    # 완전 자동화 파이프라인"
echo "  /test                    # 테스트 실행"
echo "  /clean                   # 코드 정리"  
echo "  /deploy                  # 배포"
echo "  python3 .claude/automation-manager.py  # 자동화 매니저"
echo "  ./scripts/live-log-viewer.sh live      # 실시간 로그 뷰어"
echo ""

# 전체 상태 요약
echo "📊 전체 시스템 상태 요약:"
status_count=0
if [ -f ".claude/mcp-integration-config.json" ]; then ((status_count++)); fi
if [ -f ".github/workflows/claude-code-action.yml" ]; then ((status_count++)); fi
if [ -f ".claude/automation-manager.py" ] && [ -x ".claude/automation-manager.py" ]; then ((status_count++)); fi
if curl -f --max-time 5 "http://192.168.50.110:30777/api/health" >/dev/null 2>&1; then ((status_count++)); fi
if command -v python3 >/dev/null 2>&1; then ((status_count++)); fi

if [ $status_count -ge 4 ]; then
    echo "  🎉 시스템 상태: 우수 ($status_count/5)"
elif [ $status_count -ge 3 ]; then
    echo "  ✅ 시스템 상태: 양호 ($status_count/5)"
elif [ $status_count -ge 2 ]; then
    echo "  ⚠️ 시스템 상태: 보통 ($status_count/5)"
else
    echo "  ❌ 시스템 상태: 점검 필요 ($status_count/5)"
fi

echo ""
echo "🎯 Claude Code 자동화 시스템 준비 완료!"