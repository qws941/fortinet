#!/usr/bin/env python3
"""
Standalone packet path analysis demonstration
패킷 경로 분석 독립 실행 데모
"""

import json
from datetime import datetime


class PacketPathAnalyzer:
    """Simple packet path analyzer"""

    def __init__(self):
        # Define network topology
        self.networks = {
            "LAN": {"subnet": "192.168.1.0/24", "interface": "port1"},
            "DMZ": {"subnet": "172.16.10.0/24", "interface": "port2"},
            "GUEST": {"subnet": "10.10.1.0/24", "interface": "port3"},
            "WAN": {"subnet": "0.0.0.0/0", "interface": "port4"},
        }

        # Define firewall policies
        self.policies = [
            {
                "id": 1,
                "name": "LAN-to-Internet",
                "src": "LAN",
                "dst": "WAN",
                "service": ["HTTP", "HTTPS", "DNS"],
                "action": "ACCEPT",
                "nat": True,
            },
            {
                "id": 2,
                "name": "LAN-to-DMZ",
                "src": "LAN",
                "dst": "DMZ",
                "service": ["HTTP", "HTTPS", "SSH"],
                "action": "ACCEPT",
                "nat": False,
            },
            {
                "id": 3,
                "name": "DMZ-to-Internet",
                "src": "DMZ",
                "dst": "WAN",
                "service": ["HTTP", "HTTPS"],
                "action": "ACCEPT",
                "nat": True,
            },
            {
                "id": 4,
                "name": "Guest-to-Internet",
                "src": "GUEST",
                "dst": "WAN",
                "service": ["HTTP", "HTTPS"],
                "action": "ACCEPT",
                "nat": True,
            },
            {
                "id": 99,
                "name": "Deny-All",
                "src": "any",
                "dst": "any",
                "service": "any",
                "action": "DENY",
                "nat": False,
            },
        ]

        # Service definitions
        self.services = {"HTTP": 80, "HTTPS": 443, "SSH": 22, "DNS": 53}

    def identify_network(self, ip):
        """Identify which network an IP belongs to"""
        if ip.startswith("192.168.1."):
            return "LAN"
        elif ip.startswith("172.16.10."):
            return "DMZ"
        elif ip.startswith("10.10.1."):
            return "GUEST"
        else:
            return "WAN"

    def find_matching_policy(self, src_net, dst_net, port):
        """Find the first matching firewall policy"""
        service_name = None
        for svc, svc_port in self.services.items():
            if svc_port == port:
                service_name = svc
                break

        for policy in self.policies:
            # Check source network
            if policy["src"] != "any" and policy["src"] != src_net:
                continue

            # Check destination network
            if policy["dst"] != "any" and policy["dst"] != dst_net:
                continue

            # Check service
            if policy["service"] != "any":
                if service_name and service_name in policy["service"]:
                    return policy
                elif not service_name and port not in [self.services[s] for s in policy["service"]]:
                    continue

            return policy

        return None

    def analyze_packet_path(self, src_ip, dst_ip, port, protocol="tcp"):
        """Analyze the path a packet would take through the firewall"""

        # Step 1: Ingress Interface Determination
        src_net = self.identify_network(src_ip)
        ingress_interface = self.networks[src_net]["interface"]

        # Step 2: Route Lookup
        dst_net = self.identify_network(dst_ip)
        egress_interface = self.networks[dst_net]["interface"]

        # Step 3: Policy Lookup
        policy = self.find_matching_policy(src_net, dst_net, port)

        # Build analysis result
        path = []

        # Ingress step
        path.append(
            {
                "step": "Ingress Interface",
                "action": f"Packet received on {ingress_interface}",
                "details": f'Source network: {src_net} ({self.networks[src_net]["subnet"]})',
                "status": "success",
            }
        )

        # Routing step
        path.append(
            {
                "step": "Route Lookup",
                "action": f"Route found to {dst_net}",
                "details": f"Next-hop interface: {egress_interface}",
                "status": "success",
            }
        )

        # Policy step
        if policy:
            path.append(
                {
                    "step": "Policy Match",
                    "action": f'Policy #{policy["id"]} - {policy["name"]}',
                    "details": f'Action: {policy["action"]}',
                    "status": "success" if policy["action"] == "ACCEPT" else "blocked",
                }
            )

            # NAT step if applicable
            if policy["action"] == "ACCEPT" and policy.get("nat"):
                path.append(
                    {
                        "step": "NAT Processing",
                        "action": "Source NAT applied",
                        "details": f"Original: {src_ip} → Translated: {egress_interface} IP",
                        "status": "success",
                    }
                )
        else:
            path.append(
                {
                    "step": "Policy Match",
                    "action": "No matching policy found",
                    "details": "Default action: DENY",
                    "status": "blocked",
                }
            )

        # Egress step
        if policy and policy["action"] == "ACCEPT":
            path.append(
                {
                    "step": "Egress Interface",
                    "action": f"Packet forwarded via {egress_interface}",
                    "details": f"Destination: {dst_ip}:{port}",
                    "status": "success",
                }
            )
            result = "allowed"
        else:
            result = "blocked"

        return {
            "timestamp": datetime.now().isoformat(),
            "result": result,
            "path": path,
            "summary": {
                "src": f"{src_ip} ({src_net})",
                "dst": f"{dst_ip}:{port} ({dst_net})",
                "protocol": protocol.upper(),
                "policy": policy["name"] if policy else "No match",
                "action": policy["action"] if policy else "DENY",
            },
        }


def main():
    """Run packet path analysis demonstration"""
    analyzer = PacketPathAnalyzer()

    print("🔍 FortiGate 패킷 경로 분석 (Packet Path Analysis)")
    print("=" * 80)

    # Test scenarios
    test_cases = [
        {
            "name": "LAN → DMZ Web Server",
            "src_ip": "192.168.1.100",
            "dst_ip": "172.16.10.50",
            "port": 80,
            "protocol": "tcp",
        },
        {
            "name": "LAN → Internet HTTPS",
            "src_ip": "192.168.1.200",
            "dst_ip": "8.8.8.8",
            "port": 443,
            "protocol": "tcp",
        },
        {
            "name": "Guest → LAN (Blocked)",
            "src_ip": "10.10.1.50",
            "dst_ip": "192.168.1.10",
            "port": 22,
            "protocol": "tcp",
        },
        {
            "name": "DMZ → Internet",
            "src_ip": "172.16.10.100",
            "dst_ip": "1.1.1.1",
            "port": 443,
            "protocol": "tcp",
        },
    ]

    for i, test in enumerate(test_cases, 1):
        print(f"\n📦 테스트 케이스 {i}: {test['name']}")
        print(f"   Source: {test['src_ip']} → Destination: {test['dst_ip']}:{test['port']}")
        print("-" * 80)

        result = analyzer.analyze_packet_path(test["src_ip"], test["dst_ip"], test["port"], test["protocol"])

        # Display path
        print("📍 경로 분석:")
        for j, step in enumerate(result["path"], 1):
            icon = "✅" if step["status"] == "success" else "❌"
            print(f"   {j}. {icon} {step['step']}")
            print(f"      → {step['action']}")
            if "details" in step:
                print(f"      ℹ️  {step['details']}")

        # Display result
        print(f"\n📊 결과: **{result['result'].upper()}**")
        print(f"   정책: {result['summary']['policy']}")
        print(f"   액션: {result['summary']['action']}")

    print("\n" + "=" * 80)
    print("✅ 패킷 경로 분석 완료!")
    print("\n주요 기능:")
    print("- Ingress interface determination")
    print("- Routing table lookup")
    print("- Policy matching and enforcement")
    print("- NAT processing")
    print("- Egress interface forwarding")


if __name__ == "__main__":
    main()
