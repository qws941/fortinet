#!/bin/bash
# Fortinet 프로젝트 보안 감사 자동화 스크립트

set -euo pipefail

# 색상 설정
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 Fortinet 프로젝트 보안 감사 시작${NC}"
echo "================================================="
echo "감사 시간: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 보안 점수 초기화
SECURITY_SCORE=100
ISSUES_FOUND=0

# 1. 하드코딩된 시크릿 검사
echo -e "${BLUE}🔐 1. 하드코딩된 시크릿 검사${NC}"
echo "--------------------------------"

# 위험한 패턴 검색
HARDCODED_SECRETS=$(grep -r \
  -E "(password|passwd|secret|key|token).*=.*['\"][^'\"]{8,}['\"]" \
  --include="*.py" --include="*.yml" --include="*.yaml" --include="*.js" \
  . 2>/dev/null | grep -v ".git" | grep -v "__pycache__" || true)

if [[ -n "$HARDCODED_SECRETS" ]]; then
    echo -e "${RED}❌ 하드코딩된 시크릿 발견:${NC}"
    echo "$HARDCODED_SECRETS" | head -10
    SECURITY_SCORE=$((SECURITY_SCORE - 20))
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
else
    echo -e "${GREEN}✅ 하드코딩된 시크릿 없음${NC}"
fi

# 2. SSL 검증 비활성화 검사
echo ""
echo -e "${BLUE}🔒 2. SSL 검증 설정 검사${NC}"
echo "--------------------------------"

SSL_DISABLED=$(grep -r "verify.*=.*False\|VERIFY_SSL.*false" \
  --include="*.py" . 2>/dev/null | grep -v ".git" || true)

if [[ -n "$SSL_DISABLED" ]]; then
    echo -e "${RED}❌ SSL 검증 비활성화 발견:${NC}"
    echo "$SSL_DISABLED"
    SECURITY_SCORE=$((SECURITY_SCORE - 15))
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
else
    echo -e "${GREEN}✅ SSL 검증 설정 양호${NC}"
fi

# 3. Flask SECRET_KEY 검사
echo ""
echo -e "${BLUE}🔑 3. Flask SECRET_KEY 보안 검사${NC}"
echo "--------------------------------"

WEAK_SECRET_KEY=$(grep -r "SECRET_KEY.*=" src/ 2>/dev/null | \
  grep -E "(test|dev|debug|123|abc|secret)" || true)

if [[ -n "$WEAK_SECRET_KEY" ]]; then
    echo -e "${RED}❌ 약한 SECRET_KEY 발견:${NC}"
    echo "$WEAK_SECRET_KEY"
    SECURITY_SCORE=$((SECURITY_SCORE - 25))
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
else
    echo -e "${GREEN}✅ SECRET_KEY 설정 양호${NC}"
fi

# 4. 환경변수 사용 여부 검사
echo ""
echo -e "${BLUE}📋 4. 환경변수 사용 검사${NC}"
echo "--------------------------------"

if [[ -f ".env.production" ]]; then
    echo -e "${GREEN}✅ .env.production 파일 존재${NC}"
    ENV_VARS=$(grep -c "^[A-Z_]*=" .env.production || echo "0")
    echo "환경변수 개수: $ENV_VARS"
    
    if [[ $ENV_VARS -lt 10 ]]; then
        echo -e "${YELLOW}⚠️  환경변수가 적습니다 (권장: 10개 이상)${NC}"
        SECURITY_SCORE=$((SECURITY_SCORE - 5))
    fi
else
    echo -e "${RED}❌ .env.production 파일 없음${NC}"
    SECURITY_SCORE=$((SECURITY_SCORE - 15))
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi

# 5. Docker 보안 설정 검사
echo ""
echo -e "${BLUE}🐳 5. Docker 보안 설정 검사${NC}"
echo "--------------------------------"

if [[ -f "docker-compose.secure.yml" ]]; then
    echo -e "${GREEN}✅ 보안 강화된 Docker Compose 파일 존재${NC}"
    
    # 보안 컨텍스트 확인
    SECURITY_CONTEXTS=$(grep -c "security_opt:" docker-compose.secure.yml || echo "0")
    echo "보안 컨텍스트 설정 개수: $SECURITY_CONTEXTS"
    
    if [[ $SECURITY_CONTEXTS -lt 5 ]]; then
        echo -e "${YELLOW}⚠️  보안 컨텍스트 설정이 부족합니다${NC}"
        SECURITY_SCORE=$((SECURITY_SCORE - 10))
    fi
else
    echo -e "${RED}❌ 보안 강화된 Docker Compose 파일 없음${NC}"
    SECURITY_SCORE=$((SECURITY_SCORE - 10))
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi

# 6. JWT 설정 검사
echo ""
echo -e "${BLUE}🎫 6. JWT 토큰 보안 검사${NC}"
echo "--------------------------------"

if [[ -f "src/utils/enhanced_security.py" ]]; then
    echo -e "${GREEN}✅ 보안 강화된 JWT 모듈 존재${NC}"
    
    # JWT 만료 시간 설정 확인
    JWT_EXPIRY=$(grep -c "expires_in.*=" src/utils/enhanced_security.py || echo "0")
    if [[ $JWT_EXPIRY -gt 0 ]]; then
        echo -e "${GREEN}✅ JWT 만료 시간 설정됨${NC}"
    else
        echo -e "${RED}❌ JWT 만료 시간 미설정${NC}"
        SECURITY_SCORE=$((SECURITY_SCORE - 15))
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
    fi
else
    echo -e "${RED}❌ 보안 강화된 JWT 모듈 없음${NC}"
    SECURITY_SCORE=$((SECURITY_SCORE - 20))
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi

# 7. Kubernetes 보안 설정 검사
echo ""
echo -e "${BLUE}☸️  7. Kubernetes 보안 설정 검사${NC}"
echo "--------------------------------"

if [[ -f "charts/fortinet/values.yaml" ]]; then
    echo -e "${GREEN}✅ Helm Values 파일 존재${NC}"
    
    # 보안 컨텍스트 확인
    K8S_SECURITY=$(grep -c "runAs\|allowPrivilegeEscalation\|readOnlyRootFilesystem" \
      charts/fortinet/values.yaml || echo "0")
    echo "Kubernetes 보안 설정 개수: $K8S_SECURITY"
    
    if [[ $K8S_SECURITY -lt 3 ]]; then
        echo -e "${YELLOW}⚠️  Kubernetes 보안 설정이 부족합니다${NC}"
        SECURITY_SCORE=$((SECURITY_SCORE - 10))
    fi
else
    echo -e "${RED}❌ Helm Values 파일 없음${NC}"
    SECURITY_SCORE=$((SECURITY_SCORE - 5))
fi

# 8. 의존성 취약점 검사 (pip-audit 사용)
echo ""
echo -e "${BLUE}📦 8. Python 의존성 취약점 검사${NC}"
echo "--------------------------------"

if command -v pip-audit >/dev/null 2>&1; then
    echo "pip-audit로 의존성 취약점 검사 중..."
    if pip-audit --desc --format=json > audit_results.json 2>/dev/null; then
        VULNERABILITIES=$(jq -r '.vulnerabilities | length' audit_results.json 2>/dev/null || echo "0")
        if [[ $VULNERABILITIES -gt 0 ]]; then
            echo -e "${RED}❌ $VULNERABILITIES개의 취약점 발견${NC}"
            SECURITY_SCORE=$((SECURITY_SCORE - VULNERABILITIES * 2))
            ISSUES_FOUND=$((ISSUES_FOUND + VULNERABILITIES))
        else
            echo -e "${GREEN}✅ 의존성 취약점 없음${NC}"
        fi
        rm -f audit_results.json
    else
        echo -e "${YELLOW}⚠️  pip-audit 실행 실패${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  pip-audit 미설치 (pip install pip-audit)${NC}"
fi

# 9. 로그 보안 검사
echo ""
echo -e "${BLUE}📝 9. 로그 보안 검사${NC}"
echo "--------------------------------"

LOG_LEAKS=$(grep -r -i \
  -E "(password|token|secret|key).*=.*[a-zA-Z0-9]{8,}" \
  --include="*.log" . 2>/dev/null | head -5 || true)

if [[ -n "$LOG_LEAKS" ]]; then
    echo -e "${RED}❌ 로그에서 민감정보 누출 발견:${NC}"
    echo "$LOG_LEAKS"
    SECURITY_SCORE=$((SECURITY_SCORE - 10))
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
else
    echo -e "${GREEN}✅ 로그 보안 양호${NC}"
fi

# 10. 파일 권한 검사
echo ""
echo -e "${BLUE}🔐 10. 파일 권한 검사${NC}"
echo "--------------------------------"

# 중요 파일들의 권한 검사
declare -a IMPORTANT_FILES=(
    ".env.production"
    "scripts/generate-production-secrets.sh"
    "docker-compose.secure.yml"
)

for file in "${IMPORTANT_FILES[@]}"; do
    if [[ -f "$file" ]]; then
        PERMS=$(stat -c "%a" "$file" 2>/dev/null || echo "000")
        if [[ "$PERMS" == "600" ]] || [[ "$PERMS" == "700" ]]; then
            echo -e "${GREEN}✅ $file 권한 안전: $PERMS${NC}"
        else
            echo -e "${RED}❌ $file 권한 위험: $PERMS (권장: 600)${NC}"
            SECURITY_SCORE=$((SECURITY_SCORE - 5))
            ISSUES_FOUND=$((ISSUES_FOUND + 1))
        fi
    fi
done

# 보안 감사 결과 요약
echo ""
echo "================================================="
echo -e "${BLUE}📊 보안 감사 결과 요약${NC}"
echo "================================================="
echo "감사 완료 시간: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 보안 점수에 따른 등급 결정
if [[ $SECURITY_SCORE -ge 90 ]]; then
    GRADE="A"
    COLOR=$GREEN
elif [[ $SECURITY_SCORE -ge 80 ]]; then
    GRADE="B"
    COLOR=$GREEN
elif [[ $SECURITY_SCORE -ge 70 ]]; then
    GRADE="C"
    COLOR=$YELLOW
elif [[ $SECURITY_SCORE -ge 60 ]]; then
    GRADE="D"
    COLOR=$YELLOW
else
    GRADE="F"
    COLOR=$RED
fi

echo -e "${COLOR}🏆 최종 보안 점수: $SECURITY_SCORE/100 (등급: $GRADE)${NC}"
echo -e "🚨 발견된 보안 이슈: $ISSUES_FOUND개"
echo ""

# 권장사항
echo -e "${BLUE}💡 권장사항:${NC}"
if [[ $SECURITY_SCORE -lt 80 ]]; then
    echo "1. 하드코딩된 시크릿을 환경변수로 변경하세요"
    echo "2. ./scripts/generate-production-secrets.sh를 실행하세요"
    echo "3. docker-compose.secure.yml를 사용하세요"
    echo "4. JWT 토큰 만료 시간을 설정하세요"
    echo "5. SSL 검증을 활성화하세요"
fi

if [[ $SECURITY_SCORE -ge 80 ]]; then
    echo -e "${GREEN}🎉 보안 수준이 양호합니다!${NC}"
    echo "정기적인 보안 감사를 계속 진행하세요."
fi

# 보고서 저장
REPORT_FILE="security-audit-report-$(date +%Y%m%d-%H%M%S).txt"
{
    echo "Fortinet 프로젝트 보안 감사 보고서"
    echo "=================================="
    echo "감사 시간: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "최종 보안 점수: $SECURITY_SCORE/100 (등급: $GRADE)"
    echo "발견된 보안 이슈: $ISSUES_FOUND개"
    echo ""
    echo "상세 결과는 감사 실행 로그를 참조하세요."
} > "$REPORT_FILE"

echo ""
echo -e "${GREEN}📄 보고서 저장됨: $REPORT_FILE${NC}"

# 종료 코드 설정
if [[ $SECURITY_SCORE -ge 80 ]]; then
    exit 0
else
    exit 1
fi