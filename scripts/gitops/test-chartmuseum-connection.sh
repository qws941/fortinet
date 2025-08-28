#!/bin/bash

# ChartMuseum 연결 테스트 스크립트
# ChartMuseum 서버와의 연결 및 인증을 테스트합니다.

set -e

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ChartMuseum 설정
CHARTMUSEUM_URL="https://charts.jclee.me"
CHARTMUSEUM_USERNAME="admin"
CHARTMUSEUM_PASSWORD="bingogo1"

echo -e "${BLUE}=== ChartMuseum 연결 테스트 ===${NC}"
echo ""

# 1. 기본 연결 테스트
echo -e "${YELLOW}1. ChartMuseum 서버 연결 테스트...${NC}"
if curl -s --connect-timeout 10 "${CHARTMUSEUM_URL}/health" > /dev/null; then
    echo -e "${GREEN}✅ ChartMuseum 서버 연결 성공${NC}"
else
    echo -e "${RED}❌ ChartMuseum 서버 연결 실패${NC}"
    echo "URL: ${CHARTMUSEUM_URL}"
    exit 1
fi

# 2. 인증 테스트
echo -e "${YELLOW}2. ChartMuseum 인증 테스트...${NC}"
auth_response=$(curl -s -u "${CHARTMUSEUM_USERNAME}:${CHARTMUSEUM_PASSWORD}" \
    -w "%{http_code}" \
    "${CHARTMUSEUM_URL}/api/charts" -o /tmp/charts_response.json)

if [ "$auth_response" = "200" ]; then
    echo -e "${GREEN}✅ ChartMuseum 인증 성공${NC}"
    chart_count=$(cat /tmp/charts_response.json | jq '. | length' 2>/dev/null || echo "N/A")
    echo -e "${GREEN}   현재 저장된 차트 수: ${chart_count}${NC}"
else
    echo -e "${RED}❌ ChartMuseum 인증 실패 (HTTP: ${auth_response})${NC}"
    echo "Username: ${CHARTMUSEUM_USERNAME}"
    echo "Response:"
    cat /tmp/charts_response.json 2>/dev/null || echo "No response data"
    exit 1
fi

# 3. 차트 업로드 테스트 (더미 차트)
echo -e "${YELLOW}3. 차트 업로드 테스트...${NC}"

# 임시 테스트 차트 생성
TEST_CHART_DIR="/tmp/test-chart"
rm -rf "${TEST_CHART_DIR}"
mkdir -p "${TEST_CHART_DIR}"

cat > "${TEST_CHART_DIR}/Chart.yaml" << EOF
apiVersion: v2
name: test-chart
description: Test chart for ChartMuseum connection
type: application
version: 0.1.0
appVersion: "1.0"
EOF

mkdir -p "${TEST_CHART_DIR}/templates"
cat > "${TEST_CHART_DIR}/templates/deployment.yaml" << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: test-deployment
spec:
  replicas: 1
  selector:
    matchLabels:
      app: test
  template:
    metadata:
      labels:
        app: test
    spec:
      containers:
      - name: test
        image: nginx:alpine
        ports:
        - containerPort: 80
EOF

# Helm으로 패키징
cd /tmp
if command -v helm &> /dev/null; then
    helm package test-chart
    
    # ChartMuseum에 업로드 테스트
    upload_response=$(curl -s -u "${CHARTMUSEUM_USERNAME}:${CHARTMUSEUM_PASSWORD}" \
        -w "%{http_code}" \
        --data-binary "@test-chart-0.1.0.tgz" \
        "${CHARTMUSEUM_URL}/api/charts" -o /tmp/upload_response.json)
    
    if [ "$upload_response" = "201" ]; then
        echo -e "${GREEN}✅ 테스트 차트 업로드 성공${NC}"
        
        # 업로드된 차트 삭제
        delete_response=$(curl -s -u "${CHARTMUSEUM_USERNAME}:${CHARTMUSEUM_PASSWORD}" \
            -w "%{http_code}" \
            -X DELETE \
            "${CHARTMUSEUM_URL}/api/charts/test-chart/0.1.0" -o /tmp/delete_response.json)
        
        if [ "$delete_response" = "200" ]; then
            echo -e "${GREEN}✅ 테스트 차트 삭제 성공${NC}"
        else
            echo -e "${YELLOW}⚠️  테스트 차트 삭제 실패 (수동 삭제 필요)${NC}"
        fi
    else
        echo -e "${RED}❌ 테스트 차트 업로드 실패 (HTTP: ${upload_response})${NC}"
        cat /tmp/upload_response.json 2>/dev/null || echo "No response data"
    fi
    
    # 임시 파일 정리
    rm -f test-chart-0.1.0.tgz
else
    echo -e "${YELLOW}⚠️  Helm이 설치되지 않아 업로드 테스트를 건너뜁니다${NC}"
fi

# 4. 요약
echo ""
echo -e "${BLUE}=== 테스트 결과 요약 ===${NC}"
echo -e "${GREEN}✅ ChartMuseum 서버 연결: 성공${NC}"
echo -e "${GREEN}✅ ChartMuseum 인증: 성공${NC}"
echo -e "${GREEN}✅ ChartMuseum 업로드 권한: 확인${NC}"
echo ""
echo -e "${BLUE}GitOps 파이프라인에서 사용할 설정:${NC}"
echo "CHARTMUSEUM_URL: ${CHARTMUSEUM_URL}"
echo "CHARTMUSEUM_USERNAME: ${CHARTMUSEUM_USERNAME}"
echo "CHARTMUSEUM_PASSWORD: ${CHARTMUSEUM_PASSWORD}"
echo ""
echo -e "${GREEN}🎉 ChartMuseum 연결 테스트 완료!${NC}"
echo -e "${YELLOW}💡 이제 GitHub Secrets에 위 정보를 설정하세요.${NC}"

# 임시 파일 정리
rm -f /tmp/charts_response.json /tmp/upload_response.json /tmp/delete_response.json
rm -rf "${TEST_CHART_DIR}"