#\!/bin/bash
# 폐쇄망 배포 패키지 생성 스크립트
# 모든 필요한 파일을 하나의 패키지로 묶어서 오프라인 환경에서 설치 가능하게 함

set -e

echo "🔧 FortiGate Nextrade 오프라인 배포 패키지 생성 시작..."

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 변수 설정
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PACKAGE_NAME="fortinet-offline-deploy-${TIMESTAMP}"
TEMP_DIR="./${PACKAGE_NAME}"
IMAGE_NAME="fortigate-nextrade:latest"
IMAGE_FILE="fortigate-nextrade-offline.tar"

# 임시 디렉토리 생성
echo -e "${BLUE}임시 디렉토리 생성: ${TEMP_DIR}${NC}"
mkdir -p "${TEMP_DIR}"

# 1. Docker 이미지 저장
echo -e "${YELLOW}Docker 이미지를 파일로 저장 중...${NC}"
docker save -o "${TEMP_DIR}/${IMAGE_FILE}" "${IMAGE_NAME}"
echo -e "${GREEN}✓ Docker 이미지 저장 완료${NC}"

# 2. 필요한 파일 복사
echo -e "${YELLOW}애플리케이션 파일 복사 중...${NC}"

# 설치 스크립트
cp fortinet-installer.sh "${TEMP_DIR}/"
cp fortinet-installer.ps1 "${TEMP_DIR}/"

# Dockerfile (참고용)
cp Dockerfile.offline "${TEMP_DIR}/"

# README
cp README.md "${TEMP_DIR}/"

# 설정 디렉토리 생성
mkdir -p "${TEMP_DIR}/data"
cp data/config.json "${TEMP_DIR}/data/"

echo -e "${GREEN}✓ 파일 복사 완료${NC}"

# 3. 패키지 생성
echo -e "${YELLOW}tar.gz 패키지 생성 중...${NC}"
tar -czf "${PACKAGE_NAME}.tar.gz" "${PACKAGE_NAME}"

# 정리
rm -rf "${TEMP_DIR}"

echo -e "${GREEN}✅ 오프라인 배포 패키지 생성 완료\!${NC}"
echo -e "${BLUE}패키지 파일: ~/dev/fortinet/${PACKAGE_NAME}.tar.gz${NC}"
echo -e "${BLUE}파일 크기: $(ls -lh ~/dev/fortinet/${PACKAGE_NAME}.tar.gz  < /dev/null |  awk '{print $5}')${NC}"
