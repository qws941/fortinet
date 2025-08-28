#!/usr/bin/env python3
"""
통합 모니터링 관리자 - 모든 모니터링 모듈을 중앙에서 관리
CLAUDE.md 지시사항에 따른 완전 자율적 모니터링 시스템의 중앙 제어기
"""
import json
import logging
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from threading import RLock
from typing import Callable, Dict, List

from config.unified_settings import CONFIG
from utils.performance_optimizer import LRUCache, measure_time

from .base import MonitoringBase, register_monitor, unregister_monitor
from .config import get_config_manager

logger = logging.getLogger(__name__)


class EventAggregator:
    """이벤트 집계 및 처리 - 성능 최적화됨"""

    def __init__(self):
        # 성능 최적화: 메모리 사용량 줄이기
        self.events = deque(maxlen=CONFIG.thresholds.MAX_EVENT_QUEUE_SIZE)
        self.event_handlers = defaultdict(list)
        self.correlation_rules = []
        self._lock = RLock()
        # 이벤트 캐시 추가
        self._event_cache = LRUCache(maxsize=1000)

    def add_event(self, event: Dict):
        """이벤트 추가"""
        with self._lock:
            event["id"] = f"evt_{datetime.now().timestamp()}"
            event["timestamp"] = datetime.now().isoformat()
            self.events.append(event)

            # 이벤트 핸들러 실행
            self._process_event(event)

            # 상관관계 분석
            self._analyze_correlations(event)

    def add_handler(self, event_type: str, handler: Callable):
        """이벤트 핸들러 추가"""
        with self._lock:
            if handler not in self.event_handlers[event_type]:
                self.event_handlers[event_type].append(handler)

    def remove_handler(self, event_type: str, handler: Callable):
        """이벤트 핸들러 제거"""
        with self._lock:
            if handler in self.event_handlers[event_type]:
                self.event_handlers[event_type].remove(handler)

    @measure_time
    def get_events(self, hours: int = 1, event_type: str = None) -> List[Dict]:
        """이벤트 조회 - 캐시 최적화됨"""
        # 캐시 키 생성
        cache_key = f"events_{hours}_{event_type}"
        cached_result = self._event_cache.get(cache_key)

        if cached_result is not None:
            return cached_result

        cutoff = datetime.now() - timedelta(hours=hours)

        with self._lock:
            filtered_events = [event for event in self.events if datetime.fromisoformat(event["timestamp"]) > cutoff]

            if event_type:
                filtered_events = [event for event in filtered_events if event.get("type") == event_type]

            result = sorted(filtered_events, key=lambda x: x["timestamp"], reverse=True)

            # 결과를 캐시에 저장 (30초 TTL)
            self._event_cache.set(cache_key, result)

            return result

    def _process_event(self, event: Dict):
        """이벤트 처리"""
        event_type = event.get("type", "unknown")

        for handler in self.event_handlers[event_type]:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"이벤트 핸들러 실행 실패: {e}")

    def _analyze_correlations(self, event: Dict):
        """이벤트 상관관계 분석"""
        # 간단한 상관관계 분석 (추후 확장 가능)
        recent_events = self.get_events(hours=1)

        # 유사한 이벤트 패턴 감지
        similar_events = [
            e
            for e in recent_events[-10:]  # 최근 10개 이벤트
            if e.get("source") == event.get("source") and e.get("type") == event.get("type")
        ]

        if len(similar_events) >= 3:
            # 패턴 감지 이벤트 생성
            pattern_event = {
                "type": "pattern_detected",
                "source": "event_aggregator",
                "data": {
                    "pattern_type": f"{event.get('source')}_{event.get('type')}",
                    "event_count": len(similar_events),
                    "time_window": "1 hour",
                },
            }
            self.add_event(pattern_event)


class DataIntegrator:
    """모니터링 데이터 통합 및 분석"""

    def __init__(self):
        self.integrated_data = deque(maxlen=1000)
        self.correlation_cache = {}
        self._lock = RLock()

    def integrate_data(self, monitor_data: Dict[str, Dict]) -> Dict:
        """여러 모니터링 모듈의 데이터를 통합"""
        try:
            with self._lock:
                integrated = {
                    "timestamp": datetime.now().isoformat(),
                    "sources": list(monitor_data.keys()),
                    "data": monitor_data.copy(),
                    "correlations": {},
                    "insights": [],
                    "alerts": [],
                }

                # 상관관계 분석
                integrated["correlations"] = self._analyze_data_correlations(monitor_data)

                # 인사이트 생성
                integrated["insights"] = self._generate_insights(monitor_data)

                # 통합 알림 생성
                integrated["alerts"] = self._generate_integrated_alerts(monitor_data)

                # 통합 데이터 저장
                self.integrated_data.append(integrated)

                return integrated

        except Exception as e:
            logger.error(f"데이터 통합 실패: {e}")
            return {}

    def _analyze_data_correlations(self, data: Dict[str, Dict]) -> Dict:
        """데이터 간 상관관계 분석"""
        correlations = {}

        try:
            # 시스템 메트릭과 API 성능 상관관계
            if "system_metrics" in data and "api_performance" in data:
                system_data = data["system_metrics"].get("data", {})
                data["api_performance"].get("data", {})

                cpu_usage = system_data.get("cpu", {}).get("usage_percent", 0)
                memory_usage = system_data.get("memory", {}).get("usage_percent", 0)

                # API 응답시간과 시스템 리소스 상관관계
                if cpu_usage > 80 or memory_usage > 80:
                    correlations["high_resource_usage"] = {
                        "description": "높은 시스템 리소스 사용률이 API 성능에 영향을 줄 수 있습니다",
                        "cpu_usage": cpu_usage,
                        "memory_usage": memory_usage,
                        "severity": ("warning" if max(cpu_usage, memory_usage) < 90 else "critical"),
                    }

            # 보안 스캔과 시스템 상태 상관관계
            if "security_scanner" in data and "system_metrics" in data:
                security_data = data["security_scanner"].get("data", {})
                vulnerabilities = security_data.get("vulnerabilities", [])

                if vulnerabilities:
                    high_severity = [v for v in vulnerabilities if v.get("severity") in ["high", "critical"]]
                    if high_severity:
                        correlations["security_risk"] = {
                            "description": "높은 심각도의 보안 취약점이 발견되었습니다",
                            "vulnerability_count": len(high_severity),
                            "severity": "critical",
                        }

        except Exception as e:
            logger.error(f"상관관계 분석 실패: {e}")

        return correlations

    def _generate_insights(self, data: Dict[str, Dict]) -> List[Dict]:
        """데이터 기반 인사이트 생성"""
        insights = []

        try:
            # 성능 추세 분석
            if "api_performance" in data:
                api_data = data["api_performance"].get("data", {})
                stats = api_data.get("overall_stats", {})

                if stats.get("overall_error_rate", 0) > 5:
                    insights.append(
                        {
                            "type": "performance",
                            "title": "API 오류율 증가",
                            "description": f"전체 API 오류율이 {stats['overall_error_rate']:.1f}%로 높습니다",
                            "recommendation": "API 엔드포인트별 상세 분석이 필요합니다",
                            "priority": "high",
                        }
                    )

            # 리소스 사용 패턴 분석
            if "system_metrics" in data:
                system_data = data["system_metrics"].get("data", {})

                cpu_usage = system_data.get("cpu", {}).get("usage_percent", 0)
                memory_usage = system_data.get("memory", {}).get("usage_percent", 0)

                if cpu_usage > 70 and memory_usage > 70:
                    insights.append(
                        {
                            "type": "resource",
                            "title": "시스템 리소스 압박",
                            "description": f"CPU {cpu_usage:.1f}%, 메모리 {memory_usage:.1f}% 사용 중",
                            "recommendation": "리소스 확장 또는 워크로드 최적화를 고려하세요",
                            "priority": "medium",
                        }
                    )

            # 보안 상태 분석
            if "security_scanner" in data:
                security_data = data["security_scanner"].get("data", {})
                scan_result = security_data.get("latest_scan", {})

                critical_vulns = scan_result.get("severity_summary", {}).get("critical", 0)
                if critical_vulns > 0:
                    insights.append(
                        {
                            "type": "security",
                            "title": "중요 보안 취약점 발견",
                            "description": f"{critical_vulns}개의 중요 취약점이 발견되었습니다",
                            "recommendation": "즉시 보안 패치를 적용하세요",
                            "priority": "critical",
                        }
                    )

        except Exception as e:
            logger.error(f"인사이트 생성 실패: {e}")

        return insights

    def _generate_integrated_alerts(self, data: Dict[str, Dict]) -> List[Dict]:
        """통합 알림 생성"""
        alerts = []

        try:
            # 각 모니터링 모듈의 알림 수집
            for source, module_data in data.items():
                module_alerts = module_data.get("data", {}).get("alerts", [])
                for alert in module_alerts:
                    alert["source"] = source
                    alerts.append(alert)

            # 중복 제거 및 우선순위 정렬
            unique_alerts = self._deduplicate_alerts(alerts)
            return sorted(
                unique_alerts,
                key=lambda x: self._get_alert_priority(x),
                reverse=True,
            )

        except Exception as e:
            logger.error(f"통합 알림 생성 실패: {e}")
            return []

    def _deduplicate_alerts(self, alerts: List[Dict]) -> List[Dict]:
        """중복 알림 제거"""
        seen = set()
        unique_alerts = []

        for alert in alerts:
            # 알림 식별자 생성 (소스 + 유형 + 메시지 해시)
            identifier = f"{alert.get('source')}_{alert.get('type')}_{hash(alert.get('message', ''))}"

            if identifier not in seen:
                seen.add(identifier)
                unique_alerts.append(alert)

        return unique_alerts

    def _get_alert_priority(self, alert: Dict) -> int:
        """알림 우선순위 계산"""
        severity_weights = {
            "critical": 100,
            "high": 80,
            "error": 70,
            "warning": 50,
            "medium": 40,
            "info": 20,
            "low": 10,
        }

        severity = alert.get("severity", "info")
        return severity_weights.get(severity, 0)


class UnifiedMonitoringManager:
    """통합 모니터링 관리자"""

    def __init__(self):
        self.config_manager = get_config_manager()
        self.event_aggregator = EventAggregator()
        self.data_integrator = DataIntegrator()

        # 상태 관리
        self.is_running = False
        self.management_thread = None
        self._stop_event = threading.Event()
        self._lock = RLock()

        # 등록된 모니터링 모듈
        self.monitors = {}

        # 글로벌 리스너
        self.global_listeners = []

        # 통계
        self.stats = {
            "start_time": None,
            "total_events": 0,
            "total_alerts": 0,
            "active_monitors": 0,
            "last_integration": None,
        }

        # 설정 변경 감시
        self.config_manager.add_config_watcher(self._on_config_changed)

    def start(self) -> bool:
        """통합 모니터링 시스템 시작"""
        try:
            with self._lock:
                if self.is_running:
                    logger.warning("통합 모니터링 매니저가 이미 실행 중입니다")
                    return False

                logger.info("통합 모니터링 시스템 시작")

                # 등록된 모든 모니터 시작
                self._start_all_monitors()

                # 관리 스레드 시작
                self.is_running = True
                self._stop_event.clear()
                self.management_thread = threading.Thread(
                    target=self._management_loop,
                    name="unified-monitoring-manager",
                    daemon=True,
                )
                self.management_thread.start()

                # 통계 초기화
                self.stats["start_time"] = datetime.now().isoformat()
                self.stats["active_monitors"] = len(self.monitors)

                logger.info("통합 모니터링 시스템 시작 완료")
                return True

        except Exception as e:
            logger.error(f"통합 모니터링 시스템 시작 실패: {e}")
            return False

    def stop(self, timeout: float = 30.0) -> bool:
        """통합 모니터링 시스템 중지"""
        try:
            with self._lock:
                if not self.is_running:
                    return True

                logger.info("통합 모니터링 시스템 중지")

                # 관리 스레드 중지
                self.is_running = False
                self._stop_event.set()

                if self.management_thread and self.management_thread.is_alive():
                    self.management_thread.join(timeout=timeout / 2)

                # 모든 모니터 중지
                self._stop_all_monitors()

                logger.info("통합 모니터링 시스템 중지 완료")
                return True

        except Exception as e:
            logger.error(f"통합 모니터링 시스템 중지 실패: {e}")
            return False

    def register_monitor(self, monitor: MonitoringBase) -> bool:
        """모니터링 모듈 등록"""
        try:
            with self._lock:
                if monitor.name in self.monitors:
                    logger.warning(f"모니터 '{monitor.name}'가 이미 등록되어 있습니다")
                    return False

                # 글로벌 레지스트리에 등록
                if not register_monitor(monitor):
                    logger.error(f"모니터 '{monitor.name}' 글로벌 등록 실패")
                    return False

                # 로컬 등록
                self.monitors[monitor.name] = monitor

                # 이벤트 리스너 추가
                monitor.add_listener(self._on_monitor_event)

                logger.info(f"모니터 '{monitor.name}' 등록됨")

                # 실행 중이면 즉시 시작
                if self.is_running:
                    monitor.start()

                self.stats["active_monitors"] = len(self.monitors)
                return True

        except Exception as e:
            logger.error(f"모니터 등록 실패: {e}")
            return False

    def unregister_monitor(self, name: str) -> bool:
        """모니터링 모듈 등록 해제"""
        try:
            with self._lock:
                if name not in self.monitors:
                    return False

                monitor = self.monitors[name]

                # 모니터 중지
                monitor.stop()

                # 리스너 제거
                monitor.remove_listener(self._on_monitor_event)

                # 등록 해제
                del self.monitors[name]
                unregister_monitor(name)

                logger.info(f"모니터 '{name}' 등록 해제됨")

                self.stats["active_monitors"] = len(self.monitors)
                return True

        except Exception as e:
            logger.error(f"모니터 등록 해제 실패: {e}")
            return False

    def get_status(self) -> Dict:
        """전체 시스템 상태 조회"""
        with self._lock:
            monitor_status = {}

            for name, monitor in self.monitors.items():
                monitor_status[name] = monitor.get_status()

            return {
                "manager": {
                    "is_running": self.is_running,
                    "stats": self.stats.copy(),
                    "monitor_count": len(self.monitors),
                },
                "monitors": monitor_status,
                "config": {
                    "file": self.config_manager.config_file,
                    "last_updated": getattr(self.config_manager.config, "_metadata", {}).get("last_updated", "unknown"),
                },
            }

    def get_integrated_data(self, hours: int = 1) -> Dict:
        """통합 모니터링 데이터 조회"""
        try:
            # 모든 모니터에서 데이터 수집
            monitor_data = {}

            for name, monitor in self.monitors.items():
                try:
                    recent_data = monitor.get_recent_data(minutes=hours * 60)
                    if recent_data:
                        monitor_data[name] = {
                            "data": recent_data[-1] if recent_data else {},
                            "history_count": len(recent_data),
                            "status": monitor.get_status(),
                        }
                except Exception as e:
                    logger.error(f"모니터 '{name}' 데이터 수집 실패: {e}")

            # 데이터 통합
            integrated = self.data_integrator.integrate_data(monitor_data)
            return integrated

        except Exception as e:
            logger.error(f"통합 데이터 조회 실패: {e}")
            return {}

    def get_events(self, hours: int = 1, event_type: str = None) -> List[Dict]:
        """이벤트 조회"""
        return self.event_aggregator.get_events(hours, event_type)

    def add_global_listener(self, callback: Callable):
        """글로벌 이벤트 리스너 추가"""
        if callback not in self.global_listeners:
            self.global_listeners.append(callback)

    def remove_global_listener(self, callback: Callable):
        """글로벌 이벤트 리스너 제거"""
        if callback in self.global_listeners:
            self.global_listeners.remove(callback)

    def _management_loop(self):
        """관리 루프"""
        logger.info("통합 모니터링 관리 루프 시작")

        integration_interval = 30  # 30초마다 데이터 통합

        while self.is_running and not self._stop_event.is_set():
            try:
                # 데이터 통합 수행
                integrated_data = self.get_integrated_data(hours=1)

                if integrated_data:
                    self.stats["last_integration"] = datetime.now().isoformat()

                    # 통합 이벤트 생성
                    integration_event = {
                        "type": "data_integration",
                        "source": "unified_manager",
                        "data": {
                            "sources": integrated_data.get("sources", []),
                            "insights_count": len(integrated_data.get("insights", [])),
                            "alerts_count": len(integrated_data.get("alerts", [])),
                            "correlations_count": len(integrated_data.get("correlations", {})),
                        },
                    }

                    self.event_aggregator.add_event(integration_event)

                    # 글로벌 리스너들에게 알림
                    self._notify_global_listeners("data_integrated", integrated_data)

                # 헬스체크 수행
                self._perform_health_check()

                # 다음 사이클까지 대기
                self._stop_event.wait(timeout=integration_interval)

            except Exception as e:
                logger.error(f"관리 루프 오류: {e}")
                self._stop_event.wait(timeout=integration_interval * 2)

        logger.info("통합 모니터링 관리 루프 종료")

    def _start_all_monitors(self):
        """모든 모니터 시작"""
        for name, monitor in self.monitors.items():
            try:
                if monitor.start():
                    logger.info(f"모니터 '{name}' 시작됨")
                else:
                    logger.warning(f"모니터 '{name}' 시작 실패")
            except Exception as e:
                logger.error(f"모니터 '{name}' 시작 오류: {e}")

    def _stop_all_monitors(self):
        """모든 모니터 중지"""
        for name, monitor in self.monitors.items():
            try:
                if monitor.stop():
                    logger.info(f"모니터 '{name}' 중지됨")
                else:
                    logger.warning(f"모니터 '{name}' 중지 실패")
            except Exception as e:
                logger.error(f"모니터 '{name}' 중지 오류: {e}")

    def _on_monitor_event(self, event_type: str, data: Dict):
        """모니터 이벤트 처리"""
        try:
            # 이벤트 집계기에 추가
            event = {
                "type": event_type,
                "source": data.get("source", "unknown"),
                "data": data.get("data", {}),
            }

            self.event_aggregator.add_event(event)
            self.stats["total_events"] += 1

            # 알림인 경우 카운트 증가
            if "alert" in event_type.lower() or "alarm" in event_type.lower():
                self.stats["total_alerts"] += 1

        except Exception as e:
            logger.error(f"모니터 이벤트 처리 실패: {e}")

    def _on_config_changed(self, event_type: str, data: Dict):
        """설정 변경 처리"""
        try:
            logger.info(f"설정 변경 감지: {event_type}")

            # 설정 변경 이벤트 생성
            config_event = {
                "type": "config_changed",
                "source": "config_manager",
                "data": {"event_type": event_type, "details": data},
            }

            self.event_aggregator.add_event(config_event)

            # 모니터들에게 설정 변경 알림 (필요한 경우)
            # 각 모니터가 설정 변경에 따라 재구성될 수 있도록 함

        except Exception as e:
            logger.error(f"설정 변경 처리 실패: {e}")

    def _perform_health_check(self):
        """시스템 헬스체크"""
        try:
            unhealthy_monitors = []

            for name, monitor in self.monitors.items():
                status = monitor.get_status()

                if not status.get("is_running", False):
                    unhealthy_monitors.append(name)
                elif status.get("error_count", 0) > 10:  # 오류가 너무 많은 경우
                    unhealthy_monitors.append(name)

            if unhealthy_monitors:
                health_event = {
                    "type": "health_check_warning",
                    "source": "unified_manager",
                    "data": {
                        "unhealthy_monitors": unhealthy_monitors,
                        "total_monitors": len(self.monitors),
                    },
                }

                self.event_aggregator.add_event(health_event)

        except Exception as e:
            logger.error(f"헬스체크 실패: {e}")

    def _notify_global_listeners(self, event_type: str, data: Dict):
        """글로벌 리스너들에게 알림"""
        for listener in self.global_listeners[:]:
            try:
                listener(event_type, data)
            except Exception as e:
                logger.error(f"글로벌 리스너 호출 실패: {e}")
                self.global_listeners.remove(listener)

    def export_all_data(self, filepath: str) -> bool:
        """모든 모니터링 데이터 내보내기"""
        try:
            export_data = {
                "export_time": datetime.now().isoformat(),
                "manager_status": self.get_status(),
                "integrated_data": self.get_integrated_data(hours=24),
                "events": self.get_events(hours=24),
                "monitor_data": {},
            }

            # 각 모니터의 데이터
            for name, monitor in self.monitors.items():
                try:
                    export_data["monitor_data"][name] = {
                        "status": monitor.get_status(),
                        "statistics": monitor.get_statistics(),
                        "recent_data": monitor.get_recent_data(minutes=1440),  # 24시간
                    }
                except Exception as e:
                    logger.error(f"모니터 '{name}' 데이터 내보내기 실패: {e}")

            # 파일에 저장
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            logger.info(f"전체 모니터링 데이터 내보내기 완료: {filepath}")
            return True

        except Exception as e:
            logger.error(f"전체 데이터 내보내기 실패: {e}")
            return False


# 전역 통합 모니터링 매니저
_global_manager = None
_manager_lock = RLock()


def get_unified_manager() -> UnifiedMonitoringManager:
    """전역 통합 모니터링 매니저 반환"""
    global _global_manager
    with _manager_lock:
        if _global_manager is None:
            _global_manager = UnifiedMonitoringManager()
        return _global_manager


def start_unified_monitoring() -> bool:
    """통합 모니터링 시스템 시작"""
    return get_unified_manager().start()


def stop_unified_monitoring() -> bool:
    """통합 모니터링 시스템 중지"""
    return get_unified_manager().stop()


if __name__ == "__main__":
    # 테스트 코드
    manager = UnifiedMonitoringManager()

    def test_global_listener(event_type, data):
        print(f"글로벌 이벤트: {event_type}")

    manager.add_global_listener(test_global_listener)
    manager.start()

    try:
        time.sleep(10)
        print("시스템 상태:", manager.get_status())
    except KeyboardInterrupt:
        pass

    manager.stop()
    print("테스트 완료")
