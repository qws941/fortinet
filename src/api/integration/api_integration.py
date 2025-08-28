#!/usr/bin/env python3
"""
API Integration Module for FortiGate Nextrade
Provides unified API management and integration
"""

import os
import threading
import time
from typing import Any, Dict, List, Optional

from api.clients.fortigate_api_client import FortiGateAPIClient
from api.clients.fortimanager_api_client import FortiManagerAPIClient
from utils.unified_logger import get_logger

logger = get_logger(__name__)


class APIIntegrationManager:
    """API 통합 관리자"""

    def __init__(self, config: Dict[str, Any], redis_cache=None):
        self.config = config
        self.redis_cache = redis_cache
        self.fortigate_clients = {}  # {device_id: client}
        self.fortimanager_client = None
        self.connection_status = {}  # {device_id: status}
        self.monitor_thread = None
        self.monitoring = False

    def initialize_connections(self):
        """모든 API 연결 초기화"""
        # FortiManager 연결
        if self.config.get("fortimanager", {}).get("host"):
            self._connect_fortimanager()

        # FortiGate 연결 (FortiManager를 통해 장치 목록 가져오기)
        if self.fortimanager_client:
            self._discover_fortigate_devices()
        elif self.config.get("fortigate", {}).get("host"):
            # FortiManager가 없으면 직접 연결
            self._connect_fortigate_direct()

    def _connect_fortimanager(self):
        """FortiManager 연결"""
        try:
            from config.unified_settings import unified_settings

            settings = unified_settings

            # 환경변수에서 우선 읽기
            fm_config = {
                "host": os.getenv("FORTIMANAGER_HOST") or settings.fortimanager.host,
                "username": os.getenv("FORTIMANAGER_USERNAME") or settings.fortimanager.username,
                "password": os.getenv("FORTIMANAGER_PASSWORD") or settings.fortimanager.password,
                "api_token": os.getenv("FORTIMANAGER_API_TOKEN") or settings.fortimanager.api_token,
                "port": int(os.getenv("FORTIMANAGER_PORT", str(settings.fortimanager.port))),
                "verify_ssl": os.getenv(
                    "FORTIMANAGER_VERIFY_SSL",
                    str(settings.fortimanager.verify_ssl),
                ).lower()
                == "true",
            }

            logger.info(f"FortiManager 연결 시도: {fm_config['host']}:{fm_config['port']}")

            self.fortimanager_client = FortiManagerAPIClient(
                host=fm_config["host"],
                api_token=fm_config["api_token"],
                username=fm_config["username"],
                password=fm_config["password"],
                port=fm_config["port"],
                verify_ssl=fm_config["verify_ssl"],
            )

            # 연결 테스트
            success, message = self.fortimanager_client.test_connection()
            if success:
                logger.info(f"FortiManager 연결 성공: {fm_config.get('hostname')}")
                self.connection_status["fortimanager"] = {
                    "status": "connected",
                    "message": message,
                    "last_check": time.time(),
                }
            else:
                logger.error(f"FortiManager 연결 실패: {message}")
                self.connection_status["fortimanager"] = {
                    "status": "disconnected",
                    "message": message,
                    "last_check": time.time(),
                }
                self.fortimanager_client = None

        except Exception as e:
            logger.error(f"FortiManager 연결 오류: {str(e)}")
            self.connection_status["fortimanager"] = {
                "status": "error",
                "message": str(e),
                "last_check": time.time(),
            }
            self.fortimanager_client = None

    def _discover_fortigate_devices(self):
        """FortiManager를 통해 FortiGate 장치 검색"""
        if not self.fortimanager_client:
            return

        try:
            # ADOM 목록 가져오기
            adoms = self.fortimanager_client.get_adom_list()
            if not adoms:
                adoms = [{"name": "root"}]

            # 각 ADOM에서 장치 가져오기
            for adom in adoms:
                adom_name = adom.get("name", "root")
                devices = self.fortimanager_client.get_devices(adom_name)

                if devices:
                    for device in devices:
                        device_name = device.get("name")
                        device_ip = device.get("ip")

                        if device_name and device_ip:
                            # FortiGate 클라이언트 생성
                            self._create_fortigate_client(device_name, device_ip, device)

            logger.info(f"총 {len(self.fortigate_clients)}개의 FortiGate 장치를 발견했습니다.")

        except Exception as e:
            logger.error(f"FortiGate 장치 검색 오류: {str(e)}")

    def _connect_fortigate_direct(self):
        """직접 FortiGate 연결"""
        try:
            fg_config = self.config["fortigate"]
            device_id = f"fortigate_{fg_config.get('hostname', 'unknown')}"

            client = FortiGateAPIClient(
                host=fg_config.get("hostname"),
                api_token=fg_config.get("token"),
                username=fg_config.get("username"),
                password=fg_config.get("password"),
                use_https=True,
                verify_ssl=fg_config.get("verify_ssl", False),
            )

            # 연결 테스트
            success, result = client.test_connection()
            if success:
                self.fortigate_clients[device_id] = client
                self.connection_status[device_id] = {
                    "status": "connected",
                    "info": result,
                    "last_check": time.time(),
                }
                logger.info(f"FortiGate 직접 연결 성공: {fg_config.get('hostname')}")
            else:
                logger.error(f"FortiGate 직접 연결 실패: {result}")
                self.connection_status[device_id] = {
                    "status": "disconnected",
                    "message": result,
                    "last_check": time.time(),
                }

        except Exception as e:
            logger.error(f"FortiGate 직접 연결 오류: {str(e)}")

    def _create_fortigate_client(self, device_name: str, device_ip: str, device_info: Dict):
        """FortiGate 클라이언트 생성"""
        try:
            # FortiManager의 인증 정보 사용
            client = FortiGateAPIClient(
                host=device_ip,
                api_token=device_info.get("api_token"),
                username=device_info.get("username") or self.config["fortimanager"].get("username"),
                password=device_info.get("password") or self.config["fortimanager"].get("password"),
                use_https=True,
                verify_ssl=False,
            )

            # 연결 테스트
            try:
                test_result = client.test_connection()
                if isinstance(test_result, tuple) and len(test_result) == 2:
                    success, result = test_result
                else:
                    success = bool(test_result)
                    result = str(test_result)
            except Exception as test_error:
                success = False
                result = str(test_error)

            if success:
                self.fortigate_clients[device_name] = client
                self.connection_status[device_name] = {
                    "status": "connected",
                    "info": result,
                    "device_info": device_info,
                    "last_check": time.time(),
                }
                logger.info(f"FortiGate 장치 연결 성공: {device_name} ({device_ip})")
            else:
                logger.warning(f"FortiGate 장치 연결 실패: {device_name} - {result}")
                self.connection_status[device_name] = {
                    "status": "disconnected",
                    "message": result,
                    "last_check": time.time(),
                }

        except Exception as e:
            logger.error(f"FortiGate 클라이언트 생성 오류 ({device_name}): {str(e)}")
            self.connection_status[device_name] = {
                "status": "error",
                "message": str(e),
                "last_check": time.time(),
            }

    def get_all_devices(self) -> List[Dict[str, Any]]:
        """모든 장치 정보 가져오기"""
        devices = []

        # FortiGate 장치들
        for device_id, client in self.fortigate_clients.items():
            status = self.connection_status.get(device_id, {})
            device_info = {
                "id": device_id,
                "type": "fortigate",
                "status": status.get("status", "unknown"),
                "last_check": status.get("last_check", 0),
            }

            # 연결된 경우 추가 정보 가져오기
            if status.get("status") == "connected":
                try:
                    system_info = client.get_system_status()
                    device_info.update(system_info)
                except Exception as e:
                    logger.error(f"장치 정보 가져오기 오류 ({device_id}): {str(e)}")

            devices.append(device_info)

        # FortiManager
        if self.fortimanager_client:
            fm_status = self.connection_status.get("fortimanager", {})
            devices.append(
                {
                    "id": "fortimanager",
                    "type": "fortimanager",
                    "hostname": self.config["fortimanager"].get("hostname"),
                    "status": fm_status.get("status", "unknown"),
                    "last_check": fm_status.get("last_check", 0),
                }
            )

        return devices

    def get_device_client(self, device_id: str) -> Optional[FortiGateAPIClient]:
        """특정 장치의 API 클라이언트 가져오기"""
        return self.fortigate_clients.get(device_id)

    def get_fortigate_clients(self) -> Dict[str, FortiGateAPIClient]:
        """모든 FortiGate 클라이언트 가져오기"""
        return self.fortigate_clients

    def get_fortimanager_client(self) -> Optional[FortiManagerAPIClient]:
        """FortiManager API 클라이언트 가져오기"""
        return self.fortimanager_client

    def start_connection_monitoring(self, interval: int = 60):
        """연결 상태 모니터링 시작"""
        if self.monitoring:
            return

        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._connection_monitor_loop, args=(interval,), daemon=True)
        self.monitor_thread.start()
        logger.info("API 연결 모니터링 시작")

    def stop_connection_monitoring(self):
        """연결 상태 모니터링 중지"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=10)
        logger.info("API 연결 모니터링 중지")

    def _connection_monitor_loop(self, interval: int):
        """연결 상태 모니터링 루프"""
        while self.monitoring:
            try:
                # FortiManager 연결 확인
                if self.fortimanager_client:
                    (
                        success,
                        message,
                    ) = self.fortimanager_client.test_connection()
                    self.connection_status["fortimanager"] = {
                        "status": "connected" if success else "disconnected",
                        "message": message,
                        "last_check": time.time(),
                    }

                # FortiGate 연결 확인
                for device_id, client in list(self.fortigate_clients.items()):
                    try:
                        success, result = client.test_connection()
                        self.connection_status[device_id]["status"] = "connected" if success else "disconnected"
                        self.connection_status[device_id]["last_check"] = time.time()

                        # 재연결 시도
                        if not success and self.connection_status[device_id].get("retry_count", 0) < 3:
                            logger.warning(f"장치 {device_id} 재연결 시도...")
                            time.sleep(5)
                            success, result = client.test_connection()
                            if success:
                                self.connection_status[device_id]["status"] = "connected"
                                self.connection_status[device_id]["retry_count"] = 0
                            else:
                                self.connection_status[device_id]["retry_count"] = (
                                    self.connection_status[device_id].get("retry_count", 0) + 1
                                )
                    except Exception as e:
                        logger.error(f"장치 {device_id} 연결 확인 오류: {str(e)}")
                        self.connection_status[device_id]["status"] = "error"
                        self.connection_status[device_id]["message"] = str(e)
                        self.connection_status[device_id]["last_check"] = time.time()

                # 다음 확인까지 대기
                time.sleep(interval)

            except Exception as e:
                logger.error(f"연결 모니터링 오류: {str(e)}")
                time.sleep(interval)

    def get_connection_status(self) -> Dict[str, Any]:
        """전체 연결 상태 가져오기"""
        return self.connection_status.copy()

    def refresh_connections(self):
        """모든 연결 새로고침"""
        logger.info("API 연결 새로고침 시작...")

        # 기존 연결 정리
        self.fortigate_clients.clear()
        self.fortimanager_client = None
        self.connection_status.clear()

        # 재연결
        self.initialize_connections()

        logger.info("API 연결 새로고침 완료")
