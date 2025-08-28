#!/bin/bash

# External-DNS 상태 확인 스크립트

echo "🔍 External-DNS 상태 확인"
echo "========================"

# 1. Pod 상태
echo -e "\n1️⃣ Pod 상태:"
kubectl get pods -n external-dns

# 2. 로그 확인
echo -e "\n2️⃣ 최근 로그:"
kubectl logs -n external-dns -l app.kubernetes.io/name=external-dns --tail=20

# 3. 관리 중인 DNS 레코드
echo -e "\n3️⃣ 관리 중인 DNS 레코드:"
kubectl logs -n external-dns -l app.kubernetes.io/name=external-dns | grep -E "CREATE|UPDATE|DELETE" | tail -10

# 4. 현재 Ingress의 External-DNS 설정
echo -e "\n4️⃣ Ingress External-DNS 설정:"
kubectl get ingress -A -o json | jq -r '.items[] | select(.metadata.annotations."external-dns.alpha.kubernetes.io/hostname" != null) | "\(.metadata.namespace)/\(.metadata.name): \(.metadata.annotations."external-dns.alpha.kubernetes.io/hostname")"'

# 5. DNS 조회 테스트
echo -e "\n5️⃣ DNS 조회 테스트:"
for domain in fortinet.jclee.me app.jclee.me; do
  echo -n "$domain: "
  dig +short $domain @8.8.8.8 || echo "조회 실패"
done

# 6. External-DNS 메트릭
echo -e "\n6️⃣ 메트릭 (Prometheus):"
kubectl port-forward -n external-dns svc/external-dns-metrics 9187:9187 &
PF_PID=$!
sleep 2
curl -s http://localhost:9187/metrics | grep -E "external_dns_" | head -10
kill $PF_PID 2>/dev/null