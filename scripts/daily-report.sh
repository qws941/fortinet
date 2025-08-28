#!/bin/bash
# FortiGate Nextrade 일일 운영 보고서 자동 생성 스크립트
# 매일 자동 실행되는 종합 모니터링 리포트

set -euo pipefail

# 설정
NAMESPACE="fortinet"
APP_NAME="fortinet"
REPORT_DIR="/home/jclee/app/fortinet/reports"
DATE=$(date +%Y%m%d)
DATETIME=$(date '+%Y-%m-%d %H:%M:%S')
REPORT_FILE="${REPORT_DIR}/daily-report-${DATE}.md"

# 디렉토리 생성
mkdir -p "$REPORT_DIR"

# 보고서 생성
cat > "$REPORT_FILE" << EOF
# 🚀 FortiGate Nextrade 일일 운영 보고서

**생성일시**: $DATETIME  
**네임스페이스**: $NAMESPACE  
**애플리케이션**: $APP_NAME  

---

## ✅ 서비스 상태

### Pod 현황
\`\`\`
$(kubectl get pods -n "$NAMESPACE" -l app="$APP_NAME" -o wide 2>/dev/null || echo "Pod 정보 없음")
\`\`\`

### Service 현황  
\`\`\`
$(kubectl get svc -n "$NAMESPACE" -l app="$APP_NAME" -o wide 2>/dev/null || echo "Service 정보 없음")
\`\`\`

### Ingress 현황
\`\`\`
$(kubectl get ingress -n "$NAMESPACE" -o wide 2>/dev/null || echo "Ingress 정보 없음")
\`\`\`

---

## 📊 리소스 사용량

### Pod 리소스 사용률
\`\`\`
$(kubectl top pods -n "$NAMESPACE" -l app="$APP_NAME" 2>/dev/null || echo "메트릭 정보 수집 불가")
\`\`\`

### 노드 리소스 현황
\`\`\`
$(kubectl top nodes 2>/dev/null | head -5 || echo "노드 메트릭 정보 수집 불가")
\`\`\`

---

## 🔗 접속 정보

- **🌐 외부 웹사이트**: https://fortinet.jclee.me
- **🏥 Health Check**: https://fortinet.jclee.me/api/health  
- **🔧 내부 접속**: http://192.168.50.110:30777
- **📊 ArgoCD**: https://argo.jclee.me/applications/fortinet
- **📈 모니터링**: https://grafana.jclee.me/d/fortinet

---

## 📈 오늘의 메트릭

### 응답 시간 측정
EOF

# 헬스체크 응답 시간 측정 (5회)
echo "### 헬스체크 테스트 (5회 실행)" >> "$REPORT_FILE"
echo '```' >> "$REPORT_FILE"

EXTERNAL_URL="https://fortinet.jclee.me/api/health"
INTERNAL_URL="http://192.168.50.110:30777/api/health"

for i in {1..5}; do
    # 외부 엔드포인트
    if external_time=$(curl -w "%{time_total}s" -o /dev/null -s --max-time 10 "$EXTERNAL_URL" 2>/dev/null); then
        echo "외부 #$i: $external_time" >> "$REPORT_FILE"
    else
        echo "외부 #$i: 실패" >> "$REPORT_FILE"
    fi
    
    # 내부 엔드포인트  
    if internal_time=$(curl -w "%{time_total}s" -o /dev/null -s --max-time 10 "$INTERNAL_URL" 2>/dev/null); then
        echo "내부 #$i: $internal_time" >> "$REPORT_FILE"
    else
        echo "내부 #$i: 실패" >> "$REPORT_FILE"
    fi
    
    sleep 1
done

echo '```' >> "$REPORT_FILE"

# 로그 분석 추가
cat >> "$REPORT_FILE" << EOF

### 애플리케이션 로그 요약 (최근 24시간)
\`\`\`
총 로그 라인 수: $(kubectl logs -n "$NAMESPACE" -l app="$APP_NAME" --since=24h 2>/dev/null | wc -l || echo "0")
ERROR 로그 수: $(kubectl logs -n "$NAMESPACE" -l app="$APP_NAME" --since=24h 2>/dev/null | grep -i error | wc -l || echo "0")  
WARNING 로그 수: $(kubectl logs -n "$NAMESPACE" -l app="$APP_NAME" --since=24h 2>/dev/null | grep -i warning | wc -l || echo "0")
INFO 로그 수: $(kubectl logs -n "$NAMESPACE" -l app="$APP_NAME" --since=24h 2>/dev/null | grep -i info | wc -l || echo "0")
\`\`\`

### 최근 에러 로그 (최대 5개)
\`\`\`
$(kubectl logs -n "$NAMESPACE" -l app="$APP_NAME" --since=24h 2>/dev/null | grep -i error | tail -5 || echo "에러 로그 없음")
\`\`\`

---

## 🔄 배포 정보

### ArgoCD 동기화 상태
EOF

# ArgoCD 애플리케이션 상태 (시도)
if kubectl get applications -n argocd fortinet -o jsonpath='{.status.sync.status}' >/dev/null 2>&1; then
    sync_status=$(kubectl get applications -n argocd fortinet -o jsonpath='{.status.sync.status}' 2>/dev/null)
    health_status=$(kubectl get applications -n argocd fortinet -o jsonpath='{.status.health.status}' 2>/dev/null)
    
    cat >> "$REPORT_FILE" << EOF
\`\`\`
동기화 상태: $sync_status
헬스 상태: $health_status
마지막 동기화: $(kubectl get applications -n argocd fortinet -o jsonpath='{.status.operationState.finishedAt}' 2>/dev/null || echo "정보 없음")
\`\`\`
EOF
else
    cat >> "$REPORT_FILE" << EOF
\`\`\`
ArgoCD 애플리케이션 정보 수집 불가
\`\`\`
EOF
fi

# 최근 이벤트
cat >> "$REPORT_FILE" << EOF

### 최근 Kubernetes 이벤트 (최대 10개)
\`\`\`
$(kubectl get events -n "$NAMESPACE" --sort-by='.metadata.creationTimestamp' 2>/dev/null | tail -10 || echo "이벤트 정보 없음")
\`\`\`

---

## 🛡️ 보안 및 백업

### 백업 상태  
- **마지막 백업**: $(ls -t /backup/fortinet/backup-metadata_*.json 2>/dev/null | head -1 | sed 's/.*_\([0-9]*_[0-9]*\).json/\1/' | sed 's/_/ /' || echo "백업 정보 없음")
- **백업 파일 수**: $(ls /backup/fortinet/ 2>/dev/null | wc -l || echo "0")개

### 인증서 상태
\`\`\`
$(kubectl get certificates -n "$NAMESPACE" 2>/dev/null || echo "인증서 정보 없음")
\`\`\`

---

## 📝 운영 참고사항

### 오늘의 알려진 이슈
- 현재 확인된 문제점 없음

### 예정된 작업
- 정기 보안 업데이트 예정
- 모니터링 대시보드 개선

### 담당자 연락처
- **운영팀**: ops@jclee.me
- **장애 신고**: emergency@jclee.me  
- **Slack**: #fortinet-ops

---

*📊 이 보고서는 자동으로 생성되었습니다. 문의사항은 운영팀에 연락하세요.*

**다음 보고서**: $(date -d '+1 day' +%Y-%m-%d)
EOF

# 보고서 완료 메시지
echo "✅ 일일 운영 보고서 생성 완료: $REPORT_FILE"

# 보고서 요약 출력
echo
echo "📋 보고서 요약:"
echo "- 파일: $REPORT_FILE"
echo "- 크기: $(du -sh "$REPORT_FILE" | cut -f1)"
echo "- 생성 시간: $DATETIME"

# Slack 알림 (선택적)
if [[ -n "${SLACK_WEBHOOK:-}" ]]; then
    curl -X POST "$SLACK_WEBHOOK" \
        -H 'Content-type: application/json' \
        --data "{\"text\":\"📊 FortiGate Nextrade 일일 보고서 생성\\n• 날짜: $(date +%Y-%m-%d)\\n• 파일: $(basename "$REPORT_FILE")\\n• 크기: $(du -sh "$REPORT_FILE" | cut -f1)\"}" \
        2>/dev/null || echo "⚠️ Slack 알림 실패"
fi