#!/usr/bin/env python3
"""
Ingress Progressing 상태 원인 분석 스크립트
"""

import json
import os
from datetime import datetime

import requests

# ArgoCD 설정
ARGOCD_SERVER = "https://argo.jclee.me"
ARGOCD_TOKEN = os.getenv("ARGOCD_AUTH_TOKEN", "")


def check_ingress_status():
    """Ingress 상태 상세 확인"""

    if not ARGOCD_TOKEN:
        # GitHub Secrets에서 토큰 사용
        print("❌ ARGOCD_AUTH_TOKEN이 설정되지 않았습니다!")
        return

    session = requests.Session()
    session.verify = False

    headers = {
        "Authorization": f"Bearer {ARGOCD_TOKEN}",
        "Content-Type": "application/json",
    }

    print("🔍 Ingress 상태 분석 시작...")
    print("=" * 50)

    # 1. 애플리케이션 상태 확인
    try:
        response = session.get(
            f"{ARGOCD_SERVER}/api/v1/applications/fortinet", headers=headers
        )

        if response.status_code == 200:
            app = response.json()

            # Ingress 리소스 찾기
            resources = app.get("status", {}).get("resources", [])
            ingress_resources = [r for r in resources if r.get("kind") == "Ingress"]

            for ingress in ingress_resources:
                print(f"\n📋 Ingress: {ingress.get('name')}")
                print(f"   네임스페이스: {ingress.get('namespace')}")
                print(f"   상태: {ingress.get('status')}")
                print(f"   Health: {ingress.get('health', {}).get('status')}")

                # 상세 메시지 확인
                health_msg = ingress.get("health", {}).get("message", "")
                if health_msg:
                    print(f"   메시지: {health_msg}")

                # 추가 정보
                print(f"   버전: {ingress.get('version')}")
                print(f"   그룹: {ingress.get('group')}")

    except Exception as e:
        print(f"❌ 오류: {e}")

    # 2. 클러스터 이벤트 확인 (ArgoCD API로는 제한적)
    print("\n📊 추가 분석 필요:")
    print("1. kubectl describe ingress fortinet-ingress -n fortinet")
    print("2. kubectl get events -n fortinet | grep ingress")
    print("3. kubectl logs -n ingress-nginx deployment/ingress-nginx-controller")

    # 3. 일반적인 Ingress Progressing 원인들
    print("\n💡 일반적인 원인들:")
    print("- LoadBalancer IP 할당 대기")
    print("- NGINX Ingress Controller 준비 중")
    print("- Backend 서비스 연결 확인 중")
    print("- DNS 전파 대기")
    print("- Certificate Manager (TLS 사용 시)")

    # 4. ArgoCD Health 판단 기준
    print("\n🔧 ArgoCD Ingress Health 판단 기준:")
    print("- LoadBalancer 타입: IP 할당 확인")
    print("- Rules 존재 여부")
    print("- Backend 서비스 존재 여부")
    print("- TLS 설정 시 인증서 상태")


if __name__ == "__main__":
    import urllib3

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    check_ingress_status()
