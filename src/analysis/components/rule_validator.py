"""
규칙 검증 컴포넌트

IP 주소와 서비스가 방화벽 규칙에 매치되는지 검증하는 책임을 담당합니다.
"""

import ipaddress

from utils.unified_logger import setup_logger

logger = setup_logger("rule_validator")


class RuleValidator:
    """방화벽 규칙 검증을 담당하는 클래스"""

    def __init__(self, data_loader=None):
        """
        규칙 검증기 초기화

        Args:
            data_loader: DataLoader 인스턴스
        """
        self.data_loader = data_loader
        self.logger = logger

    def is_ip_in_address_object(self, ip, address_obj, firewall_id="default"):
        """
        IP가 주소 객체에 포함되는지 확인

        Args:
            ip (str): 확인할 IP 주소
            address_obj (dict): 주소 객체
            firewall_id (str): 방화벽 식별자

        Returns:
            bool: IP가 주소 객체에 포함되는지 여부
        """
        try:
            obj_type = address_obj.get("type")

            if obj_type == "ipmask":
                return self._validate_ipmask(ip, address_obj)
            elif obj_type == "iprange":
                return self._validate_iprange(ip, address_obj)
            elif obj_type in ("fqdn", "wildcard-fqdn"):
                # FQDN은 IP 확인에 적합하지 않음
                return False
            else:
                self.logger.warning(f"지원되지 않는 주소 객체 유형: {obj_type}")
                return False

        except Exception as e:
            self.logger.error(f"주소 객체 확인 중 오류: {str(e)}")
            return False

    def _validate_ipmask(self, ip, address_obj):
        """IP 마스크 유형의 주소 객체 검증"""
        subnet = address_obj.get("subnet", "0.0.0.0/0")

        # subnet 형식이 '192.168.1.0 255.255.255.0'인 경우 CIDR 형식으로 변환
        if " " in subnet:
            ip_part, mask_part = subnet.split(" ")
            mask_prefix = sum([bin(int(x)).count("1") for x in mask_part.split(".")])
            subnet = f"{ip_part}/{mask_prefix}"

        return ipaddress.ip_address(ip) in ipaddress.ip_network(subnet)

    def _validate_iprange(self, ip, address_obj):
        """IP 범위 유형의 주소 객체 검증"""
        start_ip = address_obj.get("start-ip", "0.0.0.0")
        end_ip = address_obj.get("end-ip", "255.255.255.255")

        ip_int = int(ipaddress.ip_address(ip))
        start_int = int(ipaddress.ip_address(start_ip))
        end_int = int(ipaddress.ip_address(end_ip))

        return start_int <= ip_int <= end_int

    def is_ip_in_address_group(self, ip, group_name, firewall_id="default"):
        """
        IP가 주소 그룹에 포함되는지 확인

        Args:
            ip (str): 확인할 IP 주소
            group_name (str): 주소 그룹 이름
            firewall_id (str): 방화벽 식별자

        Returns:
            bool: IP가 주소 그룹에 포함되는지 여부
        """
        address_groups = self.data_loader.get_address_groups(firewall_id)
        if not address_groups:
            self.logger.error(f"방화벽 {firewall_id}의 주소 그룹 데이터가 로드되지 않았습니다.")
            return False

        # 그룹 찾기
        group = self._find_address_group(group_name, address_groups)
        if not group:
            self.logger.warning(f"주소 그룹을 찾을 수 없음: {group_name}")
            return False

        # 그룹 멤버 확인
        members = group.get("member", [])

        for member in members:
            member_name = member.get("name")

            # 멤버가 다른 주소 그룹인지 확인
            if self._is_address_group(member_name, address_groups):
                if self.is_ip_in_address_group(ip, member_name, firewall_id):
                    return True
            else:
                # 멤버가 주소 객체인 경우
                address_obj = self._find_address_object(member_name, firewall_id)
                if address_obj and self.is_ip_in_address_object(
                    ip, address_obj, firewall_id
                ):
                    return True

        return False

    def _find_address_group(self, group_name, address_groups):
        """주소 그룹 찾기"""
        for addr_group in address_groups:
            if addr_group.get("name") == group_name:
                return addr_group
        return None

    def _is_address_group(self, name, address_groups):
        """이름이 주소 그룹인지 확인"""
        return self._find_address_group(name, address_groups) is not None

    def _find_address_object(self, name, firewall_id):
        """주소 객체 찾기"""
        addresses = self.data_loader.get_addresses(firewall_id)
        for addr in addresses:
            if addr.get("name") == name:
                return addr
        return None

    def is_port_in_service_object(
        self, port, protocol, service_obj, firewall_id="default"
    ):
        """
        포트가 서비스 객체에 포함되는지 확인

        Args:
            port (int): 확인할 포트 번호
            protocol (str): 프로토콜 (tcp/udp)
            service_obj (dict): 서비스 객체
            firewall_id (str): 방화벽 식별자

        Returns:
            bool: 포트가 서비스 객체에 포함되는지 여부
        """
        try:
            # 프로토콜 확인
            service_protocol = service_obj.get("protocol", "").lower()
            if service_protocol and service_protocol != protocol.lower():
                return False

            # TCP/UDP 포트 범위 확인
            if protocol.lower() == "tcp":
                tcp_portrange = service_obj.get("tcp-portrange", "")
                return self._is_port_in_range(port, tcp_portrange)
            elif protocol.lower() == "udp":
                udp_portrange = service_obj.get("udp-portrange", "")
                return self._is_port_in_range(port, udp_portrange)

            return False

        except Exception as e:
            self.logger.error(f"서비스 객체 확인 중 오류: {str(e)}")
            return False

    def _is_port_in_range(self, port, port_range):
        """포트가 포트 범위에 포함되는지 확인"""
        if not port_range:
            return False

        # 단일 포트인 경우
        if "-" not in port_range:
            try:
                return int(port_range) == port
            except ValueError:
                return False

        # 포트 범위인 경우
        try:
            start_port, end_port = map(int, port_range.split("-"))
            return start_port <= port <= end_port
        except ValueError:
            return False

    def is_port_in_service_group(
        self, port, protocol, group_name, firewall_id="default"
    ):
        """
        포트가 서비스 그룹에 포함되는지 확인

        Args:
            port (int): 확인할 포트 번호
            protocol (str): 프로토콜 (tcp/udp)
            group_name (str): 서비스 그룹 이름
            firewall_id (str): 방화벽 식별자

        Returns:
            bool: 포트가 서비스 그룹에 포함되는지 여부
        """
        service_groups = self.data_loader.get_service_groups(firewall_id)
        if not service_groups:
            self.logger.error(f"방화벽 {firewall_id}의 서비스 그룹 데이터가 로드되지 않았습니다.")
            return False

        # 그룹 찾기
        group = self._find_service_group(group_name, service_groups)
        if not group:
            self.logger.warning(f"서비스 그룹을 찾을 수 없음: {group_name}")
            return False

        # 그룹 멤버 확인
        members = group.get("member", [])

        for member in members:
            member_name = member.get("name")

            # 멤버가 다른 서비스 그룹인지 확인
            if self._is_service_group(member_name, service_groups):
                if self.is_port_in_service_group(
                    port, protocol, member_name, firewall_id
                ):
                    return True
            else:
                # 멤버가 서비스 객체인 경우
                service_obj = self._find_service_object(member_name, firewall_id)
                if service_obj and self.is_port_in_service_object(
                    port, protocol, service_obj, firewall_id
                ):
                    return True

        return False

    def _find_service_group(self, group_name, service_groups):
        """서비스 그룹 찾기"""
        for service_group in service_groups:
            if service_group.get("name") == group_name:
                return service_group
        return None

    def _is_service_group(self, name, service_groups):
        """이름이 서비스 그룹인지 확인"""
        return self._find_service_group(name, service_groups) is not None

    def _find_service_object(self, name, firewall_id):
        """서비스 객체 찾기"""
        services = self.data_loader.get_services(firewall_id)
        for service in services:
            if service.get("name") == name:
                return service
        return None
