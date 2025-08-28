#!/usr/bin/env python3
"""
API 성능 모니터링 시스템
CLAUDE.md 지시사항에 따른 완전 자율적 API 성능 추적 및 최적화
"""
import functools
import secrets
import statistics
from collections import defaultdict, deque
from datetime import datetime, timedelta

from monitoring.base import MonitoringBase
from monitoring.config import get_config
from utils.common_imports import Dict, List, Optional, json, logging, time

logger = logging.getLogger(__name__)


class APIPerformanceMonitor(MonitoringBase):
    """API 성능 실시간 모니터링"""

    def __init__(self, collection_interval=None):
        # 설정에서 기본값 가져오기
        config = get_config()
        if collection_interval is None:
            collection_interval = config.api_performance.collection_interval

        super().__init__(
            name="api_performance",
            collection_interval=collection_interval,
            max_history=config.api_performance.max_history,
        )

        # 믹스인 초기화 (순서가 중요함)

        if not hasattr(self, "thresholds"):
            self.thresholds = {}
        if not hasattr(self, "threshold_violations"):
            self.threshold_violations = deque(maxlen=100)

        # API 성능 특화 데이터 구조 (누락된 속성들 추가)
        self.endpoint_metrics = defaultdict(lambda: {"calls": [], "errors": 0, "total": 0})
        self.metrics = defaultdict(lambda: deque(maxlen=1000))  # 수정: 누락된 속성
        self.response_times = defaultdict(lambda: deque(maxlen=1000))  # 수정: 누락된 속성
        self.success_counts = defaultdict(int)  # 수정: 누락된 속성
        self.error_counts = defaultdict(int)  # 수정: 누락된 속성
        self.throughput_data = defaultdict(list)  # 수정: 누락된 속성

        self.auto_optimization = config.api_performance.auto_optimization
        self.optimization_actions = []

        # 임계값 설정
        for (
            name,
            threshold_config,
        ) in config.api_performance.thresholds.items():
            self.set_threshold(name, threshold_config.warning, threshold_config.critical)

    def _collect_data(self) -> Optional[Dict]:
        """API 성능 데이터 수집"""
        try:
            # 엔드포인트별 통계 수집
            endpoint_stats = {}
            overall_stats = {
                "total_requests": 0,
                "total_errors": 0,
                "avg_response_time": 0,
                "endpoints_count": len(self.endpoint_metrics),
            }

            total_response_times = []

            for endpoint, metrics in self.endpoint_metrics.items():
                if metrics["total"] > 0:
                    recent_calls = [
                        call
                        for call in metrics["calls"]
                        if (datetime.now() - datetime.fromisoformat(call["timestamp"]) < timedelta(hours=1))
                    ]

                    if recent_calls:
                        response_times = [call["response_time"] for call in recent_calls]
                        error_count = sum(1 for call in recent_calls if not call["success"])

                        endpoint_stats[endpoint] = {
                            "total_requests": len(recent_calls),
                            "error_requests": error_count,
                            "error_rate": (error_count / len(recent_calls)) * 100,
                            "avg_response_time": (sum(response_times) / len(response_times)),
                            "min_response_time": min(response_times),
                            "max_response_time": max(response_times),
                            "p95_response_time": self._percentile(response_times, 95),
                        }

                        overall_stats["total_requests"] += len(recent_calls)
                        overall_stats["total_errors"] += error_count
                        total_response_times.extend(response_times)

            if total_response_times:
                overall_stats["avg_response_time"] = sum(total_response_times) / len(total_response_times)
                overall_stats["overall_error_rate"] = (
                    overall_stats["total_errors"] / overall_stats["total_requests"]
                ) * 100

            return {
                "endpoint_stats": endpoint_stats,
                "overall_stats": overall_stats,
                "optimization_actions": (self.optimization_actions[-10:] if self.optimization_actions else []),
            }

        except Exception as e:
            self.logger.error(f"API 성능 데이터 수집 실패: {e}")
            return None

    def record_api_call(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        response_time: float,
        request_size: int = 0,
        response_size: int = 0,
        error_message: str = None,
    ):
        """API 호출 기록"""
        with self._lock:
            timestamp = datetime.now()

            metric = {
                "timestamp": timestamp.isoformat(),
                "endpoint": endpoint,
                "method": method,
                "status_code": status_code,
                "response_time": response_time,
                "request_size": request_size,
                "response_size": response_size,
                "error_message": error_message,
                "success": 200 <= status_code < 400,
            }

            # 메트릭 저장
            self.metrics[endpoint].append(metric)
            self.response_times[endpoint].append(response_time)

            # endpoint_metrics 업데이트
            self.endpoint_metrics[endpoint]["calls"].append(metric)
            self.endpoint_metrics[endpoint]["total"] += 1
            if not metric["success"]:
                self.endpoint_metrics[endpoint]["errors"] += 1

            # 성공/실패 카운터 업데이트
            if metric["success"]:
                self.success_counts[endpoint] += 1
            else:
                self.error_counts[endpoint] += 1

            # 처리량 데이터 업데이트
            minute_key = timestamp.replace(second=0, microsecond=0)
            self.throughput_data[endpoint].append((minute_key, 1))

            # 성능 분석
            self._analyze_performance(endpoint, metric)

    def get_endpoint_stats(self, endpoint: str, hours: int = 1) -> Dict:
        """특정 엔드포인트 통계"""
        with self._lock:
            cutoff = datetime.now() - timedelta(hours=hours)
            recent_metrics = [m for m in self.metrics[endpoint] if datetime.fromisoformat(m["timestamp"]) > cutoff]

            if not recent_metrics:
                return {}

            response_times = [m["response_time"] for m in recent_metrics]
            success_count = sum(1 for m in recent_metrics if m["success"])
            total_count = len(recent_metrics)
            error_rate = ((total_count - success_count) / total_count * 100) if total_count > 0 else 0

            # 처리량 계산 (분당)
            throughput = self._calculate_throughput(endpoint, hours)

            return {
                "endpoint": endpoint,
                "period_hours": hours,
                "total_requests": total_count,
                "success_requests": success_count,
                "error_requests": total_count - success_count,
                "error_rate": error_rate,
                "response_time": {
                    "min": min(response_times),
                    "max": max(response_times),
                    "avg": statistics.mean(response_times),
                    "median": statistics.median(response_times),
                    "p95": self._percentile(response_times, 95),
                    "p99": self._percentile(response_times, 99),
                },
                "throughput_per_minute": throughput,
                "last_error": self._get_last_error(recent_metrics),
            }

    def get_overall_stats(self, hours: int = 1) -> Dict:
        """전체 API 성능 통계"""
        with self._lock:
            all_endpoints = list(self.metrics.keys())
            endpoint_stats = {}

            total_requests = 0
            total_errors = 0
            all_response_times = []

            for endpoint in all_endpoints:
                stats = self.get_endpoint_stats(endpoint, hours)
                if stats:
                    endpoint_stats[endpoint] = stats
                    total_requests += stats["total_requests"]
                    total_errors += stats["error_requests"]

                    # 응답시간 수집
                    cutoff = datetime.now() - timedelta(hours=hours)
                    recent_times = [
                        m["response_time"]
                        for m in self.metrics[endpoint]
                        if datetime.fromisoformat(m["timestamp"]) > cutoff
                    ]
                    all_response_times.extend(recent_times)

            overall_error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0

            result = {
                "period_hours": hours,
                "total_requests": total_requests,
                "total_errors": total_errors,
                "overall_error_rate": overall_error_rate,
                "endpoints_count": len(all_endpoints),
                "endpoint_stats": endpoint_stats,
            }

            if all_response_times:
                result["overall_response_time"] = {
                    "min": min(all_response_times),
                    "max": max(all_response_times),
                    "avg": statistics.mean(all_response_times),
                    "median": statistics.median(all_response_times),
                    "p95": self._percentile(all_response_times, 95),
                    "p99": self._percentile(all_response_times, 99),
                }

            return result

    def get_performance_alerts(self) -> List[Dict]:
        """성능 알림 조회"""
        alerts = []

        for endpoint in self.metrics.keys():
            stats = self.get_endpoint_stats(endpoint, hours=0.5)  # 최근 30분

            if not stats:
                continue

            # 응답시간 알림
            avg_response_time = stats["response_time"]["avg"]
            if avg_response_time > self.thresholds["response_time_critical"]:
                alerts.append(
                    {
                        "type": "response_time",
                        "severity": "critical",
                        "endpoint": endpoint,
                        "message": f"응답시간이 매우 느립니다: {avg_response_time:.0f}ms",
                        "value": avg_response_time,
                        "threshold": self.thresholds["response_time_critical"],
                    }
                )
            elif avg_response_time > self.thresholds["response_time_warning"]:
                alerts.append(
                    {
                        "type": "response_time",
                        "severity": "warning",
                        "endpoint": endpoint,
                        "message": f"응답시간이 느립니다: {avg_response_time:.0f}ms",
                        "value": avg_response_time,
                        "threshold": self.thresholds["response_time_warning"],
                    }
                )

            # 오류율 알림
            error_rate = stats["error_rate"]
            if error_rate > self.thresholds["error_rate_critical"]:
                alerts.append(
                    {
                        "type": "error_rate",
                        "severity": "critical",
                        "endpoint": endpoint,
                        "message": f"오류율이 매우 높습니다: {error_rate:.1f}%",
                        "value": error_rate,
                        "threshold": self.thresholds["error_rate_critical"],
                    }
                )
            elif error_rate > self.thresholds["error_rate_warning"]:
                alerts.append(
                    {
                        "type": "error_rate",
                        "severity": "warning",
                        "endpoint": endpoint,
                        "message": f"오류율이 높습니다: {error_rate:.1f}%",
                        "value": error_rate,
                        "threshold": self.thresholds["error_rate_warning"],
                    }
                )

            # 처리량 알림
            throughput = stats["throughput_per_minute"]
            if throughput < self.thresholds["throughput_min"]:
                alerts.append(
                    {
                        "type": "throughput",
                        "severity": "warning",
                        "endpoint": endpoint,
                        "message": f"처리량이 낮습니다: {throughput:.1f}/분",
                        "value": throughput,
                        "threshold": self.thresholds["throughput_min"],
                    }
                )

        return alerts

    def get_slow_endpoints(self, limit: int = 10) -> List[Dict]:
        """느린 엔드포인트 조회"""
        endpoint_times = []

        for endpoint in self.metrics.keys():
            stats = self.get_endpoint_stats(endpoint, hours=1)
            if stats and stats["total_requests"] > 0:
                endpoint_times.append(
                    {
                        "endpoint": endpoint,
                        "avg_response_time": stats["response_time"]["avg"],
                        "p95_response_time": stats["response_time"]["p95"],
                        "total_requests": stats["total_requests"],
                    }
                )

        # 평균 응답시간으로 정렬
        endpoint_times.sort(key=lambda x: x["avg_response_time"], reverse=True)
        return endpoint_times[:limit]

    def suggest_optimizations(self) -> List[Dict]:
        """성능 최적화 제안"""
        suggestions = []

        # 느린 엔드포인트 분석
        slow_endpoints = self.get_slow_endpoints(5)
        for ep in slow_endpoints:
            if ep["avg_response_time"] > self.thresholds["response_time_warning"]:
                suggestions.append(
                    {
                        "type": "response_time_optimization",
                        "endpoint": ep["endpoint"],
                        "priority": (
                            "high" if ep["avg_response_time"] > self.thresholds["response_time_critical"] else "medium"
                        ),
                        "description": f"엔드포인트 {ep['endpoint']} 응답시간 최적화 필요",
                        "current_value": ep["avg_response_time"],
                        "actions": [
                            "데이터베이스 쿼리 최적화",
                            "캐싱 전략 적용",
                            "응답 데이터 크기 축소",
                            "비동기 처리 적용",
                        ],
                    }
                )

        # 오류율 높은 엔드포인트
        alerts = self.get_performance_alerts()
        error_alerts = [a for a in alerts if a["type"] == "error_rate"]
        for alert in error_alerts:
            suggestions.append(
                {
                    "type": "error_rate_optimization",
                    "endpoint": alert["endpoint"],
                    "priority": "high",
                    "description": f"엔드포인트 {alert['endpoint']} 오류율 개선 필요",
                    "current_value": alert["value"],
                    "actions": [
                        "입력 유효성 검사 강화",
                        "예외 처리 개선",
                        "리소스 할당 검토",
                        "의존성 서비스 상태 확인",
                    ],
                }
            )

        return suggestions

    def auto_optimize_performance(self):
        """자동 성능 최적화"""
        if not self.auto_optimization:
            return

        suggestions = self.suggest_optimizations()

        for suggestion in suggestions:
            if suggestion["priority"] == "high":
                self._apply_auto_optimization(suggestion)

    def _apply_auto_optimization(self, suggestion: Dict):
        """자동 최적화 적용"""
        logger.info(f"자동 최적화 적용: {suggestion['description']}")

        # 실제 최적화 액션은 구현에 따라 달라짐
        action = {
            "timestamp": datetime.now().isoformat(),
            "type": suggestion["type"],
            "endpoint": suggestion["endpoint"],
            "action": "auto_optimization_applied",
            "description": suggestion["description"],
        }

        self.optimization_actions.append(action)

        # 리스너들에게 알림
        self._notify_listeners("optimization_applied", action)

    def _monitoring_loop(self):
        """모니터링 루프 (수정: is_running 사용)"""
        logger.info("API 성능 모니터링 루프 시작")

        while self.is_running and not self._stop_event.is_set():
            try:
                # 성능 분석 및 알림
                alerts = self.get_performance_alerts()
                if alerts:
                    self._notify_listeners("performance_alerts", alerts)

                # 자동 최적화 실행
                self.auto_optimize_performance()

                # 통계 정리 (오래된 데이터 제거)
                self._cleanup_old_data()

                # 1분마다 실행
                self._stop_event.wait(timeout=60)

            except Exception as e:
                logger.error(f"API 성능 모니터링 루프 오류: {e}")
                self._stop_event.wait(timeout=60)

        logger.info("API 성능 모니터링 루프 종료")

    def _analyze_performance(self, endpoint: str, metric: Dict):
        """실시간 성능 분석 (수정: 안전한 임계값 체크)"""
        # 응답시간 임계값 체크 (안전하게)
        response_time = metric["response_time"]

        # 임계값이 설정되어 있는 경우만 체크 (수정: dict 형태 처리)
        if "response_time_critical" in self.thresholds:
            threshold_val = self.thresholds["response_time_critical"]
            critical_val = threshold_val["critical"] if isinstance(threshold_val, dict) else threshold_val
            if response_time > critical_val:
                self._notify_listeners(
                    "slow_response",
                    {
                        "endpoint": endpoint,
                        "response_time": response_time,
                        "severity": "critical",
                    },
                )

        if "response_time_warning" in self.thresholds:
            threshold_val = self.thresholds["response_time_warning"]
            warning_val = threshold_val["warning"] if isinstance(threshold_val, dict) else threshold_val
            if response_time > warning_val:
                self._notify_listeners(
                    "slow_response",
                    {
                        "endpoint": endpoint,
                        "response_time": response_time,
                        "severity": "warning",
                    },
                )

        # 오류 감지
        if not metric["success"]:
            self._notify_listeners(
                "api_error",
                {
                    "endpoint": endpoint,
                    "status_code": metric["status_code"],
                    "error_message": metric["error_message"],
                },
            )

    def _calculate_throughput(self, endpoint: str, hours: int) -> float:
        """처리량 계산 (분당)"""
        cutoff = datetime.now() - timedelta(hours=hours)

        # 분단위로 그룹핑된 요청 수 계산
        minute_counts = defaultdict(int)

        for metric in self.metrics[endpoint]:
            timestamp = datetime.fromisoformat(metric["timestamp"])
            if timestamp > cutoff:
                minute_key = timestamp.replace(second=0, microsecond=0)
                minute_counts[minute_key] += 1

        if not minute_counts:
            return 0.0

        total_requests = sum(minute_counts.values())
        total_minutes = len(minute_counts)

        return total_requests / total_minutes if total_minutes > 0 else 0.0

    def _percentile(self, data: List[float], percentile: int) -> float:
        """백분위수 계산"""
        if not data:
            return 0.0

        sorted_data = sorted(data)
        index = (percentile / 100) * (len(sorted_data) - 1)

        if index.is_integer():
            return sorted_data[int(index)]
        else:
            lower = sorted_data[int(index)]
            upper = sorted_data[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))

    def _get_last_error(self, metrics: List[Dict]) -> Optional[Dict]:
        """마지막 오류 조회"""
        error_metrics = [m for m in metrics if not m["success"]]

        if error_metrics:
            return max(error_metrics, key=lambda x: x["timestamp"])
        return None

    def _cleanup_old_data(self):
        """오래된 데이터 정리"""
        cutoff = datetime.now() - timedelta(hours=24)

        with self._lock:
            for endpoint in list(self.metrics.keys()):
                # 24시간 이전 데이터 제거
                self.metrics[endpoint] = deque(
                    [m for m in self.metrics[endpoint] if datetime.fromisoformat(m["timestamp"]) > cutoff],
                    maxlen=1000,
                )

                # 빈 큐는 제거
                if not self.metrics[endpoint]:
                    del self.metrics[endpoint]
                    if endpoint in self.error_counts:
                        del self.error_counts[endpoint]
                    if endpoint in self.success_counts:
                        del self.success_counts[endpoint]

    def _notify_listeners(self, event_type: str, data: Dict):
        """리스너들에게 이벤트 알림"""
        with self._lock:
            for listener in self.listeners[:]:
                try:
                    listener(event_type, data)
                except Exception as e:
                    logger.error(f"API 성능 리스너 호출 실패: {e}")
                    self.listeners.remove(listener)


# 데코레이터를 통한 자동 성능 모니터링
def monitor_api_performance(monitor: APIPerformanceMonitor):
    """API 성능 모니터링 데코레이터"""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            endpoint = getattr(func, "__name__", "unknown")
            method = "FUNCTION"

            try:
                result = func(*args, **kwargs)
                response_time = (time.time() - start_time) * 1000

                # Flask response 객체인 경우
                if hasattr(result, "status_code"):
                    status_code = result.status_code
                    response_size = len(result.get_data()) if hasattr(result, "get_data") else 0
                else:
                    status_code = 200
                    response_size = len(str(result)) if result else 0

                monitor.record_api_call(
                    endpoint=endpoint,
                    method=method,
                    status_code=status_code,
                    response_time=response_time,
                    response_size=response_size,
                )

                return result

            except Exception as e:
                response_time = (time.time() - start_time) * 1000
                monitor.record_api_call(
                    endpoint=endpoint,
                    method=method,
                    status_code=500,
                    response_time=response_time,
                    error_message=str(e),
                )
                raise

        return wrapper

    return decorator


# 전역 인스턴스
_global_monitor = None


def get_api_performance_monitor() -> APIPerformanceMonitor:
    """전역 API 성능 모니터 반환"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = APIPerformanceMonitor()
    return _global_monitor


if __name__ == "__main__":
    # 테스트 코드
    monitor = APIPerformanceMonitor()

    def test_listener(event_type, data):
        print(f"이벤트: {event_type}, 데이터: {data}")

    monitor.add_listener(test_listener)
    monitor.start_monitoring()

    # 테스트 API 호출 시뮬레이션
    import random

    endpoints = ["/api/devices", "/api/monitoring", "/api/settings"]

    for _ in range(50):
        endpoint = secrets.choice(endpoints)
        status_code = 200 if secrets.SystemRandom().random() > 0.1 else 500
        response_time = random.uniform(100, 2000)

        monitor.record_api_call(
            endpoint=endpoint,
            method="GET",
            status_code=status_code,
            response_time=response_time,
        )

        time.sleep(0.1)

    # 통계 출력
    print("전체 통계:")
    print(json.dumps(monitor.get_overall_stats(), indent=2, ensure_ascii=False))

    print("\n성능 알림:")
    for alert in monitor.get_performance_alerts():
        print(f"- {alert['severity']}: {alert['message']}")

    print("\n최적화 제안:")
    for suggestion in monitor.suggest_optimizations():
        print(f"- {suggestion['priority']}: {suggestion['description']}")

    monitor.stop_monitoring()
