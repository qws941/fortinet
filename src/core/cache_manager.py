#!/usr/bin/env python3

"""
Nextrade FortiGate - Unified Cache Manager
통합 캐시 관리자 - 메모리 및 Redis 캐시 통합 관리
Version: 3.0.0
Date: 2025-05-30
"""

import hashlib
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

import orjson

from config.constants import CACHE_SETTINGS, DEFAULT_PORTS


class CacheBackend(Enum):
    """Cache backend types."""

    MEMORY = "memory"
    REDIS = "redis"
    FILE = "file"
    AUTO = "auto"


@dataclass
class CacheItem:
    """Cache item container."""

    key: str
    value: Any
    expires_at: Optional[datetime] = None
    created_at: datetime = None
    access_count: int = 0
    last_accessed: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.last_accessed is None:
            self.last_accessed = self.created_at

    def is_expired(self) -> bool:
        """Check if cache item is expired."""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

    def touch(self):
        """Update access information."""
        self.access_count += 1
        self.last_accessed = datetime.now()


class BaseCacheBackend(ABC):
    """Base class for cache backends."""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete value from cache."""

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""

    @abstractmethod
    def clear(self) -> bool:
        """Clear all cache entries."""

    @abstractmethod
    def keys(self, pattern: str = "*") -> List[str]:
        """Get all keys matching pattern."""

    @abstractmethod
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""


class MemoryCacheBackend(BaseCacheBackend):
    """In-memory cache backend."""

    def __init__(self, max_size: int = None, cleanup_interval: int = None):
        """
        Initialize memory cache.

        Args:
            max_size: Maximum number of items to store
            cleanup_interval: Cleanup interval in seconds
        """
        self._cache: Dict[str, CacheItem] = {}
        self._max_size = max_size or CACHE_SETTINGS["MAX_SIZE"]
        self._cleanup_interval = cleanup_interval or CACHE_SETTINGS["CLEANUP_INTERVAL"]
        self._last_cleanup = time.time()

        # Statistics
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "evictions": 0,
            "size": 0,
        }

    def get(self, key: str) -> Optional[Any]:
        """Get value from memory cache."""
        self._cleanup_if_needed()

        item = self._cache.get(key)
        if item is None:
            self._stats["misses"] += 1
            return None

        if item.is_expired():
            self.delete(key)
            self._stats["misses"] += 1
            return None

        item.touch()
        self._stats["hits"] += 1
        return item.value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in memory cache."""
        self._cleanup_if_needed()

        # Check if we need to evict items
        if len(self._cache) >= self._max_size and key not in self._cache:
            self._evict_lru()

        expires_at = None
        if ttl is not None:
            expires_at = datetime.now() + timedelta(seconds=ttl)

        self._cache[key] = CacheItem(key=key, value=value, expires_at=expires_at)

        self._stats["sets"] += 1
        self._stats["size"] = len(self._cache)
        return True

    def delete(self, key: str) -> bool:
        """Delete value from memory cache."""
        if key in self._cache:
            del self._cache[key]
            self._stats["deletes"] += 1
            self._stats["size"] = len(self._cache)
            return True
        return False

    def exists(self, key: str) -> bool:
        """Check if key exists in memory cache."""
        item = self._cache.get(key)
        if item is None:
            return False

        if item.is_expired():
            self.delete(key)
            return False

        return True

    def clear(self) -> bool:
        """Clear all cache entries."""
        self._cache.clear()
        self._stats["size"] = 0
        return True

    def keys(self, pattern: str = "*") -> List[str]:
        """Get all keys matching pattern."""
        import fnmatch

        return [key for key in self._cache.keys() if fnmatch.fnmatch(key, pattern)]

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        hit_rate = 0
        total_requests = self._stats["hits"] + self._stats["misses"]
        if total_requests > 0:
            hit_rate = self._stats["hits"] / total_requests

        return {**self._stats, "hit_rate": hit_rate, "backend": "memory"}

    def _cleanup_if_needed(self):
        """Cleanup expired items if needed."""
        current_time = time.time()
        if current_time - self._last_cleanup > self._cleanup_interval:
            self._cleanup_expired()
            self._last_cleanup = current_time

    def _cleanup_expired(self):
        """Remove expired items."""
        expired_keys = []
        for key, item in self._cache.items():
            if item.is_expired():
                expired_keys.append(key)

        for key in expired_keys:
            self.delete(key)

    def _evict_lru(self):
        """Evict least recently used item."""
        if not self._cache:
            return

        lru_key = min(self._cache.keys(), key=lambda k: self._cache[k].last_accessed)
        self.delete(lru_key)
        self._stats["evictions"] += 1


class RedisCacheBackend(BaseCacheBackend):
    """Redis cache backend."""

    def __init__(
        self,
        host: str = None,
        port: int = None,
        db: int = None,
        password: Optional[str] = None,
        prefix: str = "nextrade:",
    ):
        """
        Initialize Redis cache.

        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password
            prefix: Key prefix
        """
        import os

        self._host = host or os.getenv("REDIS_HOST", "localhost")
        self._port = port or DEFAULT_PORTS["REDIS"]
        self._db = db or int(os.getenv("REDIS_DB", "0"))
        self._password = password or os.getenv("REDIS_PASSWORD")
        self._prefix = prefix
        self._redis = None
        self._connected = False

        # Statistics
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0,
        }

        self._connect()

    def _connect(self):
        """Connect to Redis."""
        try:
            import redis

            self._redis = redis.Redis(
                host=self._host,
                port=self._port,
                db=self._db,
                password=self._password,
                decode_responses=False,
                socket_timeout=5,
                socket_connect_timeout=5,
            )
            # Test connection
            self._redis.ping()
            self._connected = True
        except ImportError:
            print("Redis library not installed. Please install: pip install redis")
            self._connected = False
        except Exception as e:
            print(f"Redis connection failed: {e}")
            self._connected = False

    def _prefixed_key(self, key: str) -> str:
        """Add prefix to key."""
        return f"{self._prefix}{key}"

    def _unprefixed_key(self, key: str) -> str:
        """Remove prefix from key."""
        if key.startswith(self._prefix):
            return key[len(self._prefix) :]
        return key

    def get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache."""
        if not self._connected:
            self._stats["misses"] += 1
            return None

        try:
            prefixed_key = self._prefixed_key(key)
            data = self._redis.get(prefixed_key)

            if data is None:
                self._stats["misses"] += 1
                return None

            value = json.loads(data.decode() if isinstance(data, bytes) else data)
            self._stats["hits"] += 1
            return value

        except Exception as e:
            print(f"Redis get error: {e}")
            self._stats["errors"] += 1
            self._stats["misses"] += 1
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in Redis cache."""
        if not self._connected:
            return False

        try:
            prefixed_key = self._prefixed_key(key)
            data = orjson.dumps(value)

            if ttl is not None:
                self._redis.setex(prefixed_key, ttl, data)
            else:
                self._redis.set(prefixed_key, data)

            self._stats["sets"] += 1
            return True

        except Exception as e:
            print(f"Redis set error: {e}")
            self._stats["errors"] += 1
            return False

    def delete(self, key: str) -> bool:
        """Delete value from Redis cache."""
        if not self._connected:
            return False

        try:
            prefixed_key = self._prefixed_key(key)
            result = self._redis.delete(prefixed_key)
            self._stats["deletes"] += 1
            return result > 0

        except Exception as e:
            print(f"Redis delete error: {e}")
            self._stats["errors"] += 1
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists in Redis cache."""
        if not self._connected:
            return False

        try:
            prefixed_key = self._prefixed_key(key)
            return self._redis.exists(prefixed_key) > 0

        except Exception as e:
            print(f"Redis exists error: {e}")
            self._stats["errors"] += 1
            return False

    def clear(self) -> bool:
        """Clear all cache entries with prefix."""
        if not self._connected:
            return False

        try:
            pattern = f"{self._prefix}*"
            keys = self._redis.keys(pattern)
            if keys:
                self._redis.delete(*keys)
            return True

        except Exception as e:
            print(f"Redis clear error: {e}")
            self._stats["errors"] += 1
            return False

    def keys(self, pattern: str = "*") -> List[str]:
        """Get all keys matching pattern."""
        if not self._connected:
            return []

        try:
            prefixed_pattern = self._prefixed_key(pattern)
            keys = self._redis.keys(prefixed_pattern)
            return [self._unprefixed_key(key.decode()) for key in keys]

        except Exception as e:
            print(f"Redis keys error: {e}")
            self._stats["errors"] += 1
            return []

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        hit_rate = 0
        total_requests = self._stats["hits"] + self._stats["misses"]
        if total_requests > 0:
            hit_rate = self._stats["hits"] / total_requests

        stats = {
            **self._stats,
            "hit_rate": hit_rate,
            "backend": "redis",
            "connected": self._connected,
        }

        if self._connected:
            try:
                info = self._redis.info()
                stats.update(
                    {
                        "redis_memory_used": info.get("used_memory_human", "Unknown"),
                        "redis_keys": (info.get("db0", {}).get("keys", 0) if "db0" in info else 0),
                    }
                )
            except Exception:
                pass

        return stats


class CacheManager:
    """
    Unified Cache Manager
    메모리 및 Redis 캐시를 통합 관리
    """

    def __init__(
        self,
        backends: Optional[List[CacheBackend]] = None,
        memory_config: Optional[Dict] = None,
        redis_config: Optional[Dict] = None,
    ):
        """
        Initialize cache manager.

        Args:
            backends: List of backends to use
            memory_config: Memory cache configuration
            redis_config: Redis cache configuration
        """
        self._backends: Dict[CacheBackend, BaseCacheBackend] = {}

        # Default backends
        if backends is None:
            backends = [CacheBackend.MEMORY, CacheBackend.REDIS]

        # Setup backends
        for backend in backends:
            if backend == CacheBackend.MEMORY:
                config = memory_config or {}
                self._backends[backend] = MemoryCacheBackend(**config)
            elif backend == CacheBackend.REDIS:
                config = redis_config or {}
                self._backends[backend] = RedisCacheBackend(**config)

    def get(self, key: str, backend: CacheBackend = CacheBackend.AUTO) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key
            backend: Specific backend to use

        Returns:
            Cached value or None
        """
        if backend == CacheBackend.AUTO:
            # Try memory first, then Redis
            for backend_type in [CacheBackend.MEMORY, CacheBackend.REDIS]:
                if backend_type in self._backends:
                    value = self._backends[backend_type].get(key)
                    if value is not None:
                        # Populate lower-priority caches
                        self._populate_lower_caches(key, value, backend_type)
                        return value
            return None
        else:
            backend_instance = self._backends.get(backend)
            if backend_instance:
                return backend_instance.get(key)
            return None

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        backends: Optional[List[CacheBackend]] = None,
    ) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            backends: Specific backends to use

        Returns:
            True if set in at least one backend
        """
        if backends is None:
            backends = list(self._backends.keys())

        success = False
        for backend in backends:
            backend_instance = self._backends.get(backend)
            if backend_instance:
                if backend_instance.set(key, value, ttl):
                    success = True

        return success

    def delete(self, key: str, backends: Optional[List[CacheBackend]] = None) -> bool:
        """
        Delete value from cache.

        Args:
            key: Cache key
            backends: Specific backends to use

        Returns:
            True if deleted from at least one backend
        """
        if backends is None:
            backends = list(self._backends.keys())

        success = False
        for backend in backends:
            backend_instance = self._backends.get(backend)
            if backend_instance:
                if backend_instance.delete(key):
                    success = True

        return success

    def exists(self, key: str, backend: CacheBackend = CacheBackend.AUTO) -> bool:
        """
        Check if key exists in cache.

        Args:
            key: Cache key
            backend: Specific backend to use

        Returns:
            True if key exists
        """
        if backend == CacheBackend.AUTO:
            for backend_type in [CacheBackend.MEMORY, CacheBackend.REDIS]:
                if backend_type in self._backends:
                    if self._backends[backend_type].exists(key):
                        return True
            return False
        else:
            backend_instance = self._backends.get(backend)
            if backend_instance:
                return backend_instance.exists(key)
            return False

    def clear(self, backends: Optional[List[CacheBackend]] = None) -> bool:
        """
        Clear cache.

        Args:
            backends: Specific backends to clear

        Returns:
            True if cleared successfully
        """
        if backends is None:
            backends = list(self._backends.keys())

        success = True
        for backend in backends:
            backend_instance = self._backends.get(backend)
            if backend_instance:
                if not backend_instance.clear():
                    success = False

        return success

    def keys(self, pattern: str = "*", backend: CacheBackend = CacheBackend.AUTO) -> List[str]:
        """
        Get keys matching pattern.

        Args:
            pattern: Key pattern
            backend: Specific backend to use

        Returns:
            List of matching keys
        """
        if backend == CacheBackend.AUTO:
            # Combine keys from all backends
            all_keys = set()
            for backend_instance in self._backends.values():
                all_keys.update(backend_instance.keys(pattern))
            return list(all_keys)
        else:
            backend_instance = self._backends.get(backend)
            if backend_instance:
                return backend_instance.keys(pattern)
            return []

    def stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Statistics for all backends
        """
        stats = {"backends": {}}

        for backend_type, backend_instance in self._backends.items():
            stats["backends"][backend_type.value] = backend_instance.stats()

        return stats

    def cache_key(self, *args, **kwargs) -> str:
        """
        Generate cache key from arguments.

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Generated cache key
        """
        # Create deterministic key from arguments
        key_data = {"args": args, "kwargs": sorted(kwargs.items())}

        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.sha256(key_str.encode()).hexdigest()

    def cached(
        self,
        ttl: Optional[int] = None,
        backends: Optional[List[CacheBackend]] = None,
    ):
        """
        Decorator for caching function results.

        Args:
            ttl: Time to live in seconds
            backends: Specific backends to use

        Returns:
            Decorator function
        """

        def decorator(func):
            def wrapper(*args, **kwargs):
                # Generate cache key
                key = f"func:{func.__name__}:{self.cache_key(*args, **kwargs)}"

                # Try to get from cache
                result = self.get(key)
                if result is not None:
                    return result

                # Execute function and cache result
                result = func(*args, **kwargs)
                self.set(key, result, ttl, backends)
                return result

            return wrapper

        return decorator

    def _populate_lower_caches(self, key: str, value: Any, source_backend: CacheBackend):
        """
        Populate lower-priority caches with value from higher-priority cache.

        Args:
            key: Cache key
            value: Value to populate
            source_backend: Backend where value was found
        """
        # Only populate memory cache from Redis
        if source_backend == CacheBackend.REDIS and CacheBackend.MEMORY in self._backends:
            self._backends[CacheBackend.MEMORY].set(key, value)


# Global cache manager instance
cache_manager = CacheManager()

# Alias for compatibility
UnifiedCacheManager = CacheManager
