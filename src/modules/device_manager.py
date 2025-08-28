"""
FortiGate 연결 장치 관리 모듈
- 네트워크에 연결된 장치 목록 조회 및 관리
- FortiGate/FortiManager API를 통한 장치 정보 수집
- 장치 인터페이스, 정책, 라우팅 등 상세 정보 제공
"""

from api.clients.fortigate_api_client import FortiGateAPIClient
from config.unified_settings import unified_settings as CONFIG
from utils.common_imports import Any, Dict, List, logging, time

logger = logging.getLogger(__name__)


class DeviceManager:
    """FortiGate 네트워크 장치 관리 클래스"""

    def __init__(self, api_client: FortiGateAPIClient = None, faz_client=None):
        """
        DeviceManager 클래스 초기화

        Args:
            api_client: FortiGate API 클라이언트 인스턴스
            faz_client: FortiAnalyzer API 클라이언트 인스턴스 (선택적)
        """
        self.api_client = api_client
        # faz_client은 옵션 - None이면 모의 데이터 사용
        self.faz_client = faz_client
        # 장치 정보 캐시 (장치 이름: 장치 정보)
        self._device_cache: Dict[str, Dict[str, Any]] = {}
        # 캐시 만료 시간 (초)
        self._cache_ttl = 300  # 5분
        # 마지막 캐시 업데이트 시간
        self._last_cache_update = 0

    def get_fortigate_devices(self) -> List[Dict[str, Any]]:
        """
        FortiGate 장치 목록 조회

        Returns:
            FortiGate 장치 목록
        """
        devices = []

        try:
            # FortiAnalyzer API를 통해 장치 목록 조회
            if self.faz_client:
                devices_data = self.faz_client.get_devices()

                # 필요한 정보만 필터링
                for device in devices_data:
                    if device.get("type") == "FortiGate":
                        devices.append(
                            {
                                "name": device.get("name", ""),
                                "hostname": device.get("hostname", device.get("name", "")),
                                "ip": device.get("ip", ""),
                                "platform": device.get("platform", ""),
                                "version": device.get("version", ""),
                                "adom": device.get("adom", ""),
                                "status": device.get("status", ""),
                                "serial": device.get("serial", ""),
                                "last_seen": device.get("last_seen", ""),
                                "type": "FortiGate",
                            }
                        )
            else:
                # FortiAnalyzer 클라이언트가 없으면 빈 목록 반환 (운영 모드)
                # 테스트 모드는 API 라우트에서 처리
                devices = []

            # 장치 정보 캐시 업데이트
            self._update_device_cache(devices)

            return devices

        except Exception as e:
            logger.error(f"FortiGate 장치 목록 조회 실패: {str(e)}")
            return []

    def _get_current_timestamp(self) -> str:
        """현재 시간을 문자열로 반환"""
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    def _update_device_cache(self, devices: List[Dict[str, Any]]) -> None:
        """
        장치 정보 캐시 업데이트

        Args:
            devices: 장치 목록
        """
        for device in devices:
            name = device.get("name", "")
            if name:
                self._device_cache[name] = {
                    "basic_info": device,
                    "updated_at": time.time(),
                    "interfaces": None,
                    "policies": None,
                    "routes": None,
                    "connected_devices": None,
                }

        self._last_cache_update = time.time()

    def _is_cache_valid(self, device_name: str, data_type: str) -> bool:
        """
        캐시 유효성 확인

        Args:
            device_name: 장치 이름
            data_type: 데이터 유형 ('interfaces', 'policies', 'routes', 'connected_devices')

        Returns:
            캐시 유효 여부
        """
        if device_name not in self._device_cache:
            return False

        device_cache = self._device_cache[device_name]
        if data_type not in device_cache or device_cache[data_type] is None:
            return False

        cache_time = device_cache.get("updated_at", 0)
        return (time.time() - cache_time) < self._cache_ttl

    def get_device_interfaces(self, device_name: str) -> List[Dict[str, Any]]:
        """
        장치 인터페이스 목록 조회

        Args:
            device_name: 장치 이름

        Returns:
            인터페이스 목록
        """
        # 캐시 확인
        if self._is_cache_valid(device_name, "interfaces"):
            return self._device_cache[device_name]["interfaces"]

        interfaces = []

        try:
            if self.api_client:
                # FortiGate API를 통해 인터페이스 목록 조회
                response = self.api_client.get(
                    device_name=device_name,
                    url="/api/v2/cmdb/system/interface",
                )

                if response and "results" in response:
                    for interface in response["results"]:
                        interfaces.append(
                            {
                                "name": interface.get("name", ""),
                                "type": interface.get("type", ""),
                                "ip": interface.get("ip", ""),
                                "mask": interface.get("netmask", ""),
                                "vdom": interface.get("vdom", ""),
                                "status": interface.get("status", ""),
                                "description": interface.get("description", ""),
                                "alias": interface.get("alias", ""),
                                "zone": interface.get("zone", ""),
                                "speed": interface.get("speed", ""),
                                "mtu": interface.get("mtu", 1500),
                                "link": interface.get("link", False),
                            }
                        )
            else:
                # 모의 데이터 (테스트용)
                mock_interfaces = [
                    {
                        "name": "port1",
                        "type": "physical",
                        "ip": "192.168.1.1",
                        "mask": "255.255.255.0",
                        "vdom": "root",
                        "status": "up",
                        "description": "Management Interface",
                        "alias": "lan",
                        "zone": "internal",
                        "speed": "auto",
                        "mtu": 1500,
                        "link": True,
                    },
                    {
                        "name": "port2",
                        "type": "physical",
                        "ip": "10.0.0.1",
                        "mask": "255.255.255.0",
                        "vdom": "root",
                        "status": "up",
                        "description": "Internal Network",
                        "alias": "internal",
                        "zone": "internal",
                        "speed": "auto",
                        "mtu": 1500,
                        "link": True,
                    },
                    {
                        "name": "port3",
                        "type": "physical",
                        "ip": "203.0.113.1",
                        "mask": "255.255.255.0",
                        "vdom": "root",
                        "status": "up",
                        "description": "External Network",
                        "alias": "wan1",
                        "zone": "external",
                        "speed": "auto",
                        "mtu": 1500,
                        "link": True,
                    },
                    {
                        "name": "port4",
                        "type": "physical",
                        "ip": "172.16.0.1",
                        "mask": "255.255.255.0",
                        "vdom": "root",
                        "status": "up",
                        "description": "DMZ Network",
                        "alias": "dmz",
                        "zone": "dmz",
                        "speed": "auto",
                        "mtu": 1500,
                        "link": True,
                    },
                ]
                interfaces = mock_interfaces

            # 캐시 업데이트
            if device_name in self._device_cache:
                self._device_cache[device_name]["interfaces"] = interfaces
                self._device_cache[device_name]["updated_at"] = time.time()

            return interfaces

        except Exception as e:
            logger.error(f"장치 인터페이스 목록 조회 실패: {str(e)}")
            return []

    def get_firewall_policies(self, device_name: str) -> List[Dict[str, Any]]:
        """
        장치 방화벽 정책 목록 조회

        Args:
            device_name: 장치 이름

        Returns:
            정책 목록
        """
        # 캐시 확인
        if self._is_cache_valid(device_name, "policies"):
            return self._device_cache[device_name]["policies"]

        policies = []

        try:
            if self.api_client:
                # FortiGate API를 통해 방화벽 정책 목록 조회
                response = self.api_client.get(device_name=device_name, url="/api/v2/cmdb/firewall/policy")

                if response and "results" in response:
                    for policy in response["results"]:
                        policies.append(
                            {
                                "id": policy.get("policyid", 0),
                                "name": policy.get("name", ""),
                                "srcintf": policy.get("srcintf", []),
                                "dstintf": policy.get("dstintf", []),
                                "srcaddr": policy.get("srcaddr", []),
                                "dstaddr": policy.get("dstaddr", []),
                                "service": policy.get("service", []),
                                "action": policy.get("action", ""),
                                "status": policy.get("status", ""),
                                "comments": policy.get("comments", ""),
                                "nat": policy.get("nat", False),
                                "log": policy.get("log", False),
                                "schedule": policy.get("schedule", ""),
                            }
                        )
            else:
                # 모의 데이터 (테스트용)
                mock_policies = [
                    {
                        "id": 1,
                        "name": "Allow_Internal_to_Internet",
                        "srcintf": [{"name": "port2"}],
                        "dstintf": [{"name": "port3"}],
                        "srcaddr": [{"name": "Internal_Network"}],
                        "dstaddr": [{"name": "all"}],
                        "service": [
                            {"name": "HTTP"},
                            {"name": "HTTPS"},
                            {"name": "DNS"},
                        ],
                        "action": "accept",
                        "status": "enable",
                        "comments": "Allow internal users to access internet",
                        "nat": True,
                        "log": True,
                        "schedule": "always",
                    },
                    {
                        "id": 2,
                        "name": "Allow_DMZ_Web_Server",
                        "srcintf": [{"name": "port3"}],
                        "dstintf": [{"name": "port4"}],
                        "srcaddr": [{"name": "all"}],
                        "dstaddr": [{"name": "Web_Server"}],
                        "service": [{"name": "HTTP"}, {"name": "HTTPS"}],
                        "action": "accept",
                        "status": "enable",
                        "comments": "Allow access to DMZ web server",
                        "nat": False,
                        "log": True,
                        "schedule": "always",
                    },
                    {
                        "id": 3,
                        "name": "Block_DMZ_to_Internal",
                        "srcintf": [{"name": "port4"}],
                        "dstintf": [{"name": "port2"}],
                        "srcaddr": [{"name": "all"}],
                        "dstaddr": [{"name": "Internal_Network"}],
                        "service": [{"name": "ALL"}],
                        "action": "deny",
                        "status": "enable",
                        "comments": "Block DMZ access to internal network",
                        "nat": False,
                        "log": True,
                        "schedule": "always",
                    },
                ]
                policies = mock_policies

            # 캐시 업데이트
            if device_name in self._device_cache:
                self._device_cache[device_name]["policies"] = policies
                self._device_cache[device_name]["updated_at"] = time.time()

            return policies

        except Exception as e:
            logger.error(f"방화벽 정책 목록 조회 실패: {str(e)}")
            return []

    def get_routing_table(self, device_name: str) -> List[Dict[str, Any]]:
        """
        장치 라우팅 테이블 조회

        Args:
            device_name: 장치 이름

        Returns:
            라우팅 테이블
        """
        # 캐시 확인
        if self._is_cache_valid(device_name, "routes"):
            return self._device_cache[device_name]["routes"]

        routes = []

        try:
            if self.api_client:
                # FortiGate API를 통해 라우팅 테이블 조회
                response = self.api_client.get(device_name=device_name, url="/api/v2/monitor/router/ipv4")

                if response and "results" in response:
                    for route in response["results"]:
                        routes.append(
                            {
                                "dest": route.get("ip_mask", ""),
                                "gateway": route.get("gateway", ""),
                                "interface": route.get("interface", ""),
                                "type": route.get("type", ""),
                                "distance": route.get("distance", 0),
                                "metric": route.get("metric", 0),
                                "priority": route.get("priority", 0),
                            }
                        )
            else:
                # 모의 데이터 (테스트용)
                mock_routes = [
                    {
                        "dest": "0.0.0.0/0",
                        "gateway": CONFIG.network.DEFAULT_GATEWAY,
                        "interface": "port3",
                        "type": "static",
                        "distance": 10,
                        "metric": 0,
                        "priority": 0,
                    },
                    {
                        "dest": CONFIG.network.MANAGEMENT_NETWORK,
                        "gateway": "0.0.0.0",
                        "interface": "port1",
                        "type": "connected",
                        "distance": 0,
                        "metric": 0,
                        "priority": 0,
                    },
                    {
                        "dest": "10.0.0.0/24",
                        "gateway": "0.0.0.0",
                        "interface": "port2",
                        "type": "connected",
                        "distance": 0,
                        "metric": 0,
                        "priority": 0,
                    },
                    {
                        "dest": CONFIG.network.DMZ_NETWORK,
                        "gateway": "0.0.0.0",
                        "interface": "port4",
                        "type": "connected",
                        "distance": 0,
                        "metric": 0,
                        "priority": 0,
                    },
                    {
                        "dest": "192.168.2.0/24",
                        "gateway": "10.0.0.254",
                        "interface": "port2",
                        "type": "static",
                        "distance": 10,
                        "metric": 0,
                        "priority": 0,
                    },
                ]
                routes = mock_routes

            # 캐시 업데이트
            if device_name in self._device_cache:
                self._device_cache[device_name]["routes"] = routes
                self._device_cache[device_name]["updated_at"] = time.time()

            return routes

        except Exception as e:
            logger.error(f"라우팅 테이블 조회 실패: {str(e)}")
            return []

    def get_connected_devices(self, device_name: str) -> List[Dict[str, Any]]:
        """
        장치에 연결된 네트워크 장치 목록 조회

        Args:
            device_name: 장치 이름

        Returns:
            연결된 장치 목록
        """
        # 캐시 확인
        if self._is_cache_valid(device_name, "connected_devices"):
            return self._device_cache[device_name]["connected_devices"]

        connected_devices = []

        try:
            if self.api_client:
                # FortiGate API를 통해 ARP 테이블 및 DHCP 리스 정보 조회
                arp_response = self.api_client.get(device_name=device_name, url="/api/v2/monitor/system/arp")

                dhcp_response = self.api_client.get(device_name=device_name, url="/api/v2/monitor/system/dhcp")

                # ARP 테이블에서 연결된 장치 정보 추출
                if arp_response and "results" in arp_response:
                    for entry in arp_response["results"]:
                        device = {
                            "ip": entry.get("ip", ""),
                            "mac": entry.get("mac", ""),
                            "interface": entry.get("interface", ""),
                            "type": "Unknown",
                            "hostname": "",
                            "vendor": "",
                            "last_seen": self._get_current_timestamp(),
                            "source": "ARP",
                        }
                        connected_devices.append(device)

                # DHCP 리스 정보에서 추가 정보 보완
                if dhcp_response and "results" in dhcp_response:
                    for server in dhcp_response["results"]:
                        if "leases" in server:
                            for lease in server["leases"]:
                                ip = lease.get("ip", "")
                                # 기존 리스트에서 동일 IP 찾기
                                found = False
                                for device in connected_devices:
                                    if device["ip"] == ip:
                                        # 기존 장치 정보 업데이트
                                        device["hostname"] = lease.get("hostname", "")
                                        device["type"] = "DHCP Client"
                                        device["source"] = "DHCP"
                                        found = True
                                        break

                                # 새로운 장치 추가
                                if not found:
                                    device = {
                                        "ip": ip,
                                        "mac": lease.get("mac", ""),
                                        "interface": server.get("interface", ""),
                                        "type": "DHCP Client",
                                        "hostname": lease.get("hostname", ""),
                                        "vendor": "",
                                        "last_seen": self._get_current_timestamp(),
                                        "source": "DHCP",
                                    }
                                    connected_devices.append(device)
            else:
                # 모의 데이터 (테스트용)
                mock_devices = [
                    {
                        "ip": "192.168.1.10",
                        "mac": "00:11:22:33:44:55",
                        "interface": "port1",
                        "type": "PC",
                        "hostname": "workstation1",
                        "vendor": "Dell Inc.",
                        "last_seen": self._get_current_timestamp(),
                        "source": "DHCP",
                    },
                    {
                        "ip": "192.168.1.11",
                        "mac": "00:11:22:33:44:66",
                        "interface": "port1",
                        "type": "Mobile",
                        "hostname": "employee-phone",
                        "vendor": "Apple Inc.",
                        "last_seen": self._get_current_timestamp(),
                        "source": "DHCP",
                    },
                    {
                        "ip": "10.0.0.10",
                        "mac": "AA:BB:CC:DD:EE:FF",
                        "interface": "port2",
                        "type": "Server",
                        "hostname": "fileserver",
                        "vendor": "HP Enterprise",
                        "last_seen": self._get_current_timestamp(),
                        "source": "ARP",
                    },
                    {
                        "ip": "172.16.0.10",
                        "mac": "AA:BB:CC:11:22:33",
                        "interface": "port4",
                        "type": "Server",
                        "hostname": "webserver",
                        "vendor": "Cisco Systems",
                        "last_seen": self._get_current_timestamp(),
                        "source": "ARP",
                    },
                ]
                connected_devices = mock_devices

            # 장치 유형 및 벤더 정보 추론
            for device in connected_devices:
                if not device["type"] or device["type"] == "Unknown":
                    device["type"] = self._infer_device_type(device)
                if not device["vendor"]:
                    device["vendor"] = self._infer_vendor_from_mac(device["mac"])

            # 캐시 업데이트
            if device_name in self._device_cache:
                self._device_cache[device_name]["connected_devices"] = connected_devices
                self._device_cache[device_name]["updated_at"] = time.time()

            return connected_devices

        except Exception as e:
            logger.error(f"연결된 장치 목록 조회 실패: {str(e)}")
            return []

    def _infer_device_type(self, device: Dict[str, Any]) -> str:
        """
        장치 유형 추론

        Args:
            device: 장치 정보

        Returns:
            추론된 장치 유형
        """
        hostname = device.get("hostname", "").lower()

        # 호스트명 기반 추론
        if any(server in hostname for server in ["server", "srv"]):
            return "Server"
        elif any(pc in hostname for pc in ["pc", "desktop", "workstation"]):
            return "PC"
        elif any(mobile in hostname for mobile in ["phone", "iphone", "android", "mobile"]):
            return "Mobile"
        elif any(printer in hostname for printer in ["print", "printer", "hp", "canon"]):
            return "Printer"
        elif any(network in hostname for network in ["switch", "router", "ap", "wifi"]):
            return "Network Device"

        # IP 주소 기반 추론 (예: 서버는 종종 특정 IP 범위에 할당)
        ip = device.get("ip", "")
        if ip.endswith(".1") or ip.endswith(".254"):
            return "Network Device"

        # 기본값
        return "Unknown"

    def _infer_vendor_from_mac(self, mac: str) -> str:
        """
        MAC 주소에서 벤더 정보 추론

        Args:
            mac: MAC 주소

        Returns:
            추론된 벤더 이름
        """
        if not mac:
            return "Unknown"

        # MAC 주소 정규화
        mac = mac.upper().replace(":", "").replace("-", "")
        oui = mac[:6]

        # 간단한 OUI 매핑 (실제로는 IEEE OUI 데이터베이스 필요)
        oui_map = {
            "000C29": "VMware, Inc.",
            "001122": "Cisco Systems, Inc.",
            "0080C2": "IEEE",
            "001B63": "Apple Inc.",
            "001D7E": "Cisco-Linksys, LLC",
            "0025AE": "Microsoft Corporation",
            "001018": "Broadcom Corporation",
            "AABBCC": "Dell Inc.",
            "DDEEFF": "HP Enterprise",
            "AABBCD": "Juniper Networks",
        }

        return oui_map.get(oui, "Unknown Vendor")

    def get_device_details(self, device_name: str) -> Dict[str, Any]:
        """
        장치 상세 정보 조회 (인터페이스, 정책, 라우팅 등)

        Args:
            device_name: 장치 이름

        Returns:
            장치 상세 정보
        """
        details = {
            "basic_info": None,
            "interfaces": [],
            "policies": [],
            "routes": [],
            "connected_devices": [],
        }

        try:
            # 기본 정보
            if device_name in self._device_cache:
                details["basic_info"] = self._device_cache[device_name].get("basic_info", {})
            else:
                devices = self.get_fortigate_devices()
                for device in devices:
                    if device.get("name") == device_name:
                        details["basic_info"] = device
                        break

            # 인터페이스 정보
            details["interfaces"] = self.get_device_interfaces(device_name)

            # 정책 정보
            details["policies"] = self.get_firewall_policies(device_name)

            # 라우팅 정보
            details["routes"] = self.get_routing_table(device_name)

            # 연결된 장치 정보
            details["connected_devices"] = self.get_connected_devices(device_name)

            return details

        except Exception as e:
            logger.error(f"장치 상세 정보 조회 실패: {str(e)}")
            return details

    def search_devices(self, keyword: str) -> List[Dict[str, Any]]:
        """
        키워드로 장치 검색

        Args:
            keyword: 검색 키워드

        Returns:
            검색 결과 장치 목록
        """
        results = []
        keyword = keyword.lower()

        try:
            # FortiGate 장치 검색
            fortigate_devices = self.get_fortigate_devices()
            for device in fortigate_devices:
                # 이름, 호스트명, IP 등으로 검색
                if (
                    keyword in device.get("name", "").lower()
                    or keyword in device.get("hostname", "").lower()
                    or keyword in device.get("ip", "").lower()
                    or keyword in device.get("platform", "").lower()
                ):
                    results.append(device)

            # 연결된 장치 검색
            for fg_device in fortigate_devices:
                device_name = fg_device.get("name", "")
                connected_devices = self.get_connected_devices(device_name)

                for device in connected_devices:
                    # 이름, 호스트명, IP, MAC 등으로 검색
                    if (
                        keyword in device.get("hostname", "").lower()
                        or keyword in device.get("ip", "").lower()
                        or keyword in device.get("mac", "").lower()
                        or keyword in device.get("type", "").lower()
                    ):
                        # FortiGate 정보 추가
                        device["fortigate_device"] = device_name
                        results.append(device)

            return results

        except Exception as e:
            logger.error(f"장치 검색 실패: {str(e)}")
            return []
