#!/usr/bin/env python3
"""
패킷 캡처러 - 실시간 패킷 캡처 엔진
"""

import queue
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base_sniffer import BaseSniffer, MockDataGenerator, PacketInfo, SnifferConfig
from .device_manager import DeviceManager
from .session_manager import get_session_manager


@dataclass
class CaptureFilter:
    """패킷 캡처 필터"""

    src_ip: Optional[str] = None
    dst_ip: Optional[str] = None
    src_port: Optional[int] = None
    dst_port: Optional[int] = None
    protocol: Optional[str] = None
    interface: Optional[str] = None

    def matches(self, packet: PacketInfo) -> bool:
        """패킷이 필터 조건에 맞는지 확인"""
        if self.src_ip and packet.src_ip != self.src_ip:
            return False
        if self.dst_ip and packet.dst_ip != self.dst_ip:
            return False
        if self.src_port and packet.src_port != self.src_port:
            return False
        if self.dst_port and packet.dst_port != self.dst_port:
            return False
        if self.protocol and packet.protocol != self.protocol:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "src_ip": self.src_ip,
            "dst_ip": self.dst_ip,
            "src_port": self.src_port,
            "dst_port": self.dst_port,
            "protocol": self.protocol,
            "interface": self.interface,
        }


class PacketBuffer:
    """패킷 버퍼 - 순환 버퍼 방식"""

    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.packets: List[PacketInfo] = []
        self.current_index = 0
        self.total_packets = 0
        self.lock = threading.RLock()

    def add_packet(self, packet: PacketInfo) -> None:
        """패킷 추가"""
        with self.lock:
            if len(self.packets) < self.max_size:
                self.packets.append(packet)
            else:
                # 순환 버퍼: 가장 오래된 패킷 덮어쓰기
                self.packets[self.current_index] = packet
                self.current_index = (self.current_index + 1) % self.max_size

            self.total_packets += 1

    def get_packets(self, limit: Optional[int] = None, since: Optional[datetime] = None) -> List[PacketInfo]:
        """패킷 조회"""
        with self.lock:
            packets = self.packets.copy()

            # 시간 필터링
            if since:
                since_timestamp = since.timestamp()
                packets = [p for p in packets if p.timestamp >= since_timestamp]

            # 최신 패킷 우선으로 정렬
            packets.sort(key=lambda p: p.timestamp, reverse=True)

            # 개수 제한
            if limit:
                packets = packets[:limit]

            return packets

    def get_latest_packet(self) -> Optional[PacketInfo]:
        """가장 최신 패킷 조회"""
        with self.lock:
            if not self.packets:
                return None

            # 가장 최신 타임스탬프를 가진 패킷 찾기
            latest_packet = max(self.packets, key=lambda p: p.timestamp)
            return latest_packet

    def clear(self) -> None:
        """버퍼 초기화"""
        with self.lock:
            self.packets.clear()
            self.current_index = 0
            self.total_packets = 0

    def get_stats(self) -> Dict[str, Any]:
        """버퍼 통계"""
        with self.lock:
            return {
                "current_size": len(self.packets),
                "max_size": self.max_size,
                "total_packets": self.total_packets,
                "buffer_usage": len(self.packets) / self.max_size * 100,
            }


class PacketCapturer(BaseSniffer):
    """패킷 캡처러"""

    def __init__(self, config: Optional[SnifferConfig] = None):
        super().__init__(config)

        # 컴포넌트 초기화
        self.session_manager = get_session_manager()
        self.device_manager = DeviceManager(config)

        # 패킷 버퍼
        self.packet_buffer = PacketBuffer(self.config.max_packets)

        # 캡처 상태
        self.active_sessions: Dict[str, bool] = {}
        self.capture_filters: Dict[str, CaptureFilter] = {}

        # 캡처 스레드
        self.capture_threads: Dict[str, threading.Thread] = {}
        self.capture_queues: Dict[str, queue.Queue] = {}

        # 통계
        self.capture_stats = {
            "total_captured": 0,
            "filtered_out": 0,
            "errors": 0,
            "start_time": None,
        }

        # FortiGate API 클라이언트 (필요시 초기화)
        self._fortigate_client = None

        self.logger.info("패킷 캡처러 초기화됨")

    def initialize(self) -> bool:
        """캡처러 초기화"""
        try:
            with self._lock:
                if self._is_initialized:
                    return True

                # 장치 관리자 초기화
                self.device_manager._initialize_interfaces()

                # FortiGate 클라이언트 초기화 (오프라인 모드가 아닌 경우)
                if not self.config.offline_mode and self.config.fortigate_host:
                    self._initialize_fortigate_client()

                self._is_initialized = True
                self.logger.info("패킷 캡처러 초기화 완료")
                return True

        except Exception as e:
            self.logger.error(f"패킷 캡처러 초기화 실패: {e}")
            return False

    def _initialize_fortigate_client(self) -> None:
        """FortiGate API 클라이언트 초기화"""
        try:
            from api.clients.fortigate_api_client import FortiGateAPIClient

            self._fortigate_client = FortiGateAPIClient(
                host=self.config.fortigate_host,
                api_token=self.config.fortigate_token,
            )
            self.logger.info("FortiGate API 클라이언트 초기화됨")
        except Exception as e:
            self.logger.warning(f"FortiGate API 클라이언트 초기화 실패: {e}")

    def start(self) -> bool:
        """캡처러 시작"""
        try:
            with self._lock:
                if self._is_running:
                    return True

                if not self._is_initialized:
                    if not self.initialize():
                        return False

                self._is_running = True
                self.stats["start_time"] = time.time()
                self.capture_stats["start_time"] = datetime.now()

                self.logger.info("패킷 캡처러 시작됨")
                return True

        except Exception as e:
            self.logger.error(f"패킷 캡처러 시작 실패: {e}")
            return False

    def stop(self) -> bool:
        """캡처러 중지"""
        try:
            with self._lock:
                if not self._is_running:
                    return True

                # 모든 활성 세션 중지
                for session_id in list(self.active_sessions.keys()):
                    self.stop_capture_session(session_id)

                self._is_running = False
                self.logger.info("패킷 캡처러 중지됨")
                return True

        except Exception as e:
            self.logger.error(f"패킷 캡처러 중지 실패: {e}")
            return False

    def cleanup(self) -> None:
        """리소스 정리"""
        self.stop()
        self.packet_buffer.clear()
        self.device_manager.cleanup()
        self.logger.info("패킷 캡처러 정리 완료")

    def start_capture_session(
        self,
        session_id: str,
        capture_filter: Optional[CaptureFilter] = None,
        interface: str = "any",
    ) -> bool:
        """캡처 세션 시작"""
        try:
            if session_id in self.active_sessions:
                self.logger.warning(f"세션 {session_id}가 이미 활성화되어 있습니다")
                return False

            # 세션 상태 확인
            session = self.session_manager.get_session(session_id)
            if not session:
                self.logger.error(f"세션 {session_id}를 찾을 수 없습니다")
                return False

            # 필터 설정
            if capture_filter:
                self.capture_filters[session_id] = capture_filter

            # 캡처 큐 생성
            self.capture_queues[session_id] = queue.Queue(maxsize=1000)

            # 캡처 스레드 시작
            capture_thread = threading.Thread(
                target=self._capture_worker,
                args=(session_id, interface),
                daemon=True,
                name=f"capture_{session_id[:8]}",
            )

            self.capture_threads[session_id] = capture_thread
            self.active_sessions[session_id] = True

            # 세션 시작
            if not self.session_manager.start_session(session_id):
                self.logger.error(f"세션 {session_id} 시작 실패")
                return False

            capture_thread.start()
            self.logger.info(f"캡처 세션 시작됨: {session_id} (인터페이스: {interface})")
            return True

        except Exception as e:
            self.logger.error(f"캡처 세션 시작 실패: {e}")
            return False

    def stop_capture_session(self, session_id: str) -> bool:
        """캡처 세션 중지"""
        try:
            if session_id not in self.active_sessions:
                return False

            # 캡처 중지
            self.active_sessions[session_id] = False

            # 스레드 종료 대기
            if session_id in self.capture_threads:
                thread = self.capture_threads[session_id]
                if thread.is_alive():
                    thread.join(timeout=5)
                del self.capture_threads[session_id]

            # 큐 정리
            if session_id in self.capture_queues:
                del self.capture_queues[session_id]

            # 필터 정리
            if session_id in self.capture_filters:
                del self.capture_filters[session_id]

            # 세션 중지
            self.session_manager.stop_session(session_id)

            self.logger.info(f"캡처 세션 중지됨: {session_id}")
            return True

        except Exception as e:
            self.logger.error(f"캡처 세션 중지 실패: {e}")
            return False

    def _capture_worker(self, session_id: str, interface: str) -> None:
        """캡처 작업자 스레드"""
        self.logger.info(f"캡처 작업자 시작: {session_id} (인터페이스: {interface})")

        try:
            # 캡처 방식 결정 - 테스트 환경이나 오프라인 모드에서는 Mock 데이터 사용
            use_mock = (
                self.config.offline_mode
                or self.config.mock_data
                or not self._fortigate_client
                or interface == "any"  # 'any' 인터페이스는 mock 모드로 처리
            )

            if use_mock:
                self.logger.info(f"Mock 모드로 패킷 캡처 시작: {session_id}")
                self._mock_capture_loop(session_id, interface)
            else:
                # 실제 패킷 캡처는 FortiGate API를 통해 수행
                self.logger.info(f"FortiGate 모드로 패킷 캡처 시작: {session_id}")
                self._fortigate_capture_loop(session_id, interface)

        except Exception as e:
            self.logger.error(f"캡처 작업자 오류 ({session_id}): {e}")
            self.capture_stats["errors"] += 1
        finally:
            self.logger.info(f"캡처 작업자 종료: {session_id}")

    def _mock_capture_loop(self, session_id: str, interface: str) -> None:
        """가짜 패킷 캡처 루프"""
        packet_interval = 0.1  # 100ms마다 패킷 생성
        packet_count = 0
        max_packets = 20  # 테스트를 위해 최대 20개 패킷 생성

        self.logger.info(f"Mock 캡처 루프 시작: {session_id}")

        while self.active_sessions.get(session_id, False) and packet_count < max_packets:
            try:
                # 가짜 패킷 생성
                packet = MockDataGenerator.generate_packet_info()

                # 필터 적용
                if self._should_capture_packet(session_id, packet):
                    self._process_captured_packet(session_id, packet)
                    packet_count += 1
                    self.logger.debug(f"Mock 패킷 생성됨: {packet_count}/{max_packets}")
                else:
                    self.capture_stats["filtered_out"] += 1

                time.sleep(packet_interval)

            except Exception as e:
                self.logger.error(f"가짜 패킷 생성 오류: {e}")
                time.sleep(1)

        self.logger.info(f"Mock 캡처 루프 완료: {session_id}, 총 {packet_count}개 패킷 생성")

    def _fortigate_capture_loop(self, session_id: str, interface: str) -> None:
        """FortiGate를 통한 실제 패킷 캡처 루프"""
        if not self._fortigate_client:
            self.logger.warning("FortiGate 클라이언트가 초기화되지 않음")
            return

        try:
            # FortiGate 패킷 캡처 시작
            capture_config = {
                "interface": interface,
                "max_packets": self.config.max_packets,
                "duration": 3600,
            }  # 1시간

            success = self._fortigate_client.start_packet_capture(**capture_config)
            if not success:
                self.logger.error("FortiGate 패킷 캡처 시작 실패")
                return

            # 패킷 데이터 폴링
            while self.active_sessions.get(session_id, False):
                try:
                    # FortiGate에서 캡처된 패킷 조회
                    packets = self._fortigate_client.get_latest_packets()

                    if packets:
                        for packet_data in packets:
                            packet = self._parse_fortigate_packet(packet_data)
                            if packet and self._should_capture_packet(session_id, packet):
                                self._process_captured_packet(session_id, packet)

                    time.sleep(1)  # 1초마다 폴링

                except Exception as e:
                    self.logger.error(f"FortiGate 패킷 조회 오류: {e}")
                    time.sleep(5)

        except Exception as e:
            self.logger.error(f"FortiGate 캡처 루프 오류: {e}")
        finally:
            # 캡처 정리
            try:
                if self._fortigate_client:
                    self._fortigate_client.stop_packet_capture()
            except Exception as e:
                self.logger.error(f"FortiGate 캡처 정리 오류: {e}")

    def _parse_fortigate_packet(self, packet_data: Dict[str, Any]) -> Optional[PacketInfo]:
        """FortiGate 패킷 데이터 파싱"""
        try:
            packet = PacketInfo(
                timestamp=packet_data.get("timestamp", time.time()),
                src_ip=packet_data.get("src_ip", ""),
                dst_ip=packet_data.get("dst_ip", ""),
                src_port=packet_data.get("src_port", 0),
                dst_port=packet_data.get("dst_port", 0),
                protocol=packet_data.get("protocol", ""),
                size=packet_data.get("size", 0),
                payload=packet_data.get("payload", b""),
                flags=packet_data.get("flags", {}),
            )
            return packet

        except Exception as e:
            self.logger.error(f"FortiGate 패킷 파싱 오류: {e}")
            return None

    def _should_capture_packet(self, session_id: str, packet: PacketInfo) -> bool:
        """패킷 캡처 여부 결정"""
        # 필터 확인
        if session_id in self.capture_filters:
            capture_filter = self.capture_filters[session_id]
            if not capture_filter.matches(packet):
                return False

        return True

    def _process_captured_packet(self, session_id: str, packet: PacketInfo) -> None:
        """캡처된 패킷 처리"""
        try:
            # 통계 업데이트
            self.capture_stats["total_captured"] += 1
            self._update_stats("packets_captured")

            # 세션에 패킷 추가
            self.session_manager.add_packet_to_session(session_id, packet)

            # 전역 버퍼에 추가
            self.packet_buffer.add_packet(packet)

            # 콜백 호출
            self._notify_callbacks(packet)

        except Exception as e:
            self.logger.error(f"패킷 처리 오류: {e}")
            self.capture_stats["errors"] += 1

    def get_real_time_packet(self, session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """실시간 패킷 조회"""
        if session_id:
            # 특정 세션의 최신 패킷
            session = self.session_manager.get_session(session_id)
            if session:
                packets = session.get_packets(limit=1)
                return packets[0].to_dict() if packets else None
        else:
            # 전역 버퍼의 최신 패킷
            packet = self.packet_buffer.get_latest_packet()
            return packet.to_dict() if packet else None

    def get_latest_packets(self, session_id: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """최신 패킷 목록 조회"""
        if session_id:
            # 특정 세션의 패킷들
            session = self.session_manager.get_session(session_id)
            if session:
                packets = session.get_packets(limit=limit)
                return [p.to_dict() for p in packets]
        else:
            # 전역 버퍼의 패킷들
            packets = self.packet_buffer.get_packets(limit=limit)
            return [p.to_dict() for p in packets]

        return []

    def get_all_packets(self, session_id: str) -> List[Dict[str, Any]]:
        """세션의 모든 패킷 조회"""
        session = self.session_manager.get_session(session_id)
        if session:
            packets = session.get_packets()
            return [p.to_dict() for p in packets]
        return []

    def filter_packets(self, packets: List[Dict[str, Any]], filter_criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """패킷 필터링"""
        filtered_packets = []

        for packet in packets:
            should_include = True

            # 필터 조건 확인
            for key, value in filter_criteria.items():
                if key in packet and packet[key] != value:
                    should_include = False
                    break

            if should_include:
                filtered_packets.append(packet)

        return filtered_packets

    def get_capture_status(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """캡처 상태 조회"""
        if session_id:
            # 특정 세션 상태
            session = self.session_manager.get_session(session_id)
            if session:
                return {
                    "session_id": session_id,
                    "status": session.info.status.value,
                    "packets_captured": session.info.packets_captured,
                    "is_active": session_id in self.active_sessions,
                    "has_filter": session_id in self.capture_filters,
                }
        else:
            # 전체 캡처 상태
            return {
                "is_running": self.is_running,
                "active_sessions": len(self.active_sessions),
                "total_captured": self.capture_stats["total_captured"],
                "filtered_out": self.capture_stats["filtered_out"],
                "errors": self.capture_stats["errors"],
                "buffer_stats": self.packet_buffer.get_stats(),
                "start_time": (
                    self.capture_stats["start_time"].isoformat() if self.capture_stats["start_time"] else None
                ),
            }

        return {}

    def get_active_sessions(self) -> List[str]:
        """활성 캡처 세션 목록"""
        return list(self.active_sessions.keys())

    def create_capture_filter(self, **kwargs) -> CaptureFilter:
        """캡처 필터 생성"""
        return CaptureFilter(**kwargs)

    def export_capture_data(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """캡처 데이터 내보내기"""
        export_data = {
            "timestamp": datetime.now().isoformat(),
            "capture_stats": self.capture_stats.copy(),
            "buffer_stats": self.packet_buffer.get_stats(),
        }

        if session_id:
            # 특정 세션 데이터
            session_data = self.session_manager.export_session_data(session_id)
            if session_data:
                export_data["session_data"] = session_data
        else:
            # 모든 세션 데이터
            export_data["all_sessions"] = self.session_manager.get_all_sessions()
            export_data["global_packets"] = [p.to_dict() for p in self.packet_buffer.get_packets()]

        return export_data

    def get_performance_metrics(self) -> Dict[str, Any]:
        """성능 메트릭 조회"""
        stats = self.get_stats()
        buffer_stats = self.packet_buffer.get_stats()

        metrics = {
            "packets_per_second": stats.get("packets_per_second", 0),
            "buffer_usage_percent": buffer_stats["buffer_usage"],
            "active_sessions": len(self.active_sessions),
            "memory_usage": len(self.packet_buffer.packets) * 1024,  # 추정치
            "error_rate": self.capture_stats["errors"] / max(self.capture_stats["total_captured"], 1) * 100,
        }

        return metrics


# 편의 함수들
def create_packet_capturer(
    config: Optional[SnifferConfig] = None,
) -> PacketCapturer:
    """패킷 캡처러 생성"""
    return PacketCapturer(config)


def create_capture_filter(**kwargs) -> CaptureFilter:
    """캡처 필터 생성"""
    return CaptureFilter(**kwargs)
