#!/usr/bin/env python3
"""
TLS/SSL 프로토콜 분석기
TLS 연결 분석, 인증서 검증, 암호화 강도 분석
"""

import logging
import struct
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TLSAnalyzer:
    """TLS/SSL 프로토콜 분석기"""

    # TLS 콘텐츠 타입
    TLS_CONTENT_TYPES = {
        20: "change_cipher_spec",
        21: "alert",
        22: "handshake",
        23: "application_data",
        24: "heartbeat",
    }

    # TLS 버전
    TLS_VERSIONS = {
        0x0300: "SSL 3.0",
        0x0301: "TLS 1.0",
        0x0302: "TLS 1.1",
        0x0303: "TLS 1.2",
        0x0304: "TLS 1.3",
    }

    # TLS 핸드셰이크 타입
    HANDSHAKE_TYPES = {
        0: "hello_request",
        1: "client_hello",
        2: "server_hello",
        11: "certificate",
        12: "server_key_exchange",
        13: "certificate_request",
        14: "server_hello_done",
        15: "certificate_verify",
        16: "client_key_exchange",
        20: "finished",
    }

    # 알려진 취약한 암호화 스위트
    WEAK_CIPHER_SUITES = {
        "NULL",
        "RC4",
        "MD5",
        "SHA1",
        "DES",
        "3DES",
        "EXPORT",
    }

    def __init__(self):
        self.connections = {}  # TLS 연결 추적
        self.certificates = {}  # 인증서 캐시

    def analyze(self, packet_data: bytes, packet_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        TLS 패킷 분석

        Args:
            packet_data: 패킷 데이터
            packet_info: 패킷 기본 정보

        Returns:
            dict: TLS 분석 결과
        """
        try:
            if not self._is_tls_packet(packet_data, packet_info):
                return {}

            tls_analysis = {
                "protocol": "TLS/SSL",
                "timestamp": packet_info.get("timestamp", datetime.now().isoformat()),
                "src_ip": packet_info.get("src_ip"),
                "dst_ip": packet_info.get("dst_ip"),
                "src_port": packet_info.get("src_port"),
                "dst_port": packet_info.get("dst_port"),
                "records": [],
                "security_issues": [],
                "connection_info": {},
            }

            # TLS 레코드 파싱
            records = self._parse_tls_records(packet_data)

            for record in records:
                tls_analysis["records"].append(record)

                # 핸드셰이크 분석
                if record.get("content_type") == "handshake":
                    handshake_analysis = self._analyze_handshake(record, packet_info)
                    if handshake_analysis:
                        tls_analysis.update(handshake_analysis)

                # 경고 분석
                elif record.get("content_type") == "alert":
                    alert_analysis = self._analyze_alert(record)
                    if alert_analysis:
                        tls_analysis["security_issues"].append(alert_analysis)

            # 연결 정보 업데이트
            connection_key = (
                f"{packet_info.get('src_ip')}:{packet_info.get('src_port')}-"
                f"{packet_info.get('dst_ip')}:{packet_info.get('dst_port')}"
            )
            if connection_key in self.connections:
                tls_analysis["connection_info"] = self.connections[connection_key]

            # 보안 검사
            security_issues = self._check_security_issues(tls_analysis)
            tls_analysis["security_issues"].extend(security_issues)

            return tls_analysis

        except Exception as e:
            logger.error(f"TLS 분석 오류: {e}")
            return {
                "protocol": "TLS/SSL",
                "error": str(e),
                "timestamp": packet_info.get("timestamp", datetime.now().isoformat()),
            }

    def _is_tls_packet(self, packet_data: bytes, packet_info: Dict[str, Any]) -> bool:
        """TLS 패킷인지 확인"""
        # 포트 기반 확인
        if packet_info.get("dst_port") in [
            443,
            993,
            995,
            636,
        ] or packet_info.get(
            "src_port"
        ) in [443, 993, 995, 636]:
            return True

        # TLS 레코드 헤더 확인
        if len(packet_data) >= 5:
            content_type = packet_data[0]
            version = struct.unpack(">H", packet_data[1:3])[0]

            if content_type in self.TLS_CONTENT_TYPES and version in self.TLS_VERSIONS:
                return True

        return False

    def _parse_tls_records(self, data: bytes) -> List[Dict[str, Any]]:
        """TLS 레코드 파싱"""
        records = []
        offset = 0

        while offset < len(data) - 5:
            try:
                # TLS 레코드 헤더 (5바이트)
                content_type = data[offset]
                version = struct.unpack(">H", data[offset + 1 : offset + 3])[0]
                length = struct.unpack(">H", data[offset + 3 : offset + 5])[0]

                if offset + 5 + length > len(data):
                    break

                record_data = data[offset + 5 : offset + 5 + length]

                record = {
                    "content_type": self.TLS_CONTENT_TYPES.get(content_type, f"unknown_{content_type}"),
                    "version": self.TLS_VERSIONS.get(version, f"unknown_{version:04x}"),
                    "length": length,
                    "data": record_data,
                }

                # 핸드셰이크 메시지 상세 파싱
                if content_type == 22:  # handshake
                    handshake_info = self._parse_handshake(record_data)
                    if handshake_info:
                        record.update(handshake_info)

                records.append(record)
                offset += 5 + length

            except Exception as e:
                logger.error(f"TLS 레코드 파싱 오류: {e}")
                break

        return records

    def _parse_handshake(self, data: bytes) -> Optional[Dict[str, Any]]:
        """핸드셰이크 메시지 파싱"""
        try:
            if len(data) < 4:
                return None

            msg_type = data[0]
            msg_length = struct.unpack(">I", b"\x00" + data[1:4])[0]

            handshake_info = {
                "handshake_type": self.HANDSHAKE_TYPES.get(msg_type, f"unknown_{msg_type}"),
                "message_length": msg_length,
            }

            if len(data) >= 4 + msg_length:
                msg_data = data[4 : 4 + msg_length]

                # Client Hello 파싱
                if msg_type == 1:
                    client_hello = self._parse_client_hello(msg_data)
                    if client_hello:
                        handshake_info.update(client_hello)

                # Server Hello 파싱
                elif msg_type == 2:
                    server_hello = self._parse_server_hello(msg_data)
                    if server_hello:
                        handshake_info.update(server_hello)

                # Certificate 파싱
                elif msg_type == 11:
                    cert_info = self._parse_certificate(msg_data)
                    if cert_info:
                        handshake_info.update(cert_info)

            return handshake_info

        except Exception as e:
            logger.error(f"핸드셰이크 파싱 오류: {e}")
            return None

    def _parse_client_hello(self, data: bytes) -> Optional[Dict[str, Any]]:
        """Client Hello 메시지 파싱"""
        try:
            if len(data) < 38:
                return None

            offset = 0

            # 프로토콜 버전
            client_version = struct.unpack(">H", data[offset : offset + 2])[0]
            offset += 2

            # 랜덤 값 (32바이트)
            random = data[offset : offset + 32]
            offset += 32

            # 세션 ID
            session_id_length = data[offset]
            offset += 1
            session_id = data[offset : offset + session_id_length] if session_id_length > 0 else b""
            offset += session_id_length

            # 암호화 스위트
            if offset + 2 > len(data):
                return None
            cipher_suites_length = struct.unpack(">H", data[offset : offset + 2])[0]
            offset += 2

            cipher_suites = []
            cipher_end = offset + cipher_suites_length
            while offset < cipher_end and offset + 2 <= len(data):
                suite = struct.unpack(">H", data[offset : offset + 2])[0]
                cipher_suites.append(f"0x{suite:04x}")
                offset += 2

            return {
                "client_version": self.TLS_VERSIONS.get(client_version, f"unknown_{client_version:04x}"),
                "random": random.hex(),
                "session_id": session_id.hex() if session_id else "",
                "cipher_suites": cipher_suites,
                "cipher_suite_count": len(cipher_suites),
            }

        except Exception as e:
            logger.error(f"Client Hello 파싱 오류: {e}")
            return None

    def _parse_server_hello(self, data: bytes) -> Optional[Dict[str, Any]]:
        """Server Hello 메시지 파싱"""
        try:
            if len(data) < 38:
                return None

            offset = 0

            # 프로토콜 버전
            server_version = struct.unpack(">H", data[offset : offset + 2])[0]
            offset += 2

            # 랜덤 값
            random = data[offset : offset + 32]
            offset += 32

            # 세션 ID
            session_id_length = data[offset]
            offset += 1
            session_id = data[offset : offset + session_id_length] if session_id_length > 0 else b""
            offset += session_id_length

            # 선택된 암호화 스위트
            if offset + 2 > len(data):
                return None
            chosen_cipher_suite = struct.unpack(">H", data[offset : offset + 2])[0]
            offset += 2

            # 압축 방법
            compression_method = data[offset] if offset < len(data) else 0

            return {
                "server_version": self.TLS_VERSIONS.get(server_version, f"unknown_{server_version:04x}"),
                "random": random.hex(),
                "session_id": session_id.hex() if session_id else "",
                "chosen_cipher_suite": f"0x{chosen_cipher_suite:04x}",
                "compression_method": compression_method,
            }

        except Exception as e:
            logger.error(f"Server Hello 파싱 오류: {e}")
            return None

    def _parse_certificate(self, data: bytes) -> Optional[Dict[str, Any]]:
        """Certificate 메시지 파싱"""
        try:
            if len(data) < 3:
                return None

            # 인증서 체인 길이
            chain_length = struct.unpack(">I", b"\x00" + data[0:3])[0]
            offset = 3

            certificates = []

            while offset < len(data) and offset < 3 + chain_length:
                if offset + 3 > len(data):
                    break

                cert_length = struct.unpack(">I", b"\x00" + data[offset : offset + 3])[0]
                offset += 3

                if offset + cert_length > len(data):
                    break

                cert_data = data[offset : offset + cert_length]
                offset += cert_length

                # 인증서 정보 추출
                cert_info = self._analyze_certificate(cert_data)
                if cert_info:
                    certificates.append(cert_info)

            return {
                "certificate_count": len(certificates),
                "certificates": certificates,
            }

        except Exception as e:
            logger.error(f"Certificate 파싱 오류: {e}")
            return None

    def _analyze_certificate(self, cert_data: bytes) -> Optional[Dict[str, Any]]:
        """X.509 인증서 분석"""
        try:
            # 실제 구현에서는 cryptography 라이브러리 사용
            # 여기서는 기본적인 정보만 추출

            cert_info = {
                "size": len(cert_data),
                "fingerprint": self._calculate_fingerprint(cert_data),
                "der_format": True,
            }

            # 간단한 ASN.1 파싱으로 기본 정보 추출
            # 실제로는 cryptography.x509 사용 권장

            return cert_info

        except Exception as e:
            logger.error(f"인증서 분석 오류: {e}")
            return None

    def _calculate_fingerprint(self, data: bytes) -> str:
        """인증서 지문 계산"""
        import hashlib

        return hashlib.sha256(data).hexdigest()

    def _analyze_handshake(self, record: Dict[str, Any], packet_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """핸드셰이크 분석"""
        try:
            connection_key = (
                f"{packet_info.get('src_ip')}:{packet_info.get('src_port')}-"
                f"{packet_info.get('dst_ip')}:{packet_info.get('dst_port')}"
            )

            if connection_key not in self.connections:
                self.connections[connection_key] = {
                    "handshake_messages": [],
                    "negotiated_version": None,
                    "negotiated_cipher": None,
                    "certificates": [],
                    "security_level": "unknown",
                }

            connection = self.connections[connection_key]

            # 핸드셰이크 메시지 추가
            handshake_type = record.get("handshake_type")
            if handshake_type:
                connection["handshake_messages"].append(
                    {
                        "type": handshake_type,
                        "timestamp": packet_info.get("timestamp"),
                        "direction": (
                            "client_to_server"
                            if packet_info.get("src_port") > packet_info.get("dst_port")
                            else "server_to_client"
                        ),
                    }
                )

            # 협상된 정보 업데이트
            if "client_version" in record:
                connection["client_version"] = record["client_version"]

            if "server_version" in record:
                connection["negotiated_version"] = record["server_version"]

            if "chosen_cipher_suite" in record:
                connection["negotiated_cipher"] = record["chosen_cipher_suite"]
                connection["security_level"] = self._assess_cipher_security(record["chosen_cipher_suite"])

            if "certificates" in record:
                connection["certificates"].extend(record["certificates"])

            return {"connection_analysis": connection}

        except Exception as e:
            logger.error(f"핸드셰이크 분석 오류: {e}")
            return None

    def _analyze_alert(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """TLS 경고 분석"""
        try:
            data = record.get("data", b"")
            if len(data) >= 2:
                alert_level = data[0]
                alert_description = data[1]

                alert_levels = {1: "warning", 2: "fatal"}
                alert_descriptions = {
                    0: "close_notify",
                    10: "unexpected_message",
                    20: "bad_record_mac",
                    21: "decryption_failed",
                    22: "record_overflow",
                    30: "decompression_failure",
                    40: "handshake_failure",
                    41: "no_certificate",
                    42: "bad_certificate",
                    43: "unsupported_certificate",
                    44: "certificate_revoked",
                    45: "certificate_expired",
                    46: "certificate_unknown",
                    47: "illegal_parameter",
                    48: "unknown_ca",
                    49: "access_denied",
                    50: "decode_error",
                    51: "decrypt_error",
                    60: "export_restriction",
                    70: "protocol_version",
                    71: "insufficient_security",
                    80: "internal_error",
                    90: "user_canceled",
                    100: "no_renegotiation",
                }

                return {
                    "type": "tls_alert",
                    "level": alert_levels.get(alert_level, f"unknown_{alert_level}"),
                    "description": alert_descriptions.get(alert_description, f"unknown_{alert_description}"),
                    "severity": "high" if alert_level == 2 else "medium",
                }

        except Exception as e:
            logger.error(f"TLS 경고 분석 오류: {e}")

        return None

    def _assess_cipher_security(self, cipher_suite: str) -> str:
        """암호화 스위트 보안 수준 평가"""
        try:
            # 취약한 암호화 스위트 검사
            for weak_cipher in self.WEAK_CIPHER_SUITES:
                if weak_cipher.lower() in cipher_suite.lower():
                    return "weak"

            # 현대적인 암호화 스위트 검사
            modern_ciphers = ["AES256", "CHACHA20", "GCM", "ECDHE"]
            if any(cipher in cipher_suite.upper() for cipher in modern_ciphers):
                return "strong"

            return "medium"

        except Exception:
            return "unknown"

    def _check_security_issues(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """보안 문제 검사"""
        issues = []

        try:
            # 취약한 TLS 버전 검사
            for record in analysis.get("records", []):
                version = record.get("version", "")
                if "SSL" in version or "TLS 1.0" in version or "TLS 1.1" in version:
                    issues.append(
                        {
                            "type": "weak_tls_version",
                            "description": f"취약한 TLS 버전 사용: {version}",
                            "severity": "high",
                            "recommendation": "TLS 1.2 이상 사용 권장",
                        }
                    )

            # 연결 정보에서 보안 문제 검사
            connection_info = analysis.get("connection_info", {})

            # 취약한 암호화 스위트
            if connection_info.get("security_level") == "weak":
                issues.append(
                    {
                        "type": "weak_cipher_suite",
                        "description": f'취약한 암호화 스위트: {connection_info.get("negotiated_cipher")}',
                        "severity": "high",
                        "recommendation": "강력한 암호화 스위트로 변경 필요",
                    }
                )

            # 인증서 관련 문제
            certificates = connection_info.get("certificates", [])
            for cert in certificates:
                if cert.get("size", 0) < 1024:  # 너무 작은 키 크기
                    issues.append(
                        {
                            "type": "weak_certificate",
                            "description": "약한 인증서 키 크기",
                            "severity": "medium",
                            "recommendation": "2048비트 이상의 키 사용 권장",
                        }
                    )

        except Exception as e:
            logger.error(f"보안 검사 오류: {e}")

        return issues


# 팩토리 함수
def create_tls_analyzer() -> TLSAnalyzer:
    """TLS 분석기 인스턴스 생성"""
    return TLSAnalyzer()
