#!/usr/bin/env python3
"""
성능 최적화 관련 API Routes
"""

import threading
import time
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, List

import psutil
from flask import Blueprint, g, request

from utils.api_utils import get_data_source
from utils.route_helpers import standard_api_response
from utils.security import rate_limit
from utils.unified_cache_manager import get_cache_manager
from utils.unified_logger import get_logger


# Performance optimization decorator
def optimized_response(cache_ttl=60, compress=True):
    """API 응답 최적화 데코레이터"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Track response time
            g.start_time = time.time()

            # Check cache first
            cache_key = f"{func.__name__}_{str(args)}_{str(kwargs)}"
            cache = get_cache_manager()
            cached = cache.get(cache_key)

            if cached:
                g.cache_hit = True
                return cached

            # Execute function
            result = func(*args, **kwargs)

            # Cache result
            cache.set(cache_key, result, ttl=cache_ttl)

            # Add performance metadata
            if isinstance(result, dict):
                result["_performance"] = {
                    "response_time": time.time() - g.start_time,
                    "cache_hit": getattr(g, "cache_hit", False),
                    "compressed": compress,
                }

            return result

        return wrapper

    return decorator


class APIOptimizer:
    """API 성능 최적화 관리자"""

    def __init__(self):
        self.metrics = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "avg_response_time": 0,
            "error_count": 0,
            "slow_requests": 0,
            "endpoints": {},
        }
        self.lock = threading.Lock()

    def record_request(self, endpoint: str, response_time: float, cache_hit: bool = False):
        """요청 메트릭 기록"""
        with self.lock:
            self.metrics["total_requests"] += 1

            if cache_hit:
                self.metrics["cache_hits"] += 1
            else:
                self.metrics["cache_misses"] += 1

            if response_time > 1.0:  # Slow request threshold
                self.metrics["slow_requests"] += 1

            # Update average response time
            prev_avg = self.metrics["avg_response_time"]
            self.metrics["avg_response_time"] = (
                prev_avg * (self.metrics["total_requests"] - 1) + response_time
            ) / self.metrics["total_requests"]

            # Update endpoint specific metrics
            if endpoint not in self.metrics["endpoints"]:
                self.metrics["endpoints"][endpoint] = {"count": 0, "avg_time": 0, "max_time": 0}

            ep_metrics = self.metrics["endpoints"][endpoint]
            ep_metrics["count"] += 1
            ep_metrics["avg_time"] = (ep_metrics["avg_time"] * (ep_metrics["count"] - 1) + response_time) / ep_metrics[
                "count"
            ]
            ep_metrics["max_time"] = max(ep_metrics["max_time"], response_time)

    def get_performance_metrics(self) -> Dict[str, Any]:
        """성능 메트릭 반환"""
        with self.lock:
            return {
                "total_requests": self.metrics["total_requests"],
                "cache_hit_rate": (self.metrics["cache_hits"] / max(1, self.metrics["total_requests"])) * 100,
                "avg_response_time_ms": self.metrics["avg_response_time"] * 1000,
                "slow_request_rate": (self.metrics["slow_requests"] / max(1, self.metrics["total_requests"])) * 100,
                "top_endpoints": sorted(self.metrics["endpoints"].items(), key=lambda x: x[1]["count"], reverse=True)[
                    :10
                ],
            }


# Global optimizer instance
_api_optimizer = APIOptimizer()


def get_api_optimizer():
    """API 최적화 관리자 반환"""
    return _api_optimizer


def get_performance_cache():
    """성능 캐시 반환"""
    return get_cache_manager()


class CacheWarmer:
    """캐시 예열 관리자"""

    def __init__(self, cache):
        self.cache = cache
        self.tasks = []
        self.results = {"success": [], "failed": []}

    def add_warming_task(self, namespace: str, key: str, data_func: Callable, ttl: int = 300):
        """캐시 예열 작업 추가"""
        self.tasks.append({"namespace": namespace, "key": key, "data_func": data_func, "ttl": ttl})

    def warm_cache(self) -> Dict[str, List]:
        """캐시 예열 실행"""
        for task in self.tasks:
            try:
                # Execute data function
                data = task["data_func"]()

                # Store in cache
                cache_key = f"{task['namespace']}:{task['key']}"
                self.cache.set(cache_key, data, ttl=task["ttl"])

                self.results["success"].append(cache_key)
                logger.info(f"Cache warmed: {cache_key}")

            except Exception as e:
                self.results["failed"].append({"key": f"{task['namespace']}:{task['key']}", "error": str(e)})
                logger.error(f"Cache warming failed for {task['namespace']}:{task['key']}: {e}")

        return self.results


class RealTimeMonitor:
    """실시간 모니터링 시스템"""

    def __init__(self):
        self.is_running = False
        self.collection_interval = 5  # seconds
        self.metrics_history = []
        self.max_history_size = 1000
        self.monitor_thread = None
        self.lock = threading.Lock()

    def collect_metrics(self):
        """시스템 메트릭 수집"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            network = psutil.net_io_counters()

            return {
                "timestamp": datetime.now().isoformat(),
                "cpu": {"percent": cpu_percent, "count": psutil.cpu_count()},
                "memory": {
                    "percent": memory.percent,
                    "used_gb": memory.used / (1024**3),
                    "available_gb": memory.available / (1024**3),
                },
                "disk": {
                    "percent": disk.percent,
                    "used_gb": disk.used / (1024**3),
                    "free_gb": disk.free / (1024**3),
                },
                "network": {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv,
                },
            }
        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")
            return {}

    def _monitor_loop(self):
        """모니터링 루프"""
        while self.is_running:
            metrics = self.collect_metrics()

            with self.lock:
                self.metrics_history.append(metrics)

                # Maintain history size
                if len(self.metrics_history) > self.max_history_size:
                    self.metrics_history = self.metrics_history[-self.max_history_size :]

            time.sleep(self.collection_interval)

    def start_monitoring(self):
        """모니터링 시작"""
        if not self.is_running:
            self.is_running = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            logger.info("Real-time monitoring started")

    def stop_monitoring(self):
        """모니터링 중지"""
        if self.is_running:
            self.is_running = False
            if self.monitor_thread:
                self.monitor_thread.join(timeout=10)
            logger.info("Real-time monitoring stopped")

    def get_current_metrics(self) -> Dict[str, Any]:
        """현재 메트릭 반환"""
        if self.metrics_history:
            with self.lock:
                return self.metrics_history[-1]
        return self.collect_metrics()

    def get_metric_history(self, metric_name: str, duration_minutes: int) -> List[Dict]:
        """메트릭 히스토리 반환"""
        cutoff_time = datetime.now() - timedelta(minutes=duration_minutes)

        with self.lock:
            filtered_history = []

            for metrics in self.metrics_history:
                try:
                    metric_time = datetime.fromisoformat(metrics["timestamp"])
                    if metric_time > cutoff_time:
                        # Extract specific metric
                        if "." in metric_name:
                            parts = metric_name.split(".")
                            value = metrics
                            for part in parts:
                                value = value.get(part, {})

                            filtered_history.append({"timestamp": metrics["timestamp"], "value": value})
                        else:
                            filtered_history.append(
                                {"timestamp": metrics["timestamp"], "value": metrics.get(metric_name)}
                            )
                except Exception:
                    continue

            return filtered_history

    def get_metrics(self):
        """메트릭 반환 (호환성)"""
        return self.get_current_metrics()

    def get_monitoring_status(self):
        """모니터링 상태 반환"""
        return {
            "is_running": self.is_running,
            "collection_interval": self.collection_interval,
            "history_size": len(self.metrics_history),
        }


# Global monitor instance
_real_time_monitor = RealTimeMonitor()


def get_real_time_monitor():
    """실시간 모니터 반환"""
    return _real_time_monitor


logger = get_logger(__name__)

performance_bp = Blueprint("performance", __name__, url_prefix="/api/performance")


@performance_bp.route("/metrics", methods=["GET"])
@optimized_response()
def get_performance_metrics():
    """성능 메트릭 조회"""
    try:
        # API 최적화 메트릭
        optimizer = get_api_optimizer()
        api_metrics = optimizer.get_performance_metrics()

        # 캐시 메트릭
        cache = get_performance_cache()
        cache_metrics = cache.get_stats()

        return {
            "api_optimization": api_metrics,
            "cache_performance": cache_metrics,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"성능 메트릭 조회 실패: {e}")
        return {
            "error": str(e),
            "api_optimization": {},
            "cache_performance": {},
            "timestamp": datetime.now().isoformat(),
        }


@performance_bp.route("/cache/clear", methods=["POST"])
@rate_limit(max_requests=5, window=60)
def clear_performance_cache():
    """성능 캐시 삭제"""
    try:
        data = request.get_json() or {}
        namespace = data.get("namespace", "all")

        cache = get_performance_cache()

        if namespace == "all":
            # 전체 캐시 삭제 (메모리만, Redis는 선택적으로)
            cache.memory_cache.clear()
            cleared_count = len(cache.memory_cache)
        else:
            # 특정 네임스페이스만 삭제
            cleared_count = cache.clear_namespace(namespace)

        # 통합 캐시 매니저도 삭제
        get_cache_manager().clear()

        return standard_api_response(
            success=True,
            message=f"Cache cleared successfully. {cleared_count} items removed.",
            data={
                "namespace": namespace,
                "cleared_items": cleared_count,
                "timestamp": datetime.now().isoformat(),
            },
        )

    except Exception as e:
        logger.error(f"캐시 삭제 실패: {e}")
        return standard_api_response(
            success=False,
            message=f"Cache clear failed: {str(e)}",
            status_code=500,
        )


@performance_bp.route("/cache/warmup", methods=["POST"])
@rate_limit(max_requests=3, window=300)  # 5분에 3번만 허용
def warmup_performance_cache():
    """성능 캐시 예열"""
    try:
        cache = get_performance_cache()
        warmer = CacheWarmer(cache)

        # 주요 데이터 예열 작업 정의
        def warm_devices():
            try:
                api_manager, dummy_generator, test_mode = get_data_source()
                if test_mode:
                    return dummy_generator.generate_devices(20)
                else:
                    # 실제 장치 데이터 수집 로직 (간단화)
                    return []
            except Exception:
                return []

        def warm_dashboard_stats():
            try:
                from api.integration.dashboard_collector import DashboardDataCollector

                api_manager, dummy_generator, test_mode = get_data_source()
                if test_mode:
                    return dummy_generator.generate_dashboard_stats()
                else:
                    collector = DashboardDataCollector(api_manager)
                    return collector.get_dashboard_stats()
            except Exception:
                return {}

        def warm_monitoring_data():
            try:
                api_manager, dummy_generator, test_mode = get_data_source()
                if test_mode:
                    return {
                        "cpu_usage": dummy_generator.generate_cpu_usage(),
                        "memory_usage": dummy_generator.generate_memory_usage(),
                    }
                else:
                    return {}
            except Exception:
                return {}

        # 예열 작업 추가
        warmer.add_warming_task("devices", "list", warm_devices, ttl=300)
        warmer.add_warming_task("dashboard", "stats", warm_dashboard_stats, ttl=180)
        warmer.add_warming_task("monitoring", "data", warm_monitoring_data, ttl=120)

        # 예열 실행
        results = warmer.warm_cache()

        return standard_api_response(
            success=True,
            message="Cache warming completed",
            data={
                "warmed_items": results["success"],
                "failed_items": results["failed"],
                "timestamp": datetime.now().isoformat(),
            },
        )

    except Exception as e:
        logger.error(f"캐시 예열 실패: {e}")
        return standard_api_response(
            success=False,
            message=f"Cache warming failed: {str(e)}",
            status_code=500,
        )


@performance_bp.route("/cache/stats", methods=["GET"])
@optimized_response()
def get_cache_stats():
    """캐시 통계 조회"""
    try:
        cache = get_performance_cache()
        stats = cache.get_stats()

        # 만료된 캐시 정리
        expired_count = cache.cleanup_expired()

        stats["expired_cleaned"] = expired_count
        stats["timestamp"] = datetime.now().isoformat()

        return stats

    except Exception as e:
        logger.error(f"캐시 통계 조회 실패: {e}")
        return {"error": str(e), "timestamp": datetime.now().isoformat()}


@performance_bp.route("/response-time/test", methods=["GET"])
@optimized_response()
def test_response_time():
    """API 응답 시간 테스트"""
    import time

    start_time = time.time()

    # 시뮬레이션 작업
    test_data = {
        "message": "Response time test completed",
        "data_size": "medium",
        "test_items": [f"item_{i}" for i in range(100)],  # 100개 항목
        "nested_data": {"level1": {"level2": {"level3": list(range(50))}}},
    }

    processing_time = time.time() - start_time

    return {
        "test_result": test_data,
        "processing_time_seconds": round(processing_time, 4),
        "timestamp": datetime.now().isoformat(),
    }


@performance_bp.route("/compression/test", methods=["GET"])
@optimized_response()
def test_compression():
    """데이터 압축 효과 테스트"""

    # 큰 데이터 생성 (압축 효과 확인용)
    large_data = {
        "description": "This is a compression test with repeated data " * 100,
        "repeated_array": ["same_value"] * 1000,
        "numbers": list(range(1000)),
        "text_data": "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 200,
        "nested_structures": [
            {
                "id": i,
                "name": f"Item {i}",
                "description": "A very long description that repeats many times " * 10,
                "tags": ["tag1", "tag2", "tag3"] * 5,
            }
            for i in range(100)
        ],
    }

    return {
        "message": "Compression test data",
        "data": large_data,
        "total_items": len(large_data["nested_structures"]),
        "estimated_size_kb": len(str(large_data)) / 1024,
        "timestamp": datetime.now().isoformat(),
    }


@performance_bp.route("/monitoring/realtime", methods=["GET"])
@optimized_response()
def get_realtime_monitoring():
    """실시간 모니터링 데이터 조회"""
    try:
        monitor = get_real_time_monitor()

        # 현재 메트릭 조회
        current_metrics = monitor.get_current_metrics()

        return {
            "status": "success",
            "is_monitoring_active": monitor.is_running,
            "current_metrics": current_metrics,
            "collection_interval": monitor.collection_interval,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"실시간 모니터링 데이터 조회 실패: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@performance_bp.route("/monitoring/start", methods=["POST"])
@rate_limit(max_requests=5, window=60)
def start_realtime_monitoring():
    """실시간 모니터링 시작"""
    try:
        monitor = get_real_time_monitor()
        monitor.start_monitoring()

        return standard_api_response(
            success=True,
            message="Real-time monitoring started successfully",
            data={
                "is_monitoring_active": monitor.is_running,
                "collection_interval": monitor.collection_interval,
                "timestamp": datetime.now().isoformat(),
            },
        )

    except Exception as e:
        logger.error(f"실시간 모니터링 시작 실패: {e}")
        return standard_api_response(
            success=False,
            message=f"Failed to start real-time monitoring: {str(e)}",
            status_code=500,
        )


@performance_bp.route("/monitoring/stop", methods=["POST"])
@rate_limit(max_requests=5, window=60)
def stop_realtime_monitoring():
    """실시간 모니터링 중지"""
    try:
        monitor = get_real_time_monitor()
        monitor.stop_monitoring()

        return standard_api_response(
            success=True,
            message="Real-time monitoring stopped successfully",
            data={
                "is_monitoring_active": monitor.is_running,
                "timestamp": datetime.now().isoformat(),
            },
        )

    except Exception as e:
        logger.error(f"실시간 모니터링 중지 실패: {e}")
        return standard_api_response(
            success=False,
            message=f"Failed to stop real-time monitoring: {str(e)}",
            status_code=500,
        )


@performance_bp.route("/monitoring/history/<metric_name>", methods=["GET"])
@optimized_response()
def get_metric_history(metric_name):
    """메트릭 히스토리 조회"""
    try:
        duration_minutes = request.args.get("duration", 60, type=int)
        duration_minutes = min(duration_minutes, 1440)  # 최대 24시간

        monitor = get_real_time_monitor()
        history = monitor.get_metric_history(metric_name, duration_minutes)

        return {
            "status": "success",
            "metric_name": metric_name,
            "duration_minutes": duration_minutes,
            "data_points": len(history),
            "history": history,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"메트릭 히스토리 조회 실패: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@performance_bp.route("/monitoring/alerts/recent", methods=["GET"])
@optimized_response()
def get_recent_alerts():
    """최근 알림 조회"""
    try:
        limit = request.args.get("limit", 50, type=int)
        limit = min(limit, 200)  # 최대 200개

        get_performance_cache()

        # 캐시에서 최근 알림들 조회 (간단한 구현)
        alerts = []

        # 실제 구현에서는 Redis나 데이터베이스에서 알림 목록을 조회
        # 여기서는 시뮬레이션 데이터 반환

        return {
            "status": "success",
            "total_alerts": len(alerts),
            "alerts": alerts,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"최근 알림 조회 실패: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }
