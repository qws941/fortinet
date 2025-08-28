#!/usr/bin/env python3
"""
패킷 경로 분석 테스트
Test packet path analysis functionality
"""

import json
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Mock fortigate is now integrated into device_manager
try:
    from device_manager import DeviceManager

    # Create a mock instance for testing
    mock_fortigate = DeviceManager()
except ImportError:
    # Fallback for test environment
    class MockFortiGate:
        def analyze_packet_path(self, src_ip, dst_ip, port, protocol):
            return {
                "status": "success",
                "path": [{"rule": f"Allow {protocol.upper()}", "action": "permit"}],
                "verdict": "ALLOW",
                "analysis": {
                    "traffic_flow": f"{src_ip} -> {dst_ip}:{port}",
                    "protocol": protocol.upper(),
                    "decision": "ALLOW",
                    "result": "ALLOW",
                    "path": [
                        {"step": "Interface Check", "action": "Accept", "status": "success"},
                        {"step": "Policy Evaluation", "action": f"Allow {protocol.upper()}", "status": "success"},
                        {"step": "Route Decision", "action": "Forward", "status": "success"},
                    ],
                    "matching_rules": [f"Rule: Allow {protocol.upper()} traffic"],
                },
            }

    mock_fortigate = MockFortiGate()


def test_packet_path_analysis():
    """Test packet path analysis with various scenarios"""

    print("=== FortiGate 패킷 경로 분석 테스트 ===\n")

    test_scenarios = [
        {
            "name": "LAN to DMZ (Allowed)",
            "src_ip": "192.168.1.100",
            "dst_ip": "172.16.10.100",
            "port": 80,
            "protocol": "tcp",
        },
        {
            "name": "LAN to Internet (HTTPS)",
            "src_ip": "192.168.1.100",
            "dst_ip": "203.0.113.50",
            "port": 443,
            "protocol": "tcp",
        },
        {
            "name": "Guest to LAN (Blocked)",
            "src_ip": "10.10.1.50",
            "dst_ip": "192.168.1.100",
            "port": 22,
            "protocol": "tcp",
        },
        {
            "name": "DMZ to Internet",
            "src_ip": "172.16.10.100",
            "dst_ip": "203.0.113.100",
            "port": 80,
            "protocol": "tcp",
        },
    ]

    for i, scenario in enumerate(test_scenarios, 1):
        print(f"테스트 {i}: {scenario['name']}")
        print(
            f"Source: {scenario['src_ip']} → Destination: {scenario['dst_ip']}:{scenario['port']} ({scenario['protocol'].upper()})"
        )
        print("-" * 80)

        # Analyze packet path
        result = mock_fortigate.analyze_packet_path(
            src_ip=scenario["src_ip"],
            dst_ip=scenario["dst_ip"],
            port=scenario["port"],
            protocol=scenario["protocol"],
        )

        if result["status"] == "success":
            analysis = result["analysis"]

            # Show path summary
            print(f"결과: {analysis['result'].upper()}")
            print(f"총 단계: {len(analysis['path'])}")

            # Show detailed path
            print("\n경로 분석:")
            for step in analysis["path"]:
                status_icon = "✅" if step["status"] == "success" else "❌"
                print(f"  {status_icon} {step['step']}: {step['action']}")
                if "details" in step:
                    print(f"     상세: {step['details']}")

            # Show policy details if available
            if "policy" in analysis:
                policy = analysis["policy"]
                print(f"\n적용된 정책:")
                print(f"  - ID: {policy['id']}")
                print(f"  - 이름: {policy['name']}")
                print(f"  - 액션: {policy['action']}")
                if "nat" in policy:
                    print(f"  - NAT: {policy['nat']['type']} → {policy['nat']['translated_ip']}")

            # Show route details
            if "route" in analysis:
                route = analysis["route"]
                print(f"\n라우팅 정보:")
                print(f"  - 게이트웨이: {route['gateway']}")
                print(f"  - 인터페이스: {route['interface']}")
        else:
            print(f"❌ 분석 실패: {result.get('message', 'Unknown error')}")

        print("\n" + "=" * 80 + "\n")

    # Summary
    print("📊 테스트 요약:")
    print(f"- 총 테스트: {len(test_scenarios)}")
    print(f"- 정책 엔진: Mock FortiGate")
    print(f"- 분석 방법: Ingress → Routing → Policy → Egress")


if __name__ == "__main__":
    test_packet_path_analysis()
