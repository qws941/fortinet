#!/usr/bin/env python3
"""
FortiGate API 검증 및 테스트 프레임워크
고급 FortiGate API 기능의 유효성 검사 및 자동화된 테스트

기능:
- API 연결 검증
- API 응답 유효성 검사
- 성능 테스트 및 벤치마킹
- 보안 검사 및 취약점 스캐닝
- 자동화된 기능 테스트
- 실시간 모니터링 검증
"""

import asyncio
import json
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List

from api.advanced_fortigate_api import AdvancedFortiGateAPI
from utils.unified_logger import get_logger

logger = get_logger(__name__)


class ValidationSeverity(Enum):
    """검증 결과 심각도"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationResult:
    """검증 결과 데이터 클래스"""

    test_name: str
    status: str  # "pass", "fail", "skip"
    severity: ValidationSeverity
    message: str
    details: Dict[str, Any] = None
    execution_time: float = 0.0
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.details is None:
            self.details = {}


class FortiGateAPIValidator:
    """FortiGate API 검증 프레임워크"""

    def __init__(self, api_client: AdvancedFortiGateAPI):
        """
        검증기 초기화

        Args:
            api_client: 검증할 FortiGate API 클라이언트
        """
        self.api_client = api_client
        self.results: List[ValidationResult] = []
        self.test_config = {
            "timeout_threshold": 5.0,  # API 응답 시간 임계값 (초)
            "performance_samples": 10,  # 성능 테스트 샘플 수
            "security_scan_depth": "basic",  # 보안 스캔 깊이 (basic, full)
            "concurrent_connections": 5,  # 동시 연결 테스트 수
        }

        logger.info("FortiGate API validator initialized")

    def configure_tests(self, config: Dict[str, Any]):
        """테스트 설정 업데이트"""
        self.test_config.update(config)
        logger.info(f"Test configuration updated: {config}")

    async def run_all_validations(self, test_categories: List[str] = None) -> Dict[str, Any]:
        """
        모든 검증 테스트 실행

        Args:
            test_categories: 실행할 테스트 카테고리 목록
                           (None이면 모든 테스트 실행)

        Returns:
            종합 검증 결과
        """
        start_time = time.time()
        self.results = []

        # 기본 테스트 카테고리
        if test_categories is None:
            test_categories = [
                "connection",
                "authentication",
                "basic_operations",
                "performance",
                "security",
                "functionality",
                "monitoring",
            ]

        logger.info(f"Starting validation tests: {test_categories}")

        # 테스트 카테고리별 실행
        for category in test_categories:
            try:
                await self._run_category_tests(category)
            except Exception as e:
                self._add_result(
                    ValidationResult(
                        test_name=f"{category}_category",
                        status="fail",
                        severity=ValidationSeverity.ERROR,
                        message=f"Test category {category} failed: {str(e)}",
                    )
                )

        total_time = time.time() - start_time

        # 결과 집계
        summary = self._generate_summary(total_time)

        logger.info(
            f"Validation completed in {total_time:.2f}s - "
            f"{summary['total_tests']} tests, {summary['passed']} passed, "
            f"{summary['failed']} failed"
        )

        return {
            "summary": summary,
            "results": [self._result_to_dict(r) for r in self.results],
            "test_config": self.test_config,
            "execution_time": total_time,
        }

    async def _run_category_tests(self, category: str):
        """카테고리별 테스트 실행"""
        test_methods = {
            "connection": self._test_connection,
            "authentication": self._test_authentication,
            "basic_operations": self._test_basic_operations,
            "performance": self._test_performance,
            "security": self._test_security,
            "functionality": self._test_functionality,
            "monitoring": self._test_monitoring,
        }

        test_method = test_methods.get(category)
        if test_method:
            await test_method()
        else:
            self._add_result(
                ValidationResult(
                    test_name=f"unknown_category_{category}",
                    status="skip",
                    severity=ValidationSeverity.WARNING,
                    message=f"Unknown test category: {category}",
                )
            )

    # ===== 연결 테스트 =====

    async def _test_connection(self):
        """기본 연결 테스트"""
        start_time = time.time()

        try:
            connection_result = await self.api_client.test_connection()
            execution_time = time.time() - start_time

            if connection_result.get("status") == "connected":
                self._add_result(
                    ValidationResult(
                        test_name="basic_connection",
                        status="pass",
                        severity=ValidationSeverity.INFO,
                        message="API connection successful",
                        details=connection_result,
                        execution_time=execution_time,
                    )
                )
            else:
                self._add_result(
                    ValidationResult(
                        test_name="basic_connection",
                        status="fail",
                        severity=ValidationSeverity.CRITICAL,
                        message=f"API connection failed: {connection_result.get('error')}",
                        details=connection_result,
                        execution_time=execution_time,
                    )
                )

        except Exception as e:
            self._add_result(
                ValidationResult(
                    test_name="basic_connection",
                    status="fail",
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Connection test exception: {str(e)}",
                    execution_time=time.time() - start_time,
                )
            )

    async def _test_concurrent_connections(self):
        """동시 연결 테스트"""
        concurrent_count = self.test_config["concurrent_connections"]
        start_time = time.time()

        try:
            # 동시에 여러 연결 테스트 수행
            tasks = [self.api_client.test_connection() for _ in range(concurrent_count)]

            results = await asyncio.gather(*tasks, return_exceptions=True)
            execution_time = time.time() - start_time

            successful_connections = 0
            failed_connections = 0

            for result in results:
                if isinstance(result, Exception):
                    failed_connections += 1
                elif result.get("status") == "connected":
                    successful_connections += 1
                else:
                    failed_connections += 1

            if successful_connections == concurrent_count:
                severity = ValidationSeverity.INFO
                status = "pass"
                message = f"All {concurrent_count} concurrent connections successful"
            elif successful_connections > 0:
                severity = ValidationSeverity.WARNING
                status = "pass"
                message = f"{successful_connections}/{concurrent_count} concurrent connections successful"
            else:
                severity = ValidationSeverity.ERROR
                status = "fail"
                message = f"All {concurrent_count} concurrent connections failed"

            self._add_result(
                ValidationResult(
                    test_name="concurrent_connections",
                    status=status,
                    severity=severity,
                    message=message,
                    details={
                        "concurrent_count": concurrent_count,
                        "successful": successful_connections,
                        "failed": failed_connections,
                    },
                    execution_time=execution_time,
                )
            )

        except Exception as e:
            self._add_result(
                ValidationResult(
                    test_name="concurrent_connections",
                    status="fail",
                    severity=ValidationSeverity.ERROR,
                    message=f"Concurrent connection test failed: {str(e)}",
                    execution_time=time.time() - start_time,
                )
            )

    # ===== 인증 테스트 =====

    async def _test_authentication(self):
        """인증 관련 테스트"""
        await self._test_api_key_auth()
        await self._test_permission_levels()

    async def _test_api_key_auth(self):
        """API 키 인증 테스트"""
        start_time = time.time()

        try:
            # 시스템 상태 조회로 인증 테스트
            status = await self.api_client.get_system_status()
            execution_time = time.time() - start_time

            if status and "results" in status:
                self._add_result(
                    ValidationResult(
                        test_name="api_key_authentication",
                        status="pass",
                        severity=ValidationSeverity.INFO,
                        message="API key authentication successful",
                        details={"fortigate_version": status.get("results", {}).get("version")},
                        execution_time=execution_time,
                    )
                )
            else:
                self._add_result(
                    ValidationResult(
                        test_name="api_key_authentication",
                        status="fail",
                        severity=ValidationSeverity.ERROR,
                        message="API key authentication failed - no valid response",
                        execution_time=execution_time,
                    )
                )

        except Exception as e:
            self._add_result(
                ValidationResult(
                    test_name="api_key_authentication",
                    status="fail",
                    severity=ValidationSeverity.ERROR,
                    message=f"API key authentication failed: {str(e)}",
                    execution_time=time.time() - start_time,
                )
            )

    async def _test_permission_levels(self):
        """권한 레벨 테스트"""
        start_time = time.time()

        # 다양한 권한이 필요한 작업들을 테스트
        permission_tests = [
            ("read_policies", "cmdb/firewall/policy", "GET"),
            ("read_system_status", "monitor/system/status", "GET"),
            ("read_interfaces", "monitor/system/available-interfaces/select", "GET"),
        ]

        results = {}

        for test_name, endpoint, method in permission_tests:
            try:
                response = await self.api_client._make_request(method, endpoint)
                results[test_name] = "allowed" if response else "denied"
            except Exception as e:
                if "403" in str(e) or "permission" in str(e).lower():
                    results[test_name] = "denied"
                else:
                    results[test_name] = f"error: {str(e)}"

        execution_time = time.time() - start_time

        allowed_count = sum(1 for result in results.values() if result == "allowed")
        total_count = len(results)

        if allowed_count == total_count:
            status = "pass"
            severity = ValidationSeverity.INFO
            message = f"All {total_count} permission tests passed"
        elif allowed_count > 0:
            status = "pass"
            severity = ValidationSeverity.WARNING
            message = f"{allowed_count}/{total_count} permission tests passed"
        else:
            status = "fail"
            severity = ValidationSeverity.ERROR
            message = "All permission tests failed"

        self._add_result(
            ValidationResult(
                test_name="permission_levels",
                status=status,
                severity=severity,
                message=message,
                details=results,
                execution_time=execution_time,
            )
        )

    # ===== 기본 작업 테스트 =====

    async def _test_basic_operations(self):
        """기본 API 작업 테스트"""
        await self._test_policy_operations()
        await self._test_system_queries()
        await self._test_log_queries()

    async def _test_policy_operations(self):
        """방화벽 정책 작업 테스트"""
        start_time = time.time()

        try:
            # 정책 목록 조회 테스트
            policies = await self.api_client.get_firewall_policies()
            execution_time = time.time() - start_time

            if isinstance(policies, list):
                self._add_result(
                    ValidationResult(
                        test_name="policy_list_query",
                        status="pass",
                        severity=ValidationSeverity.INFO,
                        message=f"Successfully retrieved {len(policies)} firewall policies",
                        details={"policy_count": len(policies)},
                        execution_time=execution_time,
                    )
                )
            else:
                self._add_result(
                    ValidationResult(
                        test_name="policy_list_query",
                        status="fail",
                        severity=ValidationSeverity.ERROR,
                        message="Invalid response format for policy query",
                        execution_time=execution_time,
                    )
                )

        except Exception as e:
            self._add_result(
                ValidationResult(
                    test_name="policy_list_query",
                    status="fail",
                    severity=ValidationSeverity.ERROR,
                    message=f"Policy query failed: {str(e)}",
                    execution_time=time.time() - start_time,
                )
            )

    async def _test_system_queries(self):
        """시스템 쿼리 테스트"""
        start_time = time.time()

        system_tests = [
            ("system_status", self.api_client.get_system_status),
            ("performance_stats", self.api_client.get_performance_stats),
            ("interface_stats", self.api_client.get_interface_stats),
        ]

        for test_name, test_func in system_tests:
            try:
                result = await test_func()

                if result:
                    self._add_result(
                        ValidationResult(
                            test_name=test_name,
                            status="pass",
                            severity=ValidationSeverity.INFO,
                            message=f"{test_name} query successful",
                            details={"response_keys": list(result.keys()) if isinstance(result, dict) else None},
                        )
                    )
                else:
                    self._add_result(
                        ValidationResult(
                            test_name=test_name,
                            status="fail",
                            severity=ValidationSeverity.WARNING,
                            message=f"{test_name} returned empty result",
                        )
                    )

            except Exception as e:
                self._add_result(
                    ValidationResult(
                        test_name=test_name,
                        status="fail",
                        severity=ValidationSeverity.ERROR,
                        message=f"{test_name} failed: {str(e)}",
                    )
                )

        execution_time = time.time() - start_time
        logger.debug(f"System queries completed in {execution_time:.2f}s")

    async def _test_log_queries(self):
        """로그 쿼리 테스트"""
        start_time = time.time()

        log_types = ["traffic", "security", "system"]

        for log_type in log_types:
            try:
                logs = await self.api_client.get_realtime_logs(log_type, limit=10)
                execution_time = time.time() - start_time

                if isinstance(logs, list):
                    self._add_result(
                        ValidationResult(
                            test_name=f"log_query_{log_type}",
                            status="pass",
                            severity=ValidationSeverity.INFO,
                            message=f"Successfully retrieved {len(logs)} {log_type} logs",
                            details={"log_count": len(logs)},
                            execution_time=execution_time,
                        )
                    )
                else:
                    self._add_result(
                        ValidationResult(
                            test_name=f"log_query_{log_type}",
                            status="fail",
                            severity=ValidationSeverity.WARNING,
                            message=f"Invalid response format for {log_type} logs",
                            execution_time=execution_time,
                        )
                    )

            except Exception as e:
                self._add_result(
                    ValidationResult(
                        test_name=f"log_query_{log_type}",
                        status="fail",
                        severity=ValidationSeverity.ERROR,
                        message=f"{log_type} log query failed: {str(e)}",
                        execution_time=time.time() - start_time,
                    )
                )

    # ===== 성능 테스트 =====

    async def _test_performance(self):
        """성능 관련 테스트"""
        await self._test_response_times()
        await self._test_throughput()
        await self._test_concurrent_requests()

    async def _test_response_times(self):
        """응답 시간 테스트"""
        samples = self.test_config["performance_samples"]
        threshold = self.test_config["timeout_threshold"]

        response_times = []

        for i in range(samples):
            start_time = time.time()
            try:
                await self.api_client.get_system_status()
                response_time = time.time() - start_time
                response_times.append(response_time)
            except Exception as e:
                logger.warning(f"Performance test sample {i + 1} failed: {e}")

        if response_times:
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            min_time = min(response_times)

            if avg_time < threshold:
                status = "pass"
                severity = ValidationSeverity.INFO
                message = f"Average response time {avg_time:.3f}s is below threshold {threshold}s"
            else:
                status = "fail"
                severity = ValidationSeverity.WARNING
                message = f"Average response time {avg_time:.3f}s exceeds threshold {threshold}s"

            self._add_result(
                ValidationResult(
                    test_name="response_time_performance",
                    status=status,
                    severity=severity,
                    message=message,
                    details={
                        "samples": len(response_times),
                        "average_time": avg_time,
                        "max_time": max_time,
                        "min_time": min_time,
                        "threshold": threshold,
                    },
                )
            )
        else:
            self._add_result(
                ValidationResult(
                    test_name="response_time_performance",
                    status="fail",
                    severity=ValidationSeverity.ERROR,
                    message="No successful response time samples collected",
                )
            )

    async def _test_throughput(self):
        """처리량 테스트"""
        start_time = time.time()
        request_count = 50

        try:
            # 짧은 시간 내 많은 요청 수행
            tasks = [self.api_client.get_system_status() for _ in range(request_count)]

            results = await asyncio.gather(*tasks, return_exceptions=True)
            execution_time = time.time() - start_time

            successful_requests = sum(1 for r in results if not isinstance(r, Exception))
            failed_requests = request_count - successful_requests

            throughput = successful_requests / execution_time if execution_time > 0 else 0

            if successful_requests >= request_count * 0.8:  # 80% 성공률
                status = "pass"
                severity = ValidationSeverity.INFO
                message = f"Throughput test passed: {throughput:.1f} requests/sec"
            else:
                status = "fail"
                severity = ValidationSeverity.WARNING
                message = f"Low success rate in throughput test: {successful_requests}/{request_count}"

            self._add_result(
                ValidationResult(
                    test_name="throughput_performance",
                    status=status,
                    severity=severity,
                    message=message,
                    details={
                        "total_requests": request_count,
                        "successful_requests": successful_requests,
                        "failed_requests": failed_requests,
                        "execution_time": execution_time,
                        "throughput_per_sec": throughput,
                    },
                )
            )

        except Exception as e:
            self._add_result(
                ValidationResult(
                    test_name="throughput_performance",
                    status="fail",
                    severity=ValidationSeverity.ERROR,
                    message=f"Throughput test failed: {str(e)}",
                    execution_time=time.time() - start_time,
                )
            )

    async def _test_concurrent_requests(self):
        """동시 요청 처리 테스트"""
        await self._test_concurrent_connections()

    # ===== 보안 테스트 =====

    async def _test_security(self):
        """보안 관련 테스트"""
        await self._test_ssl_configuration()
        await self._test_api_security()
        await self._test_threat_detection()

    async def _test_ssl_configuration(self):
        """SSL/TLS 설정 테스트"""
        start_time = time.time()

        try:
            import socket
            import ssl

            # SSL 인증서 정보 확인
            context = ssl.create_default_context()

            with socket.create_connection((self.api_client.host, self.api_client.port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=self.api_client.host) as ssock:
                    cert = ssock.getpeercert()
                    cipher = ssock.cipher()

            execution_time = time.time() - start_time

            # SSL 설정 분석
            ssl_version = cipher[1] if cipher else "unknown"
            cert_subject = dict(x[0] for x in cert.get("subject", []))
            cert_issuer = dict(x[0] for x in cert.get("issuer", []))

            # 만료일 확인
            not_after = cert.get("notAfter")
            if not_after:
                expire_date = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
                days_until_expiry = (expire_date - datetime.now()).days
            else:
                days_until_expiry = None

            # 보안 평가
            if ssl_version in ["TLSv1.2", "TLSv1.3"]:
                if days_until_expiry is None or days_until_expiry > 30:
                    status = "pass"
                    severity = ValidationSeverity.INFO
                    message = f"SSL configuration secure ({ssl_version})"
                else:
                    status = "pass"
                    severity = ValidationSeverity.WARNING
                    message = f"SSL cert expires in {days_until_expiry} days"
            else:
                status = "fail"
                severity = ValidationSeverity.ERROR
                message = f"Insecure SSL version: {ssl_version}"

            self._add_result(
                ValidationResult(
                    test_name="ssl_configuration",
                    status=status,
                    severity=severity,
                    message=message,
                    details={
                        "ssl_version": ssl_version,
                        "cert_subject": cert_subject,
                        "cert_issuer": cert_issuer,
                        "days_until_expiry": days_until_expiry,
                    },
                    execution_time=execution_time,
                )
            )

        except Exception as e:
            self._add_result(
                ValidationResult(
                    test_name="ssl_configuration",
                    status="fail",
                    severity=ValidationSeverity.ERROR,
                    message=f"SSL configuration test failed: {str(e)}",
                    execution_time=time.time() - start_time,
                )
            )

    async def _test_api_security(self):
        """API 보안 테스트"""
        start_time = time.time()

        security_checks = []

        # API 키 보안 검증
        if hasattr(self.api_client, "api_key") and self.api_client.api_key:
            api_key = self.api_client.api_key

            # API 키 강도 검사
            if len(api_key) >= 32:
                security_checks.append(("api_key_length", "pass", "API key length adequate"))
            else:
                security_checks.append(("api_key_length", "fail", "API key too short"))

            # API 키 복잡성 검사 (간단한 버전)
            if (
                any(c.isupper() for c in api_key)
                and any(c.islower() for c in api_key)
                and any(c.isdigit() for c in api_key)
            ):
                security_checks.append(("api_key_complexity", "pass", "API key has mixed case and digits"))
            else:
                security_checks.append(("api_key_complexity", "warning", "API key lacks complexity"))

        # 세션 보안 확인
        if hasattr(self.api_client, "session") and self.api_client.session:
            headers = self.api_client.session.headers

            if "Authorization" in headers:
                security_checks.append(("authorization_header", "pass", "Authorization header present"))
            else:
                security_checks.append(("authorization_header", "fail", "No authorization header"))

        execution_time = time.time() - start_time

        # 결과 집계
        failed_checks = [check for check in security_checks if check[1] == "fail"]
        warning_checks = [check for check in security_checks if check[1] == "warning"]

        if not failed_checks:
            if warning_checks:
                status = "pass"
                severity = ValidationSeverity.WARNING
                message = f"API security acceptable with {len(warning_checks)} warnings"
            else:
                status = "pass"
                severity = ValidationSeverity.INFO
                message = "API security checks passed"
        else:
            status = "fail"
            severity = ValidationSeverity.ERROR
            message = f"API security issues: {len(failed_checks)} failures"

        self._add_result(
            ValidationResult(
                test_name="api_security",
                status=status,
                severity=severity,
                message=message,
                details={"security_checks": security_checks},
                execution_time=execution_time,
            )
        )

    async def _test_threat_detection(self):
        """위협 탐지 기능 테스트"""
        start_time = time.time()

        try:
            # 최근 보안 위협 조회
            threats = await self.api_client.detect_security_threats(
                time_range=3600, severity_threshold="medium"  # 1시간
            )

            execution_time = time.time() - start_time

            if isinstance(threats, list):
                high_severity_threats = [t for t in threats if t.get("severity") in ["high", "critical"]]

                if len(high_severity_threats) == 0:
                    status = "pass"
                    severity = ValidationSeverity.INFO
                    message = f"No high-severity threats detected ({len(threats)} total threats)"
                elif len(high_severity_threats) < 10:
                    status = "pass"
                    severity = ValidationSeverity.WARNING
                    message = f"{len(high_severity_threats)} high-severity threats detected"
                else:
                    status = "fail"
                    severity = ValidationSeverity.ERROR
                    message = f"High number of severe threats: {len(high_severity_threats)}"

                self._add_result(
                    ValidationResult(
                        test_name="threat_detection",
                        status=status,
                        severity=severity,
                        message=message,
                        details={
                            "total_threats": len(threats),
                            "high_severity_threats": len(high_severity_threats),
                            "threat_types": list(set(t.get("threat_type", "unknown") for t in threats)),
                        },
                        execution_time=execution_time,
                    )
                )
            else:
                self._add_result(
                    ValidationResult(
                        test_name="threat_detection",
                        status="fail",
                        severity=ValidationSeverity.ERROR,
                        message="Invalid response format for threat detection",
                        execution_time=execution_time,
                    )
                )

        except Exception as e:
            self._add_result(
                ValidationResult(
                    test_name="threat_detection",
                    status="fail",
                    severity=ValidationSeverity.WARNING,
                    message=f"Threat detection test failed: {str(e)}",
                    execution_time=time.time() - start_time,
                )
            )

    # ===== 기능 테스트 =====

    async def _test_functionality(self):
        """고급 기능 테스트"""
        await self._test_vpn_functionality()
        await self._test_security_profiles()
        await self._test_nat_policies()
        await self._test_traffic_analysis()

    async def _test_vpn_functionality(self):
        """VPN 기능 테스트"""
        start_time = time.time()

        try:
            # IPSec VPN 터널 조회
            ipsec_tunnels = await self.api_client.get_ipsec_vpn_tunnels()

            # SSL VPN 설정 조회
            ssl_vpn_settings = await self.api_client.get_ssl_vpn_settings()

            execution_time = time.time() - start_time

            vpn_features = {
                "ipsec_tunnels": len(ipsec_tunnels) if isinstance(ipsec_tunnels, list) else 0,
                "ssl_vpn_enabled": bool(ssl_vpn_settings.get("status") == "enable") if ssl_vpn_settings else False,
            }

            if vpn_features["ipsec_tunnels"] > 0 or vpn_features["ssl_vpn_enabled"]:
                status = "pass"
                severity = ValidationSeverity.INFO
                message = "VPN functionality available"
            else:
                status = "pass"
                severity = ValidationSeverity.INFO
                message = "No VPN configuration found (may be intentional)"

            self._add_result(
                ValidationResult(
                    test_name="vpn_functionality",
                    status=status,
                    severity=severity,
                    message=message,
                    details=vpn_features,
                    execution_time=execution_time,
                )
            )

        except Exception as e:
            self._add_result(
                ValidationResult(
                    test_name="vpn_functionality",
                    status="fail",
                    severity=ValidationSeverity.WARNING,
                    message=f"VPN functionality test failed: {str(e)}",
                    execution_time=time.time() - start_time,
                )
            )

    async def _test_security_profiles(self):
        """보안 프로필 테스트"""
        start_time = time.time()

        profile_types = ["ips", "antivirus", "webfilter", "application"]
        profile_results = {}

        for profile_type in profile_types:
            try:
                profiles = await self.api_client.get_security_profiles(profile_type)
                profile_results[profile_type] = len(profiles) if isinstance(profiles, list) else 0
            except Exception as e:
                profile_results[profile_type] = f"error: {str(e)}"

        execution_time = time.time() - start_time

        # 결과 분석
        available_profiles = sum(count for count in profile_results.values() if isinstance(count, int) and count > 0)

        if available_profiles > 0:
            status = "pass"
            severity = ValidationSeverity.INFO
            message = f"Security profiles available: {available_profiles} total"
        else:
            status = "pass"
            severity = ValidationSeverity.WARNING
            message = "No security profiles configured"

        self._add_result(
            ValidationResult(
                test_name="security_profiles",
                status=status,
                severity=severity,
                message=message,
                details=profile_results,
                execution_time=execution_time,
            )
        )

    async def _test_nat_policies(self):
        """NAT 정책 테스트"""
        start_time = time.time()

        try:
            nat_policies = await self.api_client.get_nat_policies()
            execution_time = time.time() - start_time

            if isinstance(nat_policies, list):
                status = "pass"
                severity = ValidationSeverity.INFO
                message = f"NAT policies accessible: {len(nat_policies)} found"
                details = {"nat_policy_count": len(nat_policies)}
            else:
                status = "fail"
                severity = ValidationSeverity.WARNING
                message = "Invalid NAT policy response format"
                details = {"response_type": type(nat_policies).__name__}

            self._add_result(
                ValidationResult(
                    test_name="nat_policies",
                    status=status,
                    severity=severity,
                    message=message,
                    details=details,
                    execution_time=execution_time,
                )
            )

        except Exception as e:
            self._add_result(
                ValidationResult(
                    test_name="nat_policies",
                    status="fail",
                    severity=ValidationSeverity.WARNING,
                    message=f"NAT policy test failed: {str(e)}",
                    execution_time=time.time() - start_time,
                )
            )

    async def _test_traffic_analysis(self):
        """트래픽 분석 기능 테스트"""
        start_time = time.time()

        try:
            # 트래픽 패턴 분석 (짧은 시간 범위로 테스트)
            analysis = await self.api_client.analyze_traffic_patterns(time_range=600)  # 10분

            execution_time = time.time() - start_time

            if isinstance(analysis, dict) and "total_sessions" in analysis:
                session_count = analysis.get("total_sessions", 0)

                status = "pass"
                if session_count > 100:
                    severity = ValidationSeverity.INFO
                    message = f"Traffic analysis working well: {session_count} sessions analyzed"
                elif session_count > 0:
                    severity = ValidationSeverity.INFO
                    message = f"Traffic analysis functional: {session_count} sessions analyzed"
                else:
                    severity = ValidationSeverity.WARNING
                    message = "Traffic analysis functional but no recent traffic"

                self._add_result(
                    ValidationResult(
                        test_name="traffic_analysis",
                        status=status,
                        severity=severity,
                        message=message,
                        details={"total_sessions": session_count, "analysis_keys": list(analysis.keys())},
                        execution_time=execution_time,
                    )
                )
            else:
                self._add_result(
                    ValidationResult(
                        test_name="traffic_analysis",
                        status="fail",
                        severity=ValidationSeverity.ERROR,
                        message="Invalid traffic analysis response format",
                        execution_time=execution_time,
                    )
                )

        except Exception as e:
            self._add_result(
                ValidationResult(
                    test_name="traffic_analysis",
                    status="fail",
                    severity=ValidationSeverity.WARNING,
                    message=f"Traffic analysis test failed: {str(e)}",
                    execution_time=time.time() - start_time,
                )
            )

    # ===== 모니터링 테스트 =====

    async def _test_monitoring(self):
        """모니터링 기능 테스트"""
        await self._test_log_streaming()
        await self._test_real_time_stats()

    async def _test_log_streaming(self):
        """로그 스트리밍 테스트"""
        start_time = time.time()

        try:
            # 짧은 시간 동안 로그 스트리밍 테스트
            log_count = 0

            async def log_callback(log_entry):
                nonlocal log_count
                log_count += 1

            # 5초 동안만 스트리밍 테스트
            stream_task = asyncio.create_task(self.api_client.stream_logs("traffic", log_callback, interval=1))

            await asyncio.sleep(5)
            stream_task.cancel()

            try:
                await stream_task
            except asyncio.CancelledError:
                pass

            execution_time = time.time() - start_time

            if log_count > 0:
                status = "pass"
                severity = ValidationSeverity.INFO
                message = f"Log streaming functional: {log_count} logs received in 5s"
            else:
                status = "pass"
                severity = ValidationSeverity.WARNING
                message = "Log streaming functional but no logs received (may be normal)"

            self._add_result(
                ValidationResult(
                    test_name="log_streaming",
                    status=status,
                    severity=severity,
                    message=message,
                    details={"logs_received": log_count, "test_duration": 5},
                    execution_time=execution_time,
                )
            )

        except Exception as e:
            self._add_result(
                ValidationResult(
                    test_name="log_streaming",
                    status="fail",
                    severity=ValidationSeverity.ERROR,
                    message=f"Log streaming test failed: {str(e)}",
                    execution_time=time.time() - start_time,
                )
            )

    async def _test_real_time_stats(self):
        """실시간 통계 테스트"""
        start_time = time.time()

        try:
            # 연속으로 통계를 조회하여 실시간성 확인
            stats1 = await self.api_client.get_performance_stats()
            await asyncio.sleep(2)
            stats2 = await self.api_client.get_performance_stats()

            execution_time = time.time() - start_time

            if stats1 and stats2:
                # 통계가 업데이트되었는지 확인 (간단한 검증)
                stats1_str = str(stats1)
                stats2_str = str(stats2)

                if stats1_str != stats2_str:
                    status = "pass"
                    severity = ValidationSeverity.INFO
                    message = "Real-time statistics updating correctly"
                else:
                    status = "pass"
                    severity = ValidationSeverity.WARNING
                    message = "Statistics may not be updating in real-time"

                self._add_result(
                    ValidationResult(
                        test_name="real_time_stats",
                        status=status,
                        severity=severity,
                        message=message,
                        details={"stats_keys": list(stats1.keys()) if isinstance(stats1, dict) else None},
                        execution_time=execution_time,
                    )
                )
            else:
                self._add_result(
                    ValidationResult(
                        test_name="real_time_stats",
                        status="fail",
                        severity=ValidationSeverity.ERROR,
                        message="Failed to retrieve performance statistics",
                        execution_time=execution_time,
                    )
                )

        except Exception as e:
            self._add_result(
                ValidationResult(
                    test_name="real_time_stats",
                    status="fail",
                    severity=ValidationSeverity.ERROR,
                    message=f"Real-time stats test failed: {str(e)}",
                    execution_time=time.time() - start_time,
                )
            )

    # ===== 결과 처리 =====

    def _add_result(self, result: ValidationResult):
        """검증 결과 추가"""
        self.results.append(result)
        logger.debug(f"Test result: {result.test_name} - {result.status} - {result.message}")

    def _generate_summary(self, total_time: float) -> Dict[str, Any]:
        """검증 결과 요약 생성"""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.status == "pass")
        failed_tests = sum(1 for r in self.results if r.status == "fail")
        skipped_tests = sum(1 for r in self.results if r.status == "skip")

        # 심각도별 집계
        severity_counts = {}
        for severity in ValidationSeverity:
            severity_counts[severity.value] = sum(1 for r in self.results if r.severity == severity)

        # 성공률 계산
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        # 전체 평가
        if failed_tests == 0:
            overall_status = "healthy"
        elif success_rate >= 80:
            overall_status = "acceptable"
        elif success_rate >= 60:
            overall_status = "warning"
        else:
            overall_status = "critical"

        return {
            "overall_status": overall_status,
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "skipped": skipped_tests,
            "success_rate": round(success_rate, 1),
            "severity_breakdown": severity_counts,
            "total_execution_time": round(total_time, 2),
            "average_test_time": round(total_time / total_tests, 3) if total_tests > 0 else 0,
        }

    def _result_to_dict(self, result: ValidationResult) -> Dict[str, Any]:
        """ValidationResult를 딕셔너리로 변환"""
        return {
            "test_name": result.test_name,
            "status": result.status,
            "severity": result.severity.value,
            "message": result.message,
            "details": result.details,
            "execution_time": result.execution_time,
            "timestamp": result.timestamp.isoformat(),
        }

    def save_results_to_file(self, filepath: str):
        """검증 결과를 파일로 저장"""
        try:
            results_data = {
                "validation_timestamp": datetime.now().isoformat(),
                "fortigate_host": self.api_client.host,
                "test_config": self.test_config,
                "summary": self._generate_summary(0),  # 임시 시간
                "results": [self._result_to_dict(r) for r in self.results],
            }

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(results_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Validation results saved to {filepath}")

        except Exception as e:
            logger.error(f"Failed to save validation results: {e}")


# ===== 편의 함수들 =====


async def validate_fortigate_api(
    api_client: AdvancedFortiGateAPI, test_categories: List[str] = None, save_results: str = None
) -> Dict[str, Any]:
    """
    FortiGate API 유효성 검사 실행

    Args:
        api_client: 검증할 API 클라이언트
        test_categories: 실행할 테스트 카테고리 목록
        save_results: 결과 저장 파일 경로

    Returns:
        검증 결과
    """
    validator = FortiGateAPIValidator(api_client)
    results = await validator.run_all_validations(test_categories)

    if save_results:
        validator.save_results_to_file(save_results)

    return results


def create_test_report(validation_results: Dict[str, Any]) -> str:
    """
    검증 결과로부터 텍스트 리포트 생성

    Args:
        validation_results: 검증 결과 데이터

    Returns:
        텍스트 형식 리포트
    """
    summary = validation_results.get("summary", {})
    results = validation_results.get("results", [])

    report_lines = [
        "=" * 60,
        "FortiGate API Validation Report",
        "=" * 60,
        "",
        "SUMMARY:",
        f"  Overall Status: {summary.get('overall_status', 'unknown').upper()}",
        f"  Total Tests: {summary.get('total_tests', 0)}",
        f"  Passed: {summary.get('passed', 0)}",
        f"  Failed: {summary.get('failed', 0)}",
        f"  Skipped: {summary.get('skipped', 0)}",
        f"  Success Rate: {summary.get('success_rate', 0)}%",
        f"  Execution Time: {summary.get('total_execution_time', 0)}s",
        "",
        "DETAILED RESULTS:",
        "",
    ]

    # 실패한 테스트 먼저 표시
    failed_results = [r for r in results if r["status"] == "fail"]
    if failed_results:
        report_lines.extend(["FAILED TESTS:", "-" * 20])

        for result in failed_results:
            report_lines.extend(
                [
                    f"  ❌ {result['test_name']}",
                    f"     {result['message']}",
                    f"     Severity: {result['severity'].upper()}",
                    "",
                ]
            )

    # 경고가 있는 테스트
    warning_results = [r for r in results if r["status"] == "pass" and r["severity"] == "warning"]
    if warning_results:
        report_lines.extend(["WARNINGS:", "-" * 20])

        for result in warning_results:
            report_lines.extend([f"  ⚠️  {result['test_name']}", f"     {result['message']}", ""])

    # 성공한 테스트 (요약만)
    passed_results = [r for r in results if r["status"] == "pass" and r["severity"] != "warning"]
    if passed_results:
        report_lines.extend([f"PASSED TESTS: {len(passed_results)} tests passed successfully", ""])

    report_lines.extend(["=" * 60, f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "=" * 60])

    return "\n".join(report_lines)
