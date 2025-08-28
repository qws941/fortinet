#!/bin/bash

# GitOps 배포 실행 스크립트
set -e

echo "🚀 GitOps 자동 배포 시작"
echo "========================="

# Git 상태 확인
echo "📊 Git 상태 확인..."
git status

# 현재 commit SHA
CURRENT_SHA=$(git rev-parse --short HEAD)
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
IMAGE_TAG="${CURRENT_SHA}-${TIMESTAMP}"

echo "🏷️ 이미지 태그: ${IMAGE_TAG}"

# Kustomization 파일 업데이트
echo "🔄 Kustomization 업데이트..."
sed -i "s/newTag:.*/newTag: ${IMAGE_TAG}/" k8s/overlays/production/kustomization.yaml

# 변경사항 확인
echo "📝 업데이트된 kustomization.yaml:"
grep -A2 -B2 "newTag" k8s/overlays/production/kustomization.yaml

# Git add
echo "📤 변경사항 스테이징..."
git add .

# 커밋 생성
COMMIT_MESSAGE="🚀 deploy(k8s): GitOps 자동 배포 실행 ${IMAGE_TAG}

🎯 배포 정보:
- Image: registry.jclee.me/fortinet:${IMAGE_TAG}  
- Environment: production
- Namespace: fortinet
- Strategy: Pull-based GitOps

🔄 자동화 프로세스:
- Kustomize 매니페스트 업데이트 완료
- ArgoCD 자동 동기화 트리거 예정
- K8s 클러스터 무중단 배포 진행
- Health Check 자동 검증 포함

📊 인프라 정보:
- Registry: registry.jclee.me  
- ArgoCD: https://argo.jclee.me
- Target: http://192.168.50.110:30777
- External: https://fortinet.jclee.me

🤖 Generated with Claude Code GitOps Automation

Co-authored-by: Claude <noreply@anthropic.com>"

echo "💾 커밋 생성..."
git commit -m "$COMMIT_MESSAGE"

echo "🚀 GitHub Push..."
git push origin master

echo ""
echo "✅ GitOps 파이프라인 트리거 완료!"
echo ""
echo "📊 실시간 모니터링:"
echo "  🔗 GitHub Actions: https://github.com/jclee/app/actions"  
echo "  🔗 ArgoCD Dashboard: https://argo.jclee.me"
echo "  🔗 Service Health: http://192.168.50.110:30777/api/health"
echo ""
echo "⏱️ 예상 배포 시간: 3-5분"