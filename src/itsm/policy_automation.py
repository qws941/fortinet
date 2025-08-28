#!/usr/bin/env python3

"""
방화벽 정책 자동화 엔진
ITSM 요청을 자동으로 처리하여 적절한 방화벽에 정책을 배포
"""

import ipaddress
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional

from api.clients.fortigate_api_client import FortiGateAPIClient
from api.clients.fortimanager_api_client import FortiManagerAPIClient
from utils.unified_logger import get_logger

from .external_connector import ExternalITSMConnector, FirewallPolicyRequest

logger = get_logger(__name__)


class PolicyAction(Enum):
    """정책 액션"""

    ALLOW = "allow"
    DENY = "deny"
    MONITOR = "monitor"


class DeploymentResult(Enum):
    """배포 결과"""

    SUCCESS = "success"
    FAILED = "failed"
    CONFLICT = "conflict"
    INVALID_REQUEST = "invalid_request"
    NO_TARGET_FIREWALL = "no_target_firewall"


@dataclass
class NetworkZone:
    """네트워크 존 정의"""

    name: str
    cidr: str
    description: str
    security_level: int  # 1(낮음) ~ 5(높음)
    allowed_outbound: List[str] = None

    def __post_init__(self):
        if self.allowed_outbound is None:
            self.allowed_outbound = []


@dataclass
class FirewallDevice:
    """방화벽 장치 정보"""

    id: str
    name: str
    host: str
    zones: List[str]
    management_ip: str
    api_client: Optional[FortiGateAPIClient] = None
    priority: int = 1  # 1(높음) ~ 5(낮음)


@dataclass
class PolicyDeploymentPlan:
    """정책 배포 계획"""

    request: FirewallPolicyRequest
    target_firewalls: List[FirewallDevice]
    deployment_order: List[str]
    estimated_rules: List[Dict]
    risk_assessment: str
    auto_approve: bool


@dataclass
class DeploymentReport:
    """배포 결과 보고서"""

    request_id: str
    result: DeploymentResult
    deployed_rules: List[Dict]
    deployment_time: datetime
    affected_firewalls: List[str]
    error_messages: List[str] = None

    def __post_init__(self):
        if self.error_messages is None:
            self.error_messages = []


class PolicyAutomationEngine:
    """방화벽 정책 자동화 엔진"""

    def __init__(self, fortimanager_client: FortiManagerAPIClient = None):
        """
        자동화 엔진 초기화

        Args:
            fortimanager_client: FortiManager API 클라이언트
        """
        self.fortimanager = fortimanager_client
        self.firewall_devices: List[FirewallDevice] = []
        self.network_zones: List[NetworkZone] = []
        self.deployment_history: List[DeploymentReport] = []

        # 기본 네트워크 존 설정
        self._initialize_default_zones()

        # 기본 방화벽 장치 설정
        self._initialize_firewall_devices()

    def _initialize_default_zones(self):
        """기본 네트워크 존 초기화"""
        default_zones = [
            NetworkZone(
                name="internal",
                cidr="192.168.0.0/16",
                description="내부 네트워크",
                security_level=4,
                allowed_outbound=["dmz", "external"],
            ),
            NetworkZone(
                name="dmz",
                cidr="172.16.0.0/16",
                description="DMZ 네트워크",
                security_level=3,
                allowed_outbound=["external"],
            ),
            NetworkZone(
                name="external",
                cidr="0.0.0.0/0",
                description="외부 네트워크",
                security_level=1,
                allowed_outbound=[],
            ),
            NetworkZone(
                name="guest",
                cidr="10.0.0.0/16",
                description="게스트 네트워크",
                security_level=2,
                allowed_outbound=["external"],
            ),
            NetworkZone(
                name="branch",
                cidr="10.10.0.0/16",
                description="지사 네트워크",
                security_level=4,
                allowed_outbound=["internal", "dmz", "external"],
            ),
        ]

        self.network_zones.extend(default_zones)
        logger.info(f"Initialized {len(default_zones)} default network zones")

    def _initialize_firewall_devices(self):
        """기본 방화벽 장치 초기화"""
        # 기본 방화벽 4대 설정 (더미 데이터에서 사용하던 것과 동일)
        default_firewalls = [
            FirewallDevice(
                id="FW-01",
                name="FortiGate-HQ-01",
                host="192.168.1.1",
                zones=["internal", "dmz"],
                management_ip="192.168.1.1",
                priority=1,
            ),
            FirewallDevice(
                id="FW-02",
                name="FortiGate-DMZ-01",
                host="172.16.1.1",
                zones=["dmz", "external"],
                management_ip="172.16.1.1",
                priority=2,
            ),
            FirewallDevice(
                id="FW-03",
                name="FortiGate-Edge-01",
                host="203.0.113.1",
                zones=["external"],
                management_ip="203.0.113.1",
                priority=1,
            ),
            FirewallDevice(
                id="FW-04",
                name="FortiGate-Branch-01",
                host="10.10.1.1",
                zones=["branch", "internal"],
                management_ip="10.10.1.1",
                priority=3,
            ),
        ]

        self.firewall_devices.extend(default_firewalls)
        logger.info(f"Initialized {len(default_firewalls)} firewall devices")

    def get_zone_by_ip(self, ip_address: str) -> Optional[NetworkZone]:
        """IP 주소로 네트워크 존 판별"""
        try:
            ip_obj = ipaddress.ip_address(ip_address)

            for zone in self.network_zones:
                if ip_obj in ipaddress.ip_network(zone.cidr):
                    return zone

            # 매칭되지 않으면 외부로 간주
            return next((z for z in self.network_zones if z.name == "external"), None)

        except ValueError:
            logger.error(f"Invalid IP address: {ip_address}")
            return None

    def analyze_firewall_request(self, request: FirewallPolicyRequest) -> PolicyDeploymentPlan:
        """방화벽 정책 요청 분석 및 배포 계획 수립"""
        logger.info(f"Analyzing firewall request: {request.ticket_id}")

        # 출발지/목적지 존 판별
        src_zone = self.get_zone_by_ip(request.source_ip)
        dst_zone = self.get_zone_by_ip(request.destination_ip)

        if not src_zone or not dst_zone:
            logger.error(f"Unable to determine network zones for {request.source_ip} -> {request.destination_ip}")
            return PolicyDeploymentPlan(
                request=request,
                target_firewalls=[],
                deployment_order=[],
                estimated_rules=[],
                risk_assessment="INVALID: Unable to determine network zones",
                auto_approve=False,
            )

        # 경로상 필요한 방화벽 결정
        target_firewalls = self._determine_target_firewalls(src_zone, dst_zone, request)

        # 배포 순서 결정 (우선순위 및 종속성 고려)
        deployment_order = self._calculate_deployment_order(target_firewalls, src_zone, dst_zone)

        # 예상 정책 규칙 생성
        estimated_rules = self._generate_policy_rules(request, src_zone, dst_zone, target_firewalls)

        # 리스크 평가
        risk_assessment = self._assess_security_risk(request, src_zone, dst_zone)

        # 자동 승인 여부 결정
        auto_approve = self._should_auto_approve(request, src_zone, dst_zone, risk_assessment)

        plan = PolicyDeploymentPlan(
            request=request,
            target_firewalls=target_firewalls,
            deployment_order=deployment_order,
            estimated_rules=estimated_rules,
            risk_assessment=risk_assessment,
            auto_approve=auto_approve,
        )

        logger.info(
            f"Deployment plan created for {request.ticket_id}: "
            f"{len(target_firewalls)} firewalls, auto_approve={auto_approve}"
        )
        return plan

    def _determine_target_firewalls(
        self,
        src_zone: NetworkZone,
        dst_zone: NetworkZone,
        request: FirewallPolicyRequest,
    ) -> List[FirewallDevice]:
        """경로상 필요한 방화벽 장치들 결정"""
        target_firewalls = []

        # 동일 존 내부 통신
        if src_zone.name == dst_zone.name:
            # 해당 존을 관리하는 방화벽 찾기
            for fw in self.firewall_devices:
                if src_zone.name in fw.zones:
                    target_firewalls.append(fw)
        else:
            # 교차 존 통신 - 경로상 모든 방화벽 필요
            {src_zone.name, dst_zone.name}

            # 출발지 존의 방화벽
            for fw in self.firewall_devices:
                if src_zone.name in fw.zones:
                    target_firewalls.append(fw)

            # 목적지 존의 방화벽 (중복 제거)
            for fw in self.firewall_devices:
                if dst_zone.name in fw.zones and fw not in target_firewalls:
                    target_firewalls.append(fw)

            # 중간 경로 방화벽 (DMZ, Edge 등)
            if src_zone.name == "internal" and dst_zone.name == "external":
                # 내부 -> 외부: Edge 방화벽 필요
                edge_fw = next(
                    (fw for fw in self.firewall_devices if "external" in fw.zones),
                    None,
                )
                if edge_fw and edge_fw not in target_firewalls:
                    target_firewalls.append(edge_fw)

            elif src_zone.name == "external" and dst_zone.name == "dmz":
                # 외부 -> DMZ: Edge 방화벽 필요
                edge_fw = next(
                    (fw for fw in self.firewall_devices if "external" in fw.zones),
                    None,
                )
                if edge_fw and edge_fw not in target_firewalls:
                    target_firewalls.append(edge_fw)

        # 우선순위로 정렬
        target_firewalls.sort(key=lambda fw: fw.priority)

        logger.info(f"Target firewalls for {src_zone.name} -> {dst_zone.name}: {[fw.id for fw in target_firewalls]}")
        return target_firewalls

    def _calculate_deployment_order(
        self,
        firewalls: List[FirewallDevice],
        src_zone: NetworkZone,
        dst_zone: NetworkZone,
    ) -> List[str]:
        """배포 순서 계산 (종속성 및 우선순위 고려)"""
        if not firewalls:
            return []

        # 기본적으로 우선순위 순서
        ordered = sorted(firewalls, key=lambda fw: fw.priority)

        # 특정 시나리오에서 순서 조정
        if src_zone.name == "internal" and dst_zone.name == "external":
            # 내부 -> 외부: 내부 방화벽 먼저, 그다음 Edge
            internal_fw = [fw for fw in ordered if "internal" in fw.zones]
            edge_fw = [fw for fw in ordered if "external" in fw.zones and fw not in internal_fw]
            ordered = internal_fw + edge_fw

        elif src_zone.name == "external" and dst_zone.name == "internal":
            # 외부 -> 내부: Edge 먼저, 그다음 내부
            edge_fw = [fw for fw in ordered if "external" in fw.zones]
            internal_fw = [fw for fw in ordered if "internal" in fw.zones and fw not in edge_fw]
            ordered = edge_fw + internal_fw

        return [fw.id for fw in ordered]

    def _generate_policy_rules(
        self,
        request: FirewallPolicyRequest,
        src_zone: NetworkZone,
        dst_zone: NetworkZone,
        firewalls: List[FirewallDevice],
    ) -> List[Dict]:
        """예상 정책 규칙 생성"""
        rules = []

        for i, firewall in enumerate(firewalls):
            rule = {
                "firewall_id": firewall.id,
                "firewall_name": firewall.name,
                "rule_name": f"ITSM_{request.ticket_id}_{firewall.id}",
                "source_zone": src_zone.name,
                "destination_zone": dst_zone.name,
                "source_address": request.source_ip,
                "destination_address": request.destination_ip,
                "service": self._map_protocol_to_service(request.protocol, request.port),
                "action": request.action,
                "schedule": "always",
                "log_traffic": "all",
                "comment": f"Auto-created from ITSM ticket {request.ticket_id} - {request.description}",
                "nat": self._determine_nat_policy(src_zone, dst_zone),
                "security_profiles": self._get_security_profiles(src_zone, dst_zone, request),
            }

            rules.append(rule)

        return rules

    def _map_protocol_to_service(self, protocol: str, port: int) -> str:
        """프로토콜과 포트를 FortiGate 서비스 객체로 매핑"""
        protocol_upper = protocol.upper()

        # 잘 알려진 서비스 매핑
        well_known_services = {
            ("HTTP", 80): "HTTP",
            ("HTTPS", 443): "HTTPS",
            ("SSH", 22): "SSH",
            ("FTP", 21): "FTP",
            ("SMTP", 25): "SMTP",
            ("DNS", 53): "DNS",
            ("TELNET", 23): "TELNET",
            ("RDP", 3389): "RDP",
        }

        service_key = (protocol_upper, port)
        if service_key in well_known_services:
            return well_known_services[service_key]
        else:
            # 커스텀 서비스 이름 생성
            return f"{protocol_upper}_{port}"

    def _determine_nat_policy(self, src_zone: NetworkZone, dst_zone: NetworkZone) -> str:
        """NAT 정책 결정"""
        # 내부 -> 외부: NAT 활성화
        if src_zone.name in ["internal", "dmz", "branch"] and dst_zone.name == "external":
            return "enable"

        # 외부 -> 내부: 일반적으로 NAT 비활성화 (DNAT 별도 설정)
        elif src_zone.name == "external" and dst_zone.name in [
            "internal",
            "dmz",
        ]:
            return "disable"

        # 내부 간: NAT 비활성화
        else:
            return "disable"

    def _get_security_profiles(
        self,
        src_zone: NetworkZone,
        dst_zone: NetworkZone,
        request: FirewallPolicyRequest,
    ) -> Dict:
        """보안 프로파일 결정"""
        profiles = {}

        # 외부에서 들어오는 트래픽은 모든 보안 기능 적용
        if src_zone.name == "external":
            profiles.update(
                {
                    "antivirus": "default",
                    "webfilter": "default",
                    "ips": "default",
                    "application-list": "default",
                    "ssl-ssh-profile": "certificate-inspection",
                }
            )

        # 내부에서 외부로 나가는 트래픽
        elif dst_zone.name == "external":
            profiles.update(
                {
                    "antivirus": "default",
                    "webfilter": "default",
                    "application-list": "default",
                }
            )

        # 내부 간 트래픽
        else:
            profiles.update({"ips": "default"})

        return profiles

    def _assess_security_risk(
        self,
        request: FirewallPolicyRequest,
        src_zone: NetworkZone,
        dst_zone: NetworkZone,
    ) -> str:
        """보안 리스크 평가"""
        risk_factors = []
        risk_score = 0

        # 존 간 보안 레벨 차이
        security_diff = abs(src_zone.security_level - dst_zone.security_level)
        risk_score += security_diff * 10

        # 외부에서 내부로의 접근
        if src_zone.name == "external" and dst_zone.name in [
            "internal",
            "dmz",
        ]:
            risk_score += 30
            risk_factors.append("External to internal access")

        # 높은 권한 포트
        high_risk_ports = [22, 23, 3389, 1433, 3306, 5432, 443, 80]
        if request.port in high_risk_ports:
            risk_score += 20
            risk_factors.append(f"High-risk port {request.port}")

        # 와일드카드 IP
        if request.source_ip.endswith("/0") or request.destination_ip.endswith("/0"):
            risk_score += 25
            risk_factors.append("Wildcard IP address")

        # 리스크 레벨 결정
        if risk_score >= 70:
            risk_level = "HIGH"
        elif risk_score >= 40:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        risk_assessment = f"{risk_level} (Score: {risk_score})"
        if risk_factors:
            risk_assessment += f" - Factors: {', '.join(risk_factors)}"

        return risk_assessment

    def _should_auto_approve(
        self,
        request: FirewallPolicyRequest,
        src_zone: NetworkZone,
        dst_zone: NetworkZone,
        risk_assessment: str,
    ) -> bool:
        """자동 승인 여부 결정"""
        # 높은 리스크는 자동 승인 안함
        if "HIGH" in risk_assessment:
            return False

        # 외부에서 내부로 접근은 자동 승인 안함
        if src_zone.name == "external" and dst_zone.name in [
            "internal",
            "dmz",
        ]:
            return False

        # 중간 리스크도 자동 승인 안함 (설정에 따라 변경 가능)
        if "MEDIUM" in risk_assessment:
            return False

        # 낮은 리스크만 자동 승인
        return True

    async def deploy_policy(self, plan: PolicyDeploymentPlan) -> DeploymentReport:
        """정책 자동 배포"""
        logger.info(f"Starting policy deployment for {plan.request.ticket_id}")

        deployment_start = datetime.now()
        deployed_rules = []
        error_messages = []
        affected_firewalls = []

        try:
            # 자동 승인 체크
            if not plan.auto_approve:
                return DeploymentReport(
                    request_id=plan.request.ticket_id,
                    result=DeploymentResult.FAILED,
                    deployed_rules=[],
                    deployment_time=deployment_start,
                    affected_firewalls=[],
                    error_messages=["Policy requires manual approval due to security risk"],
                )

            # 순서대로 방화벽에 배포
            for firewall_id in plan.deployment_order:
                firewall = next(
                    (fw for fw in plan.target_firewalls if fw.id == firewall_id),
                    None,
                )
                if not firewall:
                    continue

                # 해당 방화벽용 규칙 찾기
                firewall_rules = [rule for rule in plan.estimated_rules if rule["firewall_id"] == firewall_id]

                for rule in firewall_rules:
                    try:
                        # FortiManager를 통한 배포 (실제 환경)
                        if self.fortimanager:
                            result = await self._deploy_via_fortimanager(firewall, rule)
                        else:
                            # 직접 FortiGate API 사용 (개발/테스트 환경)
                            result = await self._deploy_direct_fortigate(firewall, rule)

                        if result["success"]:
                            deployed_rules.append(result["rule"])
                            affected_firewalls.append(firewall_id)
                            logger.info(f"Successfully deployed rule to {firewall_id}")
                        else:
                            error_messages.append(f"Failed to deploy to {firewall_id}: {result['error']}")
                            logger.error(f"Deployment failed for {firewall_id}: {result['error']}")

                    except Exception as e:
                        error_message = f"Exception during deployment to {firewall_id}: {str(e)}"
                        error_messages.append(error_message)
                        logger.error(error_message)

            # 결과 결정
            if deployed_rules and not error_messages:
                result = DeploymentResult.SUCCESS
            elif deployed_rules and error_messages:
                result = DeploymentResult.SUCCESS  # 부분 성공
            else:
                result = DeploymentResult.FAILED

            deployment_report = DeploymentReport(
                request_id=plan.request.ticket_id,
                result=result,
                deployed_rules=deployed_rules,
                deployment_time=deployment_start,
                affected_firewalls=list(set(affected_firewalls)),
                error_messages=error_messages,
            )

            # 배포 기록 저장
            self.deployment_history.append(deployment_report)

            logger.info(f"Deployment completed for {plan.request.ticket_id}: {result.value}")
            return deployment_report

        except Exception as e:
            error_message = f"Critical error during deployment: {str(e)}"
            logger.error(error_message)

            return DeploymentReport(
                request_id=plan.request.ticket_id,
                result=DeploymentResult.FAILED,
                deployed_rules=[],
                deployment_time=deployment_start,
                affected_firewalls=[],
                error_messages=[error_message],
            )

    async def _deploy_via_fortimanager(self, firewall: FirewallDevice, rule: Dict) -> Dict:
        """FortiManager를 통한 정책 배포"""
        try:
            # FortiManager API를 통해 정책 생성
            policy_data = {
                "name": rule["rule_name"],
                "srcintf": [{"name": rule["source_zone"]}],
                "dstintf": [{"name": rule["destination_zone"]}],
                "srcaddr": [{"name": self._create_address_object(rule["source_address"])}],
                "dstaddr": [{"name": self._create_address_object(rule["destination_address"])}],
                "service": [{"name": rule["service"]}],
                "action": rule["action"],
                "schedule": rule["schedule"],
                "logtraffic": rule["log_traffic"],
                "comments": rule["comment"],
                "nat": rule["nat"],
            }

            # 보안 프로파일 추가
            if rule.get("security_profiles"):
                policy_data.update(rule["security_profiles"])

            # 실제 FortiManager API 호출 (여기서는 시뮬레이션)
            success = True  # 실제로는 self.fortimanager.create_policy() 호출

            if success:
                return {
                    "success": True,
                    "rule": {
                        "id": f"auto_generated_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        "firewall_id": firewall.id,
                        "rule_data": policy_data,
                    },
                }
            else:
                return {
                    "success": False,
                    "error": "FortiManager API call failed",
                }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _deploy_direct_fortigate(self, firewall: FirewallDevice, rule: Dict) -> Dict:
        """직접 FortiGate API를 통한 정책 배포"""
        try:
            # FortiGate API 클라이언트 초기화 (필요시)
            if not firewall.api_client:
                firewall.api_client = FortiGateAPIClient(
                    host=firewall.host,
                    username="admin",  # 실제로는 설정에서 가져와야 함
                    password=os.environ.get("PASSWORD", ""),  # 실제로는 설정에서 가져와야 함
                )

            # 정책 데이터 구성
            policy_data = {
                "name": rule["rule_name"],
                "srcintf": rule["source_zone"],
                "dstintf": rule["destination_zone"],
                "srcaddr": rule["source_address"],
                "dstaddr": rule["destination_address"],
                "service": rule["service"],
                "action": rule["action"],
                "schedule": rule["schedule"],
                "logtraffic": rule["log_traffic"],
                "comments": rule["comment"],
                "nat": rule["nat"],
            }

            # 실제 FortiGate API 호출 (여기서는 시뮬레이션)
            success = True  # 실제로는 firewall.api_client.create_policy() 호출

            if success:
                return {
                    "success": True,
                    "rule": {
                        "id": f"direct_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        "firewall_id": firewall.id,
                        "rule_data": policy_data,
                    },
                }
            else:
                return {"success": False, "error": "FortiGate API call failed"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _create_address_object(self, ip_address: str) -> str:
        """IP 주소에 대한 주소 객체 이름 생성"""
        # IP 주소를 FortiGate 주소 객체 이름으로 변환
        clean_ip = ip_address.replace(".", "_").replace("/", "_")
        return f"Host_{clean_ip}"

    async def process_itsm_requests(self, connector: ExternalITSMConnector) -> List[DeploymentReport]:
        """ITSM 요청 일괄 처리"""
        logger.info("Starting ITSM request processing")

        # 최근 24시간 내 요청 수집
        since = datetime.now() - timedelta(hours=24)
        requests = await connector.fetch_firewall_requests(since)

        deployment_reports = []

        for request in requests:
            try:
                # 분석 및 배포 계획 수립
                plan = self.analyze_firewall_request(request)

                # 정책 배포
                report = await self.deploy_policy(plan)
                deployment_reports.append(report)

                # ITSM 티켓 상태 업데이트
                if report.result == DeploymentResult.SUCCESS:
                    await connector.update_ticket_status(
                        request.ticket_id,
                        "resolved",
                        f"Firewall policy automatically deployed to: {', '.join(report.affected_firewalls)}",
                    )
                else:
                    await connector.update_ticket_status(
                        request.ticket_id,
                        "in_progress",
                        f"Deployment failed: {'; '.join(report.error_messages)}",
                    )

            except Exception as e:
                logger.error(f"Error processing request {request.ticket_id}: {e}")
                continue

        logger.info(f"Processed {len(requests)} ITSM requests, {len(deployment_reports)} deployments attempted")
        return deployment_reports

    def get_deployment_history(self, limit: int = 50) -> List[DeploymentReport]:
        """배포 기록 조회"""
        return sorted(
            self.deployment_history,
            key=lambda r: r.deployment_time,
            reverse=True,
        )[:limit]

    def get_statistics(self) -> Dict:
        """배포 통계"""
        if not self.deployment_history:
            return {
                "total_deployments": 0,
                "successful_deployments": 0,
                "failed_deployments": 0,
                "success_rate": 0.0,
                "total_firewalls_affected": 0,
                "last_deployment": None,
            }

        total = len(self.deployment_history)
        successful = len([r for r in self.deployment_history if r.result == DeploymentResult.SUCCESS])
        failed = total - successful

        all_affected_firewalls = set()
        for report in self.deployment_history:
            all_affected_firewalls.update(report.affected_firewalls)

        last_deployment = max(self.deployment_history, key=lambda r: r.deployment_time).deployment_time

        return {
            "total_deployments": total,
            "successful_deployments": successful,
            "failed_deployments": failed,
            "success_rate": (successful / total * 100) if total > 0 else 0.0,
            "total_firewalls_affected": len(all_affected_firewalls),
            "last_deployment": last_deployment.isoformat() if last_deployment else None,
        }
