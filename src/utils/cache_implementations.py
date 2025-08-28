#!/usr/bin/env python3
"""
캐시 구현체들
UnifiedCacheManager의 구체적 구현 클래스들
"""

import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

import orjson

from .unified_cache_manager import CacheBackend
from .unified_logger import get_logger

logger = get_logger(__name__)


class MemoryCacheAdapter(CacheBackend):
    """메모리 기반 캐시 어댑터"""

    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        """
        메모리 캐시 초기화

        Args:
            max_size: 최대 캐시 항목 수
            default_ttl: 기본 TTL (초)
        """
        self.cache: Dict[str, Dict] = {}
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.access_times: Dict[str, float] = {}
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 조회"""
        with self._lock:
            if key not in self.cache:
                return None

            item = self.cache[key]

            # TTL 검사
            if item["ttl"] > 0 and time.time() > item["expires_at"]:
                self.delete(key)
                return None

            # 접근 시간 업데이트 (LRU용)
            self.access_times[key] = time.time()
            return item["value"]

    def set(self, key: str, value: Any, ttl: int = 0) -> bool:
        """캐시에 값 저장"""
        with self._lock:
            try:
                # TTL이 0이면 기본값 사용
                actual_ttl = ttl if ttl > 0 else self.default_ttl
                expires_at = time.time() + actual_ttl if actual_ttl > 0 else 0

                # 캐시 크기 제한 확인
                if len(self.cache) >= self.max_size and key not in self.cache:
                    self._evict_lru()

                self.cache[key] = {
                    "value": value,
                    "ttl": actual_ttl,
                    "expires_at": expires_at,
                    "created_at": time.time(),
                }

                self.access_times[key] = time.time()
                return True

            except Exception as e:
                logger.error(f"Memory cache set error: {e}")
                return False

    def delete(self, key: str) -> bool:
        """캐시에서 값 삭제"""
        with self._lock:
            if key in self.cache:
                del self.cache[key]
                self.access_times.pop(key, None)
                return True
            return False

    def clear(self) -> bool:
        """캐시 전체 삭제"""
        with self._lock:
            self.cache.clear()
            self.access_times.clear()
            return True

    def exists(self, key: str) -> bool:
        """키 존재 여부 확인"""
        return self.get(key) is not None

    def _evict_lru(self):
        """LRU 정책으로 가장 오래된 항목 제거"""
        if not self.access_times:
            return

        # 가장 오래 전에 접근된 키 찾기
        oldest_key = min(self.access_times, key=self.access_times.get)
        self.delete(oldest_key)

    def get_stats(self) -> Dict[str, Any]:
        """캐시 통계 반환"""
        with self._lock:
            current_time = time.time()
            expired_count = 0

            for item in self.cache.values():
                if item["ttl"] > 0 and current_time > item["expires_at"]:
                    expired_count += 1

            return {
                "type": "memory",
                "total_items": len(self.cache),
                "max_size": self.max_size,
                "expired_items": expired_count,
                "memory_usage_estimation": len(str(self.cache)),  # 대략적 추정
                "default_ttl": self.default_ttl,
            }


class FileCacheAdapter(CacheBackend):
    """파일 기반 캐시 어댑터"""

    def __init__(self, cache_dir: str = None, max_files: int = 10000):
        """
        파일 캐시 초기화

        Args:
            cache_dir: 캐시 디렉토리 경로
            max_files: 최대 캐시 파일 수
        """
        self.cache_dir = Path(cache_dir or "/tmp/fortinet_cache")
        self.max_files = max_files
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _get_file_path(self, key: str) -> Path:
        """캐시 키에 대한 파일 경로 생성"""
        # 키를 파일명으로 사용 (안전한 문자로 변환)
        safe_key = key.replace("/", "_").replace("\\", "_").replace(":", "_")
        return self.cache_dir / f"{safe_key}.cache"

    def get(self, key: str) -> Optional[Any]:
        """파일에서 값 조회"""
        file_path = self._get_file_path(key)

        try:
            with self._lock:
                if not file_path.exists():
                    return None

                with open(file_path, "r") as f:
                    data = orjson.loads(f.read())

                # TTL 검사
                if data["ttl"] > 0 and time.time() > data["expires_at"]:
                    self.delete(key)
                    return None

                # 접근 시간 업데이트
                file_path.touch()
                return data["value"]

        except Exception as e:
            logger.error(f"File cache get error for key {key}: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """파일에 값 저장"""
        file_path = self._get_file_path(key)

        try:
            with self._lock:
                # 캐시 파일 수 제한 확인
                if not file_path.exists():
                    cache_files = list(self.cache_dir.glob("*.cache"))
                    if len(cache_files) >= self.max_files:
                        self._evict_oldest()

                expires_at = time.time() + ttl if ttl > 0 else 0

                data = {"value": value, "ttl": ttl, "expires_at": expires_at, "created_at": time.time()}

                with open(file_path, "w") as f:
                    f.write(orjson.dumps(data).decode("utf-8"))

                return True

        except Exception as e:
            logger.error(f"File cache set error for key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """파일 삭제"""
        file_path = self._get_file_path(key)

        try:
            if file_path.exists():
                file_path.unlink()
                return True
            return False

        except Exception as e:
            logger.error(f"File cache delete error for key {key}: {e}")
            return False

    def clear(self) -> bool:
        """모든 캐시 파일 삭제"""
        try:
            with self._lock:
                for cache_file in self.cache_dir.glob("*.cache"):
                    cache_file.unlink()
                return True

        except Exception as e:
            logger.error(f"File cache clear error: {e}")
            return False

    def exists(self, key: str) -> bool:
        """키 존재 여부 확인"""
        return self._get_file_path(key).exists()

    def _evict_oldest(self):
        """가장 오래된 캐시 파일 제거"""
        try:
            cache_files = list(self.cache_dir.glob("*.cache"))
            if not cache_files:
                return

            # 수정 시간 기준으로 가장 오래된 파일 찾기
            oldest_file = min(cache_files, key=lambda f: f.stat().st_mtime)
            oldest_file.unlink()

        except Exception as e:
            logger.error(f"File cache eviction error: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """캐시 통계 반환"""
        try:
            cache_files = list(self.cache_dir.glob("*.cache"))
            total_size = sum(f.stat().st_size for f in cache_files)

            return {
                "type": "file",
                "total_files": len(cache_files),
                "max_files": self.max_files,
                "total_size_bytes": total_size,
                "cache_directory": str(self.cache_dir),
            }

        except Exception as e:
            logger.error(f"File cache stats error: {e}")
            return {"type": "file", "error": str(e)}


class RedisCacheAdapter(CacheBackend):
    """Redis 기반 캐시 어댑터"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: str = None,
        connection_pool_size: int = 10,
    ):
        """
        Redis 캐시 초기화

        Args:
            host: Redis 호스트
            port: Redis 포트
            db: Redis 데이터베이스 번호
            password: Redis 비밀번호
            connection_pool_size: 연결 풀 크기
        """
        try:
            import redis

            # 연결 풀 생성
            pool = redis.ConnectionPool(
                host=host,
                port=port,
                db=db,
                password=password,
                max_connections=connection_pool_size,
                decode_responses=False,  # bytes로 처리
            )

            self.redis_client = redis.Redis(connection_pool=pool)
            self.key_prefix = "fortinet_cache:"

            # 연결 테스트
            self.redis_client.ping()
            logger.info(f"Redis cache connected: {host}:{port}/{db}")

        except Exception as e:
            logger.error(f"Redis cache initialization failed: {e}")
            # Redis 연결 실패 시 메모리 캐시로 폴백
            logger.info("Falling back to memory cache")
            self._fallback = MemoryCacheAdapter()
            self.redis_client = None

    def _get_key(self, key: str) -> str:
        """키에 접두사 추가"""
        return f"{self.key_prefix}{key}"

    def get(self, key: str) -> Optional[Any]:
        """Redis에서 값 조회"""
        if not self.redis_client:
            return self._fallback.get(key)

        try:
            redis_key = self._get_key(key)
            data = self.redis_client.get(redis_key)

            if data is None:
                return None

            # 데이터 역직렬화
            return orjson.loads(data)

        except Exception as e:
            logger.error(f"Redis get error for key {key}: {e}")
            if hasattr(self, "_fallback"):
                return self._fallback.get(key)
            return None

    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Redis에 값 저장"""
        if not self.redis_client:
            return self._fallback.set(key, value, ttl)

        try:
            redis_key = self._get_key(key)

            # 데이터 직렬화
            serialized_data = orjson.dumps(value)

            # TTL 설정하여 저장
            if ttl > 0:
                return self.redis_client.setex(redis_key, ttl, serialized_data)
            else:
                return self.redis_client.set(redis_key, serialized_data)

        except Exception as e:
            logger.error(f"Redis set error for key {key}: {e}")
            if hasattr(self, "_fallback"):
                return self._fallback.set(key, value, ttl)
            return False

    def delete(self, key: str) -> bool:
        """Redis에서 값 삭제"""
        if not self.redis_client:
            return self._fallback.delete(key)

        try:
            redis_key = self._get_key(key)
            return bool(self.redis_client.delete(redis_key))

        except Exception as e:
            logger.error(f"Redis delete error for key {key}: {e}")
            if hasattr(self, "_fallback"):
                return self._fallback.delete(key)
            return False

    def clear(self) -> bool:
        """Redis 캐시 전체 삭제"""
        if not self.redis_client:
            return self._fallback.clear()

        try:
            # 접두사가 있는 모든 키 삭제
            pattern = f"{self.key_prefix}*"
            keys = self.redis_client.keys(pattern)

            if keys:
                return bool(self.redis_client.delete(*keys))
            return True

        except Exception as e:
            logger.error(f"Redis clear error: {e}")
            if hasattr(self, "_fallback"):
                return self._fallback.clear()
            return False

    def exists(self, key: str) -> bool:
        """키 존재 여부 확인"""
        if not self.redis_client:
            return self._fallback.exists(key)

        try:
            redis_key = self._get_key(key)
            return bool(self.redis_client.exists(redis_key))

        except Exception as e:
            logger.error(f"Redis exists error for key {key}: {e}")
            if hasattr(self, "_fallback"):
                return self._fallback.exists(key)
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Redis 캐시 통계 반환"""
        if not self.redis_client:
            stats = self._fallback.get_stats()
            stats["fallback_mode"] = True
            return stats

        try:
            info = self.redis_client.info()

            # 접두사가 있는 키 개수 계산
            pattern = f"{self.key_prefix}*"
            key_count = len(self.redis_client.keys(pattern))

            return {
                "type": "redis",
                "total_keys": key_count,
                "redis_version": info.get("redis_version"),
                "used_memory": info.get("used_memory"),
                "used_memory_human": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
            }

        except Exception as e:
            logger.error(f"Redis stats error: {e}")
            return {"type": "redis", "error": str(e)}


class HybridCacheAdapter(CacheBackend):
    """하이브리드 캐시 어댑터 (메모리 + Redis)"""

    def __init__(self, memory_max_size: int = 100, redis_config: Dict = None):
        """
        하이브리드 캐시 초기화

        Args:
            memory_max_size: 메모리 캐시 최대 크기
            redis_config: Redis 설정
        """
        # L1 캐시: 메모리 (빠른 액세스)
        self.l1_cache = MemoryCacheAdapter(max_size=memory_max_size)

        # L2 캐시: Redis (지속성)
        redis_config = redis_config or {}
        self.l2_cache = RedisCacheAdapter(**redis_config)

        logger.info(f"Hybrid cache initialized: L1={memory_max_size}, L2=Redis")

    def get(self, key: str) -> Optional[Any]:
        """하이브리드 캐시에서 값 조회"""
        # L1 캐시에서 먼저 조회
        value = self.l1_cache.get(key)
        if value is not None:
            return value

        # L2 캐시에서 조회
        value = self.l2_cache.get(key)
        if value is not None:
            # L1 캐시에 복사 (캐시 승격)
            self.l1_cache.set(key, value, ttl=300)  # 5분 TTL

        return value

    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """하이브리드 캐시에 값 저장"""
        # 두 캐시 모두에 저장
        l1_success = self.l1_cache.set(key, value, min(ttl, 300))  # L1은 최대 5분
        l2_success = self.l2_cache.set(key, value, ttl)

        # 하나라도 성공하면 성공으로 간주
        return l1_success or l2_success

    def delete(self, key: str) -> bool:
        """두 캐시에서 모두 삭제"""
        l1_success = self.l1_cache.delete(key)
        l2_success = self.l2_cache.delete(key)

        return l1_success or l2_success

    def clear(self) -> bool:
        """두 캐시 모두 삭제"""
        l1_success = self.l1_cache.clear()
        l2_success = self.l2_cache.clear()

        return l1_success and l2_success

    def exists(self, key: str) -> bool:
        """키 존재 여부 확인"""
        return self.l1_cache.exists(key) or self.l2_cache.exists(key)

    def get_stats(self) -> Dict[str, Any]:
        """하이브리드 캐시 통계 반환"""
        l1_stats = self.l1_cache.get_stats()
        l2_stats = self.l2_cache.get_stats()

        return {"type": "hybrid", "l1_cache": l1_stats, "l2_cache": l2_stats}


# 캐시 어댑터 팩토리
class CacheAdapterFactory:
    """캐시 어댑터 팩토리"""

    @staticmethod
    def create_adapter(adapter_type: str, **kwargs) -> CacheBackend:
        """어댑터 타입으로 캐시 어댑터 생성"""
        adapters = {
            "memory": MemoryCacheAdapter,
            "file": FileCacheAdapter,
            "redis": RedisCacheAdapter,
            "hybrid": HybridCacheAdapter,
        }

        adapter_class = adapters.get(adapter_type.lower())
        if not adapter_class:
            raise ValueError(f"Unknown cache adapter type: {adapter_type}")

        return adapter_class(**kwargs)

    @staticmethod
    def create_default_adapter() -> CacheBackend:
        """환경에 따른 기본 어댑터 생성"""
        # Redis 설정이 있으면 Redis 사용, 없으면 메모리 캐시 사용
        redis_enabled = os.environ.get("REDIS_ENABLED", "false").lower() == "true"

        if redis_enabled:
            redis_host = os.environ.get("REDIS_HOST", "localhost")
            redis_port = int(os.environ.get("REDIS_PORT", "6379"))
            redis_password = os.environ.get("REDIS_PASSWORD")

            try:
                return RedisCacheAdapter(host=redis_host, port=redis_port, password=redis_password)
            except Exception as e:
                logger.warning(f"Failed to create Redis cache, using memory: {e}")
                return MemoryCacheAdapter()
        else:
            return MemoryCacheAdapter()
