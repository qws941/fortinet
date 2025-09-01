#!/bin/bash
# =============================================================================
# FortiGate Nextrade - 파이프라인 상태 모니터링 및 로그 분석
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
echo_monitor() { echo -e "${MAGENTA}[MONITOR]${NC} $1"; }

# 현재 실행 중인 파이프라인 체크
check_pipeline_status() {
    echo_monitor "📊 현재 파이프라인 상태 확인..."
    
    # 최근 5개 run 상태 확인
    local runs=$(gh run list --limit 5 --json status,conclusion,name,number,createdAt)
    
    echo "📋 최근 파이프라인 실행 상태:"
    echo "----------------------------------------"
    
    # JSON 파싱하여 상태 표시
    echo "$runs" | jq -r '.[] | "\(.number) - \(.name) - \(.status) - \(.conclusion // "running") - \(.createdAt)"' | while read -r line; do
        if echo "$line" | grep -q "completed.*success"; then
            echo -e "${GREEN}✅${NC} $line"
        elif echo "$line" | grep -q "completed.*failure"; then
            echo -e "${RED}❌${NC} $line"
        elif echo "$line" | grep -q "in_progress\|queued"; then
            echo -e "${YELLOW}🔄${NC} $line"
        else
            echo -e "${CYAN}📝${NC} $line"
        fi
    done
    
    echo "----------------------------------------"
}

# 실행 중인 파이프라인 실시간 모니터링
monitor_running_pipeline() {
    echo_monitor "🔄 실행 중인 파이프라인 실시간 모니터링..."
    
    local running_id=$(gh run list --limit 1 --json status,number | jq -r '.[] | select(.status == "in_progress" or .status == "queued") | .number')
    
    if [ -z "$running_id" ] || [ "$running_id" = "null" ]; then
        echo_warning "현재 실행 중인 파이프라인이 없습니다."
        return 1
    fi
    
    echo_info "파이프라인 #$running_id 모니터링 시작..."
    
    # 실시간 상태 체크 (30초마다)
    local attempts=0
    local max_attempts=20  # 10분 최대 대기
    
    while [ $attempts -lt $max_attempts ]; do
        local current_status=$(gh run view "$running_id" --json status,conclusion | jq -r '.status')
        
        case "$current_status" in
            "completed")
                local conclusion=$(gh run view "$running_id" --json conclusion | jq -r '.conclusion')
                if [ "$conclusion" = "success" ]; then
                    echo_success "✅ 파이프라인 #$running_id 성공!"
                    analyze_successful_pipeline "$running_id"
                else
                    echo_error "❌ 파이프라인 #$running_id 실패: $conclusion"
                    analyze_failed_pipeline "$running_id"
                fi
                return 0
                ;;
            "in_progress")
                echo_info "🔄 파이프라인 #$running_id 실행 중... (대기: ${attempts}/20)"
                ;;
            "queued")
                echo_warning "⏳ 파이프라인 #$running_id 대기 중... (대기: ${attempts}/20)"
                ;;
            *)
                echo_warning "🤔 알 수 없는 상태: $current_status"
                ;;
        esac
        
        attempts=$((attempts + 1))
        sleep 30
    done
    
    echo_warning "⏰ 모니터링 시간 초과 (10분)"
}

# 성공한 파이프라인 분석
analyze_successful_pipeline() {
    local run_id=$1
    echo_success "📈 성공한 파이프라인 #$run_id 분석 중..."
    
    # 실행 시간 및 단계별 정보
    echo "📊 실행 정보:"
    gh run view "$run_id" --json jobs,createdAt,updatedAt | jq -r '
        "총 실행 시간: \((.updatedAt | fromdateiso8601) - (.createdAt | fromdateiso8601) | floor) 초",
        "시작 시간: \(.createdAt)",
        "완료 시간: \(.updatedAt)",
        "",
        "📋 Job 별 상태:",
        (.jobs[] | "  \(.name): \(.conclusion // .status) (\(.steps | length) steps)")
    '
    
    # 성공 통계
    create_success_report "$run_id"
}

# 실패한 파이프라인 분석
analyze_failed_pipeline() {
    local run_id=$1
    echo_error "🔍 실패한 파이프라인 #$run_id 상세 분석 중..."
    
    echo "❌ 실패 정보:"
    gh run view "$run_id" --json jobs | jq -r '
        .jobs[] | select(.conclusion == "failure") | 
        "Job: \(.name)",
        "실패 단계: \(.steps[] | select(.conclusion == "failure") | .name)",
        "---"
    '
    
    # 로그 다운로드 및 분석 (백그라운드)
    echo_info "🔍 실패 로그 다운로드 중..."
    mkdir -p logs/failed-runs
    
    if gh run download "$run_id" -D "logs/failed-runs/$run_id" 2>/dev/null; then
        echo_success "✅ 로그 다운로드 완료: logs/failed-runs/$run_id"
        analyze_failure_logs "logs/failed-runs/$run_id"
    else
        echo_warning "⚠️  로그 다운로드 실패 - 직접 확인 필요"
        echo "   GitHub URL: https://github.com/qws941/fortinet/actions/runs/$run_id"
    fi
    
    create_failure_report "$run_id"
}

# 실패 로그 분석
analyze_failure_logs() {
    local log_dir=$1
    echo_monitor "🔍 실패 로그 패턴 분석 중..."
    
    if [ ! -d "$log_dir" ]; then
        echo_warning "로그 디렉토리를 찾을 수 없습니다: $log_dir"
        return 1
    fi
    
    # 공통 에러 패턴 분석
    local error_patterns=(
        "ERROR"
        "FAILED"
        "error:"
        "Error:"
        "fatal:"
        "Permission denied"
        "No such file"
        "command not found"
        "timeout"
        "killed"
    )
    
    echo "🔍 발견된 에러 패턴들:"
    for pattern in "${error_patterns[@]}"; do
        local count=$(find "$log_dir" -name "*.txt" -type f -exec grep -c "$pattern" {} + 2>/dev/null | awk -F: '{sum += $2} END {print sum+0}')
        if [ "$count" -gt 0 ]; then
            echo -e "${RED}  ❌ $pattern: $count 건${NC}"
        fi
    done
    
    # 가장 중요한 에러 메시지 추출
    echo ""
    echo "🎯 주요 에러 메시지:"
    find "$log_dir" -name "*.txt" -type f -exec grep -n -A2 -B2 "ERROR\|FAILED\|fatal:" {} + 2>/dev/null | head -10 | while read -r line; do
        echo -e "${RED}  $line${NC}"
    done
}

# 성공 리포트 생성
create_success_report() {
    local run_id=$1
    local report_file="reports/pipeline-success-$(date +%Y%m%d-%H%M%S).json"
    mkdir -p reports
    
    echo_info "📄 성공 리포트 생성 중: $report_file"
    
    gh run view "$run_id" --json \
        jobs,createdAt,updatedAt,conclusion,headBranch,headSha | \
    jq --arg timestamp "$(date -Iseconds)" '{
        "report_type": "pipeline_success",
        "timestamp": $timestamp,
        "run_id": '$run_id',
        "duration_seconds": ((.updatedAt | fromdateiso8601) - (.createdAt | fromdateiso8601) | floor),
        "branch": .headBranch,
        "commit": .headSha[0:8],
        "jobs": [.jobs[] | {
            "name": .name,
            "conclusion": .conclusion,
            "steps_count": (.steps | length),
            "successful_steps": [.steps[] | select(.conclusion == "success")] | length
        }],
        "success_metrics": {
            "total_jobs": (.jobs | length),
            "successful_jobs": [.jobs[] | select(.conclusion == "success")] | length,
            "total_steps": [.jobs[].steps[]] | length
        }
    }' > "$report_file"
    
    echo_success "✅ 성공 리포트 완료: $report_file"
}

# 실패 리포트 생성
create_failure_report() {
    local run_id=$1
    local report_file="reports/pipeline-failure-$(date +%Y%m%d-%H%M%S).json"
    mkdir -p reports
    
    echo_info "📄 실패 리포트 생성 중: $report_file"
    
    gh run view "$run_id" --json \
        jobs,createdAt,updatedAt,conclusion,headBranch,headSha | \
    jq --arg timestamp "$(date -Iseconds)" '{
        "report_type": "pipeline_failure",
        "timestamp": $timestamp,
        "run_id": '$run_id',
        "duration_seconds": ((.updatedAt | fromdateiso8601) - (.createdAt | fromdateiso8601) | floor),
        "branch": .headBranch,
        "commit": .headSha[0:8],
        "failed_jobs": [.jobs[] | select(.conclusion == "failure") | {
            "name": .name,
            "failed_steps": [.steps[] | select(.conclusion == "failure") | .name]
        }],
        "failure_analysis": {
            "total_jobs": (.jobs | length),
            "failed_jobs_count": [.jobs[] | select(.conclusion == "failure")] | length,
            "successful_jobs_count": [.jobs[] | select(.conclusion == "success")] | length
        },
        "recommendations": [
            "로그 파일 확인: logs/failed-runs/'$run_id'",
            "GitHub Actions URL: https://github.com/qws941/fortinet/actions/runs/'$run_id'"
        ]
    }' > "$report_file"
    
    echo_error "❌ 실패 리포트 완료: $report_file"
}

# 대화형 메뉴
interactive_menu() {
    while true; do
        echo ""
        echo_info "🎛️  파이프라인 모니터링 메뉴"
        echo "=================================="
        echo "1. 현재 파이프라인 상태 확인"
        echo "2. 실행 중인 파이프라인 실시간 모니터링"
        echo "3. 최근 실패 파이프라인 분석"
        echo "4. 파이프라인 로그 자동 분석"
        echo "5. 종료"
        echo "=================================="
        
        read -p "선택하세요 (1-5): " choice
        
        case $choice in
            1)
                check_pipeline_status
                ;;
            2)
                monitor_running_pipeline
                ;;
            3)
                analyze_recent_failures
                ;;
            4)
                auto_analyze_logs
                ;;
            5)
                echo_success "👋 모니터링 종료"
                exit 0
                ;;
            *)
                echo_warning "잘못된 선택입니다. 1-5 중 선택하세요."
                ;;
        esac
        
        read -p "계속하려면 Enter를 누르세요..."
    done
}

# 최근 실패 파이프라인 분석
analyze_recent_failures() {
    echo_monitor "🔍 최근 실패한 파이프라인들 분석 중..."
    
    local failed_runs=$(gh run list --limit 10 --json number,conclusion | jq -r '.[] | select(.conclusion == "failure") | .number' | head -3)
    
    if [ -z "$failed_runs" ]; then
        echo_success "✅ 최근 실패한 파이프라인이 없습니다!"
        return 0
    fi
    
    for run_id in $failed_runs; do
        echo_info "🔍 실패 파이프라인 #$run_id 분석 중..."
        analyze_failed_pipeline "$run_id"
        echo "---"
    done
}

# 자동 로그 분석
auto_analyze_logs() {
    echo_monitor "🤖 자동 로그 분석 시작..."
    
    # logs/failed-runs 디렉토리의 모든 로그 분석
    if [ -d "logs/failed-runs" ]; then
        for log_dir in logs/failed-runs/*/; do
            if [ -d "$log_dir" ]; then
                echo_info "📁 로그 디렉토리 분석: $log_dir"
                analyze_failure_logs "$log_dir"
            fi
        done
    else
        echo_warning "⚠️  분석할 로그 디렉토리가 없습니다."
        echo "   먼저 실패한 파이프라인을 분석하여 로그를 다운로드하세요."
    fi
}

# 메인 실행
main() {
    echo_info "🚀 FortiGate Nextrade - 파이프라인 모니터링 도구"
    echo_info "현재 브랜치: $(git branch --show-current 2>/dev/null || echo 'unknown')"
    echo_info "마지막 커밋: $(git log -1 --format='%h %s' 2>/dev/null || echo 'unknown')"
    echo ""
    
    # 인자가 있으면 해당 기능 실행
    case "${1:-menu}" in
        "status")
            check_pipeline_status
            ;;
        "monitor")
            monitor_running_pipeline
            ;;
        "analyze")
            analyze_recent_failures
            ;;
        "auto")
            auto_analyze_logs
            ;;
        "menu"|*)
            interactive_menu
            ;;
    esac
}

# 실행
main "$@"