#!/usr/bin/env python3

"""
정책 매핑 모듈
ITSM 요청을 실제 FortiGate 방화벽 정책으로 매핑
"""

import ipaddress
import re
from datetime import datetime
from typing import Any, Dict, List

from utils.unified_logger import get_logger

logger = get_logger(__name__)


class PolicyMapper:
    """ITSM 요청을 FortiGate 정책으로 매핑하는 클래스"""

    def __init__(self):
        """정책 매퍼 초기화"""

        # 네트워크 존 정의
        self.network_zones = {
            "internal": {
                "name": "내부망",
                "networks": ["192.168.0.0/16", "10.0.0.0/8"],
                "fortigate_zone": "internal",
                "security_level": "high",
            },
            "dmz": {
                "name": "DMZ",
                "networks": ["172.16.0.0/16", "172.17.0.0/16"],
                "fortigate_zone": "dmz",
                "security_level": "medium",
            },
            "external": {
                "name": "외부망",
                "networks": ["0.0.0.0/0"],
                "fortigate_zone": "wan",
                "security_level": "low",
            },
            "branch": {
                "name": "지사",
                "networks": ["10.10.0.0/16"],
                "fortigate_zone": "branch",
                "security_level": "medium",
            },
            "management": {
                "name": "관리망",
                "networks": ["172.28.0.0/16"],
                "fortigate_zone": "mgmt",
                "security_level": "high",
            },
        }

        # 서비스 포트 매핑
        self.service_mapping = {
            80: {"name": "HTTP", "protocol": "TCP"},
            443: {"name": "HTTPS", "protocol": "TCP"},
            22: {"name": "SSH", "protocol": "TCP"},
            21: {"name": "FTP", "protocol": "TCP"},
            25: {"name": "SMTP", "protocol": "TCP"},
            53: {"name": "DNS", "protocol": "UDP"},
            110: {"name": "POP3", "protocol": "TCP"},
            143: {"name": "IMAP", "protocol": "TCP"},
            993: {"name": "IMAPS", "protocol": "TCP"},
            995: {"name": "POP3S", "protocol": "TCP"},
            3306: {"name": "MySQL", "protocol": "TCP"},
            5432: {"name": "PostgreSQL", "protocol": "TCP"},
            1521: {"name": "Oracle", "protocol": "TCP"},
            3389: {"name": "RDP", "protocol": "TCP"},
            389: {"name": "LDAP", "protocol": "TCP"},
            636: {"name": "LDAPS", "protocol": "TCP"},
        }

        # FortiGate 방화벽 정보
        self.fortigate_devices = {
            "FW-01": {
                "name": "FortiGate-HQ-01",
                "ip": "192.168.1.1",
                "location": "본사",
                "zones": ["internal", "dmz", "wan"],
                "management_ip": "172.28.174.31",
            },
            "FW-02": {
                "name": "FortiGate-DMZ-01",
                "ip": "172.16.1.1",
                "location": "DMZ",
                "zones": ["dmz", "wan"],
                "management_ip": "172.28.174.32",
            },
            "FW-03": {
                "name": "FortiGate-WAN-01",
                "ip": "203.0.113.1",
                "location": "외부연결",
                "zones": ["wan", "external"],
                "management_ip": "172.28.174.33",
            },
            "FW-04": {
                "name": "FortiGate-Branch-01",
                "ip": "10.10.1.1",
                "location": "지사",
                "zones": ["branch", "internal"],
                "management_ip": "172.28.174.34",
            },
        }

    def map_itsm_to_fortigate_policy(self, itsm_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        ITSM 요청을 FortiGate 정책으로 매핑

        Args:
            itsm_request (Dict): ITSM 요청 데이터

        Returns:
            Dict: FortiGate 정책 매핑 결과
        """
        try:
            form_data = itsm_request.get("form_data", {})

            # 기본 정보 추출
            source_ip = form_data.get("source_ip", "")
            destination_ip = form_data.get("destination_ip", "")
            port = form_data.get("port", "")
            protocol = form_data.get("protocol", "TCP").upper()
            action = form_data.get("action", "ALLOW").upper()

            # IP 주소 정규화
            source_networks = self._normalize_ip_address(source_ip)
            destination_networks = self._normalize_ip_address(destination_ip)

            # 네트워크 존 결정
            source_zone = self._determine_zone(source_networks[0] if source_networks else "")
            destination_zone = self._determine_zone(destination_networks[0] if destination_networks else "")

            # 적절한 FortiGate 장비 선택
            target_fortigates = self._select_target_fortigates(source_zone, destination_zone)

            # 포트 및 서비스 정보 처리
            service_info = self._process_service_info(port, protocol)

            # FortiGate 정책 생성
            fortigate_policies = []
            for fw_id in target_fortigates:
                policy = self._generate_fortigate_policy(
                    fw_id=fw_id,
                    itsm_request=itsm_request,
                    source_networks=source_networks,
                    destination_networks=destination_networks,
                    source_zone=source_zone,
                    destination_zone=destination_zone,
                    service_info=service_info,
                    action=action,
                )
                fortigate_policies.append(policy)

            # 매핑 결과 구성
            mapping_result = {
                "itsm_request_id": itsm_request.get("request_id", ""),
                "mapping_status": "success",
                "analysis": {
                    "source_zone": source_zone,
                    "destination_zone": destination_zone,
                    "traffic_flow": f"{source_zone} -> {destination_zone}",
                    "service_analysis": service_info,
                    "security_impact": self._assess_security_impact(source_zone, destination_zone, service_info),
                },
                "fortigate_policies": fortigate_policies,
                "implementation_order": self._determine_implementation_order(fortigate_policies),
                "validation_tests": self._generate_validation_tests(
                    source_networks, destination_networks, service_info
                ),
                "rollback_plan": self._generate_rollback_plan(fortigate_policies),
            }

            logger.info(f"ITSM 요청 {itsm_request.get('request_id')} 매핑 완료: {len(fortigate_policies)}개 정책 생성")
            return mapping_result

        except Exception as e:
            logger.error(f"정책 매핑 중 오류 발생: {str(e)}")
            return {
                "itsm_request_id": itsm_request.get("request_id", ""),
                "mapping_status": "error",
                "error_message": str(e),
                "fortigate_policies": [],
            }

    def _normalize_ip_address(self, ip_string: str) -> List[str]:
        """IP 주소 문자열을 정규화"""
        if not ip_string:
            return []

        # 여러 IP 주소 분리 (콤마, 세미콜론, 공백으로 구분)
        ip_list = re.split(r"[,;\s]+", ip_string.strip())
        normalized_ips = []

        for ip in ip_list:
            ip = ip.strip()
            if not ip:
                continue

            try:
                # CIDR 표기법 확인
                if "/" in ip:
                    network = ipaddress.ip_network(ip, strict=False)
                    normalized_ips.append(str(network))
                else:
                    # 단일 IP 주소
                    addr = ipaddress.ip_address(ip)
                    normalized_ips.append(f"{addr}/32")
            except ValueError:
                # IP 주소가 아닌 경우 (예: "any", "all")
                if ip.lower() in ["any", "all", "0.0.0.0"]:
                    normalized_ips.append("0.0.0.0/0")
                else:
                    logger.warning(f"유효하지 않은 IP 주소: {ip}")

        return normalized_ips

    def _determine_zone(self, ip_network: str) -> str:
        """IP 네트워크로부터 존 결정"""
        if not ip_network:
            return "unknown"

        try:
            network = ipaddress.ip_network(ip_network, strict=False)

            for zone_name, zone_info in self.network_zones.items():
                for zone_network in zone_info["networks"]:
                    zone_net = ipaddress.ip_network(zone_network, strict=False)
                    if network.subnet_of(zone_net) or network.overlaps(zone_net):
                        return zone_name

            # 매칭되는 존이 없으면 외부망으로 처리
            return "external"

        except ValueError:
            return "unknown"

    def _select_target_fortigates(self, source_zone: str, destination_zone: str) -> List[str]:
        """트래픽 플로우에 따른 대상 FortiGate 선택"""
        target_fortigates = []

        # 존 간 트래픽 플로우 분석
        if source_zone == "internal" and destination_zone == "external":
            # 내부 -> 외부: FW-01 (내부) -> FW-03 (WAN)
            target_fortigates = ["FW-01", "FW-03"]
        elif source_zone == "external" and destination_zone == "dmz":
            # 외부 -> DMZ: FW-03 (WAN) -> FW-02 (DMZ)
            target_fortigates = ["FW-03", "FW-02"]
        elif source_zone == "internal" and destination_zone == "dmz":
            # 내부 -> DMZ: FW-01
            target_fortigates = ["FW-01"]
        elif source_zone == "branch" and destination_zone == "internal":
            # 지사 -> 본사: FW-04 -> FW-01
            target_fortigates = ["FW-04", "FW-01"]
        elif source_zone == destination_zone:
            # 같은 존 내 트래픽
            zone_firewalls = [
                fw_id for fw_id, fw_info in self.fortigate_devices.items() if source_zone in fw_info["zones"]
            ]
            target_fortigates = zone_firewalls[:1]  # 첫 번째 방화벽만
        else:
            # 기본: 모든 관련 방화벽
            for fw_id, fw_info in self.fortigate_devices.items():
                if source_zone in fw_info["zones"] or destination_zone in fw_info["zones"]:
                    target_fortigates.append(fw_id)

        return target_fortigates or ["FW-01"]  # 기본값

    def _process_service_info(self, port: str, protocol: str) -> Dict[str, Any]:
        """포트 및 서비스 정보 처리"""
        service_info = {
            "ports": [],
            "protocol": protocol,
            "service_names": [],
            "custom_services": [],
        }

        if not port:
            return service_info

        # 포트 범위 및 다중 포트 처리
        port_list = re.split(r"[,;\s]+", port.strip())

        for port_item in port_list:
            port_item = port_item.strip()
            if not port_item:
                continue

            if "-" in port_item:
                # 포트 범위
                try:
                    start_port, end_port = map(int, port_item.split("-"))
                    service_info["ports"].append(f"{start_port}-{end_port}")
                    service_info["service_names"].append(f"PORT_{start_port}_{end_port}")
                except ValueError:
                    logger.warning(f"유효하지 않은 포트 범위: {port_item}")
            else:
                # 단일 포트
                try:
                    port_num = int(port_item)
                    service_info["ports"].append(str(port_num))

                    # 알려진 서비스 확인
                    if port_num in self.service_mapping:
                        service_info["service_names"].append(self.service_mapping[port_num]["name"])
                    else:
                        service_info["service_names"].append(f"PORT_{port_num}")

                except ValueError:
                    logger.warning(f"유효하지 않은 포트 번호: {port_item}")

        return service_info

    def _generate_fortigate_policy(
        self,
        fw_id: str,
        itsm_request: Dict,
        source_networks: List[str],
        destination_networks: List[str],
        source_zone: str,
        destination_zone: str,
        service_info: Dict,
        action: str,
    ) -> Dict[str, Any]:
        """FortiGate 정책 생성"""

        fw_info = self.fortigate_devices.get(fw_id, {})
        request_id = itsm_request.get("request_id", "")

        # 정책 이름 생성
        policy_name = f"ITSM_{request_id}_{source_zone}_to_{destination_zone}"

        # FortiGate 존 매핑
        src_zone = self.network_zones.get(source_zone, {}).get("fortigate_zone", source_zone)
        dst_zone = self.network_zones.get(destination_zone, {}).get("fortigate_zone", destination_zone)

        # 주소 객체 생성
        src_addresses = self._create_address_objects(source_networks, f"{policy_name}_SRC")
        dst_addresses = self._create_address_objects(destination_networks, f"{policy_name}_DST")

        # 서비스 객체 생성
        service_objects = self._create_service_objects(service_info, f"{policy_name}_SVC")

        # FortiGate CLI 명령 생성
        cli_commands = self._generate_cli_commands(
            policy_name,
            src_zone,
            dst_zone,
            src_addresses,
            dst_addresses,
            service_objects,
            action,
        )

        fortigate_policy = {
            "firewall_id": fw_id,
            "firewall_name": fw_info.get("name", ""),
            "firewall_ip": fw_info.get("management_ip", ""),
            "policy_name": policy_name,
            "policy_id": None,  # 구현 후 할당
            "configuration": {
                "source_zone": src_zone,
                "destination_zone": dst_zone,
                "source_addresses": src_addresses,
                "destination_addresses": dst_addresses,
                "services": service_objects,
                "action": action.lower(),
                "log_traffic": "all",
                "nat": self._determine_nat_requirement(source_zone, destination_zone),
            },
            "cli_commands": cli_commands,
            "implementation_status": "pending",
            "itsm_request_id": request_id,
            "created_at": datetime.now().isoformat(),
        }

        return fortigate_policy

    def _create_address_objects(self, networks: List[str], prefix: str) -> List[Dict[str, str]]:
        """주소 객체 생성"""
        address_objects = []

        for i, network in enumerate(networks):
            addr_name = f"{prefix}_{i + 1}" if len(networks) > 1 else prefix
            address_objects.append({"name": addr_name, "subnet": network, "type": "subnet"})

        return address_objects

    def _create_service_objects(self, service_info: Dict, prefix: str) -> List[Dict[str, Any]]:
        """서비스 객체 생성"""
        service_objects = []

        for i, port in enumerate(service_info["ports"]):
            svc_name = f"{prefix}_{i + 1}" if len(service_info["ports"]) > 1 else prefix
            service_objects.append(
                {
                    "name": svc_name,
                    "protocol": service_info["protocol"],
                    "port_range": port,
                    "type": "custom",
                }
            )

        return service_objects

    def _generate_cli_commands(
        self,
        policy_name: str,
        src_zone: str,
        dst_zone: str,
        src_addresses: List[Dict],
        dst_addresses: List[Dict],
        service_objects: List[Dict],
        action: str,
    ) -> List[str]:
        """FortiGate CLI 명령 생성"""
        commands = []

        # 주소 객체 생성 명령
        for addr in src_addresses + dst_addresses:
            commands.append("config firewall address")
            commands.append("    edit \"{addr['name']}\"")
            commands.append(f"        set subnet {addr['subnet']}")
            commands.append("    next")
            commands.append("end")

        # 서비스 객체 생성 명령
        for svc in service_objects:
            commands.append("config firewall service custom")
            commands.append("    edit \"{svc['name']}\"")
            commands.append(f"        set protocol {svc['protocol']}")
            if "-" in svc["port_range"]:
                start, end = svc["port_range"].split("-")
                commands.append(f"        set tcp-portrange {start}-{end}")
            else:
                commands.append(f"        set tcp-portrange {svc['port_range']}")
            commands.append("    next")
            commands.append("end")

        # 방화벽 정책 생성 명령
        commands.append("config firewall policy")
        commands.append("    edit 0")
        commands.append(f'        set name "{policy_name}"')
        commands.append(f'        set srcintf "{src_zone}"')
        commands.append(f'        set dstintf "{dst_zone}"')

        # 소스 주소
        src_addr_names = [addr["name"] for addr in src_addresses]
        commands.append(f"        set srcaddr {' '.join(src_addr_names)}")

        # 목적지 주소
        dst_addr_names = [addr["name"] for addr in dst_addresses]
        commands.append(f"        set dstaddr {' '.join(dst_addr_names)}")

        # 서비스
        svc_names = [svc["name"] for svc in service_objects]
        commands.append(f"        set service {' '.join(svc_names)}")

        # 액션
        commands.append(f"        set action {action.lower()}")
        commands.append("        set logtraffic all")
        commands.append("    next")
        commands.append("end")

        return commands

    def _determine_nat_requirement(self, source_zone: str, destination_zone: str) -> bool:
        """NAT 필요성 결정"""
        # 내부에서 외부로 나가는 트래픽은 NAT 필요
        if source_zone in ["internal", "branch"] and destination_zone == "external":
            return True
        return False

    def _assess_security_impact(self, source_zone: str, destination_zone: str, service_info: Dict) -> Dict[str, Any]:
        """보안 영향 평가"""
        impact = {
            "risk_level": "medium",
            "concerns": [],
            "recommendations": [],
        }

        # 존 기반 위험도 평가
        if destination_zone == "external":
            impact["risk_level"] = "high"
            impact["concerns"].append("외부 인터넷 접근")
            impact["recommendations"].append("웹 필터링 및 안티바이러스 적용")

        if source_zone == "external":
            impact["risk_level"] = "high"
            impact["concerns"].append("외부에서 내부 접근")
            impact["recommendations"].append("엄격한 접근 제어 및 모니터링")

        # 포트 기반 위험도 평가
        for port in service_info.get("ports", []):
            port_num = int(port.split("-")[0]) if "-" in port else int(port)
            if port_num in [22, 23, 3389]:  # 관리 포트
                impact["risk_level"] = "high"
                impact["concerns"].append(f"관리 포트 {port} 접근")
                impact["recommendations"].append("MFA 및 IP 제한 적용")

        return impact

    def _determine_implementation_order(self, policies: List[Dict]) -> List[Dict[str, Any]]:
        """구현 순서 결정"""
        implementation_order = []

        for i, policy in enumerate(policies, 1):
            step = {
                "step": i,
                "firewall_id": policy["firewall_id"],
                "firewall_name": policy["firewall_name"],
                "action": "정책 구현",
                "estimated_time": "10-15분",
                "dependencies": [],
            }

            if i > 1:
                step["dependencies"] = [f"Step {i - 1} 완료"]

            implementation_order.append(step)

        return implementation_order

    def _generate_validation_tests(
        self,
        source_networks: List[str],
        destination_networks: List[str],
        service_info: Dict,
    ) -> List[Dict[str, str]]:
        """검증 테스트 생성"""
        tests = []

        for src_net in source_networks[:1]:  # 첫 번째 소스만
            for dst_net in destination_networks[:1]:  # 첫 번째 목적지만
                for port in service_info.get("ports", [])[:1]:  # 첫 번째 포트만
                    test = {
                        "test_name": "연결성 테스트",
                        "source": src_net.split("/")[0],
                        "destination": dst_net.split("/")[0],
                        "port": port.split("-")[0] if "-" in port else port,
                        "protocol": service_info.get("protocol", "TCP"),
                        "expected_result": "SUCCESS",
                        "test_command": f"telnet {dst_net.split('/')[0]} {port.split('-')[0] if '-' in port else port}",
                    }
                    tests.append(test)

        return tests

    def _generate_rollback_plan(self, policies: List[Dict]) -> List[Dict[str, str]]:
        """롤백 계획 생성"""
        rollback_steps = []

        for policy in reversed(policies):  # 역순으로 롤백
            step = {
                "firewall_id": policy["firewall_id"],
                "action": "정책 삭제",
                "command": f"delete firewall policy where name = '{policy['policy_name']}'",
                "description": f"{policy['firewall_name']}에서 정책 제거",
            }
            rollback_steps.append(step)

        return rollback_steps
