#!/usr/bin/env python3

"""
API 데이터 수집기
FortiGate/FortiManager에서 실시간 데이터를 수집하여 모니터링 대시보드에 제공
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List

from api.clients.fortigate_api_client import FortiGateAPIClient
from api.clients.fortimanager_api_client import FortiManagerAPIClient

# 절대 임포트로 변경
try:
    from utils.redis_cache import redis_cache, redis_cached
except ImportError:
    # 임포트 실패 시 더미 데코레이터 생성
    def redis_cached(*args, **kwargs):
        def decorator(func):
            return func

        return decorator

    class DummyCache:
        def get(self, key):
            return None

        def set(self, key, value, timeout=None):
            pass

        def delete(self, key):
            pass

    redis_cache = DummyCache()

logger = logging.getLogger(__name__)


class APIDataCollector:
    """API 데이터 수집기 클래스"""

    def __init__(self):
        self.config = self._load_config()
        self.fortigate_client = None
        self.fortimanager_client = None
        self._initialize_clients()

    def _load_config(self) -> dict:
        """설정 파일 로드"""
        config_path = os.path.join("data", "default_config.json")
        try:
            with open(config_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"설정 파일 로드 실패: {str(e)}")
            return {}

    def _initialize_clients(self):
        """API 클라이언트 초기화"""
        # FortiGate 클라이언트 초기화
        if self.config.get("fortigate", {}).get("host"):
            try:
                self.fortigate_client = FortiGateAPIClient(
                    host=self.config["fortigate"]["host"],
                    api_token=self.config["fortigate"].get("token"),
                    port=self.config["fortigate"].get("port", 443),
                )
                logger.info("FortiGate API 클라이언트 초기화 성공")
            except Exception as e:
                logger.error(f"FortiGate 클라이언트 초기화 실패: {str(e)}")

        # FortiManager 클라이언트 초기화
        if self.config.get("fortimanager", {}).get("host"):
            try:
                self.fortimanager_client = FortiManagerAPIClient(
                    host=self.config["fortimanager"]["host"],
                    username=self.config["fortimanager"].get("username"),
                    password=self.config["fortimanager"].get("password"),
                    adom=self.config["fortimanager"].get("adom", "root"),
                    port=self.config["fortimanager"].get("port", 443),
                )
                logger.info("FortiManager API 클라이언트 초기화 성공")
            except Exception as e:
                logger.error(f"FortiManager 클라이언트 초기화 실패: {str(e)}")

    @redis_cached(ttl=30, key_prefix="api_data")
    def get_system_status(self) -> Dict[str, Any]:
        """시스템 상태 정보 수집"""
        status = {
            "fortigate": None,
            "fortimanager": None,
            "timestamp": datetime.now().isoformat(),
        }

        # FortiGate 상태
        if self.fortigate_client:
            try:
                response = self.fortigate_client.get_system_status()
                if response.success:
                    status["fortigate"] = response.data
            except Exception as e:
                logger.error(f"FortiGate 상태 조회 실패: {str(e)}")

        # FortiManager 상태
        if self.fortimanager_client:
            try:
                response = self.fortimanager_client.get_system_status()
                if response.success:
                    status["fortimanager"] = response.data
            except Exception as e:
                logger.error(f"FortiManager 상태 조회 실패: {str(e)}")

        return status

    @redis_cached(ttl=60, key_prefix="api_data")
    def get_device_list(self) -> List[Dict[str, Any]]:
        """장치 목록 가져오기"""
        devices = []

        # FortiGate에서 직접 정보 가져오기
        if self.fortigate_client:
            device_info = {
                "name": self.config["fortigate"].get("host", "FortiGate"),
                "type": "FortiGate",
                "ip": self.config["fortigate"].get("host"),
                "status": "unknown",
                "cpu_usage": 0,
                "memory_usage": 0,
                "sessions": 0,
                "uptime": "N/A",
            }

            try:
                # 시스템 상태 가져오기
                status_response = self.fortigate_client.get_system_status()
                if status_response.success and status_response.data:
                    data = status_response.data
                    device_info["status"] = "online"
                    device_info["hostname"] = data.get("hostname", device_info["name"])
                    device_info["version"] = data.get("version", "Unknown")
                    device_info["serial"] = data.get("serial", "Unknown")

                # 리소스 사용량
                resource_response = self.fortigate_client.get_system_resource_usage()
                if resource_response.success and resource_response.data:
                    data = resource_response.data.get("results", {})
                    device_info["cpu_usage"] = data.get("cpu", 0)
                    device_info["memory_usage"] = data.get("memory", 0)
                    device_info["sessions"] = data.get("session", {}).get("count", 0)

                devices.append(device_info)

            except Exception as e:
                logger.error(f"FortiGate 장치 정보 조회 실패: {str(e)}")
                device_info["status"] = "offline"
                devices.append(device_info)

        # FortiManager에서 관리 장치 목록 가져오기
        if self.fortimanager_client:
            try:
                response = self.fortimanager_client.get_devices()
                if response.success and response.data:
                    for device in response.data:
                        device_info = {
                            "name": device.get("name", "Unknown"),
                            "type": "FortiGate (Managed)",
                            "ip": device.get("ip", "N/A"),
                            "status": ("online" if device.get("conn_status") == 1 else "offline"),
                            "cpu_usage": 0,
                            "memory_usage": 0,
                            "sessions": 0,
                            "hostname": device.get("hostname", device.get("name")),
                            "version": device.get("os_ver", "Unknown"),
                            "serial": device.get("sn", "Unknown"),
                        }
                        devices.append(device_info)
            except Exception as e:
                logger.error(f"FortiManager 장치 목록 조회 실패: {str(e)}")

        return devices

    @redis_cached(ttl=10, key_prefix="api_data")
    def get_traffic_stats(self) -> Dict[str, Any]:
        """트래픽 통계 정보"""
        stats = {
            "inbound": 0,
            "outbound": 0,
            "total_sessions": 0,
            "blocked_sessions": 0,
            "timestamp": datetime.now().isoformat(),
        }

        if self.fortigate_client:
            try:
                # 인터페이스 통계
                iface_response = self.fortigate_client.get_network_interfaces()
                if iface_response.success and iface_response.data:
                    for iface in iface_response.data:
                        stats["inbound"] += iface.get("rx_bytes", 0)
                        stats["outbound"] += iface.get("tx_bytes", 0)

                # 세션 통계
                session_response = self.fortigate_client.get_firewall_sessions()
                if session_response.success and session_response.data:
                    stats["total_sessions"] = len(session_response.data)
                    stats["blocked_sessions"] = sum(1 for s in session_response.data if s.get("action") == "deny")

            except Exception as e:
                logger.error(f"트래픽 통계 조회 실패: {str(e)}")

        return stats

    def get_security_events(self, limit: int = 20) -> List[Dict[str, Any]]:
        """보안 이벤트 가져오기"""
        events = []

        if self.fortigate_client:
            try:
                # 최근 로그 가져오기 (구현 필요)
                # 임시로 샘플 데이터 반환
                sample_events = [
                    {
                        "type": "security",
                        "message": "IPS 공격 차단: SQL Injection 시도",
                        "source": "192.168.1.100",
                        "destination": "10.0.0.5",
                        "timestamp": datetime.now().isoformat(),
                    },
                    {
                        "type": "warning",
                        "message": "비정상적인 트래픽 패턴 감지",
                        "source": "172.16.0.50",
                        "timestamp": (datetime.now() - timedelta(minutes=5)).isoformat(),
                    },
                ]
                events.extend(sample_events[:limit])

            except Exception as e:
                logger.error(f"보안 이벤트 조회 실패: {str(e)}")

        return events

    def get_system_resources(self) -> Dict[str, Any]:
        """시스템 리소스 사용량"""
        resources = {"cpu": 0, "memory": 0, "disk": 0, "temperature": 0}

        if self.fortigate_client:
            try:
                response = self.fortigate_client.get_system_resource_usage()
                if response.success and response.data:
                    data = response.data.get("results", {})
                    resources["cpu"] = data.get("cpu", 0)
                    resources["memory"] = data.get("memory", 0)
                    resources["disk"] = data.get("disk", 0)

            except Exception as e:
                logger.error(f"시스템 리소스 조회 실패: {str(e)}")

        return resources

    def get_monitoring_summary(self) -> Dict[str, Any]:
        """모니터링 요약 정보"""
        return {
            "devices": self.get_device_list(),
            "traffic": self.get_traffic_stats(),
            "resources": self.get_system_resources(),
            "events": self.get_security_events(10),
            "cache_stats": redis_cache.get_stats() if redis_cache.enabled else None,
            "timestamp": datetime.now().isoformat(),
        }


# 전역 데이터 수집기 인스턴스
data_collector = APIDataCollector()
