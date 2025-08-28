#!/usr/bin/env python3
"""
고급 에러 복구 전략 구현체들
ErrorRecoveryStrategy의 구체적 구현 클래스들
"""

import asyncio
import time
from typing import Any, Dict, List

from utils.unified_logger import get_logger

from .error_handler_advanced import ApplicationError, ErrorCategory, ErrorRecoveryStrategy, ErrorSeverity

logger = get_logger(__name__)


class NetworkRetryStrategy(ErrorRecoveryStrategy):
    """네트워크 에러 전용 재시도 전략"""

    def __init__(self, max_retries: int = 3, initial_delay: float = 1.0):
        super().__init__()
        self.max_retries = max_retries
        self.initial_delay = initial_delay

    def _can_handle_category(self, category: ErrorCategory) -> bool:
        return category == ErrorCategory.NETWORK

    def _execute_recovery(self, error: ApplicationError, context: Dict) -> Any:
        """네트워크 에러에 특화된 복구 실행"""
        operation = context.get("operation")
        if not operation:
            raise ValueError("Network recovery requires operation context")

        for attempt in range(self.max_retries):
            try:
                # 지수 백오프 지연
                if attempt > 0:
                    delay = self.initial_delay * (2 ** (attempt - 1))
                    logger.info(f"Network retry attempt {attempt + 1} after {delay}s")
                    time.sleep(delay)

                # 네트워크 연결성 검증
                if self._check_network_connectivity():
                    result = operation()
                    logger.info(f"Network recovery successful on attempt {attempt + 1}")
                    return result

            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise e
                logger.warning(f"Network attempt {attempt + 1} failed: {e}")

        raise error

    def _check_network_connectivity(self) -> bool:
        """기본 네트워크 연결성 확인"""
        import socket

        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return True
        except socket.error:
            return False


class DatabaseFallbackStrategy(ErrorRecoveryStrategy):
    """데이터베이스 에러 대응 캐시 폴백 전략"""

    def __init__(self, cache_ttl: int = 300):
        super().__init__()
        self.cache_ttl = cache_ttl
        self._cache = {}  # 간단한 메모리 캐시

    def _can_handle_category(self, category: ErrorCategory) -> bool:
        return category == ErrorCategory.DATABASE

    def _execute_recovery(self, error: ApplicationError, context: Dict) -> Any:
        """데이터베이스 에러에 대한 캐시 폴백"""
        cache_key = context.get("cache_key")
        fallback_data = context.get("fallback_data")

        # 1. 캐시에서 데이터 조회 시도
        if cache_key and cache_key in self._cache:
            cached_item = self._cache[cache_key]
            if time.time() - cached_item["timestamp"] < self.cache_ttl:
                logger.info(f"Using cached data for database error recovery: {cache_key}")
                return cached_item["data"]

        # 2. 폴백 데이터 사용
        if fallback_data:
            logger.info("Using fallback data for database error recovery")
            # 폴백 데이터를 캐시에 저장
            if cache_key:
                self._cache[cache_key] = {"data": fallback_data, "timestamp": time.time()}
            return fallback_data

        # 3. 기본 응답 반환
        logger.warning("No cache or fallback data available, returning default response")
        return {
            "status": "error",
            "message": "Database temporarily unavailable",
            "data": None,
            "recovery_method": "default_fallback",
        }


class AsyncQueueRecoveryStrategy(ErrorRecoveryStrategy):
    """비동기 큐 관련 에러 복구 전략"""

    def __init__(self):
        super().__init__()

    def _can_handle_category(self, category: ErrorCategory) -> bool:
        return category in [ErrorCategory.SYSTEM, ErrorCategory.EXTERNAL_SERVICE]

    def _additional_handle_check(self, error: ApplicationError) -> bool:
        """큐 관련 에러인지 확인"""
        queue_keywords = ["queue", "async", "worker", "task", "job"]
        error_msg = error.message.lower()
        return any(keyword in error_msg for keyword in queue_keywords)

    def _execute_recovery(self, error: ApplicationError, context: Dict) -> Any:
        """비동기 큐 에러 복구"""
        queue_name = context.get("queue_name", "default")
        operation = context.get("operation")

        if not operation:
            raise ValueError("Queue recovery requires operation context")

        try:
            # AsyncQueue 인스턴스 가져오기 또는 생성
            from ..utils.async_queue import create_queue, queue_manager

            # 큐 재시작 시도
            logger.info(f"Attempting to recover queue: {queue_name}")

            # 기존 큐 정리
            queue_manager.remove_queue(queue_name)

            # 새 큐 생성 (비동기 실행)
            if asyncio.get_event_loop().is_running():
                # 이미 실행 중인 이벤트 루프가 있는 경우
                queue = queue_manager.get_queue(queue_name, max_size=10000, worker_count=5)
                asyncio.create_task(queue.start())
            else:
                # 새 이벤트 루프 생성
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    queue = loop.run_until_complete(create_queue(queue_name, max_size=10000, worker_count=5))
                finally:
                    loop.close()

            logger.info(f"Queue {queue_name} recovered successfully")

            # 원본 작업 재시도
            return operation()

        except Exception as e:
            logger.error(f"Queue recovery failed: {e}")
            raise error


class ServiceMeshRecoveryStrategy(ErrorRecoveryStrategy):
    """마이크로서비스 환경에서의 서비스 메시 에러 복구"""

    def __init__(self, service_registry: Dict[str, List[str]] = None):
        super().__init__()
        self.service_registry = service_registry or {}

    def _can_handle_category(self, category: ErrorCategory) -> bool:
        return category == ErrorCategory.EXTERNAL_SERVICE

    def _execute_recovery(self, error: ApplicationError, context: Dict) -> Any:
        """서비스 메시 에러 복구 - 대체 인스턴스로 라우팅"""
        service_name = context.get("service_name")
        operation = context.get("operation")
        current_endpoint = context.get("current_endpoint")

        if not all([service_name, operation]):
            raise ValueError("Service mesh recovery requires service_name and operation")

        # 등록된 서비스 인스턴스들 확인
        available_instances = self.service_registry.get(service_name, [])

        if not available_instances:
            logger.warning(f"No alternative instances found for service: {service_name}")
            raise error

        # 현재 실패한 인스턴스 제외
        if current_endpoint:
            available_instances = [instance for instance in available_instances if instance != current_endpoint]

        if not available_instances:
            logger.warning(f"No healthy instances remaining for service: {service_name}")
            raise error

        # 사용 가능한 인스턴스들로 순차 재시도
        last_error = error

        for instance in available_instances:
            try:
                logger.info(f"Trying alternative instance: {instance}")

                # 컨텍스트 업데이트하여 새 인스턴스로 요청
                updated_context = context.copy()
                updated_context["target_endpoint"] = instance

                result = operation(updated_context)
                logger.info(f"Service mesh recovery successful using instance: {instance}")
                return result

            except Exception as e:
                last_error = e
                logger.warning(f"Alternative instance {instance} also failed: {e}")
                continue

        # 모든 인스턴스 실패
        logger.error(f"All instances failed for service {service_name}")
        raise last_error


class GracefulDegradationStrategy(ErrorRecoveryStrategy):
    """시스템 성능 저하 시 우아한 성능 축소 전략"""

    def __init__(self, degradation_levels: Dict[str, Dict] = None):
        super().__init__()
        self.degradation_levels = degradation_levels or {
            "level1": {"features": ["analytics", "recommendations"], "performance": 0.8},
            "level2": {"features": ["analytics", "recommendations", "real_time_updates"], "performance": 0.5},
            "level3": {"features": ["*"], "performance": 0.3},  # 최소 기능만
        }

    def _can_handle_category(self, category: ErrorCategory) -> bool:
        return category in [ErrorCategory.SYSTEM, ErrorCategory.EXTERNAL_SERVICE]

    def _can_handle_severity(self, severity: ErrorSeverity) -> bool:
        # 성능 저하는 주로 경고나 에러 수준에서 처리
        return severity in [ErrorSeverity.WARNING, ErrorSeverity.ERROR]

    def _execute_recovery(self, error: ApplicationError, context: Dict) -> Any:
        """우아한 성능 축소 실행"""
        current_load = context.get("system_load", 0.5)
        requested_features = context.get("requested_features", [])
        operation = context.get("operation")

        if not operation:
            raise ValueError("Graceful degradation requires operation context")

        # 시스템 부하에 따른 성능 축소 레벨 결정
        degradation_level = self._determine_degradation_level(current_load)

        logger.info(f"Applying graceful degradation: {degradation_level}")

        # 비활성화할 기능들 결정
        disabled_features = self.degradation_levels[degradation_level]["features"]
        performance_factor = self.degradation_levels[degradation_level]["performance"]

        # 컨텍스트 업데이트
        degraded_context = context.copy()
        degraded_context.update(
            {
                "degradation_level": degradation_level,
                "disabled_features": disabled_features,
                "performance_factor": performance_factor,
                "graceful_degradation": True,
            }
        )

        # 필수 기능만으로 작업 수행
        if disabled_features == ["*"]:
            # 최소 기능 모드
            logger.warning("Operating in minimal feature mode")
            return {
                "status": "degraded",
                "message": "Service operating with reduced functionality",
                "available_features": ["health_check", "basic_operations"],
                "performance_level": performance_factor,
            }
        else:
            # 부분 기능 비활성화 모드
            filtered_features = [feature for feature in requested_features if feature not in disabled_features]
            degraded_context["requested_features"] = filtered_features

            try:
                result = operation(degraded_context)

                # 결과에 성능 축소 정보 추가
                if isinstance(result, dict):
                    result["degradation_info"] = {
                        "level": degradation_level,
                        "disabled_features": disabled_features,
                        "performance_factor": performance_factor,
                    }

                logger.info(f"Operation completed with degraded performance: {degradation_level}")
                return result

            except Exception as e:
                # 성능 축소로도 실패한 경우 더 높은 축소 레벨 시도
                if degradation_level != "level3":
                    next_level = self._get_next_degradation_level(degradation_level)
                    logger.warning(f"Escalating degradation to {next_level}")

                    degraded_context["degradation_level"] = next_level
                    return self._execute_recovery(error, degraded_context)
                else:
                    raise e

    def _determine_degradation_level(self, system_load: float) -> str:
        """시스템 부하에 따른 성능 축소 레벨 결정"""
        if system_load < 0.6:
            return "level1"  # 경미한 축소
        elif system_load < 0.8:
            return "level2"  # 중간 축소
        else:
            return "level3"  # 최대 축소

    def _get_next_degradation_level(self, current_level: str) -> str:
        """다음 성능 축소 레벨 반환"""
        levels = ["level1", "level2", "level3"]
        current_index = levels.index(current_level)
        return levels[min(current_index + 1, len(levels) - 1)]


# 글로벌 복구 전략 팩토리
class RecoveryStrategyFactory:
    """복구 전략 팩토리 클래스"""

    @staticmethod
    def create_default_strategies() -> List[ErrorRecoveryStrategy]:
        """기본 복구 전략들 생성"""
        return [
            NetworkRetryStrategy(max_retries=3),
            DatabaseFallbackStrategy(cache_ttl=300),
            AsyncQueueRecoveryStrategy(),
            ServiceMeshRecoveryStrategy(),
            GracefulDegradationStrategy(),
        ]

    @staticmethod
    def create_strategy_by_name(name: str, **kwargs) -> ErrorRecoveryStrategy:
        """이름으로 특정 전략 생성"""
        strategies = {
            "network_retry": NetworkRetryStrategy,
            "database_fallback": DatabaseFallbackStrategy,
            "queue_recovery": AsyncQueueRecoveryStrategy,
            "service_mesh": ServiceMeshRecoveryStrategy,
            "graceful_degradation": GracefulDegradationStrategy,
        }

        strategy_class = strategies.get(name)
        if not strategy_class:
            raise ValueError(f"Unknown strategy: {name}")

        return strategy_class(**kwargs)
