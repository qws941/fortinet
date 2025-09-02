#!/usr/bin/env python3

"""
Redis 캐싱 유틸리티 - 통합 캐시 매니저 래퍼
기존 코드와의 하위 호환성을 위한 Redis 캐시 래퍼
"""

import logging
from functools import wraps
from typing import Any, Callable, Optional

from utils.unified_cache_manager import get_cache_manager

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis 캐시 관리 클래스 - 통합 캐시 매니저 래퍼"""

    def __init__(self):
        self.cache_manager = get_cache_manager()
        self.enabled = len(self.cache_manager.backends) > 0

    def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 가져오기"""
        return self.cache_manager.get(key)

    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """캐시에 값 저장 (기본 TTL: 5분)"""
        return self.cache_manager.set(key, value, ttl)

    def delete(self, key: str) -> bool:
        """캐시에서 값 삭제"""
        return self.cache_manager.delete(key)

    def exists(self, key: str) -> bool:
        """키 존재 여부 확인"""
        return self.cache_manager.exists(key)

    def clear_pattern(self, pattern: str) -> int:
        """패턴에 맞는 모든 키 삭제 (통합 캐시 매니저에서는 전체 클리어)"""
        # 패턴 매칭은 복잡하므로 전체 클리어로 대체
        logger.warning(f"패턴 매칭 삭제는 지원되지 않음 ({pattern}). 전체 캐시를 클리어합니다.")
        self.cache_manager.clear()
        return 1  # 일관성을 위해 1 반환

    def get_stats(self) -> dict:
        """캐시 통계 정보"""
        stats = self.cache_manager.get_stats()

        # Redis 형식으로 변환
        return {
            "enabled": self.enabled,
            "connected": len(self.cache_manager.backends) > 0,
            "keyspace_hits": stats.get("hits", 0),
            "keyspace_misses": stats.get("misses", 0),
            "hit_rate": stats.get("hit_rate", 0),
            "backends": stats.get("backends", 0),
            "backend_types": stats.get("backend_types", []),
        }


# 전역 Redis 캐시 인스턴스 - 통합 캐시 매니저 사용
redis_cache = RedisCache()


def redis_cached(ttl: int = 300, key_prefix: str = ""):
    """Redis 캐싱 데코레이터 - 통합 캐시 매니저 사용

    Args:
        ttl: Time-To-Live (초 단위, 기본 5분)
        key_prefix: 캐시 키 접두사
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 캐시가 비활성화된 경우 원본 함수 실행
            if not redis_cache.enabled:
                return func(*args, **kwargs)

            # 캐시 키 생성 - 통합 캐시 매니저 사용
            cache_key = redis_cache.cache_manager.generate_cache_key(
                f"{key_prefix}:{func.__name__}", *args, **kwargs
            )

            # 캐시에서 조회
            cached_value = redis_cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"캐시 히트: {cache_key}")
                return cached_value

            # 캐시 미스 - 함수 실행
            logger.debug(f"캐시 미스: {cache_key}")
            result = func(*args, **kwargs)

            # 결과를 캐시에 저장
            redis_cache.set(cache_key, result, ttl)

            return result

        # 캐시 무효화 함수 추가
        def invalidate(*args, **kwargs):
            cache_key = redis_cache.cache_manager.generate_cache_key(
                f"{key_prefix}:{func.__name__}", *args, **kwargs
            )
            redis_cache.delete(cache_key)

        wrapper.invalidate = invalidate
        return wrapper

    return decorator


def invalidate_cache_pattern(pattern: str):
    """특정 패턴의 캐시 무효화 - 통합 캐시 매니저에서는 전체 클리어"""
    cleared = redis_cache.clear_pattern(pattern)
    logger.info(f"캐시 무효화: {pattern} (전체 캐시 클리어됨)")
    return cleared


def get_cache_stats():
    """캐시 통계 반환"""
    return redis_cache.get_stats()


# 캐시 키 생성 헬퍼 함수 - 통합 캐시 매니저 사용
def make_cache_key(*args, **kwargs) -> str:
    """일관된 캐시 키 생성 - 통합 캐시 매니저 사용"""
    return redis_cache.cache_manager.generate_cache_key("helper", *args, **kwargs)
