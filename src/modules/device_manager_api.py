"""
FortiGate 장치 관리 API 모듈
- DeviceManager의 API 래퍼 클래스
- 웹 API용 인터페이스 제공
"""

import logging
from collections import defaultdict
from typing import Any, Dict, List

from api.clients.fortigate_api_client import FortiGateAPIClient

from .device_manager import DeviceManager

logger = logging.getLogger(__name__)


class DeviceManagerAPI:
    """장치 관리 API 인터페이스"""

    def __init__(self, api_client: FortiGateAPIClient = None, faz_client=None):
        """
        DeviceManagerAPI 클래스 초기화

        Args:
            api_client: FortiGate API 클라이언트 인스턴스
            faz_client: FortiAnalyzer API 클라이언트 인스턴스 (FAZClient 또는 FortiManagerAPIClient)
        """
        # faz_client은 선택적 - 없어도 모의 데이터로 동작
        self.device_manager = DeviceManager(api_client, faz_client)

    def get_all_devices(self) -> Dict[str, Any]:
        """
        모든 장치 목록 조회 (FortiGate 및 연결된 장치)

        Returns:
            장치 목록 (포티게이트 장치 및 연결된 장치)
        """
        try:
            # FortiGate 장치 목록 조회
            fortigate_devices = self.device_manager.get_fortigate_devices()

            # 모든 연결된 장치 목록 조회
            all_connected_devices = []
            for device in fortigate_devices:
                device_name = device.get("name", "")
                if device_name:
                    connected_devices = self.device_manager.get_connected_devices(device_name)
                    # FortiGate 정보 추가
                    for connected in connected_devices:
                        connected["fortigate_device"] = device_name
                    all_connected_devices.extend(connected_devices)

            # 장치 유형별 통계
            statistics = self._calculate_device_statistics(fortigate_devices, all_connected_devices)

            return {
                "fortigate_devices": fortigate_devices,
                "connected_devices": all_connected_devices,
                "statistics": statistics,
            }

        except Exception as e:
            logger.error(f"모든 장치 목록 조회 실패: {str(e)}")
            return {
                "fortigate_devices": [],
                "connected_devices": [],
                "statistics": {},
            }

    def _calculate_device_statistics(
        self,
        fortigate_devices: List[Dict[str, Any]],
        connected_devices: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        장치 통계 계산

        Args:
            fortigate_devices: FortiGate 장치 목록
            connected_devices: 연결된 장치 목록

        Returns:
            장치 통계 정보
        """
        stats = {
            "total_fortigate_devices": len(fortigate_devices),
            "total_connected_devices": len(connected_devices),
            "device_types": defaultdict(int),
            "interface_distribution": defaultdict(int),
            "vendor_distribution": defaultdict(int),
            "ip_segments": defaultdict(int),
        }

        # 장치 유형별 통계
        for device in connected_devices:
            device_type = device.get("type", "Unknown")
            stats["device_types"][device_type] += 1

            # 인터페이스별 분포
            interface = device.get("interface", "Unknown")
            stats["interface_distribution"][interface] += 1

            # 벤더별 분포
            vendor = device.get("vendor", "Unknown")
            stats["vendor_distribution"][vendor] += 1

            # IP 대역별 분포
            ip = device.get("ip", "")
            if ip:
                # IP 첫 옥텟으로 대략적인 대역 구분
                octets = ip.split(".")
                if len(octets) == 4:
                    segment = f"{octets[0]}.{octets[1]}.{octets[2]}.0/24"
                    stats["ip_segments"][segment] += 1

        # dict 형태로 변환
        stats["device_types"] = dict(stats["device_types"])
        stats["interface_distribution"] = dict(stats["interface_distribution"])
        stats["vendor_distribution"] = dict(stats["vendor_distribution"])
        stats["ip_segments"] = dict(stats["ip_segments"])

        return stats

    def get_device_details(self, device_name: str) -> Dict[str, Any]:
        """
        장치 상세 정보 조회

        Args:
            device_name: 장치 이름

        Returns:
            장치 상세 정보
        """
        try:
            return self.device_manager.get_device_details(device_name)
        except Exception as e:
            logger.error(f"장치 상세 정보 조회 실패: {str(e)}")
            return {}

    def get_device(self, device_id: str) -> Dict[str, Any]:
        """
        장치 정보 조회 (웹 API용)

        Args:
            device_id: 장치 ID (이름)

        Returns:
            장치 상세 정보
        """
        try:
            # 상세 정보 조회
            details = self.device_manager.get_device_details(device_id)

            # 웹 API 응답 형식으로 변환
            if details.get("basic_info"):
                device_info = details["basic_info"].copy()
                device_info["interfaces"] = details.get("interfaces", [])
                device_info["policies"] = details.get("policies", [])
                device_info["routes"] = details.get("routes", [])

                # 인터페이스 정보 형식 변환
                formatted_interfaces = []
                for interface in device_info["interfaces"]:
                    formatted_interfaces.append(
                        {
                            "name": interface.get("name", ""),
                            "ip": interface.get("ip", ""),
                            "vlan": interface.get("vdom", ""),
                            "zone": interface.get("zone", ""),
                            "status": interface.get("status", ""),
                        }
                    )
                device_info["interfaces"] = formatted_interfaces

                # 정책 정보 형식 변환
                formatted_policies = []
                for policy in device_info["policies"]:
                    formatted_policies.append(
                        {
                            "id": policy.get("policyid", ""),
                            "name": policy.get("name", ""),
                            "src": ", ".join(policy.get("srcaddr", [])),
                            "dst": ", ".join(policy.get("dstaddr", [])),
                            "service": ", ".join(policy.get("service", [])),
                            "action": policy.get("action", ""),
                            "srcaddr": policy.get("srcaddr", []),
                            "dstaddr": policy.get("dstaddr", []),
                        }
                    )
                device_info["policies"] = formatted_policies

                return device_info
            else:
                # 기본 정보 반환
                return {
                    "name": device_id,
                    "type": "unknown",
                    "interfaces": [],
                    "policies": [],
                }

        except Exception as e:
            logger.error(f"장치 정보 조회 실패: {str(e)}")
            return {
                "name": device_id,
                "type": "unknown",
                "interfaces": [],
                "policies": [],
            }

    def search_devices(self, keyword: str) -> Dict[str, Any]:
        """
        키워드로 장치 검색

        Args:
            keyword: 검색 키워드

        Returns:
            검색 결과
        """
        try:
            results = self.device_manager.search_devices(keyword)

            # 결과 유형별 분류
            fortigate_results = []
            connected_results = []

            for device in results:
                if device.get("type") == "FortiGate":
                    fortigate_results.append(device)
                else:
                    connected_results.append(device)

            return {
                "keyword": keyword,
                "total_results": len(results),
                "fortigate_results": fortigate_results,
                "connected_results": connected_results,
            }

        except Exception as e:
            logger.error(f"장치 검색 실패: {str(e)}")
            return {
                "keyword": keyword,
                "total_results": 0,
                "fortigate_results": [],
                "connected_results": [],
            }

    def get_fortigate_interfaces(self, device_name: str) -> List[Dict[str, Any]]:
        """
        FortiGate 인터페이스 목록 조회

        Args:
            device_name: 장치 이름

        Returns:
            인터페이스 목록
        """
        try:
            return self.device_manager.get_device_interfaces(device_name)
        except Exception as e:
            logger.error(f"인터페이스 목록 조회 실패: {str(e)}")
            return []

    def get_fortigate_policies(self, device_name: str) -> List[Dict[str, Any]]:
        """
        FortiGate 방화벽 정책 목록 조회

        Args:
            device_name: 장치 이름

        Returns:
            정책 목록
        """
        try:
            return self.device_manager.get_firewall_policies(device_name)
        except Exception as e:
            logger.error(f"방화벽 정책 목록 조회 실패: {str(e)}")
            return []

    def get_interface_connected_devices(self, device_name: str, interface: str) -> List[Dict[str, Any]]:
        """
        특정 인터페이스에 연결된 장치 목록 조회

        Args:
            device_name: 장치 이름
            interface: 인터페이스 이름

        Returns:
            연결된 장치 목록
        """
        try:
            all_devices = self.device_manager.get_connected_devices(device_name)
            filtered_devices = [d for d in all_devices if d.get("interface") == interface]
            return filtered_devices
        except Exception as e:
            logger.error(f"인터페이스 연결 장치 목록 조회 실패: {str(e)}")
            return []
