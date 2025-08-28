#!/usr/bin/env python3
"""
세션 관리자 - 패킷 캡처 세션의 생명주기 관리
"""

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from utils.unified_logger import get_logger

from .base_sniffer import PacketInfo


class SessionStatus(Enum):
    """세션 상태"""

    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"
    COMPLETED = "completed"


@dataclass
class SessionConfig:
    """세션 설정"""

    name: str = ""
    description: str = ""
    max_duration: int = 3600  # 최대 지속 시간 (초)
    max_packets: int = 10000  # 최대 패킷 수
    auto_save: bool = True
    filter_rules: List[Dict[str, Any]] = field(default_factory=list)
    capture_interface: str = "any"
    buffer_size: int = 65536

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "max_duration": self.max_duration,
            "max_packets": self.max_packets,
            "auto_save": self.auto_save,
            "filter_rules": self.filter_rules,
            "capture_interface": self.capture_interface,
            "buffer_size": self.buffer_size,
        }


@dataclass
class SessionInfo:
    """세션 정보"""

    session_id: str
    config: SessionConfig
    status: SessionStatus = SessionStatus.CREATED
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    packets_captured: int = 0
    packets_filtered: int = 0
    total_bytes: int = 0
    error_count: int = 0
    last_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "config": self.config.to_dict(),
            "status": self.status.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "packets_captured": self.packets_captured,
            "packets_filtered": self.packets_filtered,
            "total_bytes": self.total_bytes,
            "error_count": self.error_count,
            "last_error": self.last_error,
            "duration": self.get_duration(),
        }

    def get_duration(self) -> Optional[float]:
        """세션 지속 시간 계산 (초)"""
        if self.start_time:
            end = self.end_time or datetime.now()
            return (end - self.start_time).total_seconds()
        return None


class CaptureSession:
    """개별 캡처 세션"""

    def __init__(self, session_id: str, config: SessionConfig):
        self.session_id = session_id
        self.config = config
        self.info = SessionInfo(session_id, config)
        self.logger = get_logger(f"session_{session_id[:8]}", "advanced")

        # 패킷 저장소
        self.packets: List[PacketInfo] = []
        self.packet_lock = threading.RLock()

        # 콜백 관리
        self.callbacks: List[Callable] = []

        # 세션 제어
        self._should_stop = threading.Event()
        self._is_paused = threading.Event()

        # 통계 업데이트 스레드
        self._stats_thread: Optional[threading.Thread] = None

        self.logger.info(f"캡처 세션 생성됨: {session_id}")

    def add_packet(self, packet: PacketInfo) -> bool:
        """패킷 추가"""
        if self.info.status != SessionStatus.RUNNING:
            return False

        if self._is_paused.is_set():
            return False

        # 최대 패킷 수 확인
        if self.info.packets_captured >= self.config.max_packets:
            self.logger.warning("최대 패킷 수 도달")
            self._stop_session(SessionStatus.COMPLETED)
            return False

        # 최대 지속 시간 확인
        if self.info.start_time:
            duration = (datetime.now() - self.info.start_time).total_seconds()
            if duration >= self.config.max_duration:
                self.logger.warning("최대 지속 시간 도달")
                self._stop_session(SessionStatus.COMPLETED)
                return False

        with self.packet_lock:
            self.packets.append(packet)
            self.info.packets_captured += 1
            self.info.total_bytes += packet.size

        # 콜백 호출
        self._notify_callbacks(packet)

        return True

    def add_callback(self, callback: Callable[[PacketInfo], None]) -> None:
        """패킷 콜백 추가"""
        if callback not in self.callbacks:
            self.callbacks.append(callback)

    def remove_callback(self, callback: Callable[[PacketInfo], None]) -> None:
        """패킷 콜백 제거"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)

    def _notify_callbacks(self, packet: PacketInfo) -> None:
        """콜백들에게 패킷 알림"""
        for callback in self.callbacks[:]:
            try:
                callback(packet)
            except Exception as e:
                self.logger.error(f"콜백 호출 실패: {e}")
                self.info.error_count += 1
                self.info.last_error = str(e)

    def start(self) -> bool:
        """세션 시작"""
        if self.info.status != SessionStatus.CREATED:
            return False

        self.info.status = SessionStatus.RUNNING
        self.info.start_time = datetime.now()
        self._should_stop.clear()
        self._is_paused.clear()

        # 통계 업데이트 스레드 시작
        self._stats_thread = threading.Thread(
            target=self._stats_updater,
            daemon=True,
            name=f"stats_{self.session_id[:8]}",
        )
        self._stats_thread.start()

        self.logger.info(f"세션 시작됨: {self.session_id}")
        return True

    def pause(self) -> bool:
        """세션 일시정지"""
        if self.info.status != SessionStatus.RUNNING:
            return False

        self.info.status = SessionStatus.PAUSED
        self._is_paused.set()
        self.logger.info(f"세션 일시정지됨: {self.session_id}")
        return True

    def resume(self) -> bool:
        """세션 재개"""
        if self.info.status != SessionStatus.PAUSED:
            return False

        self.info.status = SessionStatus.RUNNING
        self._is_paused.clear()
        self.logger.info(f"세션 재개됨: {self.session_id}")
        return True

    def stop(self) -> bool:
        """세션 중지"""
        return self._stop_session(SessionStatus.STOPPED)

    def _stop_session(self, status: SessionStatus) -> bool:
        """세션 중지 (내부)"""
        if self.info.status in [
            SessionStatus.STOPPED,
            SessionStatus.COMPLETED,
            SessionStatus.ERROR,
        ]:
            return False

        self.info.status = status
        self.info.end_time = datetime.now()
        self._should_stop.set()
        self._is_paused.clear()

        # 통계 스레드 종료 대기
        if self._stats_thread and self._stats_thread.is_alive():
            self._stats_thread.join(timeout=5)

        self.logger.info(f"세션 중지됨: {self.session_id} (상태: {status.value})")
        return True

    def get_packets(self, limit: Optional[int] = None, offset: int = 0) -> List[PacketInfo]:
        """패킷 조회"""
        with self.packet_lock:
            packets = self.packets[offset:]
            if limit:
                packets = packets[:limit]
            return packets

    def get_packet_count(self) -> int:
        """패킷 수 조회"""
        with self.packet_lock:
            return len(self.packets)

    def clear_packets(self) -> None:
        """패킷 데이터 삭제"""
        with self.packet_lock:
            self.packets.clear()
            self.info.packets_captured = 0
            self.info.total_bytes = 0
        self.logger.info(f"세션 패킷 데이터 삭제됨: {self.session_id}")

    def export_data(self) -> Dict[str, Any]:
        """세션 데이터 내보내기"""
        with self.packet_lock:
            return {
                "session_info": self.info.to_dict(),
                "packets": [packet.to_dict() for packet in self.packets],
            }

    def _stats_updater(self) -> None:
        """통계 업데이트 스레드"""
        while not self._should_stop.is_set():
            try:
                # 주기적으로 통계 정보 업데이트 (필요한 경우)
                self._should_stop.wait(timeout=10)
            except Exception as e:
                self.logger.error(f"통계 업데이트 오류: {e}")
                self.info.error_count += 1
                self.info.last_error = str(e)


class SessionManager:
    """세션 관리자"""

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__, "advanced")
        self.sessions: Dict[str, CaptureSession] = {}
        self.session_lock = threading.RLock()

        # 세션 정리 스레드
        self._cleanup_thread: Optional[threading.Thread] = None
        self._cleanup_stop = threading.Event()

        # 설정
        self.max_sessions = 50
        self.session_timeout = 24 * 3600  # 24시간

        self.logger.info("세션 매니저 초기화됨")
        self._start_cleanup_thread()

    def create_session(self, config: SessionConfig) -> str:
        """새 세션 생성"""
        # 세션 ID 생성
        session_id = str(uuid.uuid4())

        # 설정 검증
        if not config.name:
            config.name = f"Session_{session_id[:8]}"

        with self.session_lock:
            # 최대 세션 수 확인
            if len(self.sessions) >= self.max_sessions:
                # 오래된 세션 정리
                self._cleanup_old_sessions(force=True)

                if len(self.sessions) >= self.max_sessions:
                    raise RuntimeError("최대 세션 수에 도달했습니다")

            # 세션 생성
            session = CaptureSession(session_id, config)
            self.sessions[session_id] = session

        self.logger.info(f"새 세션 생성됨: {session_id} ({config.name})")
        return session_id

    def get_session(self, session_id: str) -> Optional[CaptureSession]:
        """세션 조회"""
        with self.session_lock:
            return self.sessions.get(session_id)

    def start_session(self, session_id: str) -> bool:
        """세션 시작"""
        session = self.get_session(session_id)
        if session:
            return session.start()
        return False

    def stop_session(self, session_id: str) -> bool:
        """세션 중지"""
        session = self.get_session(session_id)
        if session:
            return session.stop()
        return False

    def pause_session(self, session_id: str) -> bool:
        """세션 일시정지"""
        session = self.get_session(session_id)
        if session:
            return session.pause()
        return False

    def resume_session(self, session_id: str) -> bool:
        """세션 재개"""
        session = self.get_session(session_id)
        if session:
            return session.resume()
        return False

    def delete_session(self, session_id: str) -> bool:
        """세션 삭제"""
        with self.session_lock:
            if session_id not in self.sessions:
                return False

            session = self.sessions[session_id]

            # 실행 중인 세션은 먼저 중지
            if session.info.status == SessionStatus.RUNNING:
                session.stop()

            # 세션 제거
            del self.sessions[session_id]

        self.logger.info(f"세션 삭제됨: {session_id}")
        return True

    def get_active_sessions(self) -> List[str]:
        """활성 세션 목록 조회"""
        with self.session_lock:
            return [
                session_id
                for session_id, session in self.sessions.items()
                if session.info.status in [SessionStatus.RUNNING, SessionStatus.PAUSED]
            ]

    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """모든 세션 정보 조회"""
        with self.session_lock:
            return [session.info.to_dict() for session in self.sessions.values()]

    def get_session_details(self, session_id: str) -> Optional[Dict[str, Any]]:
        """세션 상세 정보 조회"""
        session = self.get_session(session_id)
        if session:
            return session.info.to_dict()
        return None

    def add_packet_to_session(self, session_id: str, packet: PacketInfo) -> bool:
        """세션에 패킷 추가"""
        session = self.get_session(session_id)
        if session:
            return session.add_packet(packet)
        return False

    def register_session_callback(self, session_id: str, callback: Callable) -> bool:
        """세션 콜백 등록"""
        session = self.get_session(session_id)
        if session:
            session.add_callback(callback)
            return True
        return False

    def export_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """세션 데이터 내보내기"""
        session = self.get_session(session_id)
        if session:
            return session.export_data()
        return None

    def get_session_statistics(self) -> Dict[str, Any]:
        """전체 세션 통계"""
        with self.session_lock:
            total_sessions = len(self.sessions)
            running_sessions = len([s for s in self.sessions.values() if s.info.status == SessionStatus.RUNNING])
            paused_sessions = len([s for s in self.sessions.values() if s.info.status == SessionStatus.PAUSED])
            completed_sessions = len([s for s in self.sessions.values() if s.info.status == SessionStatus.COMPLETED])

            total_packets = sum(s.info.packets_captured for s in self.sessions.values())
            total_bytes = sum(s.info.total_bytes for s in self.sessions.values())

            return {
                "total_sessions": total_sessions,
                "running_sessions": running_sessions,
                "paused_sessions": paused_sessions,
                "completed_sessions": completed_sessions,
                "total_packets_captured": total_packets,
                "total_bytes_captured": total_bytes,
                "max_sessions": self.max_sessions,
            }

    def _start_cleanup_thread(self) -> None:
        """정리 스레드 시작"""
        self._cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True, name="session_cleanup")
        self._cleanup_thread.start()

    def _cleanup_worker(self) -> None:
        """정리 작업자 스레드"""
        while not self._cleanup_stop.is_set():
            try:
                self._cleanup_old_sessions()
                self._cleanup_stop.wait(timeout=3600)  # 1시간마다 정리
            except Exception as e:
                self.logger.error(f"세션 정리 오류: {e}")

    def _cleanup_old_sessions(self, force: bool = False) -> None:
        """오래된 세션 정리"""
        current_time = datetime.now()
        sessions_to_delete = []

        with self.session_lock:
            for session_id, session in self.sessions.items():
                # 완료되거나 오래된 세션 정리
                should_delete = False

                if session.info.status in [
                    SessionStatus.COMPLETED,
                    SessionStatus.ERROR,
                ]:
                    if session.info.end_time:
                        age = (current_time - session.info.end_time).total_seconds()
                        if age > self.session_timeout or force:
                            should_delete = True

                # 강제 정리인 경우 가장 오래된 세션부터 삭제
                elif force and session.info.status == SessionStatus.STOPPED:
                    should_delete = True

                if should_delete:
                    sessions_to_delete.append(session_id)

        # 세션 삭제
        for session_id in sessions_to_delete:
            self.delete_session(session_id)
            self.logger.info(f"오래된 세션 정리됨: {session_id}")

    def shutdown(self) -> None:
        """세션 매니저 종료"""
        self.logger.info("세션 매니저 종료 중...")

        # 정리 스레드 중지
        self._cleanup_stop.set()
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5)

        # 모든 활성 세션 중지
        with self.session_lock:
            for session in self.sessions.values():
                if session.info.status == SessionStatus.RUNNING:
                    session.stop()

        self.logger.info("세션 매니저 종료 완료")


# 전역 세션 매니저 인스턴스
_global_session_manager: Optional[SessionManager] = None
_manager_lock = threading.Lock()


def get_session_manager() -> SessionManager:
    """전역 세션 매니저 반환"""
    global _global_session_manager
    with _manager_lock:
        if _global_session_manager is None:
            _global_session_manager = SessionManager()
        return _global_session_manager


# 편의 함수들
def create_capture_session(name: str = "", **kwargs) -> str:
    """캡처 세션 생성 편의 함수"""
    config = SessionConfig(name=name, **kwargs)
    return get_session_manager().create_session(config)


def start_capture_session(session_id: str) -> bool:
    """캡처 세션 시작 편의 함수"""
    return get_session_manager().start_session(session_id)


def stop_capture_session(session_id: str) -> bool:
    """캡처 세션 중지 편의 함수"""
    return get_session_manager().stop_session(session_id)
