"""
정책 분석 컴포넌트

방화벽 정책을 분석하고 트래픽 허용 여부를 결정하는 책임을 담당합니다.
"""

from utils.common_imports import setup_module_logger

logger = setup_module_logger("policy_analyzer")


class PolicyAnalyzer:
    """방화벽 정책 분석을 담당하는 클래스"""

    def __init__(self, data_loader, rule_validator):
        """
        정책 분석기 초기화

        Args:
            data_loader: DataLoader 인스턴스
            rule_validator: RuleValidator 인스턴스
        """
        self.data_loader = data_loader
        self.rule_validator = rule_validator
        self.logger = logger

    def analyze_traffic(
        self, src_ip, dst_ip, dst_port, protocol="tcp", firewall_id="default"
    ):
        """
        트래픽이 방화벽 정책에 의해 허용되는지 분석

        Args:
            src_ip (str): 소스 IP 주소
            dst_ip (str): 목적지 IP 주소
            dst_port (int): 목적지 포트
            protocol (str): 프로토콜 (tcp/udp)
            firewall_id (str): 방화벽 식별자

        Returns:
            dict: 분석 결과
        """
        policies = self.data_loader.get_policies(firewall_id)
        if not policies:
            return {
                "allowed": False,
                "reason": "정책 데이터가 로드되지 않았습니다.",
                "matched_policies": [],
            }

        matched_policies = []

        # 정책을 순서대로 확인 (우선순위 고려)
        for policy in sorted(policies, key=lambda p: p.get("policyid", 0)):
            if self._policy_matches_traffic(
                policy, src_ip, dst_ip, dst_port, protocol, firewall_id
            ):
                matched_policies.append(policy)

                # 첫 번째 매치되는 정책의 action 확인
                action = policy.get("action", "deny").lower()

                result = {
                    "allowed": action == "accept",
                    "reason": f"정책 {policy.get('policyid')} ({action})",
                    "matched_policies": matched_policies,
                    "policy_id": policy.get("policyid"),
                    "policy_name": policy.get("name", "Unknown"),
                    "action": action,
                }

                self.logger.info(
                    f"트래픽 분석 완료: {src_ip} -> {dst_ip}:{dst_port}/{protocol} = {action}"
                )
                return result

        # 매치되는 정책이 없으면 기본적으로 거부
        return {
            "allowed": False,
            "reason": "매치되는 정책이 없습니다. (기본 거부)",
            "matched_policies": [],
            "policy_id": None,
            "policy_name": None,
            "action": "deny",
        }

    def _policy_matches_traffic(
        self, policy, src_ip, dst_ip, dst_port, protocol, firewall_id
    ):
        """
        정책이 트래픽과 매치되는지 확인

        Args:
            policy (dict): 방화벽 정책
            src_ip (str): 소스 IP
            dst_ip (str): 목적지 IP
            dst_port (int): 목적지 포트
            protocol (str): 프로토콜
            firewall_id (str): 방화벽 식별자

        Returns:
            bool: 정책이 매치되는지 여부
        """
        try:
            # 정책이 비활성화된 경우 스킵
            if policy.get("status") == "disable":
                return False

            # 소스 주소 확인
            if not self._check_source_addresses(policy, src_ip, firewall_id):
                return False

            # 목적지 주소 확인
            if not self._check_destination_addresses(policy, dst_ip, firewall_id):
                return False

            # 서비스 확인
            if not self._check_services(policy, dst_port, protocol, firewall_id):
                return False

            return True

        except Exception as e:
            self.logger.error(f"정책 매치 확인 중 오류: {str(e)}")
            return False

    def _check_source_addresses(self, policy, src_ip, firewall_id):
        """소스 주소 매치 확인"""
        srcaddr = policy.get("srcaddr", [])
        if not srcaddr:
            return True  # 소스 주소가 지정되지 않으면 모든 주소 허용

        for addr in srcaddr:
            addr_name = addr.get("name")
            if addr_name == "all":
                return True

            # 주소 그룹인지 확인
            if self.rule_validator.is_ip_in_address_group(
                src_ip, addr_name, firewall_id
            ):
                return True

            # 주소 객체인지 확인
            address_obj = self.rule_validator._find_address_object(
                addr_name, firewall_id
            )
            if address_obj and self.rule_validator.is_ip_in_address_object(
                src_ip, address_obj, firewall_id
            ):
                return True

        return False

    def _check_destination_addresses(self, policy, dst_ip, firewall_id):
        """목적지 주소 매치 확인"""
        dstaddr = policy.get("dstaddr", [])
        if not dstaddr:
            return True  # 목적지 주소가 지정되지 않으면 모든 주소 허용

        for addr in dstaddr:
            addr_name = addr.get("name")
            if addr_name == "all":
                return True

            # 주소 그룹인지 확인
            if self.rule_validator.is_ip_in_address_group(
                dst_ip, addr_name, firewall_id
            ):
                return True

            # 주소 객체인지 확인
            address_obj = self.rule_validator._find_address_object(
                addr_name, firewall_id
            )
            if address_obj and self.rule_validator.is_ip_in_address_object(
                dst_ip, address_obj, firewall_id
            ):
                return True

        return False

    def _check_services(self, policy, dst_port, protocol, firewall_id):
        """서비스 매치 확인"""
        service = policy.get("service", [])
        if not service:
            return True  # 서비스가 지정되지 않으면 모든 서비스 허용

        for svc in service:
            svc_name = svc.get("name")
            if svc_name == "ALL":
                return True

            # 서비스 그룹인지 확인
            if self.rule_validator.is_port_in_service_group(
                dst_port, protocol, svc_name, firewall_id
            ):
                return True

            # 서비스 객체인지 확인
            service_obj = self.rule_validator._find_service_object(
                svc_name, firewall_id
            )
            if service_obj and self.rule_validator.is_port_in_service_object(
                dst_port, protocol, service_obj, firewall_id
            ):
                return True

        return False

    def get_all_matching_policies(
        self, src_ip, dst_ip, dst_port, protocol="tcp", firewall_id="default"
    ):
        """
        트래픽과 매치되는 모든 정책 반환

        Args:
            src_ip (str): 소스 IP 주소
            dst_ip (str): 목적지 IP 주소
            dst_port (int): 목적지 포트
            protocol (str): 프로토콜
            firewall_id (str): 방화벽 식별자

        Returns:
            list: 매치되는 모든 정책 목록
        """
        policies = self.data_loader.get_policies(firewall_id)
        if not policies:
            return []

        matched_policies = []

        for policy in policies:
            if self._policy_matches_traffic(
                policy, src_ip, dst_ip, dst_port, protocol, firewall_id
            ):
                matched_policies.append(
                    {
                        "policy_id": policy.get("policyid"),
                        "name": policy.get("name", "Unknown"),
                        "action": policy.get("action", "deny"),
                        "status": policy.get("status", "enable"),
                        "srcaddr": policy.get("srcaddr", []),
                        "dstaddr": policy.get("dstaddr", []),
                        "service": policy.get("service", []),
                    }
                )

        return matched_policies

    def analyze_policy_conflicts(self, firewall_id="default"):
        """
        정책 충돌 분석

        Args:
            firewall_id (str): 방화벽 식별자

        Returns:
            list: 충돌하는 정책 목록
        """
        policies = self.data_loader.get_policies(firewall_id)
        if not policies:
            return []

        conflicts = []

        # 정책을 우선순위 순으로 정렬
        sorted_policies = sorted(policies, key=lambda p: p.get("policyid", 0))

        for i, policy1 in enumerate(sorted_policies):
            for policy2 in sorted_policies[i + 1 :]:
                if self._policies_overlap(policy1, policy2, firewall_id):
                    conflicts.append(
                        {
                            "policy1": {
                                "id": policy1.get("policyid"),
                                "name": policy1.get("name", "Unknown"),
                                "action": policy1.get("action", "deny"),
                            },
                            "policy2": {
                                "id": policy2.get("policyid"),
                                "name": policy2.get("name", "Unknown"),
                                "action": policy2.get("action", "deny"),
                            },
                            "conflict_type": "overlap",
                        }
                    )

        return conflicts

    def _policies_overlap(self, policy1, policy2, firewall_id):
        """
        두 정책이 겹치는지 확인

        Args:
            policy1 (dict): 첫 번째 정책
            policy2 (dict): 두 번째 정책
            firewall_id (str): 방화벽 식별자

        Returns:
            bool: 정책이 겹치는지 여부
        """
        # 간단한 겹침 검사 - 실제로는 더 복잡한 로직이 필요
        # 여기서는 기본적인 검사만 수행

        # 둘 다 같은 action이면 충돌이 아님
        if policy1.get("action") == policy2.get("action"):
            return False

        # 소스 주소, 목적지 주소, 서비스가 겹치는지 확인
        # 실제 구현에서는 더 정교한 겹침 검사가 필요
        return True  # 단순화
