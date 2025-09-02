#!/bin/bash
# =============================================================================
# FortiGate Nextrade - 실시간 파이프라인 로그 뷰어
# =============================================================================

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

echo_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
echo_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
echo_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
echo_error() { echo -e "${RED}[ERROR]${NC} $1"; }
echo_live() { echo -e "${MAGENTA}[LIVE]${NC} $1"; }

# 실시간 파이프라인 상태 뷰
live_pipeline_view() {
    local run_id=$1
    
    echo_live "🔴 실시간 파이프라인 로그 뷰어 시작..."
    echo "========================================"
    echo ""
    
    while true; do
        clear
        echo -e "${CYAN}🎯 FortiGate Nextrade - 실시간 파이프라인 로그 뷰${NC}"
        echo "========================================"
        echo "📅 $(date '+%Y-%m-%d %H:%M:%S')"
        echo ""
        
        # 현재 실행 중인 파이프라인 상태
        local current_runs=$(gh run list --limit 5 --json number,status,name,createdAt)
        
        echo "📋 최근 파이프라인 상태:"
        echo "----------------------------------------"
        echo "$current_runs" | jq -r '.[] | "\(.number) - \(.name) - \(.status) - \(.createdAt)"' | while read -r line; do
            if echo "$line" | grep -q "in_progress"; then
                echo -e "${GREEN}🔄 $line${NC}"
            elif echo "$line" | grep -q "queued"; then
                echo -e "${YELLOW}⏳ $line${NC}"
            elif echo "$line" | grep -q "completed"; then
                echo -e "${BLUE}✅ $line${NC}"
            else
                echo -e "${CYAN}📝 $line${NC}"
            fi
        done
        echo "----------------------------------------"
        echo ""
        
        # 특정 파이프라인이 지정된 경우
        if [ -n "$run_id" ]; then
            local run_status=$(gh run view "$run_id" --json status,jobs 2>/dev/null)
            if [ $? -eq 0 ]; then
                local status=$(echo "$run_status" | jq -r '.status')
                
                echo "🎯 Pipeline #$run_id 상세 상태:"
                echo "  전체 상태: $status"
                echo ""
                echo "📋 Job 별 상태:"
                echo "$run_status" | jq -r '.jobs[] | "  • \(.name): \(.status) \(.conclusion // "")"'
                echo ""
                
                # 실행 중인 경우 더 자세한 정보
                if [ "$status" = "in_progress" ]; then
                    echo_live "🔄 파이프라인 실행 중..."
                    # Job별 단계 정보 시도
                    local running_jobs=$(echo "$run_status" | jq -r '.jobs[] | select(.status == "in_progress") | .name')
                    if [ -n "$running_jobs" ]; then
                        echo "  실행 중인 Job들:"
                        echo "$running_jobs" | while read -r job; do
                            echo "    → $job"
                        done
                    fi
                elif [ "$status" = "completed" ]; then
                    local conclusion=$(gh run view "$run_id" --json conclusion | jq -r '.conclusion')
                    if [ "$conclusion" = "success" ]; then
                        echo_success "✅ 파이프라인 성공!"
                    else
                        echo_error "❌ 파이프라인 실패: $conclusion"
                    fi
                    break
                fi
            else
                echo_warning "⚠️ Pipeline #$run_id 정보를 가져올 수 없습니다"
            fi
        fi
        
        # Docker 이미지 관련 정보
        echo "🐳 Docker 이미지 상태:"
        echo "  Registry: registry.jclee.me"
        echo "  예상 이미지들:"
        echo "    • fortinet-redis:latest"
        echo "    • fortinet-postgresql:latest"
        echo "    • fortinet:latest"
        echo ""
        
        # 새로고침 정보
        echo "🔄 자동 새로고침: 30초마다"
        echo "⌨️  수동 종료: Ctrl+C"
        echo ""
        
        sleep 30
    done
}

# 로그 다운로드 및 분석
download_and_analyze_logs() {
    local run_id=$1
    
    echo_info "📥 Pipeline #$run_id 로그 다운로드 시도..."
    
    mkdir -p logs/pipeline-runs
    
    if gh run download "$run_id" -D "logs/pipeline-runs/$run_id" 2>/dev/null; then
        echo_success "✅ 로그 다운로드 완료: logs/pipeline-runs/$run_id"
        
        # 로그 분석
        echo_info "🔍 로그 분석 중..."
        
        if [ -d "logs/pipeline-runs/$run_id" ]; then
            echo ""
            echo "📂 다운로드된 로그 파일들:"
            find "logs/pipeline-runs/$run_id" -name "*.txt" | head -10
            echo ""
            
            # 에러 패턴 검색
            echo "🔍 에러 패턴 검색:"
            local error_count=0
            for pattern in "ERROR" "FAILED" "error:" "Error:" "fatal:"; do
                local count=$(find "logs/pipeline-runs/$run_id" -name "*.txt" -exec grep -c "$pattern" {} + 2>/dev/null | awk -F: '{sum += $2} END {print sum+0}')
                if [ "$count" -gt 0 ]; then
                    echo "  ❌ $pattern: $count 건"
                    error_count=$((error_count + count))
                fi
            done
            
            if [ "$error_count" -eq 0 ]; then
                echo_success "  ✅ 에러 패턴 발견되지 않음"
            fi
            
            # 주요 로그 내용 미리보기
            echo ""
            echo "📝 주요 로그 내용 (최근 20줄):"
            find "logs/pipeline-runs/$run_id" -name "*.txt" -exec tail -5 {} \; 2>/dev/null | head -20
        fi
    else
        echo_warning "⚠️ 로그 다운로드 실패 - 파이프라인이 아직 완료되지 않았을 수 있습니다"
        echo "   GitHub URL: https://github.com/qws941/fortinet/actions/runs/$run_id"
    fi
}

# 메인 실행
main() {
    echo_info "🎯 실시간 파이프라인 로그 뷰어"
    echo ""
    
    case "${1:-live}" in
        "live")
            # 가장 최근 실행 중인 파이프라인 찾기
            local current_run=$(gh run list --limit 1 --json number,status | jq -r '.[] | select(.status == "in_progress" or .status == "queued") | .number')
            
            if [ -n "$current_run" ] && [ "$current_run" != "null" ]; then
                echo_info "🎯 Pipeline #$current_run 실시간 모니터링 시작..."
                live_pipeline_view "$current_run"
            else
                echo_warning "⚠️ 현재 실행 중인 파이프라인이 없습니다"
                live_pipeline_view ""
            fi
            ;;
        "download")
            local run_id="${2:-$(gh run list --limit 1 --json number | jq -r '.[0].number')}"
            download_and_analyze_logs "$run_id"
            ;;
        *)
            echo "사용법:"
            echo "  $0 live          # 실시간 로그 뷰어"
            echo "  $0 download [ID] # 로그 다운로드 및 분석"
            ;;
    esac
}

# 실행
main "$@"