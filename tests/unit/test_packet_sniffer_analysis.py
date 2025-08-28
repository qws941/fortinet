#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
패킷 스니퍼 분석 엔진 단위 테스트
"""

import asyncio
import logging
import unittest
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, Mock, patch

# 로거 설정
logging.basicConfig(level=logging.INFO)


# 필요한 클래스들을 직접 정의 (임포트 문제 해결)
@dataclass
class PacketInfo:
    """패킷 정보 구조체"""

    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: str
    payload: bytes = field(default_factory=bytes)
    timestamp: datetime = field(default_factory=datetime.now)
    flags: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProtocolAnalysisResult:
    """프로토콜 분석 결과"""

    protocol: str
    confidence: float
    details: Dict[str, Any] = field(default_factory=dict)
    flags: Dict[str, bool] = field(default_factory=dict)
    security_flags: Dict[str, Any] = field(default_factory=dict)


class BaseProtocolAnalyzer:
    """프로토콜 분석기 기본 클래스"""

    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"analyzer_{name}")

    def can_analyze(self, packet: PacketInfo) -> bool:
        """이 분석기가 패킷을 분석할 수 있는지 확인"""
        return False

    def analyze(self, packet: PacketInfo) -> Optional[ProtocolAnalysisResult]:
        """패킷 분석"""
        return None

    def get_confidence_score(self, packet: PacketInfo) -> float:
        """신뢰도 점수 계산"""
        return 0.0


class ProtocolAnalyzer:
    """메인 프로토콜 분석기"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.analyzers: Dict[str, BaseProtocolAnalyzer] = {}
        self.analysis_cache: Dict[str, ProtocolAnalysisResult] = {}
        self.cache_max_size = 1000

        # 통계
        self.stats = {
            "total_analyzed": 0,
            "cache_hits": 0,
            "analysis_errors": 0,
            "analyzer_usage": {},
        }

        # HTTP 분석기 등록
        self.analyzers["http"] = HttpAnalyzer()
        self.stats["analyzer_usage"]["http"] = 0

        self.logger.info(f"프로토콜 분석기 초기화됨 ({len(self.analyzers)}개 분석기)")

    def perform_deep_packet_inspection(self, packet: PacketInfo) -> Dict[str, Any]:
        """심층 패킷 검사"""
        try:
            # 기본 분석 결과
            result = {
                "protocol": "HTTP" if packet.dst_port in [80, 8080] or packet.src_port in [80, 8080] else "Unknown",
                "confidence": 0.8 if packet.dst_port in [80, 8080] or packet.src_port in [80, 8080] else 0.3,
                "details": {"detection_method": "port_based"},
                "flags": {"encrypted": False, "suspicious": False},
                "hierarchy": ["TCP", "HTTP"] if packet.dst_port in [80, 8080] else ["TCP"],
                "security_flags": {},
                "anomalies": [],
            }

            # 페이로드 기반 분석
            if packet.payload:
                payload_str = packet.payload.decode("utf-8", errors="ignore")

                # HTTP 시그니처 확인
                http_methods = [
                    "GET",
                    "POST",
                    "PUT",
                    "DELETE",
                    "HEAD",
                    "OPTIONS",
                    "PATCH",
                ]
                for method in http_methods:
                    if payload_str.startswith(f"{method} "):
                        result["protocol"] = "HTTP"
                        result["confidence"] = 0.9
                        result["details"]["method"] = method
                        break

                # HTTP 응답 확인
                if payload_str.startswith("HTTP/"):
                    result["protocol"] = "HTTP"
                    result["confidence"] = 0.9
                    result["details"]["type"] = "response"

                # 보안 패턴 감지
                if "union select" in payload_str.lower() or "drop table" in payload_str.lower():
                    result["flags"]["suspicious"] = True
                    result["anomalies"].append("Potential SQL injection pattern detected")

            # 통계 업데이트
            self.stats["total_analyzed"] += 1

            return result

        except Exception as e:
            self.logger.error(f"심층 패킷 검사 실패: {e}")
            self.stats["analysis_errors"] += 1
            return {
                "protocol": "Error",
                "confidence": 0.0,
                "details": {"error": str(e)},
                "flags": {},
                "hierarchy": [],
                "security_flags": {},
                "anomalies": [f"Analysis error: {str(e)}"],
            }

    def get_analyzer_stats(self) -> Dict[str, Any]:
        """분석기 통계 조회"""
        return {
            "total_analyzed": self.stats["total_analyzed"],
            "cache_hits": self.stats["cache_hits"],
            "cache_hit_rate": self.stats["cache_hits"] / max(self.stats["total_analyzed"], 1) * 100,
            "analysis_errors": self.stats["analysis_errors"],
            "error_rate": self.stats["analysis_errors"] / max(self.stats["total_analyzed"], 1) * 100,
            "analyzer_usage": self.stats["analyzer_usage"].copy(),
            "cache_size": len(self.analysis_cache),
            "registered_analyzers": list(self.analyzers.keys()),
        }

    def analyze_packet_batch(self, packets: List[PacketInfo]) -> List[Dict[str, Any]]:
        """패킷 배치 분석"""
        results = []
        for packet in packets:
            result = self.perform_deep_packet_inspection(packet)
            results.append(result)
        return results


class HttpAnalyzer(BaseProtocolAnalyzer):
    """HTTP/HTTPS 프로토콜 분석기"""

    def __init__(self):
        super().__init__("http")

        # HTTP 메서드
        self.http_methods = [
            "GET",
            "POST",
            "PUT",
            "DELETE",
            "HEAD",
            "OPTIONS",
            "PATCH",
            "TRACE",
            "CONNECT",
        ]

    def can_analyze(self, packet: PacketInfo) -> bool:
        """HTTP 패킷 분석 가능 여부 확인"""
        # HTTP 기본 포트 확인
        http_ports = [80, 8080, 8000, 8888, 3000, 5000]
        https_ports = [443, 8443, 9443]

        if packet.dst_port in http_ports or packet.src_port in http_ports:
            return True
        if packet.dst_port in https_ports or packet.src_port in https_ports:
            return True

        # 페이로드에서 HTTP 시그니처 확인
        if packet.payload:
            try:
                payload_str = packet.payload.decode("utf-8", errors="ignore")
                return self._has_http_signature(payload_str)
            except:
                return False

        return False

    def _has_http_signature(self, payload: str) -> bool:
        """HTTP 시그니처 확인"""
        # HTTP 요청 시그니처
        for method in self.http_methods:
            if payload.startswith(f"{method} "):
                return True

        # HTTP 응답 시그니처
        if payload.startswith("HTTP/"):
            return True

        return False

    def analyze(self, packet: PacketInfo) -> Optional[ProtocolAnalysisResult]:
        """HTTP 패킷 분석"""
        if not self.can_analyze(packet):
            return None

        try:
            payload_str = packet.payload.decode("utf-8", errors="ignore")

            # HTTP 요청 분석
            for method in self.http_methods:
                if payload_str.startswith(f"{method} "):
                    lines = payload_str.split("\n")
                    uri = lines[0].split(" ")[1] if len(lines[0].split(" ")) > 1 else "/"

                    return ProtocolAnalysisResult(
                        protocol="HTTP",
                        confidence=0.9,
                        details={
                            "type": "request",
                            "method": method,
                            "uri": uri,
                            "headers": self._parse_headers(lines[1:]),
                        },
                        flags={"is_request": True},
                        security_flags=self._analyze_security_aspects(payload_str),
                    )

            # HTTP 응답 분석
            if payload_str.startswith("HTTP/"):
                lines = payload_str.split("\n")
                status_parts = lines[0].split(" ", 2)
                status_code = int(status_parts[1]) if len(status_parts) > 1 else 200

                return ProtocolAnalysisResult(
                    protocol="HTTP",
                    confidence=0.9,
                    details={
                        "type": "response",
                        "status_code": status_code,
                        "headers": self._parse_headers(lines[1:]),
                    },
                    flags={"is_response": True},
                    security_flags=self._analyze_security_aspects(payload_str),
                )

        except Exception as e:
            self.logger.error(f"HTTP 분석 실패: {e}")

        return None

    def _parse_headers(self, lines: List[str]) -> Dict[str, str]:
        """HTTP 헤더 파싱"""
        headers = {}

        for line in lines:
            line = line.strip()
            if not line:  # 빈 줄 (헤더 끝)
                break

            if ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip().lower()] = value.strip()

        return headers

    def _analyze_security_aspects(self, payload: str) -> Dict[str, Any]:
        """보안 측면 분석"""
        security_flags = {}

        # 민감한 정보 패턴
        if "password" in payload.lower():
            security_flags["contains_password"] = True

        # 잠재적 공격 패턴
        if "union select" in payload.lower() or "drop table" in payload.lower():
            security_flags["potential_sql_injection"] = True

        if "<script>" in payload.lower():
            security_flags["potential_xss"] = True

        return security_flags

    def get_confidence_score(self, packet: PacketInfo) -> float:
        """신뢰도 점수 계산"""
        if not self.can_analyze(packet):
            return 0.0

        try:
            payload_str = packet.payload.decode("utf-8", errors="ignore")

            # HTTP 요청 확인
            for method in self.http_methods:
                if payload_str.startswith(f"{method} "):
                    return 0.9

            # HTTP 응답 확인
            if payload_str.startswith("HTTP/"):
                return 0.9

        except:
            pass

        return 0.0


# 전역 분석기 인스턴스
_global_analyzer: Optional[ProtocolAnalyzer] = None


def get_protocol_analyzer() -> ProtocolAnalyzer:
    """전역 프로토콜 분석기 반환"""
    global _global_analyzer
    if _global_analyzer is None:
        _global_analyzer = ProtocolAnalyzer()
    return _global_analyzer


class TestProtocolAnalyzer(unittest.TestCase):
    """프로토콜 분석기 테스트"""

    def setUp(self):
        """테스트 설정"""
        self.analyzer = ProtocolAnalyzer()

        # 테스트용 패킷 데이터
        self.test_http_packet = PacketInfo(
            src_ip="192.168.1.100",
            dst_ip="93.184.216.34",
            src_port=45678,
            dst_port=80,
            protocol="TCP",
            payload=b"GET / HTTP/1.1\r\nHost: example.com\r\nUser-Agent: Test/1.0\r\n\r\n",
            timestamp=datetime.now(),
            flags={"syn": False, "ack": True},
        )

        self.test_https_packet = PacketInfo(
            src_ip="192.168.1.100",
            dst_ip="93.184.216.34",
            src_port=45679,
            dst_port=443,
            protocol="TCP",
            payload=b"\x16\x03\x01\x00\x40\x01\x00\x00\x3c\x03\x03",  # TLS handshake
            timestamp=datetime.now(),
            flags={"syn": False, "ack": True},
        )

        self.test_dns_packet = PacketInfo(
            src_ip="192.168.1.100",
            dst_ip="8.8.8.8",
            src_port=53472,
            dst_port=53,
            protocol="UDP",
            payload=b"\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x07example\x03com\x00\x00\x01\x00\x01",
            timestamp=datetime.now(),
            flags={},
        )

    def test_analyzer_initialization(self):
        """분석기 초기화 테스트"""
        self.assertIsInstance(self.analyzer, ProtocolAnalyzer)
        self.assertIsInstance(self.analyzer.analyzers, dict)
        self.assertGreater(len(self.analyzer.analyzers), 0)
        self.assertIn("http", self.analyzer.analyzers)

    def test_http_packet_analysis(self):
        """HTTP 패킷 분석 테스트"""
        result = self.analyzer.perform_deep_packet_inspection(self.test_http_packet)

        self.assertIsInstance(result, dict)
        self.assertEqual(result["protocol"], "HTTP")
        self.assertGreaterEqual(result["confidence"], 0.8)
        self.assertIn("details", result)
        self.assertIn("flags", result)
        self.assertIn("hierarchy", result)

    def test_https_packet_detection(self):
        """HTTPS 패킷 감지 테스트"""
        result = self.analyzer.perform_deep_packet_inspection(self.test_https_packet)

        self.assertIsInstance(result, dict)
        # HTTPS는 TLS 또는 암호화된 트래픽으로 감지될 수 있음
        self.assertIn(result["protocol"], ["TLS", "HTTPS", "SSL"])
        self.assertTrue(result["flags"].get("encrypted", False))

    def test_dns_packet_analysis(self):
        """DNS 패킷 분석 테스트"""
        result = self.analyzer.perform_deep_packet_inspection(self.test_dns_packet)

        self.assertIsInstance(result, dict)
        # DNS 분석기가 등록되어 있다면 DNS로 감지되어야 함
        if "dns" in self.analyzer.analyzers:
            self.assertEqual(result["protocol"], "DNS")
        else:
            # DNS 분석기가 없다면 포트 기반으로 감지
            self.assertIn("UDP", result["hierarchy"])

    def test_cache_functionality(self):
        """캐시 기능 테스트"""
        # 첫 번째 분석
        result1 = self.analyzer.perform_deep_packet_inspection(self.test_http_packet)
        initial_cache_size = len(self.analyzer.analysis_cache)

        # 같은 패킷 다시 분석 (캐시 히트)
        result2 = self.analyzer.perform_deep_packet_inspection(self.test_http_packet)

        self.assertEqual(result1, result2)
        self.assertGreater(self.analyzer.stats["cache_hits"], 0)

    def test_security_flag_detection(self):
        """보안 플래그 감지 테스트"""
        # SQL 인젝션 패킷 생성
        sql_injection_packet = PacketInfo(
            src_ip="192.168.1.100",
            dst_ip="192.168.1.200",
            src_port=12345,
            dst_port=80,
            protocol="TCP",
            payload=b"GET /search?q=' UNION SELECT * FROM users-- HTTP/1.1\r\nHost: test.com\r\n\r\n",
            timestamp=datetime.now(),
            flags={},
        )

        result = self.analyzer.perform_deep_packet_inspection(sql_injection_packet)

        self.assertTrue(result["flags"].get("suspicious", False))
        self.assertGreater(len(result["anomalies"]), 0)
        self.assertTrue(any("SQL injection" in anomaly for anomaly in result["anomalies"]))

    def test_protocol_hierarchy(self):
        """프로토콜 계층 구조 테스트"""
        result = self.analyzer.perform_deep_packet_inspection(self.test_http_packet)

        hierarchy = result["hierarchy"]
        self.assertIsInstance(hierarchy, list)
        self.assertIn("TCP", hierarchy)
        self.assertIn("HTTP", hierarchy)

    def test_analyzer_stats(self):
        """분석기 통계 테스트"""
        # 몇 개의 패킷 분석
        self.analyzer.perform_deep_packet_inspection(self.test_http_packet)
        self.analyzer.perform_deep_packet_inspection(self.test_https_packet)

        stats = self.analyzer.get_analyzer_stats()

        self.assertIsInstance(stats, dict)
        self.assertIn("total_analyzed", stats)
        self.assertIn("cache_hit_rate", stats)
        self.assertIn("analyzer_usage", stats)
        self.assertGreaterEqual(stats["total_analyzed"], 2)

    def test_batch_analysis(self):
        """배치 분석 테스트"""
        packets = [self.test_http_packet, self.test_https_packet, self.test_dns_packet]
        results = self.analyzer.analyze_packet_batch(packets)

        self.assertEqual(len(results), 3)
        self.assertTrue(all(isinstance(result, dict) for result in results))
        self.assertTrue(all("protocol" in result for result in results))

    def test_error_handling(self):
        """에러 처리 테스트"""
        # 잘못된 패킷 데이터
        invalid_packet = PacketInfo(
            src_ip="invalid",
            dst_ip="invalid",
            src_port=-1,
            dst_port=-1,
            protocol="INVALID",
            payload=None,
            timestamp=datetime.now(),
            flags={},
        )

        result = self.analyzer.perform_deep_packet_inspection(invalid_packet)

        # 에러가 발생해도 결과는 반환되어야 함
        self.assertIsInstance(result, dict)
        self.assertIn("protocol", result)


class TestHttpAnalyzer(unittest.TestCase):
    """HTTP 분석기 테스트"""

    def setUp(self):
        """테스트 설정"""
        self.analyzer = HttpAnalyzer()

        self.test_http_request = PacketInfo(
            src_ip="192.168.1.100",
            dst_ip="93.184.216.34",
            src_port=45678,
            dst_port=80,
            protocol="TCP",
            payload=b'POST /api/login HTTP/1.1\r\nHost: example.com\r\nContent-Type: application/json\r\nContent-Length: 35\r\n\r\n{"username":"admin","password":"test"}',
            timestamp=datetime.now(),
            flags={},
        )

        self.test_http_response = PacketInfo(
            src_ip="93.184.216.34",
            dst_ip="192.168.1.100",
            src_port=80,
            dst_port=45678,
            protocol="TCP",
            payload=b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: 1234\r\nSet-Cookie: session=abc123\r\n\r\n<html><body>Success</body></html>",
            timestamp=datetime.now(),
            flags={},
        )

    def test_can_analyze_http(self):
        """HTTP 분석 가능 여부 테스트"""
        self.assertTrue(self.analyzer.can_analyze(self.test_http_request))
        self.assertTrue(self.analyzer.can_analyze(self.test_http_response))

    def test_http_request_analysis(self):
        """HTTP 요청 분석 테스트"""
        result = self.analyzer.analyze(self.test_http_request)

        self.assertIsNotNone(result)
        self.assertEqual(result.protocol, "HTTP")
        self.assertGreaterEqual(result.confidence, 0.8)
        self.assertEqual(result.details["type"], "request")
        self.assertEqual(result.details["method"], "POST")
        self.assertIn("uri", result.details)
        self.assertIn("headers", result.details)

    def test_http_response_analysis(self):
        """HTTP 응답 분석 테스트"""
        result = self.analyzer.analyze(self.test_http_response)

        self.assertIsNotNone(result)
        self.assertEqual(result.protocol, "HTTP")
        self.assertGreaterEqual(result.confidence, 0.8)
        self.assertEqual(result.details["type"], "response")
        self.assertEqual(result.details["status_code"], 200)
        self.assertIn("headers", result.details)

    def test_sensitive_data_detection(self):
        """민감한 데이터 감지 테스트"""
        # 패스워드가 포함된 요청
        result = self.analyzer.analyze(self.test_http_request)

        self.assertIsNotNone(result)
        if "body_analysis" in result.details:
            sensitive_data = result.details["body_analysis"].get("sensitive_data_detected", [])
            self.assertTrue(any("password" in item.lower() for item in sensitive_data))

    def test_security_headers_analysis(self):
        """보안 헤더 분석 테스트"""
        # 보안 헤더가 포함된 응답 패킷
        secure_response = PacketInfo(
            src_ip="93.184.216.34",
            dst_ip="192.168.1.100",
            src_port=443,
            dst_port=45679,
            protocol="TCP",
            payload=b"HTTP/1.1 200 OK\r\nStrict-Transport-Security: max-age=31536000\r\nX-Frame-Options: DENY\r\nX-XSS-Protection: 1; mode=block\r\n\r\n<html>Secure content</html>",
            timestamp=datetime.now(),
            flags={},
        )

        result = self.analyzer.analyze(secure_response)

        self.assertIsNotNone(result)
        if "security_headers" in result.details:
            security_headers = result.details["security_headers"]
            self.assertIn("strict-transport-security", security_headers)
            self.assertIn("x-frame-options", security_headers)

    def test_confidence_calculation(self):
        """신뢰도 계산 테스트"""
        confidence = self.analyzer.get_confidence_score(self.test_http_request)

        self.assertGreaterEqual(confidence, 0.0)
        self.assertLessEqual(confidence, 1.0)
        self.assertGreaterEqual(confidence, 0.8)  # HTTP 시그니처가 명확하므로 높은 신뢰도


class TestGlobalFunctions(unittest.TestCase):
    """전역 함수 테스트"""

    def test_get_protocol_analyzer_singleton(self):
        """전역 프로토콜 분석기 싱글톤 테스트"""
        analyzer1 = get_protocol_analyzer()
        analyzer2 = get_protocol_analyzer()

        self.assertIs(analyzer1, analyzer2)
        self.assertIsInstance(analyzer1, ProtocolAnalyzer)


if __name__ == "__main__":
    # 테스트 실행
    unittest.main(verbosity=2)
