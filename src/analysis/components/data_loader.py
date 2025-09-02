"""
데이터 로더 컴포넌트

방화벽 및 FortiManager에서 데이터를 로드하는 책임을 담당합니다.
"""

from utils.unified_logger import setup_logger

logger = setup_logger("data_loader")


class DataLoader:
    """FortiGate 및 FortiManager로부터 데이터를 로드하는 클래스"""

    def __init__(self, fortigate_client=None, fortimanager_client=None):
        """
        데이터 로더 초기화

        Args:
            fortigate_client: FortiGate API 클라이언트
            fortimanager_client: FortiManager API 클라이언트
        """
        self.fortigate_client = fortigate_client
        self.fortimanager_client = fortimanager_client
        self.logger = logger

        # 데이터 캐시
        self._policies = {}
        self._addresses = {}
        self._address_groups = {}
        self._services = {}
        self._service_groups = {}
        self._routing_tables = {}
        self._firewalls = {}

    def load_firewall_data(self, firewall_id="default"):
        """
        특정 방화벽의 데이터 로드

        Args:
            firewall_id (str): 방화벽 식별자

        Returns:
            bool: 데이터 로드 성공 여부
        """
        try:
            if self.fortigate_client:
                return self._load_from_fortigate(firewall_id)
            elif self.fortimanager_client:
                return self._load_from_fortimanager(firewall_id)
            else:
                self.logger.error("FortiGate 또는 FortiManager 클라이언트가 필요합니다.")
                return False

        except Exception as e:
            self.logger.error(f"데이터 로드 중 오류 발생: {str(e)}")
            return False

    def _load_from_fortigate(self, firewall_id):
        """FortiGate에서 직접 데이터 로드"""
        self._policies[firewall_id] = self.fortigate_client.get_firewall_policies()
        self._addresses[firewall_id] = self.fortigate_client.get_firewall_addresses()
        self._address_groups[
            firewall_id
        ] = self.fortigate_client.get_firewall_address_groups()
        self._services[firewall_id] = self.fortigate_client.get_firewall_services()
        self._service_groups[
            firewall_id
        ] = self.fortigate_client.get_firewall_service_groups()
        self._routing_tables[firewall_id] = self.fortigate_client.get_routing_table()
        return True

    def _load_from_fortimanager(self, firewall_id):
        """FortiManager에서 데이터 로드"""
        self.logger.info(f"FortiManager를 통해 {firewall_id} 방화벽 데이터 로드 중...")

        adom = "root"

        # 장치 정보 로드
        device_info = self.fortimanager_client.get_device_info(firewall_id, adom)
        if not device_info:
            self.logger.error(f"장치 정보를 로드할 수 없습니다: {firewall_id}")
            return False

        self._firewalls[firewall_id] = device_info

        # 정책 패키지 정보 로드
        policy_packages = self.fortimanager_client.get_policy_packages(adom)
        if not policy_packages:
            self.logger.error(f"{firewall_id}에 대한 정책 패키지를 로드할 수 없습니다.")
            return False

        # 첫 번째 정책 패키지 사용 (단순화)
        policy_package = policy_packages[0]["name"] if policy_packages else None

        if policy_package:
            self._policies[
                firewall_id
            ] = self.fortimanager_client.get_firewall_policies(policy_package, adom)

        # 주소 객체 및 서비스 객체 로드
        self._addresses[firewall_id] = self.fortimanager_client.get_firewall_addresses(
            adom
        )
        self._address_groups[
            firewall_id
        ] = self.fortimanager_client.get_firewall_address_groups(adom)
        self._services[firewall_id] = self.fortimanager_client.get_firewall_services(
            adom
        )
        self._service_groups[
            firewall_id
        ] = self.fortimanager_client.get_firewall_service_groups(adom)

        # 라우팅 테이블 로드
        self._routing_tables[
            firewall_id
        ] = self.fortimanager_client.get_device_routing_table(firewall_id, adom)

        return True

    def load_all_firewalls(self):
        """
        FortiManager를 통해 모든 방화벽 장치의 데이터 로드

        Returns:
            bool: 데이터 로드 성공 여부
        """
        if not self.fortimanager_client:
            self.logger.error("FortiManager 클라이언트가 필요합니다.")
            return False

        try:
            adoms = self.fortimanager_client.get_adoms()
            if not adoms:
                self.logger.error("ADOM 목록을 가져올 수 없습니다.")
                return False

            loaded = False

            for adom in adoms:
                adom_name = adom.get("name")
                if not adom_name:
                    continue

                devices = self.fortimanager_client.get_devices(adom_name)
                if not devices:
                    self.logger.warning(f"ADOM '{adom_name}'에서 장치를 찾을 수 없습니다.")
                    continue

                for device in devices:
                    device_name = device.get("name")
                    if device_name and self.load_firewall_data(device_name):
                        loaded = True

            return loaded

        except Exception as e:
            self.logger.error(f"모든 방화벽 데이터 로드 중 오류 발생: {str(e)}")
            return False

    def get_policies(self, firewall_id="default"):
        """정책 데이터 반환"""
        return self._policies.get(firewall_id, [])

    def get_addresses(self, firewall_id="default"):
        """주소 객체 데이터 반환"""
        return self._addresses.get(firewall_id, [])

    def get_address_groups(self, firewall_id="default"):
        """주소 그룹 데이터 반환"""
        return self._address_groups.get(firewall_id, [])

    def get_services(self, firewall_id="default"):
        """서비스 객체 데이터 반환"""
        return self._services.get(firewall_id, [])

    def get_service_groups(self, firewall_id="default"):
        """서비스 그룹 데이터 반환"""
        return self._service_groups.get(firewall_id, [])

    def get_routing_tables(self, firewall_id="default"):
        """라우팅 테이블 데이터 반환"""
        return self._routing_tables.get(firewall_id, [])

    def get_firewalls(self, firewall_id="default"):
        """방화벽 정보 반환"""
        return self._firewalls.get(firewall_id, {})
