#!/usr/bin/env python3
"""
FortiGate 실시간 모니터링 모듈
실시간 모니터링 기능을 제공하는 클래스
"""

import json
import logging
import threading
import time
from typing import Any, Dict

# Logger 설정
logger = logging.getLogger(__name__)


class FortigateMonitor:
    """FortiGate 실시간 모니터링 클래스"""

    def __init__(self):
        """모니터 초기화"""
        self.is_running = False
        self.monitor_thread = None
        self.listeners = []
        self.data_cache = {}
        logger.info("FortigateMonitor 초기화 완료")

    def start(self) -> bool:
        """모니터링 시작"""
        try:
            if self.is_running:
                logger.warning("모니터링이 이미 실행 중입니다")
                return True

            self.is_running = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()

            logger.info("FortiGate 모니터링 시작됨")
            return True

        except Exception as e:
            logger.error(f"모니터링 시작 실패: {e}")
            return False

    def stop(self) -> bool:
        """모니터링 중지"""
        try:
            self.is_running = False
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=5.0)

            logger.info("FortiGate 모니터링 중지됨")
            return True

        except Exception as e:
            logger.error(f"모니터링 중지 실패: {e}")
            return False

    def add_listener(self, callback) -> bool:
        """이벤트 리스너 추가"""
        try:
            if callback not in self.listeners:
                self.listeners.append(callback)
                logger.debug("리스너 추가됨")
                return True
            return False

        except Exception as e:
            logger.error(f"리스너 추가 실패: {e}")
            return False

    def remove_listener(self, callback) -> bool:
        """이벤트 리스너 제거"""
        try:
            if callback in self.listeners:
                self.listeners.remove(callback)
                logger.debug("리스너 제거됨")
                return True
            return False

        except Exception as e:
            logger.error(f"리스너 제거 실패: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """모니터 상태 반환"""
        return {
            "running": self.is_running,
            "listeners_count": len(self.listeners),
            "data_cache_size": len(self.data_cache),
            "thread_alive": (self.monitor_thread.is_alive() if self.monitor_thread else False),
        }

    def get_real_time_data(self) -> Dict[str, Any]:
        """실시간 데이터 반환"""
        try:
            # 테스트 모드용 더미 데이터
            current_time = time.time()

            return {
                "timestamp": current_time,
                "system_info": {
                    "cpu_usage": 25.5,
                    "memory_usage": 45.2,
                    "uptime": 86400,
                    "version": "FortiOS 7.4.0",
                },
                "traffic_stats": {
                    "bytes_in": 1024000,
                    "bytes_out": 512000,
                    "packets_in": 1500,
                    "packets_out": 1200,
                },
                "connections": {"active": 150, "total": 1500, "ssl_vpn": 25},
                "security": {
                    "threats_blocked": 5,
                    "ips_attacks": 2,
                    "antivirus_detections": 1,
                },
            }

        except Exception as e:
            logger.error(f"실시간 데이터 가져오기 실패: {e}")
            return {}

    def _monitor_loop(self):
        """모니터링 루프 (별도 스레드에서 실행)"""
        logger.info("모니터링 루프 시작")

        while self.is_running:
            try:
                # 실시간 데이터 수집
                data = self.get_real_time_data()

                # 캐시 업데이트
                self.data_cache.update(data)

                # 리스너들에게 데이터 전송
                self._notify_listeners(data)

                # 5초 대기
                time.sleep(5)

            except Exception as e:
                logger.error(f"모니터링 루프 오류: {e}")
                time.sleep(10)  # 오류 시 더 긴 대기

        logger.info("모니터링 루프 종료")

    def _notify_listeners(self, data: Dict[str, Any]):
        """등록된 리스너들에게 데이터 전송"""
        for listener in self.listeners[:]:  # 복사본으로 순회
            try:
                listener(data)
            except Exception as e:
                logger.error(f"리스너 호출 오류: {e}")
                # 오류가 발생한 리스너는 제거
                try:
                    self.listeners.remove(listener)
                except ValueError:
                    pass  # 이미 제거됨


# 전역 모니터 인스턴스
_global_monitor = None


def get_monitor() -> FortigateMonitor:
    """전역 모니터 인스턴스 반환"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = FortigateMonitor()
    return _global_monitor


def start_monitoring() -> bool:
    """모니터링 시작 (편의 함수)"""
    monitor = get_monitor()
    return monitor.start()


def stop_monitoring() -> bool:
    """모니터링 중지 (편의 함수)"""
    monitor = get_monitor()
    return monitor.stop()


def get_monitoring_status() -> Dict[str, Any]:
    """모니터링 상태 반환 (편의 함수)"""
    monitor = get_monitor()
    return monitor.get_status()


if __name__ == "__main__":
    # 테스트 코드
    print("FortiGate Monitor 테스트 시작")

    monitor = FortigateMonitor()

    # 테스트 리스너
    def test_listener(data):
        print(f"데이터 수신: {json.dumps(data, indent=2)}")

    monitor.add_listener(test_listener)
    monitor.start()

    try:
        time.sleep(20)  # 20초 동안 실행
    except KeyboardInterrupt:
        print("중단됨")

    monitor.stop()
    print("테스트 완료")
