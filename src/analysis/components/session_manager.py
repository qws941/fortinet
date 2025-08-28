"""
세션 관리 컴포넌트

분석 세션을 관리하고 세션별 데이터를 저장하는 책임을 담당합니다.
"""

import time
import uuid

from utils.unified_logger import setup_logger

logger = setup_logger("session_manager")


class SessionManager:
    """분석 세션 관리를 담당하는 클래스"""

    def __init__(self):
        """세션 매니저 초기화"""
        self.logger = logger
        self._sessions = {}  # 세션 ID별 저장 데이터
        self._session_timeout = 3600  # 1시간 (초)

    def create_session(self, user_id=None, session_name=None):
        """
        새 분석 세션 생성

        Args:
            user_id (str, optional): 사용자 ID
            session_name (str, optional): 세션 이름

        Returns:
            str: 생성된 세션 ID
        """
        session_id = str(uuid.uuid4())
        current_time = time.time()

        self._sessions[session_id] = {
            "id": session_id,
            "user_id": user_id,
            "name": session_name or f"Session_{session_id[:8]}",
            "created_at": current_time,
            "last_accessed": current_time,
            "data": {},
            "analysis_history": [],
            "firewall_configs": {},
        }

        self.logger.info(f"새 분석 세션 생성: {session_id}")
        return session_id

    def get_session(self, session_id):
        """
        세션 정보 조회

        Args:
            session_id (str): 세션 ID

        Returns:
            dict or None: 세션 정보
        """
        if session_id not in self._sessions:
            self.logger.warning(f"존재하지 않는 세션: {session_id}")
            return None

        session = self._sessions[session_id]

        # 세션 타임아웃 확인
        if self._is_session_expired(session):
            self.logger.info(f"만료된 세션 제거: {session_id}")
            del self._sessions[session_id]
            return None

        # 마지막 접근 시간 업데이트
        session["last_accessed"] = time.time()
        return session

    def _is_session_expired(self, session):
        """세션 만료 여부 확인"""
        return (time.time() - session["last_accessed"]) > self._session_timeout

    def store_analysis_result(self, session_id, analysis_type, result):
        """
        분석 결과를 세션에 저장

        Args:
            session_id (str): 세션 ID
            analysis_type (str): 분석 유형
            result (dict): 분석 결과

        Returns:
            bool: 저장 성공 여부
        """
        session = self.get_session(session_id)
        if not session:
            return False

        # 분석 이력에 추가
        analysis_record = {
            "timestamp": time.time(),
            "type": analysis_type,
            "result": result,
        }

        session["analysis_history"].append(analysis_record)

        # 최근 100개 기록만 유지
        if len(session["analysis_history"]) > 100:
            session["analysis_history"] = session["analysis_history"][-100:]

        self.logger.info(f"분석 결과 저장: {session_id} - {analysis_type}")
        return True
