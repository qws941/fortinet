#!/usr/bin/env python3
"""
성능 최적화 유틸리티
메모리 사용량, 처리 속도, 캐시 효율성 개선을 위한 도구들
"""

import asyncio
import functools
import gc
import logging
import threading
import time
import weakref
from collections import OrderedDict, defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """성능 메트릭 데이터 구조"""

    function_name: str
    execution_time: float
    memory_usage: int
    call_count: int
    avg_time: float
    max_time: float
    min_time: float
    timestamp: datetime


class LRUCache:
    """메모리 효율적인 LRU 캐시 구현"""

    def __init__(self, maxsize: int = 128):
        self.maxsize = maxsize
        self.cache = OrderedDict()
        self._lock = threading.RLock()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 가져오기"""
        with self._lock:
            if key in self.cache:
                # 최근 사용된 항목을 맨 뒤로 이동
                value = self.cache.pop(key)
                self.cache[key] = value
                self.hits += 1
                return value
            else:
                self.misses += 1
                return None

    def set(self, key: str, value: Any):
        """캐시에 값 저장"""
        with self._lock:
            if key in self.cache:
                # 기존 키 업데이트
                self.cache.pop(key)
            elif len(self.cache) >= self.maxsize:
                # 가장 오래된 항목 제거
                self.cache.popitem(last=False)

            self.cache[key] = value

    def delete(self, key: str):
        """캐시에서 값 삭제"""
        with self._lock:
            self.cache.pop(key, None)

    def clear(self):
        """캐시 전체 삭제"""
        with self._lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0

    def get_stats(self) -> Dict[str, Any]:
        """캐시 통계 반환"""
        with self._lock:
            total_requests = self.hits + self.misses
            hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

            return {
                "size": len(self.cache),
                "maxsize": self.maxsize,
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": hit_rate,
            }


class PerformanceMonitor:
    """성능 모니터링 및 프로파일링"""

    def __init__(self):
        self.metrics = defaultdict(list)
        self.active_calls = {}
        self._lock = threading.RLock()

    def profile_function(self, func: Callable) -> Callable:
        """함수 성능 프로파일링 데코레이터"""

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            start_memory = self._get_memory_usage()

            try:
                result = func(*args, **kwargs)
                success = True
            except Exception as e:
                result = e
                success = False

            end_time = time.time()
            end_memory = self._get_memory_usage()

            execution_time = end_time - start_time
            memory_delta = end_memory - start_memory

            self._record_metrics(func.__name__, execution_time, memory_delta, success)

            if not success:
                raise result

            return result

        return wrapper

    def _get_memory_usage(self) -> int:
        """현재 메모리 사용량 반환 (KB)"""
        try:
            import os

            import psutil

            process = psutil.Process(os.getpid())
            return process.memory_info().rss // 1024
        except ImportError:
            # psutil이 없는 경우 간단한 추정
            return len(gc.get_objects())

    def _record_metrics(
        self,
        func_name: str,
        exec_time: float,
        memory_delta: int,
        success: bool,
    ):
        """메트릭 기록"""
        with self._lock:
            metrics_list = self.metrics[func_name]

            # 기존 메트릭 업데이트
            if metrics_list:
                last_metric = metrics_list[-1]
                call_count = last_metric.call_count + 1
                avg_time = (last_metric.avg_time * last_metric.call_count + exec_time) / call_count
                max_time = max(last_metric.max_time, exec_time)
                min_time = min(last_metric.min_time, exec_time)
            else:
                call_count = 1
                avg_time = max_time = min_time = exec_time

            metric = PerformanceMetrics(
                function_name=func_name,
                execution_time=exec_time,
                memory_usage=memory_delta,
                call_count=call_count,
                avg_time=avg_time,
                max_time=max_time,
                min_time=min_time,
                timestamp=datetime.now(),
            )

            metrics_list.append(metric)

            # 메트릭 히스토리 제한 (메모리 절약)
            if len(metrics_list) > 1000:
                metrics_list[:500] = []  # 오래된 절반 삭제

    def get_performance_report(self) -> Dict[str, Any]:
        """성능 보고서 생성"""
        with self._lock:
            report = {}

            for func_name, metrics_list in self.metrics.items():
                if not metrics_list:
                    continue

                latest = metrics_list[-1]
                report[func_name] = {
                    "total_calls": latest.call_count,
                    "avg_execution_time": latest.avg_time,
                    "max_execution_time": latest.max_time,
                    "min_execution_time": latest.min_time,
                    "last_execution_time": latest.execution_time,
                    "avg_memory_delta": sum(m.memory_usage for m in metrics_list) / len(metrics_list),
                    "last_updated": latest.timestamp.isoformat(),
                }

            return report

    def get_slow_functions(self, threshold: float = 1.0) -> List[Dict[str, Any]]:
        """느린 함수들 식별"""
        slow_functions = []

        with self._lock:
            for func_name, metrics_list in self.metrics.items():
                if not metrics_list:
                    continue

                latest = metrics_list[-1]
                if latest.avg_time > threshold:
                    slow_functions.append(
                        {
                            "function": func_name,
                            "avg_time": latest.avg_time,
                            "max_time": latest.max_time,
                            "call_count": latest.call_count,
                        }
                    )

        return sorted(slow_functions, key=lambda x: x["avg_time"], reverse=True)


class AsyncBatchProcessor:
    """비동기 배치 처리기 - 성능 최적화됨"""

    def __init__(self, batch_size: int = 100, max_concurrent: int = 10):
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def process_items(
        self,
        items: List[Any],
        processor: Callable,
        progress_callback: Optional[Callable] = None,
    ) -> List[Any]:
        """아이템들을 배치로 비동기 처리"""
        results = []
        total_items = len(items)
        processed_count = 0

        # 배치로 나누기
        batches = [items[i : i + self.batch_size] for i in range(0, len(items), self.batch_size)]

        for batch in batches:
            # 세마포어로 동시 실행 제한
            async with self.semaphore:
                batch_results = await asyncio.gather(
                    *[self._process_single_item(item, processor) for item in batch],
                    return_exceptions=True,
                )

                results.extend(batch_results)
                processed_count += len(batch)

                if progress_callback:
                    progress_callback(processed_count, total_items)

        return results

    async def _process_single_item(self, item: Any, processor: Callable) -> Any:
        """단일 아이템 처리"""
        try:
            if asyncio.iscoroutinefunction(processor):
                return await processor(item)
            else:
                # 동기 함수를 비동기로 실행
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, processor, item)
        except Exception as e:
            logger.error(f"Error processing item: {e}")
            return None


class MemoryOptimizer:
    """메모리 사용량 최적화"""

    @staticmethod
    def cleanup_cache_periodically(cache_manager, interval: int = 3600):
        """주기적 캐시 정리"""

        def cleanup():
            while True:
                time.sleep(interval)
                try:
                    # 만료된 캐시 정리
                    if hasattr(cache_manager, "cleanup_expired"):
                        cache_manager.cleanup_expired()

                    # 가비지 컬렉션 실행
                    collected = gc.collect()
                    logger.debug(f"Garbage collection cleaned up {collected} objects")

                except Exception as e:
                    logger.error(f"Error during cache cleanup: {e}")

        cleanup_thread = threading.Thread(target=cleanup, daemon=True)
        cleanup_thread.start()

    @staticmethod
    def optimize_data_structures(data: Dict[str, Any]) -> Dict[str, Any]:
        """데이터 구조 최적화"""
        optimized = {}

        for key, value in data.items():
            if isinstance(value, list) and len(value) > 1000:
                # 큰 리스트는 제너레이터로 변환 고려
                optimized[key] = value[:100]  # 샘플만 유지
                logger.debug(f"Truncated large list {key} from {len(value)} to 100 items")
            elif isinstance(value, dict) and len(value) > 100:
                # 큰 딕셔너리는 중요한 키만 유지
                important_keys = list(value.keys())[:50]
                optimized[key] = {k: value[k] for k in important_keys if k in value}
                logger.debug(f"Reduced large dict {key} from {len(value)} to {len(optimized[key])} items")
            else:
                optimized[key] = value

        return optimized

    @staticmethod
    def use_weak_references(obj_dict: Dict[str, Any]) -> Dict[str, Any]:
        """약한 참조 사용으로 메모리 누수 방지"""
        weak_dict = {}

        for key, value in obj_dict.items():
            try:
                weak_dict[key] = weakref.ref(value)
            except TypeError:
                # 약한 참조를 지원하지 않는 객체는 그대로 유지
                weak_dict[key] = value

        return weak_dict


# 전역 성능 모니터 인스턴스
performance_monitor = PerformanceMonitor()


# 편의 데코레이터들
def profile(func: Callable) -> Callable:
    """성능 프로파일링 데코레이터"""
    return performance_monitor.profile_function(func)


def lru_cache(maxsize: int = 128):
    """LRU 캐시 데코레이터"""

    def decorator(func: Callable) -> Callable:
        cache = LRUCache(maxsize)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 캐시 키 생성
            key = f"{func.__name__}_{hash((args, tuple(kwargs.items())))}"

            # 캐시 확인
            result = cache.get(key)
            if result is not None:
                return result

            # 함수 실행 및 캐시 저장
            result = func(*args, **kwargs)
            cache.set(key, result)

            return result

        # 캐시 통계 접근을 위한 속성 추가
        wrapper.cache = cache
        wrapper.cache_info = cache.get_stats

        return wrapper

    return decorator


def measure_time(func: Callable) -> Callable:
    """실행 시간 측정 데코레이터"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()

        execution_time = end_time - start_time
        logger.debug(f"{func.__name__} executed in {execution_time:.4f} seconds")

        return result

    return wrapper


# 성능 최적화 유틸리티 함수들
def optimize_json_operations():
    """JSON 연산 최적화"""
    try:
        import ujson as json

        logger.info("Using ujson for better JSON performance")
        return json
    except ImportError:
        import json

        logger.info("Using standard json module")
        return json


def optimize_regex_compilation():
    """정규표현식 컴파일 최적화"""
    import re

    # 자주 사용되는 패턴들을 미리 컴파일
    compiled_patterns = {
        "ip_address": re.compile(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"),
        "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
        "url": re.compile(r"https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?"),
        "uuid": re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"),
    }

    return compiled_patterns


# 전역 최적화된 객체들
optimized_json = optimize_json_operations()
compiled_regex_patterns = optimize_regex_compilation()
