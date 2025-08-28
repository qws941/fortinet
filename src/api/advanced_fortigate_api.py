#!/usr/bin/env python3
"""
고급 FortiGate API 구현체
포티넷 API를 이용한 완전한 기능 구현 및 검증

FortiGate REST API를 사용하여 다음 기능들을 구현:
- 방화벽 정책 관리 (고급 필터링, 보안 프로필 통합)
- VPN 연결 관리 (IPSec, SSL VPN)
- NAT 정책 관리 (Source/Destination NAT)
- 보안 프로필 관리 (IPS, 안티바이러스, Web 필터링)
- 실시간 로그 모니터링 및 분석
- 시스템 상태 모니터링 및 성능 메트릭
- 네트워크 인터페이스 및 라우팅 관리
"""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Union

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from api.clients.base_api_client import BaseApiClient
from utils.unified_logger import get_logger

logger = get_logger(__name__)


class AdvancedFortiGateAPI(BaseApiClient):
    """고급 FortiGate API 클라이언트 - 완전한 기능 구현"""

    def __init__(
        self,
        host: str,
        api_key: str = None,
        username: str = None,
        password: str = None,
        port: int = 443,
        verify_ssl: bool = False,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """
        고급 FortiGate API 클라이언트 초기화

        Args:
            host: FortiGate 호스트 주소
            api_key: REST API 키 (우선순위)
            username: 사용자명 (API 키가 없을 때)
            password: 비밀번호 (API 키가 없을 때)
            port: 포트 번호 (기본 443)
            verify_ssl: SSL 인증서 검증 여부
            timeout: 요청 타임아웃 (초)
            max_retries: 최대 재시도 횟수
        """
        super().__init__()

        self.host = host.rstrip("/")
        self.port = port
        self.api_key = api_key
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.max_retries = max_retries

        # Base URL 설정
        self.base_url = f"https://{self.host}:{self.port}/api/v2"

        # 세션 설정 (BaseAPIClient에서 초기화됨)
        self._setup_session()

        # API 통계
        self.api_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "last_request_time": None,
            "average_response_time": 0.0,
        }

        logger.info(f"Advanced FortiGate API client initialized for {host}:{port}")

    def _setup_session(self):
        """HTTP 세션 설정"""
        # 재시도 전략
        retry_strategy = Retry(
            total=self.max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE"],
            backoff_factor=1,
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # 기본 헤더 설정
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "FortiGate-Nextrade-API/2.0",
            }
        )

        # 인증 설정
        if self.api_key:
            self.session.headers["Authorization"] = f"Bearer {self.api_key}"
            logger.info("Using API key authentication")
        elif self.username and self.password:
            # Basic Auth 또는 로그인 세션 사용
            self._login_session()
        else:
            raise ValueError("API key or username/password must be provided")

        # SSL 설정
        self.session.verify = self.verify_ssl
        if not self.verify_ssl:
            import urllib3

            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def _login_session(self):
        """사용자명/비밀번호로 세션 로그인"""
        login_url = f"https://{self.host}:{self.port}/logincheck"
        login_data = {"username": self.username, "secretkey": self.password}

        try:
            response = self.session.post(login_url, data=login_data, timeout=self.timeout, verify=self.verify_ssl)
            response.raise_for_status()
            logger.info("Session login successful")
        except Exception as e:
            logger.error(f"Session login failed: {e}")
            raise

    async def _make_request(
        self, method: str, endpoint: str, params: Dict = None, data: Dict = None, timeout: int = None
    ) -> Dict[str, Any]:
        """
        비동기 API 요청 실행

        Args:
            method: HTTP 메소드
            endpoint: API 엔드포인트
            params: 쿼리 파라미터
            data: 요청 데이터
            timeout: 타임아웃 (기본값 사용 시 None)

        Returns:
            API 응답 데이터
        """
        start_time = time.time()
        self.api_stats["total_requests"] += 1

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        request_timeout = timeout or self.timeout

        try:
            # 동기 요청을 비동기로 실행
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, lambda: self.session.request(method, url, params=params, json=data, timeout=request_timeout)
            )

            response.raise_for_status()

            # 응답 시간 통계 업데이트
            response_time = time.time() - start_time
            self._update_stats(response_time, True)

            # JSON 응답 파싱
            result = response.json()

            logger.debug(f"API request successful: {method} {endpoint} ({response_time:.3f}s)")
            return result

        except requests.exceptions.RequestException as e:
            self._update_stats(time.time() - start_time, False)
            logger.error(f"API request failed: {method} {endpoint} - {e}")
            raise
        except json.JSONDecodeError as e:
            self._update_stats(time.time() - start_time, False)
            logger.error(f"Invalid JSON response: {e}")
            raise
        except Exception as e:
            self._update_stats(time.time() - start_time, False)
            logger.error(f"Unexpected error during API request: {method} {endpoint} - {e}")
            raise

    def _update_stats(self, response_time: float, success: bool):
        """API 통계 업데이트"""
        if success:
            self.api_stats["successful_requests"] += 1
        else:
            self.api_stats["failed_requests"] += 1

        self.api_stats["last_request_time"] = time.time()

        # 평균 응답 시간 계산
        total_requests = self.api_stats["total_requests"]
        if total_requests > 0:
            current_avg = self.api_stats["average_response_time"]
            self.api_stats["average_response_time"] = (
                current_avg * (total_requests - 1) + response_time
            ) / total_requests
        else:
            self.api_stats["average_response_time"] = response_time

    # ===== 방화벽 정책 관리 =====

    async def get_firewall_policies(self, vdom: str = "root", filters: Dict = None) -> List[Dict[str, Any]]:
        """
        방화벽 정책 목록 조회 (고급 필터링)

        Args:
            vdom: Virtual Domain 이름
            filters: 필터링 조건 (srcintf, dstintf, action 등)

        Returns:
            방화벽 정책 목록
        """
        endpoint = "cmdb/firewall/policy"
        params = {"vdom": vdom}

        if filters:
            params.update(filters)

        try:
            response = await self._make_request("GET", endpoint, params=params)
            policies = response.get("results", [])

            logger.info(f"Retrieved {len(policies)} firewall policies from {vdom}")
            return policies

        except Exception as e:
            logger.error(f"Failed to get firewall policies: {e}")
            raise

    async def create_firewall_policy(self, policy_data: Dict[str, Any], vdom: str = "root") -> Dict[str, Any]:
        """
        새로운 방화벽 정책 생성

        Args:
            policy_data: 정책 데이터
            vdom: Virtual Domain 이름

        Returns:
            생성된 정책 정보
        """
        endpoint = "cmdb/firewall/policy"
        params = {"vdom": vdom}

        # 필수 필드 검증
        required_fields = ["name", "srcintf", "dstintf", "srcaddr", "dstaddr", "service", "action"]
        missing_fields = [field for field in required_fields if field not in policy_data]

        if missing_fields:
            raise ValueError(f"Missing required fields: {missing_fields}")

        try:
            response = await self._make_request("POST", endpoint, params=params, data=policy_data)
            logger.info(f"Created firewall policy: {policy_data.get('name')}")
            return response

        except Exception as e:
            logger.error(f"Failed to create firewall policy: {e}")
            raise

    async def update_firewall_policy(
        self, policy_id: int, policy_data: Dict[str, Any], vdom: str = "root"
    ) -> Dict[str, Any]:
        """
        방화벽 정책 업데이트

        Args:
            policy_id: 정책 ID
            policy_data: 업데이트할 데이터
            vdom: Virtual Domain 이름

        Returns:
            업데이트 결과
        """
        endpoint = f"cmdb/firewall/policy/{policy_id}"
        params = {"vdom": vdom}

        try:
            response = await self._make_request("PUT", endpoint, params=params, data=policy_data)
            logger.info(f"Updated firewall policy ID {policy_id}")
            return response

        except Exception as e:
            logger.error(f"Failed to update firewall policy {policy_id}: {e}")
            raise

    async def delete_firewall_policy(self, policy_id: int, vdom: str = "root") -> Dict[str, Any]:
        """
        방화벽 정책 삭제

        Args:
            policy_id: 삭제할 정책 ID
            vdom: Virtual Domain 이름

        Returns:
            삭제 결과
        """
        endpoint = f"cmdb/firewall/policy/{policy_id}"
        params = {"vdom": vdom}

        try:
            response = await self._make_request("DELETE", endpoint, params=params)
            logger.info(f"Deleted firewall policy ID {policy_id}")
            return response

        except Exception as e:
            logger.error(f"Failed to delete firewall policy {policy_id}: {e}")
            raise

    # ===== VPN 관리 =====

    async def get_ipsec_vpn_tunnels(self, vdom: str = "root") -> List[Dict[str, Any]]:
        """IPSec VPN 터널 목록 조회"""
        endpoint = "cmdb/vpn.ipsec/phase1-interface"
        params = {"vdom": vdom}

        try:
            response = await self._make_request("GET", endpoint, params=params)
            tunnels = response.get("results", [])

            logger.info(f"Retrieved {len(tunnels)} IPSec VPN tunnels")
            return tunnels

        except Exception as e:
            logger.error(f"Failed to get IPSec VPN tunnels: {e}")
            raise

    async def get_ssl_vpn_settings(self, vdom: str = "root") -> Dict[str, Any]:
        """SSL VPN 설정 조회"""
        endpoint = "cmdb/vpn.ssl/settings"
        params = {"vdom": vdom}

        try:
            response = await self._make_request("GET", endpoint, params=params)
            settings = response.get("results", {})

            logger.info("Retrieved SSL VPN settings")
            return settings

        except Exception as e:
            logger.error(f"Failed to get SSL VPN settings: {e}")
            raise

    async def create_ipsec_vpn_tunnel(self, tunnel_data: Dict[str, Any], vdom: str = "root") -> Dict[str, Any]:
        """새로운 IPSec VPN 터널 생성"""
        endpoint = "cmdb/vpn.ipsec/phase1-interface"
        params = {"vdom": vdom}

        # 필수 필드 검증
        required_fields = ["name", "interface", "remote-gw", "psksecret"]
        missing_fields = [field for field in required_fields if field not in tunnel_data]

        if missing_fields:
            raise ValueError(f"Missing required fields for VPN tunnel: {missing_fields}")

        try:
            response = await self._make_request("POST", endpoint, params=params, data=tunnel_data)
            logger.info(f"Created IPSec VPN tunnel: {tunnel_data.get('name')}")
            return response

        except Exception as e:
            logger.error(f"Failed to create IPSec VPN tunnel: {e}")
            raise

    # ===== NAT 정책 관리 =====

    async def get_nat_policies(self, policy_type: str = "ipv4", vdom: str = "root") -> List[Dict[str, Any]]:
        """
        NAT 정책 목록 조회

        Args:
            policy_type: NAT 정책 타입 (ipv4, ipv6)
            vdom: Virtual Domain 이름

        Returns:
            NAT 정책 목록
        """
        endpoint = f"cmdb/firewall/{policy_type}-policy"
        params = {"vdom": vdom, "with_meta": True}

        try:
            response = await self._make_request("GET", endpoint, params=params)
            policies = response.get("results", [])

            # NAT가 활성화된 정책만 필터링
            nat_policies = [
                policy for policy in policies if policy.get("nat") == "enable" or policy.get("ippool") == "enable"
            ]

            logger.info(f"Retrieved {len(nat_policies)} NAT policies")
            return nat_policies

        except Exception as e:
            logger.error(f"Failed to get NAT policies: {e}")
            raise

    async def create_snat_policy(self, policy_data: Dict[str, Any], vdom: str = "root") -> Dict[str, Any]:
        """Source NAT 정책 생성"""
        # SNAT 설정 추가
        policy_data.update({"nat": "enable", "ippool": "enable" if policy_data.get("poolname") else "disable"})

        return await self.create_firewall_policy(policy_data, vdom)

    # ===== 보안 프로필 관리 =====

    async def get_security_profiles(self, profile_type: str, vdom: str = "root") -> List[Dict[str, Any]]:
        """
        보안 프로필 목록 조회

        Args:
            profile_type: 프로필 타입 (ips, antivirus, webfilter, application)
            vdom: Virtual Domain 이름

        Returns:
            보안 프로필 목록
        """
        profile_endpoints = {
            "ips": "cmdb/ips/sensor",
            "antivirus": "cmdb/antivirus/profile",
            "webfilter": "cmdb/webfilter/profile",
            "application": "cmdb/application/list",
        }

        endpoint = profile_endpoints.get(profile_type)
        if not endpoint:
            raise ValueError(f"Invalid profile type: {profile_type}")

        params = {"vdom": vdom}

        try:
            response = await self._make_request("GET", endpoint, params=params)
            profiles = response.get("results", [])

            logger.info(f"Retrieved {len(profiles)} {profile_type} profiles")
            return profiles

        except Exception as e:
            logger.error(f"Failed to get {profile_type} profiles: {e}")
            raise

    async def apply_security_profile_to_policy(
        self, policy_id: int, security_profiles: Dict[str, str], vdom: str = "root"
    ) -> Dict[str, Any]:
        """
        방화벽 정책에 보안 프로필 적용

        Args:
            policy_id: 정책 ID
            security_profiles: 보안 프로필 매핑 {'ips': 'profile_name', ...}
            vdom: Virtual Domain 이름

        Returns:
            업데이트 결과
        """
        # 기존 정책 조회
        endpoint = f"cmdb/firewall/policy/{policy_id}"
        params = {"vdom": vdom}

        try:
            # Get existing policy data (not currently used but validates policy exists)
            await self._make_request("GET", endpoint, params=params)

            # 보안 프로필 설정 업데이트
            profile_mappings = {
                "ips": "ips-sensor",
                "antivirus": "av-profile",
                "webfilter": "webfilter-profile",
                "application": "application-list",
            }

            update_data = {}
            for profile_type, profile_name in security_profiles.items():
                if profile_type in profile_mappings:
                    update_data[profile_mappings[profile_type]] = profile_name

            # SSL 검사 활성화 (HTTPS 트래픽 검사를 위해)
            if any(key in security_profiles for key in ["ips", "antivirus", "webfilter"]):
                update_data["ssl-ssh-profile"] = "deep-inspection"

            # 정책 업데이트
            return await self.update_firewall_policy(policy_id, update_data, vdom)

        except Exception as e:
            logger.error(f"Failed to apply security profiles to policy {policy_id}: {e}")
            raise

    # ===== 실시간 로그 모니터링 =====

    async def get_realtime_logs(
        self, log_type: str = "traffic", filters: Dict = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        실시간 로그 조회

        Args:
            log_type: 로그 타입 (traffic, security, system)
            filters: 로그 필터링 조건
            limit: 조회할 로그 개수

        Returns:
            로그 목록
        """
        endpoint = f"monitor/log/{log_type}/select"

        params = {"count": limit, "start": 0}

        if filters:
            # 필터 조건을 쿼리 파라미터로 변환
            filter_str = " and ".join([f"{key}='{value}'" for key, value in filters.items()])
            params["filter"] = filter_str

        try:
            response = await self._make_request("GET", endpoint, params=params)
            logs = response.get("results", [])

            logger.info(f"Retrieved {len(logs)} {log_type} logs")
            return logs

        except Exception as e:
            logger.error(f"Failed to get {log_type} logs: {e}")
            raise

    async def stream_logs(self, log_type: str = "traffic", callback: callable = None, interval: int = 5) -> None:
        """
        실시간 로그 스트리밍

        Args:
            log_type: 로그 타입
            callback: 로그 처리 콜백 함수
            interval: 폴링 간격 (초)
        """
        last_timestamp = None

        while True:
            try:
                filters = {}
                if last_timestamp:
                    filters["timestamp"] = f">{last_timestamp}"

                logs = await self.get_realtime_logs(log_type, filters, 50)

                if logs and callback:
                    for log in logs:
                        await callback(log)

                    # 마지막 타임스탬프 업데이트
                    last_timestamp = max(log.get("timestamp", 0) for log in logs)

                await asyncio.sleep(interval)

            except Exception as e:
                logger.error(f"Log streaming error: {e}")
                await asyncio.sleep(interval * 2)  # 에러 시 더 긴 간격으로 재시도

    # ===== 시스템 모니터링 =====

    async def get_system_status(self, vdom: str = "root") -> Dict[str, Any]:
        """시스템 상태 조회"""
        endpoint = "monitor/system/status"
        params = {"vdom": vdom}

        try:
            response = await self._make_request("GET", endpoint, params=params)
            status = response.get("results", {})

            logger.info("Retrieved system status")
            return status

        except Exception as e:
            logger.error(f"Failed to get system status: {e}")
            raise

    async def get_performance_stats(self, vdom: str = "root") -> Dict[str, Any]:
        """성능 통계 조회"""
        endpoint = "monitor/system/performance/status"
        params = {"vdom": vdom}

        try:
            response = await self._make_request("GET", endpoint, params=params)
            stats = response.get("results", {})

            logger.info("Retrieved performance statistics")
            return stats

        except Exception as e:
            logger.error(f"Failed to get performance stats: {e}")
            raise

    async def get_interface_stats(
        self, interface_name: str = None, vdom: str = "root"
    ) -> Union[List[Dict], Dict[str, Any]]:
        """네트워크 인터페이스 통계 조회"""
        if interface_name:
            endpoint = "monitor/system/interface/select"
            params = {"vdom": vdom, "interface_name": interface_name}
        else:
            endpoint = "monitor/system/available-interfaces/select"
            params = {"vdom": vdom}

        try:
            response = await self._make_request("GET", endpoint, params=params)
            stats = response.get("results", [] if not interface_name else {})

            logger.info(f"Retrieved interface statistics for {interface_name or 'all interfaces'}")
            return stats

        except Exception as e:
            logger.error(f"Failed to get interface stats: {e}")
            raise

    # ===== 고급 분석 기능 =====

    async def analyze_traffic_patterns(self, time_range: int = 3600, vdom: str = "root") -> Dict[str, Any]:
        """
        트래픽 패턴 분석

        Args:
            time_range: 분석 시간 범위 (초)
            vdom: Virtual Domain 이름

        Returns:
            트래픽 분석 결과
        """
        # 트래픽 로그 조회
        end_time = int(time.time())
        start_time = end_time - time_range

        filters = {"start_time": f">={start_time}", "end_time": f"<={end_time}"}

        try:
            logs = await self.get_realtime_logs("traffic", filters, 1000)

            # 트래픽 패턴 분석
            analysis = {
                "total_sessions": len(logs),
                "time_range": {"start": start_time, "end": end_time},
                "top_sources": {},
                "top_destinations": {},
                "top_applications": {},
                "protocol_distribution": {},
                "blocked_sessions": 0,
                "allowed_sessions": 0,
            }

            for log in logs:
                # Source IP 통계
                src_ip = log.get("srcip", "unknown")
                analysis["top_sources"][src_ip] = analysis["top_sources"].get(src_ip, 0) + 1

                # Destination IP 통계
                dst_ip = log.get("dstip", "unknown")
                analysis["top_destinations"][dst_ip] = analysis["top_destinations"].get(dst_ip, 0) + 1

                # Application 통계
                app = log.get("app", "unknown")
                analysis["top_applications"][app] = analysis["top_applications"].get(app, 0) + 1

                # Protocol 통계
                proto = log.get("proto", "unknown")
                analysis["protocol_distribution"][proto] = analysis["protocol_distribution"].get(proto, 0) + 1

                # Action 통계
                action = log.get("action", "unknown")
                if action.lower() in ["deny", "block"]:
                    analysis["blocked_sessions"] += 1
                elif action.lower() in ["accept", "allow"]:
                    analysis["allowed_sessions"] += 1

            # Top 10으로 제한
            for key in ["top_sources", "top_destinations", "top_applications", "protocol_distribution"]:
                analysis[key] = dict(sorted(analysis[key].items(), key=lambda x: x[1], reverse=True)[:10])

            logger.info(f"Analyzed {len(logs)} traffic sessions over {time_range} seconds")
            return analysis

        except Exception as e:
            logger.error(f"Failed to analyze traffic patterns: {e}")
            raise

    async def detect_security_threats(
        self, time_range: int = 3600, severity_threshold: str = "medium"
    ) -> List[Dict[str, Any]]:
        """
        보안 위협 탐지

        Args:
            time_range: 탐지 시간 범위 (초)
            severity_threshold: 심각도 임계값 (low, medium, high, critical)

        Returns:
            탐지된 보안 위협 목록
        """
        end_time = int(time.time())
        start_time = end_time - time_range

        filters = {"timestamp": f">={start_time}", "level": severity_threshold}

        try:
            # 보안 로그 조회
            security_logs = await self.get_realtime_logs("security", filters, 500)

            threats = []
            severity_levels = {"low": 1, "medium": 2, "high": 3, "critical": 4}
            threshold_level = severity_levels.get(severity_threshold, 2)

            for log in security_logs:
                log_severity = log.get("level", "low")
                if severity_levels.get(log_severity, 1) >= threshold_level:
                    threat = {
                        "timestamp": log.get("timestamp"),
                        "source_ip": log.get("srcip"),
                        "destination_ip": log.get("dstip"),
                        "threat_type": log.get("attack"),
                        "severity": log_severity,
                        "signature": log.get("msg"),
                        "action_taken": log.get("action"),
                        "interface": log.get("srcintf"),
                    }
                    threats.append(threat)

            # 심각도별로 정렬
            threats.sort(key=lambda x: severity_levels.get(x["severity"], 1), reverse=True)

            logger.info(f"Detected {len(threats)} security threats above {severity_threshold} level")
            return threats

        except Exception as e:
            logger.error(f"Failed to detect security threats: {e}")
            raise

    # ===== API 통계 및 상태 =====

    def get_api_statistics(self) -> Dict[str, Any]:
        """API 사용 통계 반환"""
        stats = self.api_stats.copy()

        if stats["total_requests"] > 0:
            stats["success_rate"] = (stats["successful_requests"] / stats["total_requests"]) * 100
        else:
            stats["success_rate"] = 0

        if stats["last_request_time"]:
            stats["last_request_ago"] = time.time() - stats["last_request_time"]

        return stats

    async def test_connection(self) -> Dict[str, Any]:
        """API 연결 테스트"""
        try:
            start_time = time.time()

            # 간단한 상태 조회로 연결 테스트
            response = await self._make_request("GET", "monitor/system/status")

            connection_time = time.time() - start_time

            result = {
                "status": "connected",
                "response_time": connection_time,
                "fortigate_version": response.get("results", {}).get("version"),
                "api_statistics": self.get_api_statistics(),
            }

            logger.info(f"Connection test successful ({connection_time:.3f}s)")
            return result

        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return {"status": "failed", "error": str(e), "api_statistics": self.get_api_statistics()}

    def close(self):
        """API 클라이언트 정리"""
        if hasattr(self, "session"):
            self.session.close()
        logger.info("FortiGate API client closed")


# ===== 유틸리티 함수들 =====


def create_fortigate_api_client(config: Dict[str, Any]) -> AdvancedFortiGateAPI:
    """
    설정으로부터 FortiGate API 클라이언트 생성

    Args:
        config: API 클라이언트 설정

    Returns:
        초기화된 API 클라이언트
    """
    required_fields = ["host"]
    missing_fields = [field for field in required_fields if field not in config]

    if missing_fields:
        raise ValueError(f"Missing required config fields: {missing_fields}")

    return AdvancedFortiGateAPI(**config)


async def batch_policy_operations(
    api_client: AdvancedFortiGateAPI, operations: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    배치 정책 작업 실행

    Args:
        api_client: FortiGate API 클라이언트
        operations: 작업 목록 [{"action": "create|update|delete", "data": {...}}]

    Returns:
        작업 결과 목록
    """
    results = []

    for operation in operations:
        action = operation.get("action")
        data = operation.get("data", {})

        try:
            if action == "create":
                result = await api_client.create_firewall_policy(data)
            elif action == "update":
                policy_id = operation.get("policy_id")
                result = await api_client.update_firewall_policy(policy_id, data)
            elif action == "delete":
                policy_id = operation.get("policy_id")
                result = await api_client.delete_firewall_policy(policy_id)
            else:
                raise ValueError(f"Unknown action: {action}")

            results.append({"status": "success", "action": action, "result": result})

        except Exception as e:
            results.append({"status": "error", "action": action, "error": str(e)})

    return results


# ===== 전역 API 클라이언트 인스턴스 관리 =====

_global_api_client = None


def get_fortigate_api_client() -> Optional[AdvancedFortiGateAPI]:
    """전역 FortiGate API 클라이언트 반환"""
    return _global_api_client


def initialize_global_api_client(config: Dict[str, Any]) -> AdvancedFortiGateAPI:
    """전역 FortiGate API 클라이언트 초기화"""
    global _global_api_client

    if _global_api_client:
        _global_api_client.close()

    _global_api_client = create_fortigate_api_client(config)
    logger.info("Global FortiGate API client initialized")

    return _global_api_client


def close_global_api_client():
    """전역 FortiGate API 클라이언트 정리"""
    global _global_api_client

    if _global_api_client:
        _global_api_client.close()
        _global_api_client = None
        logger.info("Global FortiGate API client closed")
