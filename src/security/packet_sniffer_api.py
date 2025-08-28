#!/usr/bin/env python3
"""
패킷 스니퍼 통합 API - 기존 PacketSnifferAPI를 모듈화된 구조로 리팩터링
대용량 파일을 여러 모듈로 분산시킨 후 통합 인터페이스 제공
"""

import queue
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from .packet_sniffer.base_sniffer import SnifferConfig
from .packet_sniffer.device_manager import DeviceManager
from .packet_sniffer.packet_capturer import CaptureFilter, create_packet_capturer
from .packet_sniffer.session_manager import create_capture_session, get_session_manager

# 분석기들 - 선택적 import (의존성 문제가 있을 수 있음)
try:
    from .packet_sniffer.analyzers.protocol_analyzer import ProtocolAnalyzer

    HAS_PROTOCOL_ANALYZER = True
except ImportError:
    ProtocolAnalyzer = None
    HAS_PROTOCOL_ANALYZER = False

try:
    from .packet_sniffer.analyzers.http_analyzer import HTTPAnalyzer

    HAS_HTTP_ANALYZER = True
except ImportError:
    HTTPAnalyzer = None
    HAS_HTTP_ANALYZER = False

try:
    from .packet_sniffer.analyzers.tls_analyzer import TLSAnalyzer

    HAS_TLS_ANALYZER = True
except ImportError:
    TLSAnalyzer = None
    HAS_TLS_ANALYZER = False

try:
    from .packet_sniffer.exporters.data_exporter import DataExporter

    HAS_DATA_EXPORTER = True
except ImportError:
    DataExporter = None
    HAS_DATA_EXPORTER = False
from utils.unified_logger import get_logger

logger = get_logger(__name__, "advanced")


class PacketSnifferAPI:
    """
    패킷 스니퍼 통합 API 인터페이스
    모듈화된 구조를 하나의 편리한 인터페이스로 통합
    """

    def __init__(self, fortigate_client=None, faz_client=None, fmg_client=None):
        """
        PacketSnifferAPI 초기화

        Args:
            fortigate_client: FortiGate API 클라이언트 (legacy 호환성)
            faz_client: FortiAnalyzer API 클라이언트 (legacy 호환성)
            fmg_client: FortiManager API 클라이언트 (legacy 호환성)
        """
        self.logger = get_logger(self.__class__.__name__, "advanced")

        # Legacy API 클라이언트들 (하위 호환성)
        self.api_client = fortigate_client
        self.faz_client = faz_client
        self.fmg_client = fmg_client

        # 모듈화된 컴포넌트들
        self.session_manager = get_session_manager()

        # 설정 생성
        config = SnifferConfig()
        if fortigate_client:
            config.fortigate_host = getattr(fortigate_client, "host", "")
            config.fortigate_token = getattr(fortigate_client, "api_token", "")

        self.packet_capturer = create_packet_capturer(config)
        self.device_manager = DeviceManager(config)

        # 분석기들 - 조건부 초기화
        self.protocol_analyzer = ProtocolAnalyzer() if HAS_PROTOCOL_ANALYZER else None
        self.http_analyzer = HTTPAnalyzer() if HAS_HTTP_ANALYZER else None
        self.tls_analyzer = TLSAnalyzer() if HAS_TLS_ANALYZER else None

        # 내보내기 도구
        self.data_exporter = DataExporter() if HAS_DATA_EXPORTER else None

        # 초기화
        self._initialize_components()

        # Legacy 호환성을 위한 속성들
        self.active_sessions = {}
        self.packet_queues = {}
        self.capture_threads = {}
        self.capture_callbacks = {}
        self.stop_flags = {}
        self.deep_inspection_enabled = True
        self.stored_packets = {}

        self.logger.info("패킷 스니퍼 API 초기화 완료")

    def _initialize_components(self):
        """컴포넌트들 초기화"""
        try:
            self.packet_capturer.initialize()
            self.device_manager._initialize_interfaces()
            self.logger.info("모든 컴포넌트 초기화 완료")
        except Exception as e:
            self.logger.error(f"컴포넌트 초기화 실패: {e}")

    # ========== Legacy API 호환성 메서드들 ==========

    def get_available_devices(self) -> List[Dict[str, Any]]:
        """사용 가능한 장치 목록 조회"""
        try:
            return self.device_manager.get_available_devices()
        except Exception as e:
            self.logger.error(f"장치 목록 조회 실패: {e}")
            return []

    def get_device_interfaces(self, device_name: str) -> List[Dict[str, Any]]:
        """장치의 인터페이스 목록 조회"""
        try:
            return self.device_manager.get_device_interfaces(device_name)
        except Exception as e:
            self.logger.error(f"인터페이스 목록 조회 실패: {e}")
            return []

    def start_capture_session(self, params: Dict[str, Any], callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        캡처 세션 시작 (Legacy 호환성)

        Args:
            params: 캡처 매개변수
            callback: 선택적 콜백 함수

        Returns:
            세션 정보
        """
        try:
            # 세션 생성
            session_id = create_capture_session(
                name=params.get("name", ""),
                description=params.get("description", ""),
                max_duration=params.get("duration", 3600),
                max_packets=params.get("max_packets", 10000),
            )

            # 캡처 필터 생성
            capture_filter = None
            if any(
                key in params
                for key in [
                    "src_ip",
                    "dst_ip",
                    "src_port",
                    "dst_port",
                    "protocol",
                ]
            ):
                capture_filter = CaptureFilter(
                    src_ip=params.get("src_ip"),
                    dst_ip=params.get("dst_ip"),
                    src_port=params.get("src_port"),
                    dst_port=params.get("dst_port"),
                    protocol=params.get("protocol"),
                    interface=params.get("interface"),
                )

            # 콜백 등록
            if callback:
                self.session_manager.register_session_callback(session_id, callback)
                self.capture_callbacks[session_id] = callback

            # 캡처 시작
            interface = params.get("interface", "any")
            if self.packet_capturer.start_capture_session(session_id, capture_filter, interface):
                # Legacy 호환성을 위한 상태 업데이트
                self.active_sessions[session_id] = True
                self.packet_queues[session_id] = queue.Queue()
                self.stop_flags[session_id] = threading.Event()
                self.stored_packets[session_id] = []

                session_info = self.session_manager.get_session_details(session_id)
                return {
                    "success": True,
                    "session_id": session_id,
                    "message": "캡처 세션이 시작되었습니다",
                    "session_info": session_info,
                }
            else:
                return {"success": False, "error": "캡처 세션 시작 실패"}

        except Exception as e:
            self.logger.error(f"캡처 세션 시작 실패: {e}")
            return {"success": False, "error": str(e)}

    def stop_capture_session(self, session_id: str) -> Dict[str, Any]:
        """캡처 세션 중지"""
        try:
            if self.packet_capturer.stop_capture_session(session_id):
                # Legacy 상태 정리
                self.active_sessions.pop(session_id, None)
                self.packet_queues.pop(session_id, None)
                self.capture_callbacks.pop(session_id, None)
                if session_id in self.stop_flags:
                    self.stop_flags[session_id].set()
                    del self.stop_flags[session_id]

                return {"success": True, "message": "캡처 세션이 중지되었습니다"}
            else:
                return {"success": False, "error": "세션을 찾을 수 없습니다"}

        except Exception as e:
            self.logger.error(f"캡처 세션 중지 실패: {e}")
            return {"success": False, "error": str(e)}

    def get_capture_status(self, session_id: str) -> Dict[str, Any]:
        """캡처 상태 조회"""
        try:
            status = self.packet_capturer.get_capture_status(session_id)
            if status:
                return {"success": True, "status": status}
            else:
                return {"success": False, "error": "세션을 찾을 수 없습니다"}

        except Exception as e:
            self.logger.error(f"캡처 상태 조회 실패: {e}")
            return {"success": False, "error": str(e)}

    def get_capture_data(self, session_id: str) -> Dict[str, Any]:
        """캡처 데이터 조회"""
        try:
            packets = self.packet_capturer.get_all_packets(session_id)
            session_details = self.session_manager.get_session_details(session_id)

            return {
                "success": True,
                "session_id": session_id,
                "packets": packets,
                "packet_count": len(packets),
                "session_info": session_details,
            }

        except Exception as e:
            self.logger.error(f"캡처 데이터 조회 실패: {e}")
            return {"success": False, "error": str(e)}

    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """활성 세션 목록 조회"""
        try:
            return self.session_manager.get_active_sessions()
        except Exception as e:
            self.logger.error(f"활성 세션 조회 실패: {e}")
            return []

    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """모든 세션 목록 조회"""
        try:
            return self.session_manager.get_all_sessions()
        except Exception as e:
            self.logger.error(f"세션 목록 조회 실패: {e}")
            return []

    def register_packet_callback(self, session_id: str, callback: Callable) -> bool:
        """패킷 콜백 등록"""
        try:
            self.capture_callbacks[session_id] = callback
            return self.session_manager.register_session_callback(session_id, callback)
        except Exception as e:
            self.logger.error(f"콜백 등록 실패: {e}")
            return False

    def unregister_packet_callback(self, session_id: str) -> bool:
        """패킷 콜백 해제"""
        try:
            self.capture_callbacks.pop(session_id, None)
            return self.session_manager.unregister_packet_callback(session_id)
        except Exception as e:
            self.logger.error(f"콜백 해제 실패: {e}")
            return False

    def get_session_details(self, session_id: str) -> Dict[str, Any]:
        """세션 상세 정보 조회"""
        try:
            details = self.session_manager.get_session_details(session_id)
            if details:
                return {"success": True, "session_details": details}
            else:
                return {"success": False, "error": "세션을 찾을 수 없습니다"}

        except Exception as e:
            self.logger.error(f"세션 상세 정보 조회 실패: {e}")
            return {"success": False, "error": str(e)}

    def delete_session(self, session_id: str) -> bool:
        """세션 삭제"""
        try:
            # 먼저 캡처 중지
            if session_id in self.active_sessions:
                self.stop_capture_session(session_id)

            # 세션 삭제
            return self.session_manager.delete_session(session_id)

        except Exception as e:
            self.logger.error(f"세션 삭제 실패: {e}")
            return False

    def get_real_time_packet(self, session_id: str) -> Dict[str, Any]:
        """실시간 패킷 조회"""
        try:
            packet = self.packet_capturer.get_real_time_packet(session_id)
            if packet:
                return {"success": True, "packet": packet}
            else:
                return {"success": False, "message": "사용 가능한 패킷이 없습니다"}

        except Exception as e:
            self.logger.error(f"실시간 패킷 조회 실패: {e}")
            return {"success": False, "error": str(e)}

    def get_latest_packets(
        self,
        session_id: str,
        count: int = 10,
        filter_criteria: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """최신 패킷 목록 조회"""
        try:
            packets = self.packet_capturer.get_latest_packets(session_id, count)

            # 필터 적용
            if filter_criteria:
                packets = self.packet_capturer.filter_packets(packets, filter_criteria)

            return {
                "success": True,
                "packets": packets,
                "count": len(packets),
                "total_available": (
                    self.session_manager.get_session(session_id).get_packet_count()
                    if self.session_manager.get_session(session_id)
                    else 0
                ),
            }

        except Exception as e:
            self.logger.error(f"최신 패킷 조회 실패: {e}")
            return {"success": False, "error": str(e)}

    def get_all_packets(self, session_id: str) -> List[Dict[str, Any]]:
        """세션의 모든 패킷 조회"""
        try:
            return self.packet_capturer.get_all_packets(session_id)
        except Exception as e:
            self.logger.error(f"모든 패킷 조회 실패: {e}")
            return []

    def filter_packets(self, packets: List[Dict[str, Any]], filter_criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """패킷 필터링"""
        try:
            return self.packet_capturer.filter_packets(packets, filter_criteria)
        except Exception as e:
            self.logger.error(f"패킷 필터링 실패: {e}")
            return []

    # ========== 심층 분석 메서드들 ==========

    def analyze_packet_content(self, packet: Dict[str, Any]) -> Dict[str, Any]:
        """패킷 내용 심층 분석"""
        try:
            analysis_result = {
                "protocol_analysis": None,
                "http_analysis": None,
                "tls_analysis": None,
            }

            # 프로토콜 분석
            if self.protocol_analyzer:
                analysis_result["protocol_analysis"] = self.protocol_analyzer.analyze_packet(packet)

            # HTTP 분석
            if (
                self.http_analyzer
                and packet.get("protocol", "").upper() == "TCP"
                and packet.get("dst_port") in [80, 8080]
            ):
                analysis_result["http_analysis"] = self.http_analyzer.analyze_packet(packet)

            # TLS 분석
            if (
                self.tls_analyzer
                and packet.get("protocol", "").upper() == "TCP"
                and packet.get("dst_port") in [443, 8443]
            ):
                analysis_result["tls_analysis"] = self.tls_analyzer.analyze_packet(packet)

            return analysis_result

        except Exception as e:
            self.logger.error(f"패킷 분석 실패: {e}")
            return {}

    def analyze_session_traffic(self, session_id: str) -> Dict[str, Any]:
        """세션 트래픽 분석"""
        try:
            packets = self.get_all_packets(session_id)

            if not packets:
                return {"error": "분석할 패킷이 없습니다"}

            # 기본 통계
            total_packets = len(packets)
            total_bytes = sum(p.get("size", 0) for p in packets)

            # 프로토콜 분포
            protocol_stats = {}
            for packet in packets:
                protocol = packet.get("protocol", "Unknown")
                protocol_stats[protocol] = protocol_stats.get(protocol, 0) + 1

            # 포트 분석
            port_stats = {}
            for packet in packets:
                dst_port = packet.get("dst_port", 0)
                if dst_port > 0:
                    port_stats[dst_port] = port_stats.get(dst_port, 0) + 1

            # 상위 통신 대상
            ip_pairs = {}
            for packet in packets:
                src_ip = packet.get("src_ip", "")
                dst_ip = packet.get("dst_ip", "")
                if src_ip and dst_ip:
                    pair = f"{src_ip} -> {dst_ip}"
                    ip_pairs[pair] = ip_pairs.get(pair, 0) + 1

            return {
                "success": True,
                "session_id": session_id,
                "analysis": {
                    "total_packets": total_packets,
                    "total_bytes": total_bytes,
                    "protocol_distribution": protocol_stats,
                    "top_ports": dict(
                        sorted(
                            port_stats.items(),
                            key=lambda x: x[1],
                            reverse=True,
                        )[:10]
                    ),
                    "top_connections": dict(sorted(ip_pairs.items(), key=lambda x: x[1], reverse=True)[:10]),
                },
            }

        except Exception as e:
            self.logger.error(f"세션 트래픽 분석 실패: {e}")
            return {"success": False, "error": str(e)}

    # ========== 내보내기 메서드들 ==========

    def export_session_data(self, session_id: str, export_format: str = "json") -> Dict[str, Any]:
        """세션 데이터 내보내기"""
        try:
            export_data = self.packet_capturer.export_capture_data(session_id)

            if export_format.lower() == "json":
                return {"success": True, "format": "json", "data": export_data}
            elif export_format.lower() == "csv":
                if self.data_exporter:
                    csv_data = self.data_exporter.export_to_csv(export_data)
                    return {"success": True, "format": "csv", "data": csv_data}
                else:
                    return {
                        "success": False,
                        "error": "CSV 내보내기 모듈을 사용할 수 없습니다",
                    }
            else:
                return {
                    "success": False,
                    "error": f"지원하지 않는 형식: {export_format}",
                }

        except Exception as e:
            self.logger.error(f"데이터 내보내기 실패: {e}")
            return {"success": False, "error": str(e)}

    # ========== 성능 모니터링 ==========

    def get_performance_metrics(self) -> Dict[str, Any]:
        """성능 메트릭 조회"""
        try:
            capturer_metrics = self.packet_capturer.get_performance_metrics()
            session_stats = self.session_manager.get_session_statistics()

            return {
                "success": True,
                "metrics": {
                    "capturer": capturer_metrics,
                    "sessions": session_stats,
                    "timestamp": time.time(),
                },
            }

        except Exception as e:
            self.logger.error(f"성능 메트릭 조회 실패: {e}")
            return {"success": False, "error": str(e)}

    def get_system_status(self) -> Dict[str, Any]:
        """시스템 상태 조회"""
        try:
            return {
                "success": True,
                "status": {
                    "capturer_running": self.packet_capturer.is_running,
                    "active_sessions": len(self.active_sessions),
                    "total_sessions": len(self.session_manager.get_all_sessions()),
                    "components_initialized": True,
                    "deep_inspection_enabled": self.deep_inspection_enabled,
                },
            }

        except Exception as e:
            self.logger.error(f"시스템 상태 조회 실패: {e}")
            return {"success": False, "error": str(e)}

    # ========== Legacy 호환성 메서드들 ==========

    def _get_elapsed_time(self, session: Dict[str, Any]) -> str:
        """경과 시간 문자열 반환 (Legacy 호환성)"""
        if "start_time" in session and session["start_time"]:
            elapsed = time.time() - session["start_time"]
            return self._format_elapsed_time(elapsed)
        return "0초"

    def _format_elapsed_time(self, elapsed: float) -> str:
        """경과 시간 포맷팅"""
        if elapsed < 60:
            return f"{int(elapsed)}초"
        elif elapsed < 3600:
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            return f"{minutes}분 {seconds}초"
        else:
            hours = int(elapsed // 3600)
            minutes = int((elapsed % 3600) // 60)
            seconds = int(elapsed % 60)
            return f"{hours}시간 {minutes}분 {seconds}초"

    def cleanup(self):
        """리소스 정리"""
        try:
            # 모든 활성 세션 중지
            for session_id in list(self.active_sessions.keys()):
                self.stop_capture_session(session_id)

            # 컴포넌트들 정리
            self.packet_capturer.cleanup()
            self.device_manager.cleanup()
            self.session_manager.shutdown()

            self.logger.info("패킷 스니퍼 API 정리 완료")

        except Exception as e:
            self.logger.error(f"리소스 정리 실패: {e}")


# 편의 함수들
def create_packet_sniffer_api(fortigate_client=None, faz_client=None, fmg_client=None) -> PacketSnifferAPI:
    """패킷 스니퍼 API 생성 편의 함수"""
    return PacketSnifferAPI(fortigate_client, faz_client, fmg_client)


# 전역 인스턴스 (필요한 경우)
_global_api_instance = None
_api_lock = threading.Lock()


def get_packet_sniffer_api(**kwargs) -> PacketSnifferAPI:
    """전역 패킷 스니퍼 API 인스턴스 반환"""
    global _global_api_instance
    with _api_lock:
        if _global_api_instance is None:
            _global_api_instance = PacketSnifferAPI(**kwargs)
        return _global_api_instance
