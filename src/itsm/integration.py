#!/usr/bin/env python3

"""
ITSM 연동 모듈
FortiGate Nextrade와 ITSM2 시스템 간의 방화벽 정책 요청 연동
"""

import ipaddress
from datetime import datetime
from typing import Any, Dict, List

import requests

from utils.unified_logger import get_logger

logger = get_logger(__name__)


class ITSMIntegration:
    """ITSM 시스템과의 연동을 위한 클래스"""

    def __init__(self, itsm_base_url=None, api_key=None):
        """
        ITSM 연동 초기화

        Args:
            itsm_base_url (str): ITSM 시스템 URL
            api_key (str): ITSM API 키 (옵션)
        """
        from config.services import EXTERNAL_SERVICES

        # Use default URL from config if not provided
        if itsm_base_url is None:
            itsm_base_url = EXTERNAL_SERVICES["itsm"]

        self.itsm_base_url = itsm_base_url
        self.api_key = api_key
        self.session = requests.Session()

        # ITSM 방화벽 관련 메뉴 ID들
        self.firewall_menu_ids = {
            "vpn_firewall_management": "VPN / 방화벽 관리",
            "firewall_allow_request": "방화벽 허용요청",
            "firewall_open_allow": "방화벽 오픈 허용",
            "web_firewall_apply": "웹방화벽 적용",
        }

        from config.services import EXTERNAL_SERVICES

        # Use default URL from config if not provided
        if itsm_base_url is None:
            itsm_base_url = EXTERNAL_SERVICES["itsm"]

    def analyze_firewall_requirement(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        방화벽 정책 요청을 분석하여 어느 방화벽에 적용해야 할지 결정

        Args:
            request_data: 방화벽 정책 요청 데이터
            {
                'source_ip': '192.168.1.100',
                'destination_ip': '10.0.0.50',
                'port': 80,
                'protocol': 'tcp',
                'service': 'HTTP',
                'description': '웹 서버 접근 허용',
                'requester': '홍길동',
                'department': 'IT팀'
            }

        Returns:
            분석 결과 및 추천 방화벽
        """
        try:
            src_ip = request_data.get("source_ip", "")
            dst_ip = request_data.get("destination_ip", "")
            port = request_data.get("port", 80)
            protocol = request_data.get("protocol", "tcp")
            request_data.get("service", "")

            # IP 주소 분석
            src_zone = self._determine_network_zone(src_ip)
            dst_zone = self._determine_network_zone(dst_ip)

            # 방화벽 선택 로직
            recommended_firewalls = self._select_appropriate_firewalls(src_zone, dst_zone, port, protocol)

            # 정책 분석
            policy_analysis = self._analyze_policy_requirements(request_data, src_zone, dst_zone)

            result = {
                "source_zone": src_zone,
                "destination_zone": dst_zone,
                "recommended_firewalls": recommended_firewalls,
                "policy_analysis": policy_analysis,
                "risk_level": self._assess_risk_level(request_data, src_zone, dst_zone),
                "approval_required": self._check_approval_requirements(request_data, src_zone, dst_zone),
                "implementation_steps": self._generate_implementation_steps(recommended_firewalls, request_data),
            }

            logger.info(f"방화벽 요청 분석 완료: {src_ip}({src_zone}) -> {dst_ip}({dst_zone})")
            return result

        except Exception as e:
            logger.error(f"방화벽 요청 분석 오류: {str(e)}")
            return {"error": str(e)}

    def _determine_network_zone(self, ip_address: str) -> str:
        """
        IP 주소를 기반으로 네트워크 존 결정

        Args:
            ip_address: IP 주소

        Returns:
            네트워크 존 ('internal', 'dmz', 'external', 'branch')
        """
        try:
            ip = ipaddress.ip_address(ip_address)

            # 내부망 (Private Networks)
            if ip in ipaddress.ip_network("192.168.0.0/16"):
                return "internal"
            elif ip in ipaddress.ip_network("10.0.0.0/8"):
                # 10.10.x.x는 지사, 나머지는 내부망
                if ip in ipaddress.ip_network("10.10.0.0/16"):
                    return "branch"
                return "internal"
            elif ip in ipaddress.ip_network("172.16.0.0/16"):
                return "dmz"
            elif ip in ipaddress.ip_network("172.17.0.0/16"):
                return "dmz"
            elif ip in ipaddress.ip_network("172.28.0.0/16"):
                return "management"  # 관리망
            else:
                return "external"

        except Exception as e:
            logger.warning(f"IP 주소 분석 실패 ({ip_address}): {str(e)}")
            return "unknown"

    def _select_appropriate_firewalls(
        self, src_zone: str, dst_zone: str, port: int, protocol: str
    ) -> List[Dict[str, Any]]:
        """
        출발지와 목적지 존을 기반으로 적절한 방화벽 선택

        Args:
            src_zone: 출발지 존
            dst_zone: 목적지 존
            port: 포트 번호
            protocol: 프로토콜

        Returns:
            추천 방화벽 목록
        """
        recommended = []

        # 방화벽 정의 (기존 더미 데이터의 4개 방화벽 사용)
        firewalls = {
            "FW-01": {
                "name": "FortiGate-HQ-01",
                "location": "본사",
                "zones": ["internal"],
                "priority": 1,
            },
            "FW-02": {
                "name": "FortiGate-DMZ-01",
                "location": "DMZ",
                "zones": ["dmz"],
                "priority": 2,
            },
            "FW-03": {
                "name": "FortiGate-WAN-01",
                "location": "외부연결",
                "zones": ["external"],
                "priority": 3,
            },
            "FW-04": {
                "name": "FortiGate-Branch-01",
                "location": "지사",
                "zones": ["branch"],
                "priority": 4,
            },
        }

        # 존 간 트래픽 경로 분석
        if src_zone == "internal" and dst_zone == "external":
            # 내부 -> 외부: FW-01 (내부) -> FW-03 (WAN)
            recommended.extend(
                [
                    {
                        "firewall_id": "FW-01",
                        "firewall_name": "FortiGate-HQ-01",
                        "location": "본사",
                        "role": "source_gateway",
                        "action": "allow_outbound",
                        "priority": 1,
                    },
                    {
                        "firewall_id": "FW-03",
                        "firewall_name": "FortiGate-WAN-01",
                        "location": "외부연결",
                        "role": "wan_gateway",
                        "action": "nat_and_forward",
                        "priority": 2,
                    },
                ]
            )
        elif src_zone == "external" and dst_zone == "dmz":
            # 외부 -> DMZ: FW-03 (WAN) -> FW-02 (DMZ)
            recommended.extend(
                [
                    {
                        "firewall_id": "FW-03",
                        "firewall_name": "FortiGate-WAN-01",
                        "location": "외부연결",
                        "role": "wan_gateway",
                        "action": "dnat_to_dmz",
                        "priority": 1,
                    },
                    {
                        "firewall_id": "FW-02",
                        "firewall_name": "FortiGate-DMZ-01",
                        "location": "DMZ",
                        "role": "dmz_gateway",
                        "action": "allow_inbound",
                        "priority": 2,
                    },
                ]
            )
        elif src_zone == "internal" and dst_zone == "dmz":
            # 내부 -> DMZ: FW-01에서 직접 또는 FW-02 경유
            recommended.append(
                {
                    "firewall_id": "FW-01",
                    "firewall_name": "FortiGate-HQ-01",
                    "location": "본사",
                    "role": "internal_gateway",
                    "action": "route_to_dmz",
                    "priority": 1,
                }
            )
        elif src_zone == "branch" and dst_zone == "internal":
            # 지사 -> 본사: FW-04 -> FW-01
            recommended.extend(
                [
                    {
                        "firewall_id": "FW-04",
                        "firewall_name": "FortiGate-Branch-01",
                        "location": "지사",
                        "role": "branch_gateway",
                        "action": "vpn_tunnel",
                        "priority": 1,
                    },
                    {
                        "firewall_id": "FW-01",
                        "firewall_name": "FortiGate-HQ-01",
                        "location": "본사",
                        "role": "hq_gateway",
                        "action": "accept_vpn",
                        "priority": 2,
                    },
                ]
            )
        else:
            # 기본: 단일 방화벽 처리
            for fw_id, fw_info in firewalls.items():
                if src_zone in fw_info["zones"] or dst_zone in fw_info["zones"]:
                    recommended.append(
                        {
                            "firewall_id": fw_id,
                            "firewall_name": fw_info["name"],
                            "location": fw_info["location"],
                            "role": "primary_gateway",
                            "action": "process_traffic",
                            "priority": fw_info["priority"],
                        }
                    )

        # 우선순위 정렬
        recommended.sort(key=lambda x: x["priority"])

        return recommended

    def _analyze_policy_requirements(
        self, request_data: Dict[str, Any], src_zone: str, dst_zone: str
    ) -> Dict[str, Any]:
        """
        정책 요구사항 분석

        Args:
            request_data: 요청 데이터
            src_zone: 출발지 존
            dst_zone: 목적지 존

        Returns:
            정책 분석 결과
        """
        port = request_data.get("port", 80)
        protocol = request_data.get("protocol", "tcp")
        service = request_data.get("service", "")

        analysis = {
            "policy_type": self._determine_policy_type(src_zone, dst_zone, port),
            "security_implications": self._assess_security_implications(src_zone, dst_zone, port, protocol),
            "recommended_restrictions": self._suggest_restrictions(request_data, src_zone, dst_zone),
            "monitoring_requirements": self._determine_monitoring_needs(src_zone, dst_zone, port),
            "compliance_check": self._check_compliance_requirements(src_zone, dst_zone, port, service),
        }

        return analysis

    def _determine_policy_type(self, src_zone: str, dst_zone: str, port: int) -> str:
        """정책 유형 결정"""
        if src_zone == "internal" and dst_zone == "external":
            return "outbound_internet"
        elif src_zone == "external" and dst_zone in ["dmz", "internal"]:
            return "inbound_public"
        elif src_zone == "internal" and dst_zone == "dmz":
            return "internal_to_dmz"
        elif src_zone == "branch":
            return "branch_connection"
        else:
            return "inter_zone"

    def _assess_security_implications(self, src_zone: str, dst_zone: str, port: int, protocol: str) -> List[str]:
        """보안 영향 평가"""
        implications = []

        if dst_zone == "external":
            implications.append("외부 인터넷 접근으로 보안 위험 존재")

        if port in [22, 23, 3389]:  # SSH, Telnet, RDP
            implications.append("원격 관리 포트로 높은 보안 주의 필요")

        if port in [80, 443]:  # HTTP, HTTPS
            implications.append("웹 트래픽으로 콘텐츠 필터링 권장")

        if src_zone == "external" and dst_zone in ["internal", "dmz"]:
            implications.append("외부에서 내부로의 접근으로 엄격한 검토 필요")

        return implications

    def _suggest_restrictions(self, request_data: Dict[str, Any], src_zone: str, dst_zone: str) -> List[str]:
        """권장 제한 사항"""
        restrictions = []

        # 시간 제한
        restrictions.append("업무 시간(09:00-18:00)으로 접근 시간 제한 권장")

        # 로깅
        restrictions.append("모든 연결에 대한 상세 로깅 활성화")

        # 특정 조건에 따른 추가 제한
        if dst_zone == "external":
            restrictions.append("안티바이러스 스캔 활성화")
            restrictions.append("DLP(Data Loss Prevention) 정책 적용")

        if request_data.get("port", 80) in [22, 23, 3389]:
            restrictions.append("특정 관리자 IP에서만 접근 허용")
            restrictions.append("MFA(Multi-Factor Authentication) 요구")

        return restrictions

    def _determine_monitoring_needs(self, src_zone: str, dst_zone: str, port: int) -> Dict[str, Any]:
        """모니터링 요구사항 결정"""
        monitoring = {
            "log_level": "standard",
            "alert_conditions": [],
            "reporting_frequency": "weekly",
        }

        if dst_zone == "external":
            monitoring["log_level"] = "detailed"
            monitoring["alert_conditions"].append("대용량 데이터 전송")

        if port in [22, 23, 3389]:
            monitoring["log_level"] = "detailed"
            monitoring["alert_conditions"].append("로그인 실패 시도")
            monitoring["reporting_frequency"] = "daily"

        return monitoring

    def _check_compliance_requirements(self, src_zone: str, dst_zone: str, port: int, service: str) -> Dict[str, Any]:
        """컴플라이언스 요구사항 확인"""
        compliance = {
            "required_approvals": [],
            "documentation_needs": [],
            "audit_requirements": [],
        }

        if dst_zone == "external":
            compliance["required_approvals"].append("보안팀 승인")
            compliance["documentation_needs"].append("비즈니스 목적 명시")

        if port in [22, 23, 3389]:
            compliance["required_approvals"].extend(["IT관리팀 승인", "CISO 승인"])
            compliance["audit_requirements"].append("분기별 접근 로그 감사")

        return compliance

    def _assess_risk_level(self, request_data: Dict[str, Any], src_zone: str, dst_zone: str) -> str:
        """위험 수준 평가"""
        risk_score = 0

        # 존 기반 위험도
        if dst_zone == "external":
            risk_score += 3
        elif src_zone == "external":
            risk_score += 4

        # 포트 기반 위험도
        port = request_data.get("port", 80)
        if port in [22, 23, 3389]:  # 관리 포트
            risk_score += 3
        elif port in [21, 25, 53, 110, 143]:  # 기타 서비스 포트
            risk_score += 2
        elif port in [80, 443]:  # 웹 포트
            risk_score += 1

        # 프로토콜 기반 위험도
        if request_data.get("protocol", "").upper() == "UDP":
            risk_score += 1

        if risk_score <= 2:
            return "Low"
        elif risk_score <= 4:
            return "Medium"
        elif risk_score <= 6:
            return "High"
        else:
            return "Critical"

    def _check_approval_requirements(
        self, request_data: Dict[str, Any], src_zone: str, dst_zone: str
    ) -> Dict[str, Any]:
        """승인 요구사항 확인"""
        approvals = {
            "required": False,
            "approval_levels": [],
            "estimated_time": "1-2 business days",
        }

        risk_level = self._assess_risk_level(request_data, src_zone, dst_zone)

        if risk_level in ["High", "Critical"]:
            approvals["required"] = True
            approvals["approval_levels"] = ["팀장", "보안팀", "CISO"]
            approvals["estimated_time"] = "3-5 business days"
        elif risk_level == "Medium":
            approvals["required"] = True
            approvals["approval_levels"] = ["팀장", "보안팀"]
            approvals["estimated_time"] = "1-3 business days"

        return approvals

    def _generate_implementation_steps(
        self,
        recommended_firewalls: List[Dict[str, Any]],
        request_data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """구현 단계 생성"""
        steps = []

        for i, firewall in enumerate(recommended_firewalls, 1):
            step = {
                "step_number": i,
                "firewall_id": firewall["firewall_id"],
                "firewall_name": firewall["firewall_name"],
                "action": firewall["action"],
                "description": self._generate_step_description(firewall, request_data),
                "estimated_time": "15-30 minutes",
                "required_permissions": ["방화벽 관리자 권한"],
                "rollback_procedure": self._generate_rollback_procedure(firewall, request_data),
            }
            steps.append(step)

        return steps

    def _generate_step_description(self, firewall: Dict[str, Any], request_data: Dict[str, Any]) -> str:
        """단계별 설명 생성"""
        action = firewall["action"]
        fw_name = firewall["firewall_name"]
        src_ip = request_data.get("source_ip", "")
        dst_ip = request_data.get("destination_ip", "")
        port = request_data.get("port", "")
        protocol = request_data.get("protocol", "")

        if action == "allow_outbound":
            return f"{fw_name}에서 {src_ip} -> {dst_ip}:{port}/{protocol} 아웃바운드 허용 정책 추가"
        elif action == "nat_and_forward":
            return f"{fw_name}에서 NAT 및 포워딩 정책 설정"
        elif action == "dnat_to_dmz":
            return f"{fw_name}에서 외부 -> DMZ DNAT 정책 설정"
        elif action == "allow_inbound":
            return f"{fw_name}에서 인바운드 허용 정책 추가"
        else:
            return f"{fw_name}에서 방화벽 정책 설정"

    def _generate_rollback_procedure(self, firewall: Dict[str, Any], request_data: Dict[str, Any]) -> str:
        """롤백 절차 생성"""
        fw_name = firewall["firewall_name"]
        return f"{fw_name}에서 추가된 정책 ID를 확인 후 해당 정책 삭제"

    def create_itsm_ticket(self, analysis_result: Dict[str, Any], request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        ITSM 시스템에 방화벽 정책 요청 티켓 생성

        Args:
            analysis_result: 방화벽 분석 결과
            request_data: 원본 요청 데이터

        Returns:
            티켓 생성 결과
        """
        try:
            # ITSM 티켓 데이터 구성
            ticket_data = {
                "title": f"방화벽 정책 요청: {request_data.get('source_ip')} -> {request_data.get('destination_ip')}",
                "description": self._generate_ticket_description(analysis_result, request_data),
                "category": "방화벽 허용요청",
                "priority": self._map_risk_to_priority(analysis_result.get("risk_level", "Medium")),
                "requester": request_data.get("requester", ""),
                "department": request_data.get("department", ""),
                "requested_date": datetime.now().isoformat(),
                "firewall_details": analysis_result.get("recommended_firewalls", []),
                "implementation_steps": analysis_result.get("implementation_steps", []),
                "approval_required": analysis_result.get("approval_required", {}).get("required", False),
            }

            # 실제 ITSM API 호출은 여기서 구현
            # 현재는 더미 응답 반환
            ticket_id = f"FW-{datetime.now().strftime('%Y%m%d')}-{hash(str(ticket_data)) % 10000:04d}"

            result = {
                "success": True,
                "ticket_id": ticket_id,
                "status": "created",
                "message": "ITSM 티켓이 성공적으로 생성되었습니다.",
                "ticket_url": f"{self.itsm_base_url}/ticket/{ticket_id}",
                "estimated_completion": analysis_result.get("approval_required", {}).get(
                    "estimated_time", "1-2 business days"
                ),
            }

            logger.info(f"ITSM 티켓 생성 완료: {ticket_id}")
            return result

        except Exception as e:
            logger.error(f"ITSM 티켓 생성 오류: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "ITSM 티켓 생성에 실패했습니다.",
            }

    def _generate_ticket_description(self, analysis_result: Dict[str, Any], request_data: Dict[str, Any]) -> str:
        """티켓 설명 생성"""
        description = """
방화벽 정책 추가 요청

== 요청 정보 ==
- 출발지 IP: {request_data.get('source_ip', '')}
- 목적지 IP: {request_data.get('destination_ip', '')}
- 포트: {request_data.get('port', '')}
- 프로토콜: {request_data.get('protocol', '')}
- 서비스: {request_data.get('service', '')}
- 요청자: {request_data.get('requester', '')}
- 부서: {request_data.get('department', '')}
- 요청 사유: {request_data.get('description', '')}

== 분석 결과 ==
- 출발지 존: {analysis_result.get('source_zone', '')}
- 목적지 존: {analysis_result.get('destination_zone', '')}
- 위험 수준: {analysis_result.get('risk_level', '')}

== 추천 방화벽 ==
"""

        for fw in analysis_result.get("recommended_firewalls", []):
            description += f"- {fw.get('firewall_name', '')} ({fw.get('location', '')}) - {fw.get('action', '')}\n"

        description += """
== 보안 고려사항 ==
"""

        for implication in analysis_result.get("policy_analysis", {}).get("security_implications", []):
            description += f"- {implication}\n"

        return description

    def _map_risk_to_priority(self, risk_level: str) -> str:
        """위험 수준을 ITSM 우선순위로 매핑"""
        mapping = {
            "Low": "4급(Low)",
            "Medium": "3급(Medium)",
            "High": "2급(High)",
            "Critical": "1급(Critical)",
        }
        return mapping.get(risk_level, "3급(Medium)")

    def get_firewall_recommendations(
        self,
        src_ip: str,
        dst_ip: str,
        port: int = 80,
        protocol: str = "tcp",
        service: str = "",
        description: str = "",
    ) -> Dict[str, Any]:
        """
        간편한 방화벽 추천 API

        Args:
            src_ip: 출발지 IP
            dst_ip: 목적지 IP
            port: 포트 번호
            protocol: 프로토콜
            service: 서비스 명
            description: 설명

        Returns:
            방화벽 추천 결과
        """
        request_data = {
            "source_ip": src_ip,
            "destination_ip": dst_ip,
            "port": port,
            "protocol": protocol,
            "service": service,
            "description": description,
            "requester": "API_USER",
            "department": "IT",
        }

        return self.analyze_firewall_requirement(request_data)
