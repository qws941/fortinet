#!/usr/bin/env python3
"""
베이스 스니퍼 클래스 - 공통 기능 및 설정 관리
"""

import os
import secrets
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from utils.unified_logger import get_logger


@dataclass
class SnifferConfig:
    """스니퍼 설정 클래스"""

    interface: str = "any"
    buffer_size: int = 65536
    timeout: float = 1.0
    max_packets: int = 1000
    offline_mode: bool = False
    mock_data: bool = False
    fortigate_host: str = ""
    fortigate_token: str = ""

    def __post_init__(self):
        """환경변수에서 설정 로드"""
        self.offline_mode = os.getenv("OFFLINE_MODE", "false").lower() == "true"
        # Mock data removed - production only
        self.fortigate_host = os.getenv("FORTIGATE_HOST", self.fortigate_host)
        self.fortigate_token = os.getenv("FORTIGATE_API_TOKEN", self.fortigate_token)


@dataclass
class PacketInfo:
    """패킷 정보 구조체"""

    timestamp: float
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: str
    size: int
    payload: bytes = field(default_factory=bytes)
    flags: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "timestamp": self.timestamp,
            "src_ip": self.src_ip,
            "dst_ip": self.dst_ip,
            "src_port": self.src_port,
            "dst_port": self.dst_port,
            "protocol": self.protocol,
            "size": self.size,
            "flags": self.flags,
        }


class BaseSniffer(ABC):
    """패킷 스니퍼 베이스 클래스"""

    def __init__(self, config: Optional[SnifferConfig] = None):
        """베이스 스니퍼 초기화"""
        self.config = config or SnifferConfig()
        self.logger = get_logger(self.__class__.__name__, "advanced")

        # 상태 관리
        self._is_running = False
        self._is_initialized = False
        self._lock = threading.RLock()

        # 통계
        self.stats = {
            "packets_captured": 0,
            "packets_analyzed": 0,
            "packets_filtered": 0,
            "start_time": None,
            "errors": 0,
        }

        # 콜백 관리
        self._callbacks: List[Callable] = []

        self.logger.info(f"{self.__class__.__name__} 초기화됨")

    @property
    def is_running(self) -> bool:
        """실행 상태 확인"""
        with self._lock:
            return self._is_running

    @property
    def is_initialized(self) -> bool:
        """초기화 상태 확인"""
        with self._lock:
            return self._is_initialized

    def add_callback(self, callback: Callable[[PacketInfo], None]) -> None:
        """패킷 처리 콜백 추가"""
        with self._lock:
            if callback not in self._callbacks:
                self._callbacks.append(callback)
                self.logger.debug(f"콜백 추가됨: {callback.__name__}")

    def remove_callback(self, callback: Callable[[PacketInfo], None]) -> None:
        """패킷 처리 콜백 제거"""
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)
                self.logger.debug(f"콜백 제거됨: {callback.__name__}")

    def _notify_callbacks(self, packet_info: PacketInfo) -> None:
        """등록된 콜백들에게 패킷 정보 전달"""
        for callback in self._callbacks[:]:  # 복사본 사용
            try:
                callback(packet_info)
            except Exception as e:
                self.logger.error(f"콜백 호출 실패: {e}")
                self.stats["errors"] += 1

    def get_stats(self) -> Dict[str, Any]:
        """통계 정보 반환"""
        with self._lock:
            stats = self.stats.copy()
            if stats["start_time"]:
                stats["uptime_seconds"] = time.time() - stats["start_time"]
                if stats["uptime_seconds"] > 0:
                    stats["packets_per_second"] = stats["packets_captured"] / stats["uptime_seconds"]
            return stats

    def reset_stats(self) -> None:
        """통계 초기화"""
        with self._lock:
            self.stats = {
                "packets_captured": 0,
                "packets_analyzed": 0,
                "packets_filtered": 0,
                "start_time": time.time() if self._is_running else None,
                "errors": 0,
            }
            self.logger.info("통계 정보 초기화됨")

    @abstractmethod
    def initialize(self) -> bool:
        """스니퍼 초기화 (추상 메서드)"""

    @abstractmethod
    def start(self) -> bool:
        """스니퍼 시작 (추상 메서드)"""

    @abstractmethod
    def stop(self) -> bool:
        """스니퍼 중지 (추상 메서드)"""

    @abstractmethod
    def cleanup(self) -> None:
        """리소스 정리 (추상 메서드)"""

    def _update_stats(self, stat_name: str, increment: int = 1) -> None:
        """통계 업데이트"""
        with self._lock:
            if stat_name in self.stats:
                self.stats[stat_name] += increment


class ProtocolIdentifier:
    """프로토콜 식별기"""

    # 잘 알려진 포트 매핑
    TCP_PORTS = {
        21: "FTP",
        22: "SSH",
        23: "Telnet",
        25: "SMTP",
        53: "DNS",
        80: "HTTP",
        110: "POP3",
        143: "IMAP",
        443: "HTTPS",
        993: "IMAPS",
        995: "POP3S",
        587: "SMTP",
        465: "SMTPS",
        119: "NNTP",
        135: "RPC",
        139: "NetBIOS",
        445: "SMB",
        514: "Syslog",
        636: "LDAPS",
        989: "FTPS",
        990: "FTPS",
        1433: "MSSQL",
        1521: "Oracle",
        3306: "MySQL",
        3389: "RDP",
        5432: "PostgreSQL",
        5900: "VNC",
        6379: "Redis",
        8080: "HTTP-Proxy",
        8443: "HTTPS-Alt",
        9200: "Elasticsearch",
        27017: "MongoDB",
    }

    UDP_PORTS = {
        53: "DNS",
        67: "DHCP",
        68: "DHCP",
        69: "TFTP",
        123: "NTP",
        161: "SNMP",
        162: "SNMP-Trap",
        514: "Syslog",
        520: "RIP",
        1812: "RADIUS",
        1813: "RADIUS-Accounting",
        4500: "IPSec-NAT",
    }

    # 프로토콜 시그니처
    PROTOCOL_SIGNATURES = {
        "HTTP": [
            b"GET ",
            b"POST ",
            b"PUT ",
            b"DELETE ",
            b"HEAD ",
            b"OPTIONS ",
        ],
        "HTTPS": [b"\x16\x03"],  # TLS 핸드셰이크
        "SSH": [b"SSH-"],
        "FTP": [b"220 ", b"USER ", b"PASS "],
        "SMTP": [b"220 ", b"EHLO ", b"MAIL FROM:"],
        "DNS": [b"\x01\x00\x00\x01"],  # 표준 DNS 쿼리
        "MQTT": [b"\x10", b"\x20", b"\x30"],  # MQTT 제어 패킷
        "ICMP": [b"\x08\x00", b"\x00\x00"],  # ICMP Echo Request/Reply
    }

    @classmethod
    def identify_by_port(cls, port: int, protocol: str) -> Optional[str]:
        """포트 기반 프로토콜 식별"""
        if protocol.upper() == "TCP":
            return cls.TCP_PORTS.get(port)
        elif protocol.upper() == "UDP":
            return cls.UDP_PORTS.get(port)
        return None

    @classmethod
    def identify_by_signature(cls, payload: bytes) -> Optional[str]:
        """시그니처 기반 프로토콜 식별"""
        if not payload:
            return None

        for protocol, signatures in cls.PROTOCOL_SIGNATURES.items():
            for signature in signatures:
                if payload.startswith(signature):
                    return protocol
        return None

    @classmethod
    def get_confidence_score(cls, protocol: str, port: int, payload: bytes) -> float:
        """프로토콜 식별 신뢰도 계산"""
        score = 0.0

        # 포트 기반 점수
        if cls.identify_by_port(port, "TCP") == protocol or cls.identify_by_port(port, "UDP") == protocol:
            score += 0.7

        # 시그니처 기반 점수
        if cls.identify_by_signature(payload) == protocol:
            score += 0.8

        return min(score, 1.0)


class MockDataGenerator:
    """테스트용 가짜 데이터 생성기"""

    @staticmethod
    def generate_packet_info(protocol: str = "TCP") -> PacketInfo:
        """가짜 패킷 정보 생성"""

        protocols = ["TCP", "UDP", "ICMP"]
        if protocol not in protocols:
            protocol = secrets.choice(protocols)

        # 일반적인 IP 주소 패턴
        src_ip = f"192.168.{secrets.randbelow(1, 255)}.{secrets.randbelow(1, 254)}"
        dst_ip = f"10.{secrets.randbelow(1, 255)}.{secrets.randbelow(1, 255)}.{secrets.randbelow(1, 254)}"

        # 포트 선택
        if protocol == "TCP":
            common_ports = [80, 443, 22, 21, 25, 110, 143, 993, 995]
        elif protocol == "UDP":
            common_ports = [53, 67, 123, 161, 514]
        else:  # ICMP
            common_ports = [0]

        src_port = secrets.choice(common_ports + [secrets.randbelow(1024, 65535)])
        dst_port = secrets.choice(common_ports)

        # 패킷 크기
        size = secrets.randbelow(64, 1500)

        # 가짜 페이로드
        payload_samples = {
            "HTTP": b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n",
            "HTTPS": b"\x16\x03\x01\x00\x4c\x01\x00\x00\x48\x03\x03",
            "DNS": b"\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00",
            "SSH": b"SSH-2.0-OpenSSH_7.4",
            "SMTP": b"220 mail.example.com ESMTP ready\r\n",
        }

        # 프로토콜에 따른 페이로드 선택
        app_protocol = ProtocolIdentifier.identify_by_port(dst_port, protocol)
        if app_protocol and app_protocol in payload_samples:
            payload = payload_samples[app_protocol]
        else:
            payload = bytes([secrets.randbelow(256) for _ in range(secrets.randbelow(90) + 10)])

        return PacketInfo(
            timestamp=time.time(),
            src_ip=src_ip,
            dst_ip=dst_ip,
            src_port=src_port,
            dst_port=dst_port,
            protocol=protocol,
            size=size,
            payload=payload,
            flags={"mock": True, "app_protocol": app_protocol},
        )

    @classmethod
    def generate_packet_batch(cls, count: int = 10) -> List[PacketInfo]:
        """패킷 배치 생성"""
        return [cls.generate_packet_info() for _ in range(count)]


def create_sniffer_config(**kwargs) -> SnifferConfig:
    """스니퍼 설정 생성 헬퍼"""
    return SnifferConfig(**kwargs)


def validate_config(config: SnifferConfig) -> bool:
    """설정 유효성 검사"""
    if config.buffer_size <= 0:
        return False
    if config.timeout < 0:
        return False
    if config.max_packets <= 0:
        return False
    return True
