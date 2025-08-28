#!/bin/bash
# FortiGate Nextrade 자동 백업 스크립트
# 매일 실행되는 완전 백업 솔루션

set -euo pipefail

# 설정
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup/fortinet"
LOG_FILE="/var/log/fortinet-backup.log"
NAMESPACE="fortinet"
APP_NAME="fortinet"
RETENTION_DAYS=7

# 로깅 함수
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# 백업 디렉토리 생성
mkdir -p "$BACKUP_DIR"

log "🚀 FortiGate Nextrade 백업 시작: $DATE"

# 1. K8s 리소스 백업
log "📦 Kubernetes 리소스 백업 중..."
kubectl get all -n "$NAMESPACE" -l app="$APP_NAME" -o yaml > "${BACKUP_DIR}/k8s-resources_${DATE}.yaml" 2>/dev/null || {
    log "❌ K8s 리소스 백업 실패"
    exit 1
}

# 2. ConfigMaps & Secrets 백업
log "🔐 ConfigMaps & Secrets 백업 중..."
kubectl get configmaps,secrets -n "$NAMESPACE" -o yaml > "${BACKUP_DIR}/k8s-configs_${DATE}.yaml" 2>/dev/null || {
    log "⚠️ ConfigMaps/Secrets 백업 실패 (무시)"
}

# 3. 애플리케이션 설정 백업
log "⚙️ 애플리케이션 설정 백업 중..."
tar -czf "${BACKUP_DIR}/app-config_${DATE}.tar.gz" \
    k8s/ argocd-apps/ .github/ data/ 2>/dev/null || {
    log "⚠️ 애플리케이션 설정 백업 부분 실패"
}

# 4. 로그 백업 (최근 24시간)
log "📋 애플리케이션 로그 백업 중..."
kubectl logs -n "$NAMESPACE" -l app="$APP_NAME" --since=24h > "${BACKUP_DIR}/app-logs_${DATE}.log" 2>/dev/null || {
    log "⚠️ 로그 백업 실패 (무시)"
}

# 5. 메타데이터 생성
log "📝 백업 메타데이터 생성 중..."
cat > "${BACKUP_DIR}/backup-metadata_${DATE}.json" << EOF
{
  "timestamp": "$DATE",
  "namespace": "$NAMESPACE",
  "app": "$APP_NAME",
  "backup_items": [
    "kubernetes_resources",
    "configs_and_secrets", 
    "application_config",
    "application_logs"
  ],
  "retention_days": $RETENTION_DAYS,
  "cluster_info": {
    "context": "$(kubectl config current-context)",
    "server": "$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')"
  },
  "file_sizes": {
    "k8s_resources": "$(du -sh "${BACKUP_DIR}/k8s-resources_${DATE}.yaml" | cut -f1)",
    "k8s_configs": "$(du -sh "${BACKUP_DIR}/k8s-configs_${DATE}.yaml" | cut -f1)",
    "app_config": "$(du -sh "${BACKUP_DIR}/app-config_${DATE}.tar.gz" | cut -f1)",
    "app_logs": "$(du -sh "${BACKUP_DIR}/app-logs_${DATE}.log" | cut -f1)"
  }
}
EOF

# 6. 백업 무결성 검증
log "🔍 백업 무결성 검증 중..."
BACKUP_FILES=(
    "${BACKUP_DIR}/k8s-resources_${DATE}.yaml"
    "${BACKUP_DIR}/k8s-configs_${DATE}.yaml"
    "${BACKUP_DIR}/app-config_${DATE}.tar.gz"
    "${BACKUP_DIR}/app-logs_${DATE}.log"
    "${BACKUP_DIR}/backup-metadata_${DATE}.json"
)

VALID_FILES=0
for file in "${BACKUP_FILES[@]}"; do
    if [[ -f "$file" && -s "$file" ]]; then
        VALID_FILES=$((VALID_FILES + 1))
        log "✅ 검증 통과: $(basename "$file")"
    else
        log "❌ 검증 실패: $(basename "$file")"
    fi
done

# 7. 이전 백업 정리 (보존 기간 초과)
log "🧹 이전 백업 정리 중 (${RETENTION_DAYS}일 이전)..."
find "$BACKUP_DIR" -name "*.yaml" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true
find "$BACKUP_DIR" -name "*.log" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true
find "$BACKUP_DIR" -name "*.json" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true

# 8. 백업 완료 알림
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
log "✅ 백업 완료: $VALID_FILES/5 파일, 총 크기: $TOTAL_SIZE"

# Slack 알림 (선택적)
if [[ -n "${SLACK_WEBHOOK:-}" ]]; then
    curl -X POST "$SLACK_WEBHOOK" \
        -H 'Content-type: application/json' \
        --data "{\"text\":\"📦 FortiGate Nextrade 백업 완료\\n• 날짜: $DATE\\n• 파일: $VALID_FILES/5개\\n• 크기: $TOTAL_SIZE\"}" \
        2>/dev/null || log "⚠️ Slack 알림 실패"
fi

log "🎉 백업 프로세스 완료"
exit 0