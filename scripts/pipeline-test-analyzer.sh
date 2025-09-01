#!/bin/bash
# =============================================================================
# FortiGate Nextrade - 파이프라인 테스트 및 로그 분석
# Watchtower 환경 통합 테스트 및 분석 도구
# =============================================================================

set -e

# Configuration
TEST_DURATION="${TEST_DURATION:-300}"  # 5분
LOG_DIR="logs/pipeline-tests"
REPORT_DIR="reports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Service ports
REDIS_PORT=7777
POSTGRESQL_PORT=7778
FORTINET_PORT=7779

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

echo_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
echo_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
echo_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
echo_error() { echo -e "${RED}[ERROR]${NC} $1"; }
echo_test() { echo -e "${CYAN}[TEST]${NC} $1"; }
echo_result() { echo -e "${MAGENTA}[RESULT]${NC} $1"; }

# 테스트 환경 초기화
init_test_environment() {
    echo_info "🧪 파이프라인 테스트 환경 초기화..."
    
    mkdir -p "$LOG_DIR" "$REPORT_DIR"
    
    # 테스트 설정 파일
    cat > "$LOG_DIR/test-config.json" << EOF
{
    "test_session": {
        "id": "pipeline_test_$TIMESTAMP",
        "start_time": "$(date -Iseconds)",
        "duration": $TEST_DURATION,
        "services": {
            "redis": {
                "port": $REDIS_PORT,
                "container": "fortinet-redis-$REDIS_PORT",
                "health_endpoint": "redis-cli -p $REDIS_PORT ping"
            },
            "postgresql": {
                "port": $POSTGRESQL_PORT,
                "container": "fortinet-postgresql-$POSTGRESQL_PORT",
                "health_endpoint": "pg_isready -h localhost -p $POSTGRESQL_PORT -U fortinet"
            },
            "fortinet": {
                "port": $FORTINET_PORT,
                "container": "fortinet-app-$FORTINET_PORT",
                "health_endpoint": "http://localhost:$FORTINET_PORT/api/health"
            }
        }
    }
}
EOF

    echo_success "테스트 환경 초기화 완료"
}

# 서비스 가용성 테스트
test_service_availability() {
    echo_test "🔍 서비스 가용성 테스트 시작..."
    
    local test_results="$LOG_DIR/availability_test_$TIMESTAMP.json"
    
    cat > "$test_results" << EOF
{
    "test_type": "service_availability",
    "timestamp": "$(date -Iseconds)",
    "results": {
EOF

    # Redis 테스트
    echo_test "Testing Redis (port $REDIS_PORT)..."
    if timeout 10 redis-cli -p $REDIS_PORT ping > /dev/null 2>&1; then
        redis_status="PASS"
        redis_response_time=$(timeout 10 time (redis-cli -p $REDIS_PORT ping) 2>&1 | grep real | awk '{print $2}')
    else
        redis_status="FAIL"
        redis_response_time="N/A"
    fi
    
    cat >> "$test_results" << EOF
        "redis": {
            "status": "$redis_status",
            "port": $REDIS_PORT,
            "response_time": "$redis_response_time",
            "test_time": "$(date -Iseconds)"
        },
EOF

    # PostgreSQL 테스트
    echo_test "Testing PostgreSQL (port $POSTGRESQL_PORT)..."
    if timeout 10 pg_isready -h localhost -p $POSTGRESQL_PORT -U fortinet > /dev/null 2>&1; then
        pg_status="PASS"
        pg_response_time=$(timeout 10 time (pg_isready -h localhost -p $POSTGRESQL_PORT -U fortinet) 2>&1 | grep real | awk '{print $2}')
    else
        pg_status="FAIL"
        pg_response_time="N/A"
    fi
    
    cat >> "$test_results" << EOF
        "postgresql": {
            "status": "$pg_status",
            "port": $POSTGRESQL_PORT,
            "response_time": "$pg_response_time",
            "test_time": "$(date -Iseconds)"
        },
EOF

    # Fortinet App 테스트
    echo_test "Testing Fortinet App (port $FORTINET_PORT)..."
    if curl -s -f --max-time 10 "http://localhost:$FORTINET_PORT/api/health" > /dev/null; then
        app_status="PASS"
        app_response_time=$(curl -o /dev/null -s -w "%{time_total}" --max-time 10 "http://localhost:$FORTINET_PORT/api/health")
    else
        app_status="FAIL"
        app_response_time="N/A"
    fi
    
    cat >> "$test_results" << EOF
        "fortinet": {
            "status": "$app_status",
            "port": $FORTINET_PORT,
            "response_time": "${app_response_time}s",
            "test_time": "$(date -Iseconds)"
        }
    }
}
EOF

    echo_result "가용성 테스트 완료 - 결과: $test_results"
}

# 부하 테스트
run_load_test() {
    echo_test "⚡ 부하 테스트 시작..."
    
    local load_test_results="$LOG_DIR/load_test_$TIMESTAMP.json"
    local concurrent_users=10
    local test_duration=60
    
    echo_test "부하 테스트 설정: $concurrent_users 동시 사용자, $test_duration 초"
    
    # Apache Bench를 사용한 부하 테스트 (또는 curl 기반 대안)
    if command -v ab > /dev/null; then
        echo_test "Apache Bench로 부하 테스트 실행..."
        ab -n 1000 -c $concurrent_users -g "$LOG_DIR/load_test_gnuplot.tsv" \
           "http://localhost:$FORTINET_PORT/api/health" > "$LOG_DIR/ab_results.txt" 2>&1 || true
    else
        echo_test "curl 기반 부하 테스트 실행..."
        
        # 백그라운드에서 여러 curl 요청 실행
        for i in $(seq 1 $concurrent_users); do
            (
                for j in $(seq 1 10); do
                    start_time=$(date +%s.%N)
                    if curl -s -f --max-time 5 "http://localhost:$FORTINET_PORT/api/health" > /dev/null; then
                        end_time=$(date +%s.%N)
                        response_time=$(echo "$end_time - $start_time" | bc -l)
                        echo "$j,$i,$response_time,SUCCESS" >> "$LOG_DIR/curl_load_test.csv"
                    else
                        echo "$j,$i,0,FAILED" >> "$LOG_DIR/curl_load_test.csv"
                    fi
                    sleep 0.1
                done
            ) &
        done
        
        wait  # 모든 백그라운드 작업 완료 대기
    fi
    
    # 결과 분석
    if [ -f "$LOG_DIR/curl_load_test.csv" ]; then
        total_requests=$(wc -l < "$LOG_DIR/curl_load_test.csv")
        successful_requests=$(grep "SUCCESS" "$LOG_DIR/curl_load_test.csv" | wc -l)
        failed_requests=$(grep "FAILED" "$LOG_DIR/curl_load_test.csv" | wc -l)
        success_rate=$(echo "scale=2; $successful_requests * 100 / $total_requests" | bc -l)
        
        cat > "$load_test_results" << EOF
{
    "test_type": "load_test",
    "timestamp": "$(date -Iseconds)",
    "configuration": {
        "concurrent_users": $concurrent_users,
        "duration": $test_duration,
        "target_url": "http://localhost:$FORTINET_PORT/api/health"
    },
    "results": {
        "total_requests": $total_requests,
        "successful_requests": $successful_requests,
        "failed_requests": $failed_requests,
        "success_rate": "${success_rate}%"
    }
}
EOF
    fi
    
    echo_result "부하 테스트 완료 - 결과: $load_test_results"
}

# 실시간 로그 수집
collect_realtime_logs() {
    echo_test "📋 실시간 로그 수집 시작..."
    
    local log_collection_dir="$LOG_DIR/realtime_logs_$TIMESTAMP"
    mkdir -p "$log_collection_dir"
    
    # 각 서비스별 로그 수집
    services=("fortinet-redis-$REDIS_PORT" "fortinet-postgresql-$POSTGRESQL_PORT" "fortinet-app-$FORTINET_PORT")
    
    for service in "${services[@]}"; do
        if docker ps --filter "name=$service" -q > /dev/null; then
            echo_test "수집 중: $service 로그..."
            docker logs "$service" --timestamps --since="10m" > "$log_collection_dir/${service}_recent.log" 2>&1 || true
            docker logs "$service" --timestamps --tail=1000 > "$log_collection_dir/${service}_tail.log" 2>&1 || true
        fi
    done
    
    # 시스템 로그도 수집
    echo_test "시스템 로그 수집..."
    journalctl --since="10 minutes ago" --no-pager > "$log_collection_dir/system_journal.log" 2>&1 || true
    
    echo_result "로그 수집 완료 - 위치: $log_collection_dir"
}

# 로그 분석 엔진
analyze_logs() {
    echo_test "🔎 로그 분석 시작..."
    
    local analysis_report="$REPORT_DIR/log_analysis_$TIMESTAMP.json"
    local log_collection_dir="$LOG_DIR/realtime_logs_$TIMESTAMP"
    
    cat > "$analysis_report" << EOF
{
    "analysis_type": "log_analysis",
    "timestamp": "$(date -Iseconds)",
    "analysis_results": {
EOF

    # 에러 패턴 분석
    echo_test "에러 패턴 분석 중..."
    local total_errors=0
    local error_patterns=""
    
    if [ -d "$log_collection_dir" ]; then
        for log_file in "$log_collection_dir"/*.log; do
            if [ -f "$log_file" ]; then
                service_name=$(basename "$log_file" .log)
                
                # 에러 키워드 검색
                error_count=$(grep -i -E "error|exception|failed|critical" "$log_file" | wc -l)
                warning_count=$(grep -i "warning" "$log_file" | wc -l)
                total_errors=$((total_errors + error_count))
                
                # 상위 에러 패턴 추출
                top_errors=$(grep -i -E "error|exception|failed" "$log_file" | cut -d' ' -f4- | sort | uniq -c | sort -nr | head -3)
                
                cat >> "$analysis_report" << EOF
        "$service_name": {
            "error_count": $error_count,
            "warning_count": $warning_count,
            "log_size": "$(wc -l < "$log_file") lines",
            "top_errors": "$(echo "$top_errors" | tr '\n' ';')"
        },
EOF
            fi
        done
    fi
    
    # 성능 메트릭 분석
    echo_test "성능 메트릭 분석 중..."
    
    # Docker 통계 수집
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" > "$LOG_DIR/docker_stats_$TIMESTAMP.txt" || true
    
    cat >> "$analysis_report" << EOF
        "summary": {
            "total_errors": $total_errors,
            "analysis_time": "$(date -Iseconds)",
            "log_files_analyzed": $(find "$log_collection_dir" -name "*.log" | wc -l)
        }
    }
}
EOF

    echo_result "로그 분석 완료 - 리포트: $analysis_report"
}

# Watchtower 상태 분석
analyze_watchtower_status() {
    echo_test "🐋 Watchtower 상태 분석..."
    
    local watchtower_report="$REPORT_DIR/watchtower_status_$TIMESTAMP.json"
    
    cat > "$watchtower_report" << EOF
{
    "watchtower_analysis": {
        "timestamp": "$(date -Iseconds)",
        "managed_containers": [
EOF

    # Watchtower 관리 대상 컨테이너 확인
    managed_containers=$(docker ps --filter "label=com.centurylinklabs.watchtower.enable=true" --format "{{.Names}}")
    
    first=true
    for container in $managed_containers; do
        if [ "$first" = false ]; then
            echo "," >> "$watchtower_report"
        fi
        first=false
        
        # 컨테이너 상세 정보
        image=$(docker inspect --format '{{.Config.Image}}' "$container")
        created=$(docker inspect --format '{{.Created}}' "$container")
        status=$(docker inspect --format '{{.State.Status}}' "$container")
        
        cat >> "$watchtower_report" << EOF
            {
                "name": "$container",
                "image": "$image",
                "status": "$status",
                "created": "$created",
                "watchtower_labels": $(docker inspect --format '{{json .Config.Labels}}' "$container" | jq 'to_entries | map(select(.key | startswith("com.centurylinklabs.watchtower")))')
            }
EOF
    done
    
    cat >> "$watchtower_report" << EOF
        ],
        "watchtower_container_status": "$(docker ps --filter 'name=watchtower' --format '{{.Status}}' || echo 'Not Found')"
    }
}
EOF

    echo_result "Watchtower 분석 완료 - 리포트: $watchtower_report"
}

# 종합 리포트 생성
generate_comprehensive_report() {
    echo_test "📊 종합 리포트 생성 중..."
    
    local comprehensive_report="$REPORT_DIR/comprehensive_pipeline_report_$TIMESTAMP.html"
    
    cat > "$comprehensive_report" << EOF
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FortiGate Pipeline 테스트 리포트</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
        h2 { color: #34495e; margin-top: 30px; }
        .status-pass { color: #27ae60; font-weight: bold; }
        .status-fail { color: #e74c3c; font-weight: bold; }
        .metric-box { background: #ecf0f1; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #3498db; }
        .error-box { background: #fdf2f2; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #e74c3c; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #3498db; color: white; }
        .footer { margin-top: 40px; text-align: center; color: #7f8c8d; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 FortiGate Nextrade 파이프라인 테스트 리포트</h1>
        
        <div class="metric-box">
            <strong>테스트 세션 정보</strong><br>
            📅 테스트 시간: $(date)<br>
            🆔 세션 ID: pipeline_test_$TIMESTAMP<br>
            ⏱️ 테스트 기간: $TEST_DURATION 초
        </div>

        <h2>📊 서비스 가용성 테스트</h2>
        <table>
            <tr><th>서비스</th><th>포트</th><th>상태</th><th>응답시간</th></tr>
EOF

    # 가용성 테스트 결과 추가 (JSON 파싱)
    if [ -f "$LOG_DIR/availability_test_$TIMESTAMP.json" ]; then
        echo "            <tr><td>Redis</td><td>$REDIS_PORT</td><td class=\"status-$([ "$redis_status" = "PASS" ] && echo "pass" || echo "fail")\">$redis_status</td><td>$redis_response_time</td></tr>" >> "$comprehensive_report"
        echo "            <tr><td>PostgreSQL</td><td>$POSTGRESQL_PORT</td><td class=\"status-$([ "$pg_status" = "PASS" ] && echo "pass" || echo "fail")\">$pg_status</td><td>$pg_response_time</td></tr>" >> "$comprehensive_report"
        echo "            <tr><td>Fortinet App</td><td>$FORTINET_PORT</td><td class=\"status-$([ "$app_status" = "PASS" ] && echo "pass" || echo "fail")\">$app_status</td><td>$app_response_time</td></tr>" >> "$comprehensive_report"
    fi

    cat >> "$comprehensive_report" << EOF
        </table>

        <h2>⚡ 부하 테스트 결과</h2>
        <div class="metric-box">
            <strong>부하 테스트 통계</strong><br>
            📊 동시 사용자: 10명<br>
            🎯 대상 URL: http://localhost:$FORTINET_PORT/api/health<br>
            📈 결과는 로그 파일에서 확인 가능
        </div>

        <h2>📋 로그 분석 요약</h2>
        <div class="error-box">
            <strong>주요 발견사항</strong><br>
            🔍 총 에러 수: $total_errors<br>
            📁 분석된 로그 파일: $(find "$LOG_DIR/realtime_logs_$TIMESTAMP" -name "*.log" 2>/dev/null | wc -l)개<br>
            📊 분석 시간: $(date)
        </div>

        <h2>🐋 Watchtower 상태</h2>
        <div class="metric-box">
            <strong>관리 대상 컨테이너</strong><br>
            $(docker ps --filter "label=com.centurylinklabs.watchtower.enable=true" --format "{{.Names}}" | wc -l)개의 컨테이너가 Watchtower에 의해 관리되고 있습니다.
        </div>

        <h2>📈 시스템 리소스</h2>
        <pre>$(docker stats --no-stream 2>/dev/null || echo "리소스 정보 수집 실패")</pre>

        <div class="footer">
            Generated by FortiGate Pipeline Test Analyzer - $(date)
        </div>
    </div>
</body>
</html>
EOF

    echo_success "종합 리포트 생성 완료: $comprehensive_report"
    echo_info "📱 브라우저에서 리포트 확인: file://$PWD/$comprehensive_report"
}

# 메인 실행 함수
main_pipeline_test() {
    echo_info "🎯 FortiGate 파이프라인 테스트 및 분석 시작..."
    echo "테스트 기간: $TEST_DURATION 초"
    echo "로그 디렉토리: $LOG_DIR"
    echo "리포트 디렉토리: $REPORT_DIR"
    echo

    init_test_environment
    sleep 2
    
    test_service_availability
    sleep 2
    
    run_load_test
    sleep 2
    
    collect_realtime_logs
    sleep 2
    
    analyze_logs
    sleep 2
    
    analyze_watchtower_status
    sleep 2
    
    generate_comprehensive_report

    echo_success "🎉 파이프라인 테스트 및 분석 완료!"
    echo
    echo_result "📊 결과 파일:"
    echo "  📁 로그: $LOG_DIR"
    echo "  📄 리포트: $REPORT_DIR"
    echo "  🌐 HTML 리포트: $REPORT_DIR/comprehensive_pipeline_report_$TIMESTAMP.html"
    echo
    echo_info "💡 추가 분석 도구:"
    echo "  실시간 모니터링: ./scripts/monitor-separated-services.sh"
    echo "  로그 재분석: grep -r 'ERROR' $LOG_DIR/"
}

# 실행
main_pipeline_test