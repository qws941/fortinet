#!/usr/bin/env python3
"""
애플리케이션 프로토콜 분석기 (통합 버전)
고레벨 애플리케이션 프로토콜 분석 및 보안 검사
"""

import logging
from typing import Any, Dict, List, Optional

from .ssh_analyzer import SSHAnalyzer
from .web_analyzer import WebAnalyzer

logger = logging.getLogger(__name__)


class ApplicationAnalyzer:
    """애플리케이션 프로토콜 통합 분석기"""

    # 애플리케이션 포트 매핑
    APPLICATION_PORTS = {
        21: "FTP",
        22: "SSH",
        23: "TELNET",
        25: "SMTP",
        53: "DNS",
        69: "TFTP",
        79: "FINGER",
        80: "HTTP",
        110: "POP3",
        119: "NNTP",
        143: "IMAP",
        161: "SNMP",
        443: "HTTPS",
        993: "IMAPS",
        995: "POP3S",
        1883: "MQTT",
        8080: "HTTP-ALT",
        8443: "HTTPS-ALT",
    }

    def __init__(self):
        self.session_info = {}

        # 전용 분석기 초기화
        self.ssh_analyzer = SSHAnalyzer()
        self.web_analyzer = WebAnalyzer()

    def analyze(self, packet_data: bytes, packet_info: Dict[str, Any]) -> Dict[str, Any]:
        """패킷 분석 메인 함수"""

        try:
            # 기본 분석 정보
            analysis = {
                "analyzer": "application",
                "timestamp": packet_info.get("timestamp"),
                "packet_size": len(packet_data),
                "src_ip": packet_info.get("src_ip"),
                "dst_ip": packet_info.get("dst_ip"),
                "src_port": packet_info.get("src_port"),
                "dst_port": packet_info.get("dst_port"),
            }

            # 포트 기반 프로토콜 식별 (페이로드 없어도 수행)
            dst_port = packet_info.get("dst_port", 0)
            src_port = packet_info.get("src_port", 0)

            protocol = self.APPLICATION_PORTS.get(dst_port) or self.APPLICATION_PORTS.get(src_port)

            # 페이로드 추출
            payload = self._extract_payload(packet_data, packet_info)
            if not payload:
                # 페이로드가 없어도 포트 기반 프로토콜은 설정
                analysis["detected_protocol"] = protocol or "UNKNOWN"
                return analysis

            if not protocol:
                # 패턴 기반 프로토콜 탐지
                detected_protocols = self._detect_protocols_by_pattern(payload)
                protocol = detected_protocols[0] if detected_protocols else "UNKNOWN"

            analysis["detected_protocol"] = protocol

            # 프로토콜별 상세 분석
            protocol_analysis = self._analyze_protocol(protocol, payload, packet_info)
            if protocol_analysis:
                analysis.update(protocol_analysis)

            # 세션 정보 업데이트
            self._update_session_info(analysis, packet_info)

            return analysis

        except Exception as e:
            logger.error(f"애플리케이션 분석 오류: {e}")
            return {
                "analyzer": "application",
                "error": str(e),
                "packet_size": len(packet_data),
            }

    def _extract_payload(self, packet_data: bytes, packet_info: Dict[str, Any]) -> Optional[bytes]:
        """페이로드 추출"""

        try:
            # 간단한 TCP/UDP 페이로드 추출
            if len(packet_data) > 54:  # Ethernet + IP + TCP 최소 크기
                return packet_data[54:]
            return None
        except Exception as e:
            logger.error(f"페이로드 추출 오류: {e}")
            return None

    def _detect_protocols_by_pattern(self, payload: bytes) -> List[str]:
        """패턴 기반 프로토콜 탐지"""

        detected = []

        try:
            # 텍스트로 변환 (에러 무시)
            payload_str = payload.decode("utf-8", errors="ignore")
            payload_lower = payload_str.lower()

            # HTTP 패턴
            if any(payload_str.startswith(method + " ") for method in ["GET", "POST", "PUT", "DELETE"]):
                detected.append("HTTP")
            elif payload_str.startswith("HTTP/"):
                detected.append("HTTP")

            # SSH 패턴
            if "ssh-" in payload_lower:
                detected.append("SSH")

            # FTP 패턴
            if any(cmd in payload_lower for cmd in ["user ", "pass ", "list", "retr ", "stor "]):
                detected.append("FTP")

            # SMTP 패턴
            if any(cmd in payload_lower for cmd in ["helo", "ehlo", "mail from:", "rcpt to:"]):
                detected.append("SMTP")

            # MQTT 패턴 (바이너리 체크)
            if len(payload) > 2 and payload[0] in [
                0x10,
                0x20,
                0x30,
                0x31,
                0x32,
                0x33,
            ]:
                detected.append("MQTT")

        except Exception as e:
            logger.error(f"프로토콜 패턴 탐지 오류: {e}")

        return detected

    def _analyze_protocol(self, protocol: str, payload: bytes, packet_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """프로토콜별 분석 라우팅"""

        try:
            if protocol in ["SSH"]:
                return self.ssh_analyzer.analyze_ssh(payload, packet_info)
            elif protocol in ["HTTP", "HTTPS"]:
                return self.web_analyzer.analyze_http(payload, packet_info)
            else:
                # 간단한 일반 분석
                return self._analyze_generic(payload, packet_info, protocol)

        except Exception as e:
            logger.error(f"{protocol} 분석 오류: {e}")
            return None

    def _analyze_generic(self, payload: bytes, packet_info: Dict[str, Any], protocol: str) -> Dict[str, Any]:
        """일반적인 프로토콜 분석"""

        analysis = {
            "protocol": protocol,
            "payload_size": len(payload),
            "is_encrypted": self._detect_encryption(payload),
            "printable_ratio": self._calculate_printable_ratio(payload),
        }

        # 텍스트 기반 프로토콜인 경우 간단한 분석
        if analysis["printable_ratio"] > 0.8:
            try:
                payload_str = payload.decode("utf-8", errors="ignore")
                analysis["sample_content"] = payload_str[:100]  # 첫 100자만
                analysis["line_count"] = payload_str.count("\n")
            except Exception:
                pass

        return analysis

    def _detect_encryption(self, payload: bytes) -> bool:
        """암호화된 데이터 탐지"""

        if len(payload) == 0:
            return False

        # 엔트로피 기반 간단한 암호화 탐지
        entropy = self._calculate_entropy(payload)
        return entropy > 7.0  # 높은 엔트로피는 암호화 가능성

    def _calculate_entropy(self, data: bytes) -> float:
        """데이터 엔트로피 계산"""

        if not data:
            return 0.0

        # 바이트 빈도 계산
        frequency = [0] * 256
        for byte in data:
            frequency[byte] += 1

        # 엔트로피 계산
        entropy = 0.0
        data_len = len(data)

        for freq in frequency:
            if freq > 0:
                prob = freq / data_len
                entropy -= prob * (prob.bit_length() - 1)

        return entropy

    def _calculate_printable_ratio(self, payload: bytes) -> float:
        """출력 가능한 문자 비율 계산"""

        if not payload:
            return 0.0

        printable_count = sum(1 for byte in payload if 32 <= byte <= 126)
        return printable_count / len(payload)

    def _update_session_info(self, analysis: Dict[str, Any], packet_info: Dict[str, Any]) -> Dict[str, Any]:
        """세션 정보 업데이트"""

        src_ip = packet_info.get("src_ip", "")
        dst_ip = packet_info.get("dst_ip", "")
        protocol = analysis.get("detected_protocol", "")

        session_key = f"{src_ip}:{dst_ip}:{protocol}"

        if session_key not in self.session_info:
            self.session_info[session_key] = {
                "start_time": analysis.get("timestamp"),
                "packet_count": 0,
                "total_bytes": 0,
                "protocol": protocol,
                "src_ip": src_ip,
                "dst_ip": dst_ip,
            }

        session = self.session_info[session_key]
        session["packet_count"] += 1
        session["total_bytes"] += analysis.get("packet_size", 0)
        session["last_seen"] = analysis.get("timestamp")

        analysis["session_info"] = session
        return analysis

    def get_session_statistics(self) -> Dict[str, Any]:
        """세션 통계 정보"""

        total_sessions = len(self.session_info)
        protocol_counts = {}
        total_bytes = 0
        total_packets = 0

        for session in self.session_info.values():
            protocol = session.get("protocol", "UNKNOWN")
            protocol_counts[protocol] = protocol_counts.get(protocol, 0) + 1
            total_bytes += session.get("total_bytes", 0)
            total_packets += session.get("packet_count", 0)

        return {
            "total_sessions": total_sessions,
            "protocol_distribution": protocol_counts,
            "total_bytes_analyzed": total_bytes,
            "total_packets_analyzed": total_packets,
            "average_session_size": total_bytes // total_sessions if total_sessions > 0 else 0,
        }

    def get_protocol_analyzer(self, protocol: str):
        """프로토콜별 전용 분석기 반환"""

        if protocol.upper() == "SSH":
            return self.ssh_analyzer
        elif protocol.upper() in ["HTTP", "HTTPS"]:
            return self.web_analyzer
        else:
            return None

    def clear_session_data(self):
        """세션 데이터 초기화"""

        self.session_info.clear()
        if hasattr(self.ssh_analyzer, "sessions"):
            self.ssh_analyzer.sessions.clear()
        if hasattr(self.web_analyzer, "http_methods"):
            self.web_analyzer.http_methods.clear()
            self.web_analyzer.user_agents.clear()
            self.web_analyzer.domains.clear()
