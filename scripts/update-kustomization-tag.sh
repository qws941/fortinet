#!/bin/bash
# =============================================================================
# FortiGate Nextrade - GitOps Kustomization 불변 태그 업데이트 스크립트
# GitOps 4원칙 준수: Git이 유일한 진실의 소스 (Git as Source of Truth)
# =============================================================================

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔄 GitOps Kustomization Immutable Tag Update${NC}"
echo "=================================================="

# 매개변수 검증
if [ $# -lt 2 ]; then
    echo -e "${RED}❌ Usage: $0 <environment> <immutable_tag> [commit_message]${NC}"
    echo "Examples:"
    echo "  $0 development development-20250811-151400-abc123"
    echo "  $0 production production-20250811-151317-def456"
    echo "  $0 staging staging-20250811-151500-ghi789"
    exit 1
fi

ENVIRONMENT=$1
IMMUTABLE_TAG=$2
COMMIT_MESSAGE="${3:-"feat: update ${ENVIRONMENT} to immutable tag ${IMMUTABLE_TAG}"}"

# 환경별 kustomization.yaml 파일 경로
KUSTOMIZATION_FILE="k8s/overlays/${ENVIRONMENT}/kustomization.yaml"

# 파일 존재 확인
if [ ! -f "${KUSTOMIZATION_FILE}" ]; then
    echo -e "${RED}❌ Error: ${KUSTOMIZATION_FILE} not found${NC}"
    exit 1
fi

echo -e "${YELLOW}📋 Update Configuration${NC}"
echo -e "  Environment: ${GREEN}${ENVIRONMENT}${NC}"
echo -e "  Immutable Tag: ${GREEN}${IMMUTABLE_TAG}${NC}"
echo -e "  Kustomization File: ${BLUE}${KUSTOMIZATION_FILE}${NC}"
echo ""

# 현재 태그 백업
BACKUP_FILE="${KUSTOMIZATION_FILE}.backup-$(date +%Y%m%d-%H%M%S)"
cp "${KUSTOMIZATION_FILE}" "${BACKUP_FILE}"
echo -e "${YELLOW}💾 Backup created: ${BACKUP_FILE}${NC}"

# 현재 태그 추출
CURRENT_TAG=$(grep -A 1 "images:" "${KUSTOMIZATION_FILE}" | grep "newTag:" | sed 's/.*newTag: *\(.*\)  *#.*/\1/' | sed 's/.*newTag: *\(.*\)$/\1/')
echo -e "  Current Tag: ${YELLOW}${CURRENT_TAG}${NC}"
echo -e "  New Tag: ${GREEN}${IMMUTABLE_TAG}${NC}"

# GitOps 불변성 검증
if [[ "${IMMUTABLE_TAG}" == "latest" ]] || [[ "${IMMUTABLE_TAG}" == *"-latest" ]]; then
    echo -e "${RED}❌ Error: 'latest' tags violate GitOps immutable principle${NC}"
    echo -e "${YELLOW}GitOps requires immutable tags for reliable deployments${NC}"
    exit 1
fi

# 태그 형식 검증 (environment-timestamp-sha 패턴)
if [[ ! "${IMMUTABLE_TAG}" =~ ^${ENVIRONMENT}-[0-9]{8}-[0-9]{6}-.+ ]]; then
    echo -e "${YELLOW}⚠️  Warning: Tag format doesn't match expected pattern${NC}"
    echo -e "   Expected: ${ENVIRONMENT}-YYYYMMDD-HHMMSS-<identifier>${NC}"
    echo -e "   Actual: ${IMMUTABLE_TAG}${NC}"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}❌ Operation cancelled${NC}"
        rm "${BACKUP_FILE}"
        exit 1
    fi
fi

# kustomization.yaml 업데이트
echo -e "${YELLOW}🔄 Updating kustomization.yaml...${NC}"

# Python을 사용한 정확한 YAML 업데이트
python3 << EOF
import re
import sys

# 파일 읽기
with open('${KUSTOMIZATION_FILE}', 'r') as f:
    content = f.read()

# newTag 값 업데이트 (주석 유지)
def update_new_tag(match):
    line = match.group(0)
    if '#' in line:
        # 주석이 있는 경우 주석 유지
        before_comment = line.split('#')[0]
        comment = '#' + '#'.join(line.split('#')[1:])
        return re.sub(r'newTag:\s*\S+', f'newTag: ${IMMUTABLE_TAG}', before_comment) + '  ' + comment
    else:
        # 주석이 없는 경우
        return re.sub(r'newTag:\s*\S+', f'newTag: ${IMMUTABLE_TAG}', line)

# 정규표현식으로 newTag 라인 찾아서 업데이트
updated_content = re.sub(
    r'^(\s*newTag:\s*\S+.*?)$',
    update_new_tag,
    content,
    flags=re.MULTILINE
)

# GitOps 메타데이터 업데이트
import datetime
current_time = datetime.datetime.utcnow().isoformat() + 'Z'

# immutable-tag annotation 업데이트
if 'gitops.immutable-tag:' in updated_content:
    updated_content = re.sub(
        r'gitops\.immutable-tag:\s*"[^"]*"',
        f'gitops.immutable-tag: "${IMMUTABLE_TAG}"',
        updated_content
    )

# 파일 쓰기
with open('${KUSTOMIZATION_FILE}', 'w') as f:
    f.write(updated_content)

print(f'✅ Updated newTag to: ${IMMUTABLE_TAG}')
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ kustomization.yaml updated successfully${NC}"
else
    echo -e "${RED}❌ Failed to update kustomization.yaml${NC}"
    echo -e "${YELLOW}Restoring backup...${NC}"
    mv "${BACKUP_FILE}" "${KUSTOMIZATION_FILE}"
    exit 1
fi

# 변경사항 확인
echo ""
echo -e "${YELLOW}📊 Changes Summary${NC}"
echo "=================================================="
echo -e "${BLUE}Before:${NC}"
grep -A 2 -B 2 "newTag:" "${BACKUP_FILE}" || echo "  (newTag not found in backup)"
echo ""
echo -e "${BLUE}After:${NC}"
grep -A 2 -B 2 "newTag:" "${KUSTOMIZATION_FILE}" || echo "  (newTag not found in current)"

# Git 작업 (선택사항)
if [ "${AUTO_COMMIT:-false}" = "true" ]; then
    echo ""
    echo -e "${YELLOW}📝 Committing changes to Git...${NC}"
    
    # Git 상태 확인
    if [ ! -d ".git" ]; then
        echo -e "${RED}❌ Error: Not a git repository${NC}"
        exit 1
    fi
    
    # 변경사항 스테이징
    git add "${KUSTOMIZATION_FILE}"
    
    # 커밋 메시지에 GitOps 메타데이터 추가
    FULL_COMMIT_MESSAGE="${COMMIT_MESSAGE}

GitOps Immutable Tag Update:
- Environment: ${ENVIRONMENT}  
- Previous Tag: ${CURRENT_TAG}
- New Tag: ${IMMUTABLE_TAG}
- File: ${KUSTOMIZATION_FILE}

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"

    # 커밋 실행
    git commit -m "${FULL_COMMIT_MESSAGE}"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Changes committed successfully${NC}"
        echo -e "  Commit message: ${BLUE}${COMMIT_MESSAGE}${NC}"
    else
        echo -e "${RED}❌ Git commit failed${NC}"
        exit 1
    fi
    
    # 푸시 (선택사항)
    if [ "${AUTO_PUSH:-false}" = "true" ]; then
        echo -e "${YELLOW}📤 Pushing to remote repository...${NC}"
        git push
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅ Changes pushed to remote${NC}"
        else
            echo -e "${RED}❌ Git push failed${NC}"
            exit 1
        fi
    fi
fi

# Kustomization 검증
echo ""
echo -e "${YELLOW}🔍 Validating kustomization...${NC}"
if command -v kustomize >/dev/null 2>&1; then
    kustomize build "k8s/overlays/${ENVIRONMENT}" > /dev/null
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Kustomization validation passed${NC}"
    else
        echo -e "${RED}❌ Kustomization validation failed${NC}"
        echo -e "${YELLOW}Restoring backup...${NC}"
        mv "${BACKUP_FILE}" "${KUSTOMIZATION_FILE}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️  kustomize not found, skipping validation${NC}"
fi

# 완료 정리
rm "${BACKUP_FILE}"

echo ""
echo -e "${GREEN}🎉 GitOps Immutable Tag Update Complete!${NC}"
echo "=================================================="
echo -e "Environment: ${BLUE}${ENVIRONMENT}${NC}"
echo -e "New Immutable Tag: ${GREEN}${IMMUTABLE_TAG}${NC}"
echo -e "Updated File: ${YELLOW}${KUSTOMIZATION_FILE}${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Review the changes: git diff ${KUSTOMIZATION_FILE}"
echo "2. Commit changes: git add ${KUSTOMIZATION_FILE} && git commit -m '${COMMIT_MESSAGE}'"
echo "3. Push to trigger ArgoCD sync: git push"
echo "4. Monitor deployment: argocd app get fortinet-${ENVIRONMENT}"
echo ""

# 환경 변수 내보내기
echo "# Export these for your CI/CD pipeline:"
echo "export UPDATED_TAG='${IMMUTABLE_TAG}'"
echo "export KUSTOMIZATION_FILE='${KUSTOMIZATION_FILE}'"
echo "export ENVIRONMENT='${ENVIRONMENT}'"