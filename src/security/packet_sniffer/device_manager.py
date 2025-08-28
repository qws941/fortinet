#!/usr/bin/env python3
"""
장치 관리자 - FortiGate 및 네트워크 장치 관리
"""

import platform
import socket
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

# 선택적 import - 없으면 Mock 모드로 동작
try:
    import netifaces

    HAS_NETIFACES = True
except ImportError:
    HAS_NETIFACES = False

try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

from utils.unified_logger import get_logger

from .base_sniffer import SnifferConfig


@dataclass
class NetworkInterface:
    """네트워크 인터페이스 정보"""

    name: str
    display_name: str = ""
    description: str = ""
    ip_addresses: List[str] = field(default_factory=list)
    mac_address: str = ""
    mtu: int = 1500
    is_up: bool = False
    is_loopback: bool = False
    speed: Optional[int] = None  # Mbps

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "ip_addresses": self.ip_addresses,
            "mac_address": self.mac_address,
            "mtu": self.mtu,
            "is_up": self.is_up,
            "is_loopback": self.is_loopback,
            "speed": self.speed,
        }


@dataclass
class FortiGateDevice:
    """FortiGate 장치 정보"""

    host: str
    name: str = ""
    model: str = ""
    version: str = ""
    serial: str = ""
    status: str = "unknown"
    interfaces: List[Dict[str, Any]] = field(default_factory=list)
    policies: List[Dict[str, Any]] = field(default_factory=list)
    last_seen: Optional[datetime] = None
    api_token: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "host": self.host,
            "name": self.name,
            "model": self.model,
            "version": self.version,
            "serial": self.serial,
            "status": self.status,
            "interfaces": self.interfaces,
            "policies": self.policies,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
        }


class DeviceManager:
    """장치 관리자"""

    def __init__(self, config: Optional[SnifferConfig] = None):
        self.config = config or SnifferConfig()
        self.logger = get_logger(self.__class__.__name__, "advanced")

        # 모듈 가용성 확인
        self.mock_mode = not (HAS_NETIFACES and HAS_PSUTIL)
        if self.mock_mode:
            self.logger.warning("일부 모듈이 없어 Mock 모드로 동작합니다.")

        # 장치 저장소
        self.fortigate_devices: Dict[str, FortiGateDevice] = {}
        self.network_interfaces: Dict[str, NetworkInterface] = {}
        self.device_lock = threading.RLock()

        # FortiGate API 클라이언트 (지연 초기화)
        self._api_client = None

        # 장치 발견 스레드
        self._discovery_thread: Optional[threading.Thread] = None
        self._discovery_stop = threading.Event()

        self.logger.info("장치 매니저 초기화됨")
        self._initialize_interfaces()

    def _initialize_interfaces(self) -> None:
        """네트워크 인터페이스 초기화"""
        try:
            self._discover_network_interfaces()
            self.logger.info(f"{len(self.network_interfaces)}개의 네트워크 인터페이스 발견됨")
        except Exception as e:
            self.logger.error(f"네트워크 인터페이스 초기화 실패: {e}")

    def _discover_network_interfaces(self) -> None:
        """네트워크 인터페이스 발견"""
        with self.device_lock:
            self.network_interfaces.clear()

            if not HAS_NETIFACES:
                self.logger.warning("netifaces 모듈이 없습니다. 기본 인터페이스를 사용합니다.")
                self._add_default_interfaces()
                return

            try:
                # netifaces를 사용한 인터페이스 발견
                for interface_name in netifaces.interfaces():
                    try:
                        interface_info = self._get_interface_details(interface_name)
                        if interface_info:
                            self.network_interfaces[interface_name] = interface_info
                    except Exception as e:
                        self.logger.debug(f"인터페이스 {interface_name} 정보 획득 실패: {e}")

            except Exception as e:
                self.logger.error(f"인터페이스 발견 중 오류: {e}")
                # 기본 인터페이스 추가
                self._add_default_interfaces()

    def _get_interface_details(self, interface_name: str) -> Optional[NetworkInterface]:
        """인터페이스 상세 정보 조회"""
        if not HAS_NETIFACES:
            return None

        try:
            addrs = netifaces.ifaddresses(interface_name)

            # IP 주소 수집
            ip_addresses = []
            if netifaces.AF_INET in addrs:
                for addr in addrs[netifaces.AF_INET]:
                    ip_addresses.append(addr["addr"])

            # MAC 주소
            mac_address = ""
            if netifaces.AF_LINK in addrs and addrs[netifaces.AF_LINK]:
                mac_address = addrs[netifaces.AF_LINK][0].get("addr", "")

            # 인터페이스 상태 (psutil 사용)
            is_up = False
            mtu = 1500
            speed = None

            try:
                net_stats = psutil.net_if_stats()
                if interface_name in net_stats:
                    stats = net_stats[interface_name]
                    is_up = stats.isup
                    mtu = stats.mtu
                    speed = stats.speed if stats.speed > 0 else None
            except Exception:
                pass

            # 루프백 인터페이스 감지
            is_loopback = (
                interface_name.startswith("lo") or interface_name.startswith("Loopback") or "127.0.0.1" in ip_addresses
            )

            return NetworkInterface(
                name=interface_name,
                display_name=self._get_interface_display_name(interface_name),
                description=self._get_interface_description(interface_name),
                ip_addresses=ip_addresses,
                mac_address=mac_address,
                mtu=mtu,
                is_up=is_up,
                is_loopback=is_loopback,
                speed=speed,
            )

        except Exception as e:
            self.logger.debug(f"인터페이스 {interface_name} 상세 정보 조회 실패: {e}")
            return None

    def _get_interface_display_name(self, interface_name: str) -> str:
        """인터페이스 표시명 생성"""
        if interface_name.startswith("lo"):
            return "Loopback"
        elif interface_name.startswith("eth"):
            return f"Ethernet ({interface_name})"
        elif interface_name.startswith("wlan") or interface_name.startswith("wifi"):
            return f"Wireless ({interface_name})"
        elif interface_name.startswith("docker"):
            return f"Docker ({interface_name})"
        elif interface_name.startswith("br"):
            return f"Bridge ({interface_name})"
        else:
            return interface_name

    def _get_interface_description(self, interface_name: str) -> str:
        """인터페이스 설명 생성"""
        descriptions = {
            "lo": "Loopback interface",
            "eth0": "Primary Ethernet interface",
            "wlan0": "Primary Wireless interface",
            "docker0": "Docker bridge interface",
        }
        return descriptions.get(interface_name, f"Network interface {interface_name}")

    def _add_default_interfaces(self) -> None:
        """기본 인터페이스 추가 (fallback)"""
        default_interfaces = [
            NetworkInterface(
                name="any",
                display_name="All Interfaces",
                description="Capture on all available interfaces",
                is_up=True,
            ),
            NetworkInterface(
                name="lo",
                display_name="Loopback",
                description="Loopback interface",
                ip_addresses=["127.0.0.1"],
                is_up=True,
                is_loopback=True,
            ),
        ]

        for interface in default_interfaces:
            self.network_interfaces[interface.name] = interface

    def get_available_devices(self) -> List[Dict[str, Any]]:
        """사용 가능한 장치 목록 반환"""
        if self.mock_mode:
            # Mock 모드에서는 기본 장치 목록 반환
            return [
                {
                    "name": "FortiGate-Mock-01",
                    "type": "fortigate",
                    "host": "192.168.1.99",
                    "status": "active",
                    "mock": True,
                },
                {
                    "name": "Local-Interface",
                    "type": "interface",
                    "interface": "any",
                    "status": "available",
                    "mock": True,
                },
            ]

        with self.device_lock:
            devices = []

            # FortiGate 장치들
            for host, device in self.fortigate_devices.items():
                devices.append(device.to_dict())

            # 네트워크 인터페이스들
            for name, interface in self.network_interfaces.items():
                device_info = interface.to_dict()
                device_info["type"] = "interface"
                devices.append(device_info)

            return devices

    def get_available_interfaces(self) -> List[Dict[str, Any]]:
        """사용 가능한 네트워크 인터페이스 목록"""
        with self.device_lock:
            return [interface.to_dict() for interface in self.network_interfaces.values()]

    def get_interface_details(self, interface_name: str) -> Optional[Dict[str, Any]]:
        """특정 인터페이스 상세 정보"""
        with self.device_lock:
            interface = self.network_interfaces.get(interface_name)
            return interface.to_dict() if interface else None

    def refresh_interfaces(self) -> None:
        """인터페이스 목록 새로고침"""
        self.logger.info("네트워크 인터페이스 새로고침 중...")
        self._discover_network_interfaces()
        self.logger.info(f"인터페이스 새로고침 완료: {len(self.network_interfaces)}개")

    def get_fortigate_client(self):
        """FortiGate API 클라이언트 반환 (지연 초기화)"""
        if self._api_client is None and not self.config.offline_mode:
            try:
                from api.clients.fortigate_api_client import FortiGateAPIClient

                self._api_client = FortiGateAPIClient(
                    host=self.config.fortigate_host,
                    api_token=self.config.fortigate_token,
                )
                self.logger.info("FortiGate API 클라이언트 초기화됨")
            except Exception as e:
                self.logger.warning(f"FortiGate API 클라이언트 초기화 실패: {e}")

        return self._api_client

    def discover_fortigate_devices(self) -> List[Dict[str, Any]]:
        """FortiGate 장치 발견"""
        discovered_devices = []

        if self.config.offline_mode or self.config.mock_data:
            # 오프라인 모드에서는 가짜 장치 반환
            return self._get_mock_fortigate_devices()

        try:
            client = self.get_fortigate_client()
            if client:
                # FortiGate 시스템 정보 조회
                success, status_data = client.test_connection()
                if success:
                    device_info = self._parse_fortigate_info(status_data)
                    with self.device_lock:
                        self.fortigate_devices[client.host] = device_info
                    discovered_devices.append(device_info.to_dict())
                    self.logger.info(f"FortiGate 장치 발견됨: {client.host}")
                else:
                    self.logger.warning(f"FortiGate 연결 실패: {client.host}")

        except Exception as e:
            self.logger.error(f"FortiGate 장치 발견 중 오류: {e}")
            # 오류 시 가짜 장치 반환
            return self._get_mock_fortigate_devices()

        return discovered_devices

    def _parse_fortigate_info(self, status_data: Any) -> FortiGateDevice:
        """FortiGate 상태 데이터 파싱"""
        try:
            if isinstance(status_data, dict):
                device = FortiGateDevice(
                    host=self.config.fortigate_host,
                    name=status_data.get("hostname", "FortiGate"),
                    model=status_data.get("model", "Unknown"),
                    version=status_data.get("version", "Unknown"),
                    serial=status_data.get("serial", "Unknown"),
                    status="connected",
                    last_seen=datetime.now(),
                )
            else:
                # 기본 장치 정보
                device = FortiGateDevice(
                    host=self.config.fortigate_host,
                    name="FortiGate",
                    status="connected",
                    last_seen=datetime.now(),
                )

            return device

        except Exception as e:
            self.logger.error(f"FortiGate 정보 파싱 실패: {e}")
            return FortiGateDevice(
                host=self.config.fortigate_host,
                name="FortiGate",
                status="error",
                last_seen=datetime.now(),
            )

    def _get_mock_fortigate_devices(self) -> List[Dict[str, Any]]:
        """가짜 FortiGate 장치 목록"""
        mock_devices = [
            {
                "host": "192.168.1.1",
                "name": "FortiGate-60F",
                "model": "FortiGate-60F",
                "version": "7.0.12",
                "serial": "FGT60F-MOCK001",
                "status": "connected",
                "interfaces": [
                    {"name": "port1", "ip": "192.168.1.1", "status": "up"},
                    {"name": "port2", "ip": "10.0.0.1", "status": "up"},
                    {"name": "wan1", "ip": "203.0.113.1", "status": "up"},
                ],
                "policies": [
                    {"id": 1, "name": "LAN_to_WAN", "action": "accept"},
                    {"id": 2, "name": "WAN_to_LAN", "action": "deny"},
                ],
                "last_seen": datetime.now().isoformat(),
            },
            {
                "host": "192.168.1.2",
                "name": "FortiGate-100F",
                "model": "FortiGate-100F",
                "version": "7.2.5",
                "serial": "FGT100F-MOCK002",
                "status": "connected",
                "interfaces": [
                    {"name": "port1", "ip": "192.168.2.1", "status": "up"},
                    {"name": "port2", "ip": "10.0.1.1", "status": "up"},
                ],
                "policies": [{"id": 1, "name": "Internal_Access", "action": "accept"}],
                "last_seen": datetime.now().isoformat(),
            },
        ]

        # 가짜 장치들을 내부 저장소에도 추가
        with self.device_lock:
            for device_data in mock_devices:
                device = FortiGateDevice(
                    host=device_data["host"],
                    name=device_data["name"],
                    model=device_data["model"],
                    version=device_data["version"],
                    serial=device_data["serial"],
                    status=device_data["status"],
                    interfaces=device_data["interfaces"],
                    policies=device_data["policies"],
                    last_seen=datetime.now(),
                )
                self.fortigate_devices[device_data["host"]] = device

        self.logger.info(f"{len(mock_devices)}개의 가짜 FortiGate 장치 생성됨")
        return mock_devices

    def get_fortigate_devices(self) -> List[Dict[str, Any]]:
        """FortiGate 장치 목록 조회"""
        with self.device_lock:
            return [device.to_dict() for device in self.fortigate_devices.values()]

    def get_fortigate_device(self, host: str) -> Optional[Dict[str, Any]]:
        """특정 FortiGate 장치 정보 조회"""
        with self.device_lock:
            device = self.fortigate_devices.get(host)
            return device.to_dict() if device else None

    def get_device_interfaces(self, host: str) -> List[Dict[str, Any]]:
        """장치의 인터페이스 목록"""
        if self.config.offline_mode or self.config.mock_data:
            # 가짜 인터페이스 반환
            return [
                {
                    "name": "port1",
                    "ip": "192.168.1.1",
                    "status": "up",
                    "type": "internal",
                },
                {
                    "name": "port2",
                    "ip": "10.0.0.1",
                    "status": "up",
                    "type": "internal",
                },
                {
                    "name": "wan1",
                    "ip": "203.0.113.1",
                    "status": "up",
                    "type": "external",
                },
                {
                    "name": "dmz",
                    "ip": "172.16.0.1",
                    "status": "down",
                    "type": "dmz",
                },
            ]

        try:
            client = self.get_fortigate_client()
            if client and client.host == host:
                # FortiGate API를 통한 인터페이스 조회
                interfaces = client.get_interfaces()
                return interfaces if interfaces else []

        except Exception as e:
            self.logger.error(f"장치 인터페이스 조회 실패 ({host}): {e}")

        return []

    def test_device_connectivity(self, host: str) -> Dict[str, Any]:
        """장치 연결성 테스트"""
        result = {
            "host": host,
            "ping": False,
            "api": False,
            "response_time": None,
            "error": None,
        }

        try:
            # Ping 테스트
            start_time = time.time()

            if platform.system().lower() == "windows":
                ping_cmd = ["ping", "-n", "1", "-w", "3000", host]
            else:
                ping_cmd = ["ping", "-c", "1", "-W", "3", host]

            ping_result = subprocess.run(ping_cmd, capture_output=True, timeout=5, text=True)

            result["ping"] = ping_result.returncode == 0
            result["response_time"] = round((time.time() - start_time) * 1000, 2)

            # API 테스트 (FortiGate가 설정된 경우)
            if result["ping"] and host == self.config.fortigate_host:
                client = self.get_fortigate_client()
                if client:
                    success, _ = client.test_connection()
                    result["api"] = success

        except subprocess.TimeoutExpired:
            result["error"] = "Ping timeout"
        except Exception as e:
            result["error"] = str(e)
            self.logger.error(f"장치 연결성 테스트 실패 ({host}): {e}")

        return result

    def start_device_discovery(self, interval: int = 300) -> None:
        """장치 발견 스레드 시작"""
        if self._discovery_thread and self._discovery_thread.is_alive():
            self.logger.warning("장치 발견 스레드가 이미 실행 중입니다")
            return

        self._discovery_stop.clear()
        self._discovery_thread = threading.Thread(
            target=self._discovery_worker,
            args=(interval,),
            daemon=True,
            name="device_discovery",
        )
        self._discovery_thread.start()
        self.logger.info(f"장치 발견 스레드 시작됨 (간격: {interval}초)")

    def stop_device_discovery(self) -> None:
        """장치 발견 스레드 중지"""
        if self._discovery_thread and self._discovery_thread.is_alive():
            self._discovery_stop.set()
            self._discovery_thread.join(timeout=10)
            self.logger.info("장치 발견 스레드 중지됨")

    def _discovery_worker(self, interval: int) -> None:
        """장치 발견 작업자 스레드"""
        while not self._discovery_stop.is_set():
            try:
                # FortiGate 장치 발견
                self.discover_fortigate_devices()

                # 네트워크 인터페이스 새로고침
                self.refresh_interfaces()

                # 다음 발견까지 대기
                self._discovery_stop.wait(timeout=interval)

            except Exception as e:
                self.logger.error(f"장치 발견 작업 오류: {e}")
                self._discovery_stop.wait(timeout=60)  # 오류 시 1분 대기

    def get_system_info(self) -> Dict[str, Any]:
        """시스템 정보 조회"""
        try:
            system_info = {
                "platform": platform.system(),
                "platform_version": platform.version(),
                "architecture": platform.architecture()[0],
                "hostname": socket.gethostname(),
                "interfaces_count": len(self.network_interfaces),
                "fortigate_devices_count": len(self.fortigate_devices),
                "offline_mode": self.config.offline_mode,
                "mock_data": self.config.mock_data,
            }

            # CPU 및 메모리 정보 추가
            try:
                system_info.update(
                    {
                        "cpu_count": psutil.cpu_count(),
                        "memory_total": psutil.virtual_memory().total,
                        "memory_available": psutil.virtual_memory().available,
                    }
                )
            except Exception:
                pass

            return system_info

        except Exception as e:
            self.logger.error(f"시스템 정보 조회 실패: {e}")
            return {"error": str(e)}

    def export_device_info(self) -> Dict[str, Any]:
        """장치 정보 내보내기"""
        with self.device_lock:
            return {
                "timestamp": datetime.now().isoformat(),
                "system_info": self.get_system_info(),
                "network_interfaces": self.get_available_interfaces(),
                "fortigate_devices": self.get_fortigate_devices(),
                "config": {
                    "offline_mode": self.config.offline_mode,
                    "mock_data": self.config.mock_data,
                    "fortigate_host": self.config.fortigate_host,
                },
            }

    def cleanup(self) -> None:
        """리소스 정리"""
        self.logger.info("장치 매니저 정리 중...")

        # 발견 스레드 중지
        self.stop_device_discovery()

        # API 클라이언트 정리
        if self._api_client:
            try:
                # 필요한 경우 API 클라이언트 정리 로직 추가
                pass
            except Exception as e:
                self.logger.error(f"API 클라이언트 정리 실패: {e}")

        self.logger.info("장치 매니저 정리 완료")
