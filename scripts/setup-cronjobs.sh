#!/bin/bash
# FortiGate Nextrade 크론잡 설정 스크립트
# 백업, 헬스체크, 보고서 자동화를 위한 크론 설정

set -euo pipefail

SCRIPT_DIR="$(dirname "$(realpath "$0")")"
CRON_DIR="/etc/cron.d"
LOG_DIR="/var/log/fortinet"

echo "🚀 FortiGate Nextrade 크론잡 설정 시작"

# 로그 디렉토리 생성
sudo mkdir -p "$LOG_DIR"
sudo chown $(whoami):$(whoami) "$LOG_DIR"

# 1. 백업 크론잡 (매일 새벽 2시)
echo "📦 백업 크론잡 설정 중..."
cat << EOF | sudo tee "${CRON_DIR}/fortinet-backup"
# FortiGate Nextrade 일일 백업
# 매일 새벽 2시에 실행
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
MAILTO=ops@jclee.me

0 2 * * * root ${SCRIPT_DIR}/backup.sh >> ${LOG_DIR}/backup.log 2>&1
EOF

# 2. 헬스체크 크론잡 (5분마다)  
echo "🏥 헬스체크 크론잡 설정 중..."
cat << EOF | sudo tee "${CRON_DIR}/fortinet-healthcheck"
# FortiGate Nextrade 헬스체크
# 5분마다 실행
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
MAILTO=ops@jclee.me

*/5 * * * * root ${SCRIPT_DIR}/healthcheck.sh >> ${LOG_DIR}/healthcheck.log 2>&1
EOF

# 3. 일일 보고서 크론잡 (매일 오전 9시)
echo "📊 일일 보고서 크론잡 설정 중..."
cat << EOF | sudo tee "${CRON_DIR}/fortinet-daily-report"
# FortiGate Nextrade 일일 보고서
# 매일 오전 9시에 실행
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
MAILTO=ops@jclee.me

0 9 * * * root ${SCRIPT_DIR}/daily-report.sh >> ${LOG_DIR}/reports.log 2>&1
EOF

# 4. 주간 로그 정리 크론잡 (매주 일요일 새벽 3시)
echo "🧹 로그 정리 크론잡 설정 중..."
cat << EOF | sudo tee "${CRON_DIR}/fortinet-logrotate"
# FortiGate Nextrade 로그 정리
# 매주 일요일 새벽 3시에 실행
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

0 3 * * 0 root find ${LOG_DIR} -name "*.log" -mtime +30 -delete && echo "\$(date): Old logs cleaned" >> ${LOG_DIR}/maintenance.log
EOF

# 5. 크론 서비스 재시작
echo "🔄 크론 서비스 재시작 중..."
sudo systemctl reload cron
sudo systemctl status cron --no-pager -l

# 6. 설정 검증
echo "🔍 크론잡 설정 검증 중..."
echo
echo "📋 설정된 크론잡 목록:"
sudo crontab -l 2>/dev/null || echo "시스템 크론탭 없음"
echo
echo "📂 크론 디렉토리 파일들:"
ls -la "${CRON_DIR}"/fortinet-*
echo
echo "📝 크론잡 내용 확인:"
for file in "${CRON_DIR}"/fortinet-*; do
    echo "--- $(basename "$file") ---"
    cat "$file"
    echo
done

# 7. 테스트 실행 (선택적)
echo "🧪 크론잡 테스트 실행 옵션:"
echo "  백업 테스트:     ${SCRIPT_DIR}/backup.sh"
echo "  헬스체크 테스트: ${SCRIPT_DIR}/healthcheck.sh"  
echo "  보고서 테스트:   ${SCRIPT_DIR}/daily-report.sh"
echo

# 8. 모니터링 설정
echo "📊 로그 모니터링 설정:"
echo "  백업 로그:       tail -f ${LOG_DIR}/backup.log"
echo "  헬스체크 로그:   tail -f ${LOG_DIR}/healthcheck.log"
echo "  보고서 로그:     tail -f ${LOG_DIR}/reports.log"
echo "  유지보수 로그:   tail -f ${LOG_DIR}/maintenance.log"

echo
echo "✅ FortiGate Nextrade 크론잡 설정 완료!"
echo
echo "📅 실행 스케줄 요약:"
echo "  • 백업:       매일 새벽 2:00"
echo "  • 헬스체크:   매 5분마다"
echo "  • 일일 보고서: 매일 오전 9:00"
echo "  • 로그 정리:   매주 일요일 새벽 3:00"
echo
echo "🔔 알림 설정: ops@jclee.me (MAILTO)"
echo "📂 로그 위치: ${LOG_DIR}/"
echo
echo "👨‍💻 운영 명령어:"
echo "  sudo systemctl status cron    # 크론 서비스 상태 확인"
echo "  sudo systemctl reload cron    # 크론 설정 재로드"
echo "  sudo journalctl -u cron -f    # 크론 실시간 로그"