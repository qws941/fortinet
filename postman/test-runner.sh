#!/bin/bash

# Postman API 테스트 실행 스크립트
# 주요 FortiGate/FortiManager API 기능을 검증합니다

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

API_HOST="${API_HOST:-localhost}"
API_PORT="${API_PORT:-7777}"
BASE_URL="http://${API_HOST}:${API_PORT}"

echo "======================================"
echo "FortiGate/FortiManager API Test Runner"
echo "======================================"
echo "Base URL: ${BASE_URL}"
echo ""

# 테스트 결과 저장
PASS_COUNT=0
FAIL_COUNT=0

# 테스트 함수
run_test() {
    local test_name="$1"
    local curl_command="$2"
    local expected_status="$3"
    
    echo -n "Testing: ${test_name}... "
    
    # curl 실행 및 상태 코드 확인
    response=$(eval "${curl_command} -w '\n%{http_code}' -s")
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "$expected_status" ]; then
        echo -e "${GREEN}✓ PASS${NC} (HTTP ${http_code})"
        ((PASS_COUNT++))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (Expected: ${expected_status}, Got: ${http_code})"
        echo "  Response: ${body}" | head -n1
        ((FAIL_COUNT++))
        return 1
    fi
}

# 1. 헬스체크
echo -e "\n${YELLOW}=== System Health Checks ===${NC}"
run_test "Health Check API" \
    "curl -X GET ${BASE_URL}/api/health" \
    "200"

# 2. 방화벽 경로 분석 (주 기능)
echo -e "\n${YELLOW}=== Firewall Path Analysis (Main Feature) ===${NC}"

# 2-1. 허용된 트래픽 분석
run_test "Allowed Traffic Analysis" \
    "curl -X POST ${BASE_URL}/api/fortimanager/analyze-packet-path \
        -H 'Content-Type: application/json' \
        -d '{\"src_ip\":\"192.168.1.10\",\"dst_ip\":\"8.8.8.8\",\"src_port\":12345,\"dst_port\":443,\"protocol\":\"tcp\"}'" \
    "200"

# 2-2. 차단된 트래픽 분석
run_test "Blocked Traffic Analysis" \
    "curl -X POST ${BASE_URL}/api/fortimanager/analyze-packet-path \
        -H 'Content-Type: application/json' \
        -d '{\"src_ip\":\"10.0.0.100\",\"dst_ip\":\"192.168.2.50\",\"src_port\":22,\"dst_port\":22,\"protocol\":\"tcp\"}'" \
    "200"

# 2-3. UDP 트래픽 분석
run_test "UDP Traffic Analysis" \
    "curl -X POST ${BASE_URL}/api/fortimanager/analyze-packet-path \
        -H 'Content-Type: application/json' \
        -d '{\"src_ip\":\"192.168.1.20\",\"dst_ip\":\"8.8.4.4\",\"src_port\":53,\"dst_port\":53,\"protocol\":\"udp\"}'" \
    "200"

# 3. FortiManager 정책 관리
echo -e "\n${YELLOW}=== FortiManager Policy Management ===${NC}"

run_test "Get Policy List" \
    "curl -X POST ${BASE_URL}/api/fortimanager/policies \
        -H 'Content-Type: application/json' \
        -d '{\"adom\":\"root\"}'" \
    "200"

# 4. 설정 관리
echo -e "\n${YELLOW}=== Configuration Management ===${NC}"

run_test "Get Settings" \
    "curl -X GET ${BASE_URL}/api/settings" \
    "200"

run_test "Update Settings" \
    "curl -X POST ${BASE_URL}/api/settings \
        -H 'Content-Type: application/json' \
        -d '{\"fortigate_host\":\"192.168.1.100\"}'" \
    "200"

# 5. 모니터링
echo -e "\n${YELLOW}=== Monitoring ===${NC}"

run_test "System Metrics" \
    "curl -X GET ${BASE_URL}/api/monitoring/metrics" \
    "200"

# 결과 요약
echo ""
echo "======================================"
echo "Test Results Summary"
echo "======================================"
echo -e "Passed: ${GREEN}${PASS_COUNT}${NC}"
echo -e "Failed: ${RED}${FAIL_COUNT}${NC}"
echo -e "Total:  $((PASS_COUNT + FAIL_COUNT))"

if [ ${FAIL_COUNT} -eq 0 ]; then
    echo -e "\n${GREEN}All tests passed successfully!${NC}"
    exit 0
else
    echo -e "\n${RED}Some tests failed. Please check the errors above.${NC}"
    exit 1
fi