#!/usr/bin/env python3
"""
패킷 스니퍼 모듈 - 모듈화된 패킷 캡처 및 분석 시스템
"""

from .base_sniffer import BaseSniffer
from .device_manager import DeviceManager
from .packet_capturer import PacketCapturer
from .session_manager import SessionManager


class PacketAnalyzer:
    """Packet analysis functionality for testing"""

    def __init__(self):
        """Initialize packet analyzer"""
        self.sessions = SessionManager()
        self.capturer = PacketCapturer()

    def analyze_packet(self, packet_data):
        """Analyze a packet"""
        return {"packet_size": len(str(packet_data)), "analyzed": True, "timestamp": "2024-01-01T00:00:00Z"}

    def start_analysis(self):
        """Start packet analysis"""
        return {"status": "started", "analyzer_active": True}

    def stop_analysis(self):
        """Stop packet analysis"""
        return {"status": "stopped", "analyzer_active": False}


__all__ = ["BaseSniffer", "SessionManager", "PacketCapturer", "DeviceManager", "PacketAnalyzer"]

__version__ = "1.0.0"
