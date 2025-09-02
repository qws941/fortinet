#!/usr/bin/env python3
"""
Security module - 패킷 스니퍼 및 보안 관련 모듈
"""

# 기존 PacketSnifferAPI 클래스를 새로운 모듈화된 구조로 리디렉션
from .packet_sniffer_api import (PacketSnifferAPI, create_packet_sniffer_api,
                                 get_packet_sniffer_api)

# 하위 호환성을 위한 별칭
PacketSniffer = PacketSnifferAPI

__all__ = [
    "PacketSnifferAPI",
    "PacketSniffer",
    "create_packet_sniffer_api",
    "get_packet_sniffer_api",
]
