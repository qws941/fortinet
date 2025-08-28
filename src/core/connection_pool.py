#!/usr/bin/env python3
"""
HTTP Connection Pool Manager
중앙화된 연결 풀 관리로 성능 최적화
"""

import logging
import threading
from typing import Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config.constants import BATCH_SETTINGS

logger = logging.getLogger(__name__)


class ConnectionPoolManager:
    """
    싱글톤 패턴 기반 연결 풀 매니저
    모든 API 클라이언트가 공유하는 연결 풀 제공
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, max_pool_size=None):
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._sessions = {}
            self._default_pool_size = max_pool_size or BATCH_SETTINGS["CONNECTION_POOL_SIZE"]
            self._default_pool_maxsize = max_pool_size or BATCH_SETTINGS["CONNECTION_POOL_SIZE"]
            self._default_max_retries = BATCH_SETTINGS["MAX_RETRIES"]
            self._default_backoff_factor = 0.3
            self._default_status_forcelist = [500, 502, 503, 504]

            logger.info("ConnectionPoolManager initialized")

    def get_session(
        self,
        identifier: str,
        pool_connections: Optional[int] = None,
        pool_maxsize: Optional[int] = None,
        max_retries: Optional[int] = None,
        backoff_factor: Optional[float] = None,
        status_forcelist: Optional[list] = None,
    ) -> requests.Session:
        """
        지정된 식별자에 대한 세션 가져오기 또는 생성

        Args:
            identifier: 세션 식별자 (예: 'fortigate', 'fortimanager')
            pool_connections: 연결 풀 크기
            pool_maxsize: 최대 연결 풀 크기
            max_retries: 최대 재시도 횟수
            backoff_factor: 재시도 간격 배수
            status_forcelist: 재시도할 HTTP 상태 코드

        Returns:
            requests.Session: 구성된 세션 객체
        """
        if identifier not in self._sessions:
            with self._lock:
                if identifier not in self._sessions:
                    self._sessions[identifier] = self._create_session(
                        pool_connections or self._default_pool_size,
                        pool_maxsize or self._default_pool_maxsize,
                        max_retries or self._default_max_retries,
                        backoff_factor or self._default_backoff_factor,
                        status_forcelist or self._default_status_forcelist,
                    )
                    logger.info(f"Created new session for {identifier}")

        return self._sessions[identifier]

    def _create_session(
        self,
        pool_connections: int,
        pool_maxsize: int,
        max_retries: int,
        backoff_factor: float,
        status_forcelist: list,
    ) -> requests.Session:
        """
        새로운 세션 생성 및 구성
        """
        session = requests.Session()

        # 재시도 전략 설정
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
            allowed_methods=[
                "HEAD",
                "GET",
                "PUT",
                "DELETE",
                "OPTIONS",
                "TRACE",
                "POST",
            ],
        )

        # HTTP 어댑터 설정
        adapter = HTTPAdapter(
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
            max_retries=retry_strategy,
        )

        # 어댑터 마운트
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # 기본 헤더 설정
        session.headers.update(
            {
                "User-Agent": "FortiGate-Nextrade/1.0",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

        return session

    def close_session(self, identifier: str):
        """
        특정 세션 닫기

        Args:
            identifier: 세션 식별자
        """
        if identifier in self._sessions:
            with self._lock:
                if identifier in self._sessions:
                    self._sessions[identifier].close()
                    del self._sessions[identifier]
                    logger.info(f"Closed session for {identifier}")

    def return_session(self, identifier: str, session: requests.Session):
        """
        세션을 풀에 반환 (호환성을 위한 메서드)

        Args:
            identifier: 세션 식별자
            session: 반환할 세션
        """
        # 현재 구현에서는 세션이 이미 풀에서 관리되므로 별도 작업 불필요
        logger.debug(f"Session returned for {identifier}")

    def close_all_sessions(self):
        """
        모든 세션 닫기
        """
        with self._lock:
            for identifier, session in self._sessions.items():
                session.close()
                logger.info(f"Closed session for {identifier}")
            self._sessions.clear()

    def get_stats(self) -> Dict[str, Dict]:
        """
        연결 풀 통계 가져오기

        Returns:
            dict: 각 세션의 연결 풀 통계
        """
        stats = {}
        for identifier, session in self._sessions.items():
            adapter = session.get_adapter("https://")
            if hasattr(adapter, "poolmanager") and adapter.poolmanager:
                pool_stats = {
                    "num_connections": len(adapter.poolmanager.pools),
                    "num_requests": (
                        adapter.poolmanager.num_requests if hasattr(adapter.poolmanager, "num_requests") else 0
                    ),
                    "num_connections_dropped": (
                        adapter.poolmanager.num_connections_dropped
                        if hasattr(adapter.poolmanager, "num_connections_dropped")
                        else 0
                    ),
                }
            else:
                pool_stats = {
                    "num_connections": 0,
                    "num_requests": 0,
                    "num_connections_dropped": 0,
                }
            stats[identifier] = pool_stats

        return stats

    def __del__(self):
        """소멸자 - 모든 세션 정리"""
        try:
            self.close_all_sessions()
        except Exception:
            pass


# 전역 연결 풀 매니저 인스턴스
connection_pool_manager = ConnectionPoolManager()
