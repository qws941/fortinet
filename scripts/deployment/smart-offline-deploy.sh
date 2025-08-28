#!/bin/bash
# FortiGate Nextrade 스마트 오프라인 배포 도구
# 폐쇄망 환경을 위한 완전 자동화된 배포 솔루션

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# 설정
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
IMAGE_NAME="fortigate-nextrade:latest"
CONTAINER_NAME="fortigate-nextrade"
PORT=7777

# 로고 출력
show_logo() {
    echo -e "${CYAN}"
    cat << 'EOF'
╔══════════════════════════════════════════════════════════════════╗
║                   FortiGate Nextrade                            ║
║              스마트 오프라인 배포 도구 v3.0                        ║
║          폐쇄망 환경 최적화 자동 배포 솔루션                        ║
╚══════════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

# 메시지 출력 함수
log() {
    echo -e "${2}[$(date '+%H:%M:%S')] $1${NC}"
}

# 도움말
show_help() {
    show_logo
    cat << EOF
${YELLOW}사용법:${NC} $0 [명령]

${BLUE}배포 명령:${NC}
  ${GREEN}create-package${NC}    완전 자동화된 오프라인 패키지 생성
  ${GREEN}create-portable${NC}   Docker 없이 실행 가능한 포터블 버전 생성
  ${GREEN}create-usb${NC}        USB 배포용 원클릭 설치 패키지 생성
  
${BLUE}설치 명령:${NC}
  ${GREEN}auto-install${NC}      환경 자동 감지 후 최적 설치
  ${GREEN}quick-install${NC}     기본 설정으로 빠른 설치
  ${GREEN}portable-run${NC}      포터블 버전 실행
  
${BLUE}관리 명령:${NC}
  ${GREEN}status${NC}            전체 시스템 상태 확인
  ${GREEN}start${NC}             서비스 시작
  ${GREEN}stop${NC}              서비스 중지
  ${GREEN}restart${NC}           서비스 재시작
  ${GREEN}logs${NC}              실시간 로그 보기
  ${GREEN}config${NC}            설정 관리
  ${GREEN}health${NC}            시스템 헬스체크
  
${BLUE}유틸리티:${NC}
  ${GREEN}network-scan${NC}      네트워크 환경 자동 스캔
  ${GREEN}export-config${NC}     설정 내보내기
  ${GREEN}import-config${NC}     설정 가져오기
  ${GREEN}cleanup${NC}           시스템 정리

${YELLOW}예제:${NC}
  $0 create-usb           # USB 배포 패키지 생성
  $0 auto-install         # 자동 설치
  $0 network-scan         # 네트워크 환경 스캔
  $0 health               # 시스템 상태 확인

EOF
}

# Docker 확인
check_docker() {
    if ! command -v docker &> /dev/null; then
        log "Docker가 필요합니다. 포터블 버전을 사용하세요: $0 portable-run" "$YELLOW"
        return 1
    fi
    
    if ! docker ps &> /dev/null; then
        log "Docker 데몬이 실행되지 않았습니다." "$RED"
        return 1
    fi
    return 0
}

# 네트워크 환경 스캔
network_scan() {
    log "네트워크 환경을 스캔하는 중..." "$BLUE"
    
    # 기본 네트워크 정보
    local_ip=$(ip route get 1 | awk '{print $7; exit}' 2>/dev/null || echo "127.0.0.1")
    gateway=$(ip route | grep default | awk '{print $3}' | head -1)
    
    # 네트워크 대역 감지
    network_range=$(ip route | grep "$(echo $local_ip | cut -d. -f1-3)" | head -1 | awk '{print $1}')
    
    # FortiManager 후보 IP 스캔 (일반적인 관리 IP 대역)
    log "FortiManager 후보 장비를 스캔하는 중..." "$YELLOW"
    
    potential_ips=(
        "172.28.174.31"  # 기본값
        "${gateway}"
        "$(echo $local_ip | cut -d. -f1-3).1"
        "$(echo $local_ip | cut -d. -f1-3).254"
        "192.168.1.1"
        "192.168.1.254"
        "10.1.1.1"
    )
    
    log "감지된 네트워크 정보:" "$CYAN"
    echo "  로컬 IP: $local_ip"
    echo "  게이트웨이: $gateway"
    echo "  네트워크: $network_range"
    
    # 간단한 포트 스캔 (443, 80)
    log "FortiManager 후보 검색 중..." "$YELLOW"
    for ip in "${potential_ips[@]}"; do
        if [[ -n "$ip" ]] && timeout 2 nc -z "$ip" 443 2>/dev/null; then
            log "발견: $ip:443 (HTTPS)" "$GREEN"
            echo "FORTIMANAGER_CANDIDATE=$ip" >> /tmp/network_scan.env
        elif [[ -n "$ip" ]] && timeout 2 nc -z "$ip" 80 2>/dev/null; then
            log "발견: $ip:80 (HTTP)" "$GREEN"
            echo "FORTIMANAGER_CANDIDATE=$ip" >> /tmp/network_scan.env
        fi
    done
    
    # 스캔 결과 저장
    cat > /tmp/network_info.json << EOF
{
    "local_ip": "$local_ip",
    "gateway": "$gateway", 
    "network_range": "$network_range",
    "scan_time": "$(date -Iseconds)",
    "recommended_fortimanager": "172.28.174.31"
}
EOF
    
    log "네트워크 스캔 완료. 결과는 /tmp/network_info.json에 저장됨" "$GREEN"
}

# 스마트 패키지 생성
create_smart_package() {
    show_logo
    log "스마트 오프라인 패키지 생성을 시작합니다..." "$BLUE"
    
    local package_name="fortinet-smart-deploy-${TIMESTAMP}"
    local temp_dir="./${package_name}"
    
    # Docker 이미지 빌드 (최신 상태로)
    log "최신 Docker 이미지를 빌드하는 중..." "$YELLOW"
    docker build --no-cache -f Dockerfile.offline -t "$IMAGE_NAME" .
    
    # 패키지 디렉토리 생성
    mkdir -p "$temp_dir"/{scripts,config,data,tools}
    
    # Docker 이미지 저장
    log "Docker 이미지를 압축하는 중..." "$YELLOW"
    docker save "$IMAGE_NAME" | gzip > "$temp_dir/fortigate-image.tar.gz"
    
    # 필수 파일 복사
    cp "$0" "$temp_dir/scripts/"
    cp fortinet-installer.sh "$temp_dir/scripts/"
    cp fortinet-installer.ps1 "$temp_dir/scripts/"
    cp README.md "$temp_dir/"
    
    # 설정 템플릿 생성
    create_config_templates "$temp_dir/config"
    
    # 실행 스크립트 생성
    cat > "$temp_dir/INSTALL.sh" << 'EOF'
#!/bin/bash
echo "🚀 FortiGate Nextrade 자동 설치 시작..."
cd "$(dirname "$0")"
chmod +x scripts/smart-offline-deploy.sh
./scripts/smart-offline-deploy.sh auto-install
EOF
    chmod +x "$temp_dir/INSTALL.sh"
    
    # Windows 실행 스크립트
    cat > "$temp_dir/INSTALL.bat" << 'EOF'
@echo off
echo 🚀 FortiGate Nextrade 자동 설치 시작...
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File scripts\fortinet-installer.ps1 install
pause
EOF
    
    # 도구 추가
    create_utility_tools "$temp_dir/tools"
    
    # README 생성
    cat > "$temp_dir/설치가이드.txt" << EOF
🚀 FortiGate Nextrade 폐쇄망 설치 가이드

=== 빠른 설치 (권장) ===
Linux: ./INSTALL.sh
Windows: INSTALL.bat 더블클릭

=== 수동 설치 ===
1. scripts/smart-offline-deploy.sh network-scan  (네트워크 스캔)
2. scripts/smart-offline-deploy.sh auto-install  (자동 설치)

=== 설정 ===
- config/ 폴더에 환경별 설정 템플릿 있음
- scripts/smart-offline-deploy.sh config 로 설정 변경

=== 접속 ===
설치 완료 후: http://localhost:7777

=== 문제 해결 ===
scripts/smart-offline-deploy.sh health  (시스템 진단)
scripts/smart-offline-deploy.sh logs    (로그 확인)
EOF
    
    # 압축
    log "패키지를 압축하는 중..." "$YELLOW"
    tar -czf "${package_name}.tar.gz" "$package_name"
    rm -rf "$temp_dir"
    
    # 파일 크기 확인
    local file_size=$(ls -lh "${package_name}.tar.gz" | awk '{print $5}')
    
    log "✅ 스마트 오프라인 패키지 생성 완료!" "$GREEN"
    log "📦 파일: ${package_name}.tar.gz (${file_size})" "$CYAN"
    log "🔧 설치: tar -xzf ${package_name}.tar.gz && cd ${package_name} && ./INSTALL.sh" "$YELLOW"
}

# 포터블 버전 생성 (Docker 없이 실행)
create_portable() {
    show_logo
    log "포터블 버전을 생성하는 중..." "$BLUE"
    
    local portable_name="fortinet-portable-${TIMESTAMP}"
    local temp_dir="./${portable_name}"
    
    mkdir -p "$temp_dir"/{app,config,data,logs}
    
    # 소스 코드 복사 (필수 파일만)
    cp -r src "$temp_dir/app/"
    cp requirements.txt "$temp_dir/app/"
    cp -r data "$temp_dir/"
    cp -r static "$temp_dir/app/" 2>/dev/null || true
    
    # 포터블 실행 스크립트
    cat > "$temp_dir/run.sh" << 'EOF'
#!/bin/bash
echo "🚀 FortiGate Nextrade 포터블 버전 시작..."

# Python 가상환경 생성
if [ ! -d "venv" ]; then
    echo "Python 가상환경 생성 중..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r app/requirements.txt
else
    source venv/bin/activate
fi

# 환경변수 설정
export FLASK_PORT=7777
export APP_MODE=production
export OFFLINE_MODE=true
export PYTHONPATH="$(pwd)/app:$PYTHONPATH"

# 서비스 시작
cd app
python3 main.py --web --port 7777
EOF
    chmod +x "$temp_dir/run.sh"
    
    # Windows 포터블 스크립트
    cat > "$temp_dir/run.bat" << 'EOF'
@echo off
echo 🚀 FortiGate Nextrade 포터블 버전 시작...

if not exist "venv" (
    echo Python 가상환경 생성 중...
    python -m venv venv
    call venv\Scripts\activate
    pip install -r app\requirements.txt
) else (
    call venv\Scripts\activate
)

set FLASK_PORT=7777
set APP_MODE=production
set OFFLINE_MODE=true
set PYTHONPATH=%cd%\app;%PYTHONPATH%

cd app
python main.py --web --port 7777
pause
EOF
    
    # 설정 파일
    cat > "$temp_dir/config.json" << EOF
{
    "app_mode": "production",
    "offline_mode": true,
    "port": 7777,
    "fortimanager": {
        "host": "172.28.174.31",
        "port": 443,
        "username": "monitor",
        "verify_ssl": false
    }
}
EOF
    
    # README
    cat > "$temp_dir/README.txt" << EOF
🚀 FortiGate Nextrade 포터블 버전

=== 실행 ===
Linux/Mac: ./run.sh
Windows: run.bat 더블클릭

=== 요구사항 ===
- Python 3.8 이상
- pip

=== 접속 ===
http://localhost:7777

=== 설정 ===
config.json 파일 수정
EOF
    
    # 압축
    tar -czf "${portable_name}.tar.gz" "$portable_name"
    rm -rf "$temp_dir"
    
    log "✅ 포터블 버전 생성 완료!" "$GREEN"
    log "📦 파일: ${portable_name}.tar.gz" "$CYAN"
    log "🏃 실행: tar -xzf ${portable_name}.tar.gz && cd ${portable_name} && ./run.sh" "$YELLOW"
}

# USB 배포 키트 생성
create_usb_kit() {
    show_logo
    log "USB 배포 키트를 생성하는 중..." "$BLUE"
    
    local usb_name="FortiGate-Nextrade-USB"
    local temp_dir="./${usb_name}"
    
    mkdir -p "$temp_dir"/{docker,portable,tools,docs}
    
    # Docker 버전
    create_smart_package
    mv fortinet-smart-deploy-*.tar.gz "$temp_dir/docker/"
    
    # 포터블 버전  
    create_portable
    mv fortinet-portable-*.tar.gz "$temp_dir/portable/"
    
    # 통합 설치 스크립트
    cat > "$temp_dir/자동설치.sh" << 'EOF'
#!/bin/bash
clear
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║              FortiGate Nextrade USB 배포 키트                     ║"
echo "║                     자동 설치 프로그램                            ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo
echo "설치 방법을 선택하세요:"
echo
echo "1) Docker 버전 (권장) - 완전한 기능, 컨테이너 기반"
echo "2) 포터블 버전 - Python 직접 실행, 가벼운 설치"
echo "3) 환경 진단 - 시스템 요구사항 확인"
echo
read -p "선택 (1-3): " choice

case $choice in
    1)
        echo "Docker 버전 설치를 시작합니다..."
        cd docker
        tar -xzf *.tar.gz
        cd fortinet-smart-deploy-*
        ./INSTALL.sh
        ;;
    2)
        echo "포터블 버전 설치를 시작합니다..."
        cd portable
        tar -xzf *.tar.gz
        cd fortinet-portable-*
        ./run.sh
        ;;
    3)
        echo "시스템 진단을 실행합니다..."
        cd tools
        ./system_check.sh
        ;;
    *)
        echo "잘못된 선택입니다."
        exit 1
        ;;
esac
EOF
    chmod +x "$temp_dir/자동설치.sh"
    
    # Windows 자동 설치
    cat > "$temp_dir/자동설치.bat" << 'EOF'
@echo off
cls
echo ╔══════════════════════════════════════════════════════════════════╗
echo ║              FortiGate Nextrade USB 배포 키트                     ║
echo ║                     자동 설치 프로그램                            ║
echo ╚══════════════════════════════════════════════════════════════════╝
echo.
echo 설치 방법을 선택하세요:
echo.
echo 1) Docker 버전 (권장) - 완전한 기능, 컨테이너 기반
echo 2) 포터블 버전 - Python 직접 실행, 가벼운 설치
echo 3) 환경 진단 - 시스템 요구사항 확인
echo.
set /p choice="선택 (1-3): "

if "%choice%"=="1" (
    echo Docker 버전 설치를 시작합니다...
    cd docker
    for %%f in (*.tar.gz) do tar -xzf "%%f"
    cd fortinet-smart-deploy-*
    INSTALL.bat
) else if "%choice%"=="2" (
    echo 포터블 버전 설치를 시작합니다...
    cd portable
    for %%f in (*.tar.gz) do tar -xzf "%%f"
    cd fortinet-portable-*
    run.bat
) else if "%choice%"=="3" (
    echo 시스템 진단을 실행합니다...
    cd tools
    system_check.bat
) else (
    echo 잘못된 선택입니다.
    pause
    exit /b 1
)
EOF
    
    # 시스템 체크 도구
    create_system_check_tools "$temp_dir/tools"
    
    # 문서
    create_documentation "$temp_dir/docs"
    
    log "✅ USB 배포 키트 생성 완료!" "$GREEN"
    log "📁 폴더: ${usb_name}/" "$CYAN"
    log "💾 USB에 복사 후 자동설치.sh 또는 자동설치.bat 실행" "$YELLOW"
}

# 설정 템플릿 생성
create_config_templates() {
    local config_dir="$1"
    
    # 기본 설정
    cat > "$config_dir/basic.json" << 'EOF'
{
    "app_mode": "production",
    "offline_mode": true,
    "port": 7777,
    "fortimanager": {
        "host": "172.28.174.31",
        "port": 443,
        "username": "monitor",
        "password": "",
        "verify_ssl": false
    },
    "logging": {
        "level": "INFO",
        "file": "/app/logs/app.log"
    }
}
EOF
    
    # 개발 환경 설정
    cat > "$config_dir/development.json" << 'EOF'
{
    "app_mode": "test",
    "offline_mode": true,
    "port": 7777,
    "debug": true,
    "fortimanager": {
        "host": "localhost",
        "port": 443,
        "username": "admin",
        "password": "",
        "verify_ssl": false
    }
}
EOF
    
    # 고가용성 설정
    cat > "$config_dir/high_availability.json" << 'EOF'
{
    "app_mode": "production",
    "offline_mode": true,
    "port": 7777,
    "fortimanager": {
        "primary": {
            "host": "172.28.174.31",
            "port": 443,
            "username": "monitor"
        },
        "secondary": {
            "host": "172.28.174.32", 
            "port": 443,
            "username": "monitor"
        },
        "verify_ssl": false
    },
    "monitoring": {
        "health_check_interval": 30,
        "auto_failover": true
    }
}
EOF
}

# 시스템 체크 도구 생성
create_system_check_tools() {
    local tools_dir="$1"
    
    cat > "$tools_dir/system_check.sh" << 'EOF'
#!/bin/bash
echo "🔍 시스템 요구사항 확인 중..."
echo

# Python 확인
if command -v python3 &> /dev/null; then
    python_version=$(python3 --version)
    echo "✅ Python: $python_version"
else
    echo "❌ Python 3.8 이상이 필요합니다"
fi

# Docker 확인
if command -v docker &> /dev/null; then
    docker_version=$(docker --version)
    echo "✅ Docker: $docker_version"
    
    if docker ps &> /dev/null; then
        echo "✅ Docker 데몬: 실행 중"
    else
        echo "⚠️ Docker 데몬: 중지됨"
    fi
else
    echo "⚠️ Docker: 미설치 (포터블 버전 사용 가능)"
fi

# 메모리 확인
memory_total=$(free -h | grep Mem | awk '{print $2}')
echo "💾 메모리: $memory_total"

# 디스크 공간 확인
disk_free=$(df -h . | tail -1 | awk '{print $4}')
echo "💿 여유 공간: $disk_free"

# 포트 확인
if ss -tuln | grep -q ":7777"; then
    echo "⚠️ 포트 7777: 사용 중"
else
    echo "✅ 포트 7777: 사용 가능"
fi

echo
echo "권장사항:"
echo "- 메모리: 최소 2GB, 권장 4GB"
echo "- 디스크: 최소 1GB 여유 공간"
echo "- 포트 7777 사용 가능"
EOF
    chmod +x "$tools_dir/system_check.sh"
    
    cat > "$tools_dir/system_check.bat" << 'EOF'
@echo off
echo 🔍 시스템 요구사항 확인 중...
echo.

python --version >nul 2>&1
if %errorlevel% == 0 (
    echo ✅ Python: 설치됨
) else (
    echo ❌ Python이 필요합니다
)

docker --version >nul 2>&1
if %errorlevel% == 0 (
    echo ✅ Docker: 설치됨
    docker ps >nul 2>&1
    if %errorlevel% == 0 (
        echo ✅ Docker 데몬: 실행 중
    ) else (
        echo ⚠️ Docker 데몬: 중지됨
    )
) else (
    echo ⚠️ Docker: 미설치 (포터블 버전 사용 가능)
)

echo.
echo 권장사항:
echo - 메모리: 최소 2GB, 권장 4GB
echo - 디스크: 최소 1GB 여유 공간
echo - 포트 7777 사용 가능
pause
EOF
}

# 자동 설치
auto_install() {
    show_logo
    log "환경 자동 감지 및 설치를 시작합니다..." "$BLUE"
    
    # 네트워크 스캔
    network_scan
    
    # Docker 확인
    if check_docker; then
        log "Docker 환경이 감지되었습니다. Docker 버전으로 설치합니다." "$GREEN"
        
        # 최신 패키지 찾기
        local package_file=$(ls -t fortinet-smart-deploy-*.tar.gz 2>/dev/null | head -1)
        if [[ -z "$package_file" ]]; then
            log "설치 패키지를 찾을 수 없습니다. 패키지를 먼저 생성하세요." "$RED"
            exit 1
        fi
        
        log "설치 패키지: $package_file" "$CYAN"
        
        # 패키지 추출
        tar -xzf "$package_file"
        local extract_dir=$(basename "$package_file" .tar.gz)
        
        cd "$extract_dir"
        
        # 자동 설정 적용
        if [[ -f "/tmp/network_scan.env" ]]; then
            source /tmp/network_scan.env
            if [[ -n "$FORTIMANAGER_CANDIDATE" ]]; then
                log "FortiManager 후보 감지: $FORTIMANAGER_CANDIDATE" "$GREEN"
                export FORTIMANAGER_HOST="$FORTIMANAGER_CANDIDATE"
            fi
        fi
        
        # 설치 실행
        ./INSTALL.sh
        
    else
        log "Docker가 없습니다. 포터블 버전으로 설치합니다." "$YELLOW"
        
        # 포터블 패키지 찾기
        local portable_file=$(ls -t fortinet-portable-*.tar.gz 2>/dev/null | head -1)
        if [[ -z "$portable_file" ]]; then
            log "포터블 패키지를 생성하는 중..." "$YELLOW"
            create_portable
            portable_file=$(ls -t fortinet-portable-*.tar.gz | head -1)
        fi
        
        log "포터블 패키지: $portable_file" "$CYAN"
        
        # 패키지 추출 및 실행
        tar -xzf "$portable_file"
        local extract_dir=$(basename "$portable_file" .tar.gz)
        
        cd "$extract_dir"
        ./run.sh
    fi
}

# 헬스체크
health_check() {
    show_logo
    log "시스템 헬스체크를 실행합니다..." "$BLUE"
    
    echo -e "${CYAN}=== 시스템 상태 ===${NC}"
    
    # Docker 상태
    if check_docker; then
        if docker ps | grep -q "$CONTAINER_NAME"; then
            log "Docker 컨테이너: 실행 중" "$GREEN"
            
            # 컨테이너 리소스 확인
            docker stats "$CONTAINER_NAME" --no-stream --format "table {{.CPUPerc}}\t{{.MemUsage}}" | tail -1 | while read cpu memory; do
                log "리소스 사용: CPU $cpu, 메모리 $memory" "$CYAN"
            done
        else
            log "Docker 컨테이너: 중지됨" "$RED"
        fi
    else
        log "Docker: 사용 불가" "$YELLOW"
    fi
    
    # 웹 서비스 확인
    if curl -s "http://localhost:$PORT" > /dev/null; then
        log "웹 서비스: 정상 응답" "$GREEN"
        log "접속 URL: http://localhost:$PORT" "$CYAN"
    else
        log "웹 서비스: 응답 없음" "$RED"
    fi
    
    # 로그 파일 확인
    if [[ -f "$SCRIPT_DIR/logs/app.log" ]]; then
        local log_size=$(ls -lh "$SCRIPT_DIR/logs/app.log" | awk '{print $5}')
        log "로그 파일: $log_size" "$CYAN"
        
        # 최근 에러 확인
        local error_count=$(tail -100 "$SCRIPT_DIR/logs/app.log" | grep -c "ERROR" || echo "0")
        if [[ "$error_count" -gt 0 ]]; then
            log "최근 오류: ${error_count}개 발견" "$YELLOW"
        else
            log "최근 오류: 없음" "$GREEN"
        fi
    fi
    
    # 네트워크 연결 확인
    if [[ -n "$FORTIMANAGER_HOST" ]]; then
        if timeout 3 nc -z "$FORTIMANAGER_HOST" 443 2>/dev/null; then
            log "FortiManager 연결: 정상" "$GREEN"
        else
            log "FortiManager 연결: 실패" "$RED"
        fi
    fi
    
    echo -e "${CYAN}=== 시스템 리소스 ===${NC}"
    
    # 메모리 사용량
    local memory_info=$(free -h | grep Mem | awk '{print $3 "/" $2 " (" $3/$2*100 "%)"}')
    log "메모리 사용: $memory_info" "$CYAN"
    
    # 디스크 사용량
    local disk_info=$(df -h "$SCRIPT_DIR" | tail -1 | awk '{print $3 "/" $2 " (" $5 ")"}')
    log "디스크 사용: $disk_info" "$CYAN"
    
    # CPU 로드
    local load_avg=$(uptime | awk -F'load average:' '{print $2}')
    log "CPU 로드:$load_avg" "$CYAN"
}

# 메인 실행 로직
case "${1:-help}" in
    create-package)
        create_smart_package
        ;;
    create-portable)
        create_portable
        ;;
    create-usb)
        create_usb_kit
        ;;
    auto-install)
        auto_install
        ;;
    quick-install)
        # 기본 설정으로 빠른 설치
        if check_docker; then
            docker run -d --name "$CONTAINER_NAME" -p "$PORT:$PORT" \
                -e OFFLINE_MODE=true \
                -e APP_MODE=production \
                "$IMAGE_NAME"
            log "빠른 설치 완료: http://localhost:$PORT" "$GREEN"
        else
            log "Docker가 필요합니다. auto-install을 사용하세요." "$RED"
        fi
        ;;
    portable-run)
        # 포터블 버전 실행
        if [[ -f "run.sh" ]]; then
            ./run.sh
        else
            log "포터블 패키지를 먼저 추출하세요." "$RED"
        fi
        ;;
    network-scan)
        network_scan
        ;;
    health)
        health_check
        ;;
    status|start|stop|restart|logs|config)
        # 기존 설치 스크립트로 위임
        if [[ -f "fortinet-installer.sh" ]]; then
            ./fortinet-installer.sh "$1"
        else
            log "설치 스크립트를 찾을 수 없습니다." "$RED"
        fi
        ;;
    cleanup)
        log "시스템 정리 중..." "$YELLOW"
        docker system prune -f
        rm -f /tmp/network_*.env /tmp/network_*.json
        log "정리 완료" "$GREEN"
        ;;
    *)
        show_help
        ;;
esac