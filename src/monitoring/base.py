#!/usr/bin/env python3
"""
모니터링 기반 클래스 - 모든 모니터링 모듈의 공통 기능 제공
CLAUDE.md 지시사항에 따른 통합 모니터링 프레임워크의 핵심 컴포넌트
"""
import json
import logging
import threading
import time
from abc import ABC, abstractmethod
from collections import deque
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional


class MonitoringBase(ABC):
    """모든 모니터링 모듈의 기반 클래스"""

    def __init__(
        self,
        name: str,
        collection_interval: float = 5.0,
        max_history: int = 1000,
    ):
        """
        Args:
            name: 모니터링 모듈 이름
            collection_interval: 수집 간격 (초)
            max_history: 최대 히스토리 개수
        """
        self.name = name
        self.collection_interval = collection_interval
        self.max_history = max_history

        # 상태 관리
        self.is_running = False
        self.is_paused = False
        self._thread = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()

        # 데이터 저장
        self.data_history = deque(maxlen=max_history)
        self.listeners = []
        self.error_count = 0
        self.last_error = None

        # 락 및 동기화
        self._lock = threading.RLock()

        # 로깅
        self.logger = logging.getLogger(f"monitoring.{name}")

        # 통계
        self.stats = {
            "start_time": None,
            "total_collections": 0,
            "successful_collections": 0,
            "failed_collections": 0,
            "average_collection_time": 0.0,
            "last_collection_time": None,
        }

    def start(self) -> bool:
        """모니터링 시작"""
        with self._lock:
            if self.is_running:
                self.logger.warning(f"{self.name} 모니터링이 이미 실행 중입니다")
                return False

            try:
                self.is_running = True
                self.is_paused = False
                self._stop_event.clear()
                self._pause_event.clear()

                self._thread = threading.Thread(
                    target=self._monitoring_loop,
                    name=f"{self.name}-monitor",
                    daemon=True,
                )
                self._thread.start()

                self.stats["start_time"] = datetime.now().isoformat()
                self.logger.info(f"{self.name} 모니터링 시작됨")

                # 초기화 후 처리
                self._on_start()
                return True

            except Exception as e:
                self.logger.error(f"{self.name} 모니터링 시작 실패: {e}")
                self.is_running = False
                return False

    def stop(self, timeout: float = 10.0) -> bool:
        """모니터링 중지"""
        with self._lock:
            if not self.is_running:
                return True

            try:
                self.logger.info(f"{self.name} 모니터링 중지 요청")

                # 중지 시그널 전송
                self.is_running = False
                self._stop_event.set()
                self._pause_event.set()  # pause 상태도 해제

                # 스레드 종료 대기
                if self._thread and self._thread.is_alive():
                    self._thread.join(timeout=timeout)

                    if self._thread.is_alive():
                        self.logger.warning(f"{self.name} 모니터링 스레드가 시간 초과로 강제 종료됨")
                        return False

                self.logger.info(f"{self.name} 모니터링 중지됨")

                # 종료 후 처리
                self._on_stop()
                return True

            except Exception as e:
                self.logger.error(f"{self.name} 모니터링 중지 실패: {e}")
                return False

    def pause(self):
        """모니터링 일시 정지"""
        if self.is_running and not self.is_paused:
            self.is_paused = True
            self._pause_event.set()
            self.logger.info(f"{self.name} 모니터링 일시 정지됨")

    def resume(self):
        """모니터링 재개"""
        if self.is_running and self.is_paused:
            self.is_paused = False
            self._pause_event.clear()
            self.logger.info(f"{self.name} 모니터링 재개됨")

    def add_listener(self, callback: Callable[[str, Dict], None]) -> bool:
        """
        리스너 추가

        Args:
            callback: 이벤트 콜백 함수 (event_type, data)
        """
        with self._lock:
            if callback not in self.listeners:
                self.listeners.append(callback)
                self.logger.debug(f"{self.name}에 리스너 추가됨")
                return True
            return False

    def remove_listener(self, callback: Callable) -> bool:
        """리스너 제거"""
        with self._lock:
            if callback in self.listeners:
                self.listeners.remove(callback)
                self.logger.debug(f"{self.name}에서 리스너 제거됨")
                return True
            return False

    def get_status(self) -> Dict:
        """현재 상태 조회"""
        with self._lock:
            return {
                "name": self.name,
                "is_running": self.is_running,
                "is_paused": self.is_paused,
                "collection_interval": self.collection_interval,
                "data_points": len(self.data_history),
                "error_count": self.error_count,
                "last_error": self.last_error,
                "stats": self.stats.copy(),
                "thread_alive": self._thread.is_alive() if self._thread else False,
            }

    def get_recent_data(self, minutes: int = 60) -> List[Dict]:
        """최근 데이터 조회"""
        cutoff = datetime.now() - timedelta(minutes=minutes)

        with self._lock:
            return [
                data
                for data in self.data_history
                if "timestamp" in data and datetime.fromisoformat(data["timestamp"]) > cutoff
            ]

    def get_statistics(self) -> Dict:
        """통계 정보 조회"""
        with self._lock:
            stats = self.stats.copy()

            if stats["total_collections"] > 0:
                stats["success_rate"] = stats["successful_collections"] / stats["total_collections"] * 100
                stats["error_rate"] = stats["failed_collections"] / stats["total_collections"] * 100
            else:
                stats["success_rate"] = 0.0
                stats["error_rate"] = 0.0

            # 실행 시간 계산
            if stats["start_time"]:
                start_time = datetime.fromisoformat(stats["start_time"])
                stats["uptime_seconds"] = (datetime.now() - start_time).total_seconds()
            else:
                stats["uptime_seconds"] = 0.0

            return stats

    def clear_history(self):
        """히스토리 데이터 정리"""
        with self._lock:
            self.data_history.clear()
            self.logger.info(f"{self.name} 히스토리 데이터 정리됨")

    def export_data(self, filepath: str, format: str = "json") -> bool:
        """데이터 내보내기"""
        try:
            with self._lock:
                data = {
                    "name": self.name,
                    "export_time": datetime.now().isoformat(),
                    "status": self.get_status(),
                    "statistics": self.get_statistics(),
                    "data_history": list(self.data_history),
                }

            if format.lower() == "json":
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            else:
                raise ValueError(f"지원하지 않는 형식: {format}")

            self.logger.info(f"{self.name} 데이터 내보내기 완료: {filepath}")
            return True

        except Exception as e:
            self.logger.error(f"{self.name} 데이터 내보내기 실패: {e}")
            return False

    def _monitoring_loop(self):
        """메인 모니터링 루프"""
        self.logger.info(f"{self.name} 모니터링 루프 시작")

        while self.is_running and not self._stop_event.is_set():
            try:
                # 일시 정지 상태 확인
                if self.is_paused:
                    self._pause_event.wait(timeout=1.0)
                    continue

                # 데이터 수집 시작 시간
                collection_start = time.time()

                # 데이터 수집 (추상 메서드)
                data = self._collect_data()

                if data is not None:
                    # 타임스탬프 추가
                    data["timestamp"] = datetime.now().isoformat()
                    data["collection_time"] = time.time() - collection_start

                    # 히스토리에 저장
                    with self._lock:
                        self.data_history.append(data)

                    # 통계 업데이트
                    self._update_stats(True, data["collection_time"])

                    # 데이터 처리 (추상 메서드)
                    processed_data = self._process_data(data)

                    # 리스너들에게 알림
                    self._notify_listeners("data_collected", processed_data or data)

                    # 추가 분석 (추상 메서드)
                    self._analyze_data(data)

                else:
                    self._update_stats(False)

                # 다음 수집까지 대기
                self._stop_event.wait(timeout=self.collection_interval)

            except Exception as e:
                self.error_count += 1
                self.last_error = {
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e),
                    "type": type(e).__name__,
                }

                self.logger.error(f"{self.name} 모니터링 루프 오류: {e}")
                self._update_stats(False)

                # 오류 시 더 긴 대기
                self._stop_event.wait(timeout=self.collection_interval * 2)

        self.logger.info(f"{self.name} 모니터링 루프 종료")

    def _update_stats(self, success: bool, collection_time: float = 0.0):
        """통계 업데이트"""
        with self._lock:
            self.stats["total_collections"] += 1
            self.stats["last_collection_time"] = datetime.now().isoformat()

            if success:
                self.stats["successful_collections"] += 1

                # 평균 수집 시간 계산
                total_time = (
                    self.stats["average_collection_time"] * (self.stats["successful_collections"] - 1) + collection_time
                )
                self.stats["average_collection_time"] = total_time / self.stats["successful_collections"]
            else:
                self.stats["failed_collections"] += 1

    def _notify_listeners(self, event_type: str, data: Dict):
        """리스너들에게 이벤트 알림"""
        with self._lock:
            listeners_to_remove = []

            for listener in self.listeners:
                try:
                    listener(
                        event_type,
                        {
                            "source": self.name,
                            "data": data,
                            "timestamp": datetime.now().isoformat(),
                        },
                    )
                except Exception as e:
                    self.logger.error(f"{self.name} 리스너 호출 실패: {e}")
                    listeners_to_remove.append(listener)

            # 실패한 리스너 제거
            for listener in listeners_to_remove:
                self.listeners.remove(listener)

    # 추상 메서드들 - 각 모니터링 모듈에서 구현해야 함
    @abstractmethod
    def _collect_data(self) -> Optional[Dict]:
        """데이터 수집 (필수 구현)"""

    def _process_data(self, data: Dict) -> Optional[Dict]:
        """데이터 처리 (선택적 구현)"""
        return None

    def _analyze_data(self, data: Dict):
        """데이터 분석 (선택적 구현)"""

    def _on_start(self):
        """시작 시 콜백 (선택적 구현)"""

    def _on_stop(self):
        """중지 시 콜백 (선택적 구현)"""


class HealthCheckMixin:
    """헬스체크 기능을 제공하는 믹스인"""

    def __init__(self, *args, **kwargs):
        # 믹스인 초기화는 안전하게 처리
        if hasattr(super(), "__init__"):
            super().__init__(*args, **kwargs)

        # 속성 초기화 (중복 방지)
        if not hasattr(self, "health_status"):
            self.health_status = "unknown"
        if not hasattr(self, "health_details"):
            self.health_details = {}

    def get_health(self) -> Dict:
        """헬스 상태 조회"""
        return {
            "status": self.health_status,
            "details": self.health_details,
            "timestamp": datetime.now().isoformat(),
        }

    def _update_health(self, status: str, details: Dict = None):
        """헬스 상태 업데이트"""
        self.health_status = status
        self.health_details = details or {}


class ThresholdMixin:
    """임계값 관리 기능을 제공하는 믹스인"""

    def __init__(self, *args, **kwargs):
        # 믹스인 초기화는 안전하게 처리
        if hasattr(super(), "__init__"):
            super().__init__(*args, **kwargs)

        # 속성 초기화 (중복 방지)
        if not hasattr(self, "thresholds"):
            self.thresholds = {}
        if not hasattr(self, "threshold_violations"):
            self.threshold_violations = deque(maxlen=100)

    def set_threshold(self, name: str, warning: float, critical: float):
        """임계값 설정"""
        self.thresholds[name] = {"warning": warning, "critical": critical}

    def check_threshold(self, name: str, value: float) -> Optional[str]:
        """임계값 체크"""
        if name not in self.thresholds:
            return None

        threshold = self.thresholds[name]

        if value >= threshold["critical"]:
            severity = "critical"
        elif value >= threshold["warning"]:
            severity = "warning"
        else:
            return None

        # 위반 기록
        violation = {
            "name": name,
            "value": value,
            "threshold": threshold[severity],
            "severity": severity,
            "timestamp": datetime.now().isoformat(),
        }

        self.threshold_violations.append(violation)
        return severity

    def get_threshold_violations(self, hours: int = 24) -> List[Dict]:
        """임계값 위반 히스토리 조회"""
        cutoff = datetime.now() - timedelta(hours=hours)

        return [v for v in self.threshold_violations if datetime.fromisoformat(v["timestamp"]) > cutoff]


# 전역 모니터링 레지스트리
_monitoring_registry = {}
_registry_lock = threading.RLock()


def register_monitor(monitor: MonitoringBase) -> bool:
    """모니터링 모듈 등록"""
    with _registry_lock:
        if monitor.name in _monitoring_registry:
            return False
        _monitoring_registry[monitor.name] = monitor
        return True


def unregister_monitor(name: str) -> bool:
    """모니터링 모듈 등록 해제"""
    with _registry_lock:
        if name in _monitoring_registry:
            del _monitoring_registry[name]
            return True
        return False


def get_monitor(name: str) -> Optional[MonitoringBase]:
    """등록된 모니터링 모듈 조회"""
    with _registry_lock:
        return _monitoring_registry.get(name)


def get_all_monitors() -> Dict[str, MonitoringBase]:
    """모든 등록된 모니터링 모듈 조회"""
    with _registry_lock:
        return _monitoring_registry.copy()


def start_all_monitors() -> Dict[str, bool]:
    """모든 모니터링 모듈 시작"""
    results = {}
    with _registry_lock:
        for name, monitor in _monitoring_registry.items():
            results[name] = monitor.start()
    return results


def stop_all_monitors() -> Dict[str, bool]:
    """모든 모니터링 모듈 중지"""
    results = {}
    with _registry_lock:
        for name, monitor in _monitoring_registry.items():
            results[name] = monitor.stop()
    return results


if __name__ == "__main__":
    # 테스트용 더미 모니터
    class TestMonitor(MonitoringBase):
        def _collect_data(self):
            return {"test_value": time.time(), "random_data": "test"}

    # 테스트 실행
    test_monitor = TestMonitor("test", collection_interval=1.0)
    register_monitor(test_monitor)

    def test_listener(event_type, data):
        print(f"이벤트: {event_type}, 데이터: {data['data']}")

    test_monitor.add_listener(test_listener)
    test_monitor.start()

    try:
        time.sleep(5)
    except KeyboardInterrupt:
        pass

    test_monitor.stop()
    print("테스트 완료")
