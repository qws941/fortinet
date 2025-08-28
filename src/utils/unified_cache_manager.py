#!/usr/bin/env python3

"""
통합 캐시 매니저
Redis와 메모리 캐시를 통합한 일관된 캐싱 전략
"""

import hashlib
import json
import os
import threading
import time
from collections import OrderedDict
from functools import wraps
from typing import Any, Callable, Dict, Optional

import orjson

from utils.unified_logger import get_logger

logger = get_logger(__name__)


class CacheBackend:
    """캐시 백엔드 인터페이스"""

    def get(self, key: str) -> Optional[Any]:
        """
        캐시에서 값 조회

        Args:
            key: 캐시 키

        Returns:
            캐시된 값 또는 None
        """
        raise NotImplementedError("Subclasses must implement get method")

    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """
        캐시에 값 저장

        Args:
            key: 캐시 키
            value: 저장할 값
            ttl: TTL(초), 0이면 무제한

        Returns:
            성공 여부
        """
        raise NotImplementedError("Subclasses must implement set method")

    def delete(self, key: str) -> bool:
        """
        캐시에서 값 삭제

        Args:
            key: 삭제할 캐시 키

        Returns:
            삭제 성공 여부
        """
        raise NotImplementedError("Subclasses must implement delete method")

    def clear(self) -> bool:
        """
        캐시 전체 삭제

        Returns:
            삭제 성공 여부
        """
        raise NotImplementedError("Subclasses must implement clear method")

    def exists(self, key: str) -> bool:
        """
        키 존재 여부 확인

        Args:
            key: 확인할 캐시 키

        Returns:
            존재 여부
        """
        raise NotImplementedError("Subclasses must implement exists method")


class MemoryCacheBackend(CacheBackend):
    """메모리 기반 캐시 백엔드"""

    def __init__(self, max_size: int = 1000):
        self.cache = OrderedDict()
        self.max_size = max_size
        self.lock = threading.Lock()
        self.expiry = {}

    def get(self, key: str) -> Optional[Any]:
        with self.lock:
            if key not in self.cache:
                return None

            # TTL 확인
            if key in self.expiry and time.time() > self.expiry[key]:
                del self.cache[key]
                del self.expiry[key]
                return None

            # LRU 업데이트
            self.cache.move_to_end(key)
            return self.cache[key]

    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        with self.lock:
            # LRU 캐시 크기 관리
            if len(self.cache) >= self.max_size and key not in self.cache:
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                if oldest_key in self.expiry:
                    del self.expiry[oldest_key]

            self.cache[key] = value
            if ttl > 0:
                self.expiry[key] = time.time() + ttl
            elif key in self.expiry:
                del self.expiry[key]

            return True

    def delete(self, key: str) -> bool:
        with self.lock:
            if key in self.cache:
                del self.cache[key]
            if key in self.expiry:
                del self.expiry[key]
            return True

    def clear(self) -> bool:
        with self.lock:
            self.cache.clear()
            self.expiry.clear()
            return True

    def exists(self, key: str) -> bool:
        with self.lock:
            if key not in self.cache:
                return False

            # TTL 확인
            if key in self.expiry and time.time() > self.expiry[key]:
                del self.cache[key]
                del self.expiry[key]
                return False

            return True


class RedisCacheBackend(CacheBackend):
    """Redis 기반 캐시 백엔드"""

    def __init__(self, host="localhost", port=6379, db=0, password=None):
        self.redis_client = None
        self.connected = False

        try:
            import redis

            self.redis_client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=False,  # pickle 사용을 위해 False
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            # 연결 테스트
            self.redis_client.ping()
            self.connected = True
            logger.info(f"Redis 연결 성공: {host}:{port}")

        except ImportError:
            logger.warning("Redis 모듈이 설치되지 않음")
        except Exception as e:
            logger.warning(f"Redis 연결 실패: {e}")
            self.redis_client = None

    def get(self, key: str) -> Optional[Any]:
        if not self.connected or not self.redis_client:
            return None

        try:
            data = self.redis_client.get(key)
            if data is None:
                return None
            return json.loads(data.decode() if isinstance(data, bytes) else data)
        except Exception as e:
            logger.error(f"Redis GET 오류: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        if not self.connected or not self.redis_client:
            return False

        try:
            data = orjson.dumps(value)
            if ttl > 0:
                return self.redis_client.setex(key, ttl, data)
            else:
                return self.redis_client.set(key, data)
        except Exception as e:
            logger.error(f"Redis SET 오류: {e}")
            return False

    def delete(self, key: str) -> bool:
        if not self.connected or not self.redis_client:
            return False

        try:
            return self.redis_client.delete(key) > 0
        except Exception as e:
            logger.error(f"Redis DELETE 오류: {e}")
            return False

    def clear(self) -> bool:
        if not self.connected or not self.redis_client:
            return False

        try:
            return self.redis_client.flushdb()
        except Exception as e:
            logger.error(f"Redis CLEAR 오류: {e}")
            return False

    def exists(self, key: str) -> bool:
        if not self.connected or not self.redis_client:
            return False

        try:
            return self.redis_client.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis EXISTS 오류: {e}")
            return False


class UnifiedCacheManager:
    """통합 캐시 매니저"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or self._load_config()
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "evictions": 0,
        }

        # 백엔드 초기화
        self.backends = []
        self.memory_cache = None
        self.redis_cache = None
        self._init_backends()

        logger.info(f"캐시 매니저 초기화 완료: {len(self.backends)}개 백엔드")

    def _load_config(self) -> Dict:
        """설정 로드"""
        # 환경 변수 기반 기본 설정
        config = {
            "redis": {
                "enabled": os.getenv("REDIS_ENABLED", "true").lower() == "true",
                "host": os.getenv("REDIS_HOST", "redis"),
                "port": int(os.getenv("REDIS_PORT", "6379")),
                "db": int(os.getenv("REDIS_DB", "0")),
                "password": os.getenv("REDIS_PASSWORD"),
            },
            "memory": {
                "enabled": True,
                "max_size": int(os.getenv("MEMORY_CACHE_SIZE", "1000")),
            },
            "default_ttl": int(os.getenv("CACHE_TTL", "300")),
        }

        # 설정 파일에서 로드 (있는 경우)
        config_file = os.path.join("data", "cache_config.json")
        if os.path.exists(config_file):
            try:
                with open(config_file, "r") as f:
                    file_config = json.load(f)
                    config.update(file_config)
            except Exception as e:
                logger.warning(f"캐시 설정 파일 로드 실패: {e}")

        return config

    def _init_backends(self):
        """백엔드 초기화"""
        # Redis 백엔드
        if self.config["redis"]["enabled"]:
            redis_backend = RedisCacheBackend(
                host=self.config["redis"]["host"],
                port=self.config["redis"]["port"],
                db=self.config["redis"]["db"],
                password=self.config["redis"]["password"],
            )
            if redis_backend.connected:
                self.backends.append(redis_backend)
                self.redis_cache = redis_backend

        # 메모리 백엔드 (항상 마지막에 추가 - fallback)
        if self.config["memory"]["enabled"]:
            memory_backend = MemoryCacheBackend(max_size=self.config["memory"]["max_size"])
            self.backends.append(memory_backend)
            self.memory_cache = memory_backend

        if not self.backends:
            logger.warning("사용 가능한 캐시 백엔드가 없음")

    def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 조회 (첫 번째로 찾은 값 반환)"""
        for i, backend in enumerate(self.backends):
            try:
                value = backend.get(key)
                if value is not None:
                    self.stats["hits"] += 1

                    # 상위 레벨 캐시에 복사 (cache promotion)
                    for j in range(i):
                        try:
                            self.backends[j].set(key, value, self.config["default_ttl"])
                        except Exception as e:
                            logger.debug(f"캐시 프로모션 실패: {e}")

                    return value
            except Exception as e:
                logger.debug(f"캐시 조회 오류 ({backend.__class__.__name__}): {e}")

        self.stats["misses"] += 1
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """모든 백엔드에 값 저장"""
        if ttl is None:
            ttl = self.config["default_ttl"]

        success = False
        for backend in self.backends:
            try:
                if backend.set(key, value, ttl):
                    success = True
            except Exception as e:
                logger.debug(f"캐시 저장 오류 ({backend.__class__.__name__}): {e}")

        if success:
            self.stats["sets"] += 1

        return success

    def delete(self, key: str) -> bool:
        """모든 백엔드에서 값 삭제"""
        success = False
        for backend in self.backends:
            try:
                if backend.delete(key):
                    success = True
            except Exception as e:
                logger.debug(f"캐시 삭제 오류 ({backend.__class__.__name__}): {e}")

        if success:
            self.stats["deletes"] += 1

        return success

    def clear(self) -> bool:
        """모든 백엔드 캐시 클리어"""
        success = False
        for backend in self.backends:
            try:
                if backend.clear():
                    success = True
            except Exception as e:
                logger.debug(f"캐시 클리어 오류 ({backend.__class__.__name__}): {e}")

        return success

    def exists(self, key: str) -> bool:
        """키 존재 여부 확인"""
        for backend in self.backends:
            try:
                if backend.exists(key):
                    return True
            except Exception as e:
                logger.debug(f"캐시 존재 확인 오류 ({backend.__class__.__name__}): {e}")

        return False

    def get_stats(self) -> Dict:
        """캐시 통계 반환"""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0

        return {
            **self.stats,
            "hit_rate": round(hit_rate, 2),
            "backends": len(self.backends),
            "backend_types": [backend.__class__.__name__ for backend in self.backends],
        }

    def generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """캐시 키 생성"""
        key_data = {
            "args": args,
            "kwargs": sorted(kwargs.items()) if kwargs else {},
        }
        key_string = json.dumps(key_data, sort_keys=True, default=str)
        key_hash = hashlib.sha256(key_string.encode()).hexdigest()
        return f"{prefix}:{key_hash}"


# 전역 캐시 매니저 인스턴스
_cache_manager = None


def get_cache_manager() -> UnifiedCacheManager:
    """전역 캐시 매니저 인스턴스 반환"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = UnifiedCacheManager()
    return _cache_manager


def cached(ttl: int = 300, key_prefix: str = "cache"):
    """캐싱 데코레이터"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_manager = get_cache_manager()

            # 캐시 키 생성
            cache_key = cache_manager.generate_cache_key(f"{key_prefix}:{func.__name__}", *args, **kwargs)

            # 캐시에서 조회
            result = cache_manager.get(cache_key)
            if result is not None:
                return result

            # 함수 실행 및 캐시 저장
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl)

            return result

        return wrapper

    return decorator


def invalidate_cache(key_prefix: str = None):
    """캐시 무효화"""
    cache_manager = get_cache_manager()
    if key_prefix:
        # 특정 prefix의 키들만 삭제 (Redis에서는 패턴 매칭 필요)
        # 여기서는 간단히 전체 클리어
        logger.info(f"캐시 무효화: {key_prefix}")

    cache_manager.clear()


# 하위 호환성을 위한 별칭
cache_manager = get_cache_manager()
