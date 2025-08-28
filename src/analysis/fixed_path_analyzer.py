#!/usr/bin/env python3

"""
고정된 경로 분석 데이터 생성기
일관된 기준을 가진 테스트 데이터를 제공합니다.
"""

import ipaddress
from datetime import datetime


class FixedPathAnalyzer:
    """일관된 경로 분석 데이터 생성"""

    def __init__(self):
        # 네트워크 구성 정의 (테스트용 고정 값)
        self.network_zones = {
            "internal": "192.168.0.0/16",
            "dmz": "172.16.0.0/12",
            "external": "0.0.0.0/0",
            "guest": "10.10.0.0/16",
            "management": "192.168.100.0/24",
        }

        # 방화벽 정책 정의 (일관된 규칙)
        self.firewall_policies = {
            # Internal to DMZ
            "POL-001": {
                "name": "Internal_to_DMZ_Web",
                "source_zone": "internal",
                "dest_zone": "dmz",
                "source_net": "192.168.0.0/16",
                "dest_net": "172.16.10.0/24",
                "service": ["HTTP", "HTTPS"],
                "port": [80, 443],
                "action": "allow",
                "description": "내부에서 DMZ 웹서버 접근 허용",
            },
            "POL-002": {
                "name": "Internal_to_DMZ_DB",
                "source_zone": "internal",
                "dest_zone": "dmz",
                "source_net": "192.168.10.0/24",
                "dest_net": "172.16.20.0/24",
                "service": ["MySQL", "PostgreSQL"],
                "port": [3306, 5432],
                "action": "allow",
                "description": "특정 내부 서버에서 DMZ DB 접근 허용",
            },
            "POL-003": {
                "name": "DMZ_to_External",
                "source_zone": "dmz",
                "dest_zone": "external",
                "source_net": "172.16.0.0/16",
                "dest_net": "0.0.0.0/0",
                "service": ["HTTP", "HTTPS", "DNS"],
                "port": [80, 443, 53],
                "action": "allow",
                "description": "DMZ에서 외부 인터넷 접근 허용",
            },
            "POL-004": {
                "name": "External_to_DMZ_Web",
                "source_zone": "external",
                "dest_zone": "dmz",
                "source_net": "0.0.0.0/0",
                "dest_net": "172.16.10.100/32",
                "service": ["HTTPS"],
                "port": [443],
                "action": "allow",
                "description": "외부에서 공개 웹서버 접근 허용",
            },
            "POL-005": {
                "name": "Internal_to_External",
                "source_zone": "internal",
                "dest_zone": "external",
                "source_net": "192.168.0.0/16",
                "dest_net": "0.0.0.0/0",
                "service": ["HTTP", "HTTPS", "DNS"],
                "port": [80, 443, 53],
                "action": "allow",
                "description": "내부에서 인터넷 접근 허용",
            },
            "POL-006": {
                "name": "Guest_Isolation",
                "source_zone": "guest",
                "dest_zone": "internal",
                "source_net": "10.10.0.0/16",
                "dest_net": "192.168.0.0/16",
                "service": ["ALL"],
                "port": ["ALL"],
                "action": "deny",
                "description": "Guest 네트워크에서 내부망 접근 차단",
            },
            "POL-007": {
                "name": "Management_Access",
                "source_zone": "management",
                "dest_zone": "internal",
                "source_net": "10.100.0.0/24",
                "dest_net": "192.168.0.0/16",
                "service": ["SSH", "HTTPS", "SNMP"],
                "port": [22, 443, 161],
                "action": "allow",
                "description": "관리 네트워크에서 내부 장비 관리",
            },
            "POL-999": {
                "name": "Deny_All",
                "source_zone": "any",
                "dest_zone": "any",
                "source_net": "0.0.0.0/0",
                "dest_net": "0.0.0.0/0",
                "service": ["ALL"],
                "port": ["ALL"],
                "action": "deny",
                "description": "기본 차단 정책",
            },
        }

        # 라우팅 테이블 정의
        self.routing_table = {
            "192.168.0.0/16": {
                "gateway": "192.168.1.1",
                "interface": "internal",
                "metric": 1,
            },
            "172.16.0.0/16": {
                "gateway": "172.16.1.1",
                "interface": "dmz",
                "metric": 1,
            },
            "10.10.0.0/16": {
                "gateway": "10.10.1.1",
                "interface": "guest",
                "metric": 1,
            },
            "10.100.0.0/24": {
                "gateway": "10.100.0.1",
                "interface": "management",
                "metric": 1,
            },
            "0.0.0.0/0": {
                "gateway": "203.0.113.1",
                "interface": "external",
                "metric": 10,
            },
        }

    def get_zone_for_ip(self, ip_str):
        """IP 주소가 속한 존 확인"""
        try:
            ip = ipaddress.ip_address(ip_str)
            for zone, network in self.network_zones.items():
                if network == "0.0.0.0/0" and zone == "external":
                    # External은 다른 내부 네트워크에 속하지 않는 경우
                    continue
                if ip in ipaddress.ip_network(network):
                    return zone
            return "external"  # 기본값
        except Exception:
            return "unknown"

    def find_matching_policy(self, src_ip, dst_ip, port=None):
        """소스/목적지 IP와 포트에 매칭되는 정책 찾기"""
        src_zone = self.get_zone_for_ip(src_ip)
        dst_zone = self.get_zone_for_ip(dst_ip)

        # 정책을 순서대로 확인
        for policy_id, policy in self.firewall_policies.items():
            # 존 매칭
            if policy["source_zone"] != "any" and policy["source_zone"] != src_zone:
                continue
            if policy["dest_zone"] != "any" and policy["dest_zone"] != dst_zone:
                continue

            # IP 매칭
            try:
                src_addr = ipaddress.ip_address(src_ip)
                dst_addr = ipaddress.ip_address(dst_ip)

                if policy["source_net"] != "0.0.0.0/0":
                    if src_addr not in ipaddress.ip_network(policy["source_net"]):
                        continue

                if policy["dest_net"] != "0.0.0.0/0":
                    if dst_addr not in ipaddress.ip_network(policy["dest_net"]):
                        continue
            except Exception:
                continue

            # 포트 매칭
            if port and "ALL" not in policy["port"]:
                if port not in policy["port"]:
                    continue

            # 매칭된 정책 반환
            return policy_id, policy

        # 기본 차단 정책
        return "POL-999", self.firewall_policies["POL-999"]

    def get_routing_path(self, src_ip, dst_ip):
        """라우팅 경로 결정"""
        path = []

        # 소스에서 목적지까지의 경로 결정
        src_zone = self.get_zone_for_ip(src_ip)
        dst_zone = self.get_zone_for_ip(dst_ip)

        # 같은 존이면 직접 통신
        if src_zone == dst_zone:
            path.append(
                {
                    "hop": 1,
                    "from": src_ip,
                    "to": dst_ip,
                    "gateway": "Direct",
                    "interface": src_zone,
                }
            )
        else:
            # 다른 존이면 라우터 경유
            # 1. 소스 -> 게이트웨이
            src_route = (
                self.routing_table.get(f"{src_ip}/32")
                or self.routing_table.get("192.168.0.0/16")
                or self.routing_table.get("0.0.0.0/0")
            )

            path.append(
                {
                    "hop": 1,
                    "from": src_ip,
                    "to": src_route["gateway"],
                    "gateway": src_route["gateway"],
                    "interface": src_route["interface"],
                }
            )

            # 2. 게이트웨이 -> 목적지
            dst_route = None
            for network, route in self.routing_table.items():
                try:
                    if ipaddress.ip_address(dst_ip) in ipaddress.ip_network(network):
                        dst_route = route
                        break
                except Exception:
                    continue

            if not dst_route:
                dst_route = self.routing_table.get("0.0.0.0/0")

            path.append(
                {
                    "hop": 2,
                    "from": src_route["gateway"],
                    "to": dst_ip,
                    "gateway": dst_route["gateway"],
                    "interface": dst_route["interface"],
                }
            )

        return path

    def analyze_path(self, src_ip, dst_ip, port=None, protocol="tcp"):
        if port is None:
            port = 80  # Default HTTP port
        """경로 분석 수행"""
        # 라우팅 경로 확인
        routing_path = self.get_routing_path(src_ip, dst_ip)

        # 방화벽 정책 확인
        policy_id, policy = self.find_matching_policy(src_ip, dst_ip, port)

        # 경로 분석 결과 생성
        path = []
        for i, route in enumerate(routing_path):
            hop = {
                "hop_number": i + 1,
                "firewall_name": f"FW-{i + 1:02d}",
                "src_ip": route["from"],
                "dst_ip": route["to"],
                "policy_id": (policy_id if i == 0 else None),  # 첫 번째 홉에서만 정책 적용
                "policy": policy if i == 0 else None,
                "action": policy["action"] if i == 0 else "forward",
                "interface_in": route["interface"],
                "interface_out": route["interface"],
                "latency": 0.5 + (i * 0.3),  # 홉당 0.3ms 추가
                "gateway": route["gateway"],
            }
            path.append(hop)

        # 최종 결과
        allowed = policy["action"] == "allow"
        result = {
            "path": path,
            "allowed": allowed,
            "final_destination": dst_ip,
            "blocked_by": (
                {
                    "firewall": "FW-01",
                    "policy_id": policy_id,
                    "policy_name": policy["name"],
                    "reason": policy["description"],
                }
                if not allowed
                else None
            ),
            "analysis_summary": {
                "source_ip": src_ip,
                "source_zone": self.get_zone_for_ip(src_ip),
                "destination_ip": dst_ip,
                "destination_zone": self.get_zone_for_ip(dst_ip),
                "total_hops": len(path),
                "total_latency": sum(h["latency"] for h in path),
                "protocol": protocol.upper(),
                "port": port,
                "matched_policy": policy_id,
                "policy_action": policy["action"],
                "policy_description": policy["description"],
                "analysis_time": datetime.now().isoformat(),
            },
            "recommendations": self.generate_recommendations(src_ip, dst_ip, port, allowed, policy),
        }

        return result

    def generate_recommendations(self, src_ip, dst_ip, port, allowed, policy):
        """분석 결과에 대한 권장사항 생성"""
        recommendations = []

        if not allowed:
            recommendations.append(
                {
                    "type": "error",
                    "message": f"트래픽이 정책 '{policy['name']}'에 의해 차단됩니다.",
                    "action": (
                        f"필요한 경우 {self.get_zone_for_ip(src_ip)}에서 "
                        f"{self.get_zone_for_ip(dst_ip)}로의 접근을 허용하는 정책을 추가하세요."
                    ),
                }
            )

            # 유사한 허용 정책 제안
            src_zone = self.get_zone_for_ip(src_ip)
            dst_zone = self.get_zone_for_ip(dst_ip)
            for pol_id, pol in self.firewall_policies.items():
                if pol["source_zone"] == src_zone and pol["dest_zone"] == dst_zone and pol["action"] == "allow":
                    recommendations.append(
                        {
                            "type": "info",
                            "message": f"유사한 허용 정책: {pol['name']}",
                            "action": "이 정책을 참고하여 새 규칙을 생성할 수 있습니다.",
                        }
                    )
                    break
        else:
            recommendations.append(
                {
                    "type": "success",
                    "message": f"트래픽이 정책 '{policy['name']}'에 의해 허용됩니다.",
                    "action": None,
                }
            )

            # 보안 권장사항
            if port in [22, 3389, 23]:  # SSH, RDP, Telnet
                recommendations.append(
                    {
                        "type": "warning",
                        "message": "관리 포트에 대한 접근이 허용되어 있습니다.",
                        "action": "MFA(다중 인증) 적용 및 접근 IP 제한을 권장합니다.",
                    }
                )

            if self.get_zone_for_ip(src_ip) == "external":
                recommendations.append(
                    {
                        "type": "warning",
                        "message": "외부에서의 접근이 허용되어 있습니다.",
                        "action": "IPS/IDS 정책 적용 및 로깅 강화를 권장합니다.",
                    }
                )

        return recommendations


# 싱글톤 인스턴스
fixed_path_analyzer = FixedPathAnalyzer()
