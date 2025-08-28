#!/bin/bash

echo "🔍 Ingress 디버깅 스크립트"
echo "========================="

# 1. DNS 확인
echo -e "\n1️⃣ DNS 확인:"
echo "- fortinet.jclee.me: $(dig fortinet.jclee.me +short)"

# 2. NodePort 접근 테스트
echo -e "\n2️⃣ NodePort 테스트 (30777):"
curl -s http://192.168.50.110:30777/api/health | jq . || echo "실패"

# 3. Ingress 접근 테스트
echo -e "\n3️⃣ Ingress 테스트 (80):"
curl -s -H "Host: fortinet.jclee.me" http://192.168.50.110:80/api/health -w "\nHTTP Status: %{http_code}\n" || echo "실패"

# 4. HTTPS 테스트
echo -e "\n4️⃣ HTTPS 테스트 (443):"
curl -s -k https://fortinet.jclee.me/api/health -m 5 -w "\nHTTP Status: %{http_code}\n" || echo "실패"

# 5. ArgoCD 상태
echo -e "\n5️⃣ ArgoCD 상태:"
argocd app get fortinet --grpc-web | grep -E "(Health Status:|Sync Status:|fortinet-ingress)"

# 6. 가능한 원인들
echo -e "\n💡 가능한 원인들:"
echo "- NGINX Ingress Controller가 fortinet namespace의 Ingress를 감지하지 못함"
echo "- IngressClass 설정 문제"
echo "- Service와 Ingress 간의 연결 문제"
echo "- NGINX Ingress Controller 자체의 설정 문제"