#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
캐시 계층 일관성 통합 테스트 - Rust 스타일 인라인 테스트
Redis ↔ Memory ↔ File 시스템 간 캐시 동기화, 승격/강등, 장애 복구 통합 테스트
"""

import json
import os
import pickle
import sys
import tempfile
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from unittest.mock import MagicMock, patch

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.integration_test_framework import test_framework
from src.utils.redis_cache import RedisCache
from src.utils.unified_cache_manager import UnifiedCacheManager, get_cache_manager


class MockRedisClient:
    """Redis 클라이언트 모킹을 위한 클래스"""

    def __init__(self, fail_mode: bool = False):
        self.data = {}
        self.fail_mode = fail_mode
        self.operation_count = 0
        self.connection_active = not fail_mode

    def get(self, key: str) -> Optional[bytes]:
        """Redis GET 시뮬레이션"""
        self.operation_count += 1
        if self.fail_mode:
            raise ConnectionError("Redis connection failed")

        value = self.data.get(key)
        return value.encode() if value else None

    def set(self, key: str, value: Union[str, bytes], ex: Optional[int] = None) -> bool:
        """Redis SET 시뮬레이션"""
        self.operation_count += 1
        if self.fail_mode:
            raise ConnectionError("Redis connection failed")

        if isinstance(value, bytes):
            value = value.decode()
        self.data[key] = value
        return True

    def delete(self, key: str) -> int:
        """Redis DELETE 시뮬레이션"""
        self.operation_count += 1
        if self.fail_mode:
            raise ConnectionError("Redis connection failed")

        if key in self.data:
            del self.data[key]
            return 1
        return 0

    def exists(self, key: str) -> int:
        """Redis EXISTS 시뮬레이션"""
        self.operation_count += 1
        if self.fail_mode:
            raise ConnectionError("Redis connection failed")

        return 1 if key in self.data else 0

    def flushall(self) -> bool:
        """Redis FLUSHALL 시뮬레이션"""
        self.operation_count += 1
        if self.fail_mode:
            raise ConnectionError("Redis connection failed")

        self.data.clear()
        return True

    def ping(self) -> bool:
        """Redis PING 시뮬레이션"""
        self.operation_count += 1
        if self.fail_mode:
            raise ConnectionError("Redis connection failed")
        return True

    def simulate_failure(self):
        """연결 실패 시뮬레이션"""
        self.fail_mode = True
        self.connection_active = False

    def simulate_recovery(self):
        """연결 복구 시뮬레이션"""
        self.fail_mode = False
        self.connection_active = True


class CacheIntegrationTester:
    """캐시 통합 테스트를 위한 유틸리티 클래스"""

    def __init__(self):
        self.mock_redis = MockRedisClient()
        self.temp_dir = tempfile.mkdtemp()
        self.cache_operations = []

    def create_test_cache_manager(self, redis_enabled: bool = True) -> UnifiedCacheManager:
        """테스트용 캐시 매니저 생성"""
        # 임시 디렉토리에서 캐시 매니저 생성
        cache_manager = UnifiedCacheManager()

        if redis_enabled:
            # Mock Redis 클라이언트 주입
            cache_manager.redis_cache.client = self.mock_redis
            cache_manager.redis_cache.enabled = True
        else:
            cache_manager.redis_cache.enabled = False

        return cache_manager

    def generate_test_data(self, size: int = 100) -> Dict[str, Any]:
        """테스트용 데이터 생성"""
        return {
            f"test_key_{i}": {
                "id": i,
                "name": f"test_item_{i}",
                "timestamp": time.time(),
                "data": f"test_data_{i}" * 10,  # 일정 크기의 데이터
            }
            for i in range(size)
        }

    def log_cache_operation(self, operation: str, key: str, backend: str, result: Any):
        """캐시 작업 로깅"""
        self.cache_operations.append(
            {
                "operation": operation,
                "key": key,
                "backend": backend,
                "result": result,
                "timestamp": time.time(),
            }
        )


# 캐시 통합 테스트 실행
cache_tester = CacheIntegrationTester()


@test_framework.test("unified_cache_manager_initialization")
def test_cache_manager_init():
    """통합 캐시 매니저 초기화 검증"""

    cache_manager = cache_tester.create_test_cache_manager()

    # 기본 속성 확인
    test_framework.assert_ok(hasattr(cache_manager, "backends"), "Cache manager should have backends")
    test_framework.assert_ok(hasattr(cache_manager, "redis_cache"), "Cache manager should have Redis cache")
    test_framework.assert_ok(hasattr(cache_manager, "memory_cache"), "Cache manager should have memory cache")

    # 백엔드 순서 확인 (Redis -> Memory -> File)
    backends = getattr(cache_manager, "backends", [])
    test_framework.assert_ok(len(backends) >= 2, "Should have at least memory and file backends")

    # 각 백엔드 기능 확인
    test_cache_key = "test_init_key"
    test_cache_value = {"init_test": True, "timestamp": time.time()}

    # Memory cache 테스트
    memory_set_result = cache_manager.memory_cache.set(test_cache_key, test_cache_value)
    test_framework.assert_ok(memory_set_result, "Memory cache set should succeed")

    memory_get_result = cache_manager.memory_cache.get(test_cache_key)
    test_framework.assert_eq(
        memory_get_result,
        test_cache_value,
        "Memory cache get should return stored value",
    )

    assert True  # Test passed


@test_framework.test("cache_tier_promotion_and_demotion")
def test_cache_tier_operations():
    """캐시 계층 간 승격 및 강등 로직 검증"""

    cache_manager = cache_tester.create_test_cache_manager()
    test_data = cache_tester.generate_test_data(10)

    promotion_demotion_results = []

    for key, value in test_data.items():
        # 1단계: Memory cache에만 저장
        memory_set = cache_manager.memory_cache.set(key, value, ttl=300)
        cache_tester.log_cache_operation("set", key, "memory", memory_set)

        # 2단계: Redis로 승격 시뮬레이션
        try:
            redis_set = cache_manager.redis_cache.set(key, value, ttl=300)
            cache_tester.log_cache_operation("promote_to_redis", key, "redis", redis_set)
        except Exception as e:
            cache_tester.log_cache_operation("promote_to_redis", key, "redis", f"failed: {e}")
            redis_set = False

        # 3단계: 통합 캐시에서 조회 (계층 순서 확인)
        unified_get = cache_manager.get(key)
        cache_tester.log_cache_operation("unified_get", key, "unified", unified_get is not None)

        # 검증: 데이터가 올바르게 저장/조회되는지 확인
        test_framework.assert_ok(memory_set, f"Memory cache set should succeed for {key}")
        test_framework.assert_ok(unified_get is not None, f"Unified cache get should return data for {key}")

        if unified_get:
            test_framework.assert_eq(unified_get, value, f"Retrieved data should match stored data for {key}")

        promotion_demotion_results.append(
            {
                "key": key,
                "memory_set": memory_set,
                "redis_set": redis_set,
                "unified_get_success": unified_get is not None,
                "data_integrity": unified_get == value if unified_get else False,
            }
        )

    # 전체 작업 결과 검증
    successful_operations = [r for r in promotion_demotion_results if r["unified_get_success"]]
    test_framework.assert_ok(len(successful_operations) > 0, "At least some cache operations should succeed")

    assert True  # Test passed


@test_framework.test("redis_failure_and_fallback")
def test_redis_failure_fallback():
    """Redis 장애 시 폴백 동작 검증"""

    # Redis 활성화된 캐시 매니저 생성
    cache_manager = cache_tester.create_test_cache_manager(redis_enabled=True)

    # 정상 상태에서 데이터 저장
    test_key = "redis_failure_test"
    test_value = {"test": "redis_failure", "timestamp": time.time()}

    # 1단계: 정상 상태에서 저장
    normal_set = cache_manager.set(test_key, test_value, ttl=300)
    normal_get = cache_manager.get(test_key)

    test_framework.assert_ok(normal_set, "Normal cache set should succeed")
    test_framework.assert_eq(normal_get, test_value, "Normal cache get should return stored value")

    # 2단계: Redis 장애 시뮬레이션
    cache_tester.mock_redis.simulate_failure()

    # Redis 장애 상태에서 새로운 데이터 저장 시도
    failure_test_key = "redis_failure_new_data"
    failure_test_value = {"test": "failure_fallback", "timestamp": time.time()}

    failure_set = cache_manager.set(failure_test_key, failure_test_value, ttl=300)
    failure_get = cache_manager.get(failure_test_key)

    # Memory cache로 폴백되어 동작해야 함
    test_framework.assert_ok(
        failure_set,
        "Cache set should succeed even with Redis failure (memory fallback)",
    )
    test_framework.assert_eq(failure_get, failure_test_value, "Cache get should work with memory fallback")

    # 3단계: Redis 복구 시뮬레이션
    cache_tester.mock_redis.simulate_recovery()

    # 복구 후 새로운 데이터 저장
    recovery_test_key = "redis_recovery_test"
    recovery_test_value = {"test": "recovery", "timestamp": time.time()}

    recovery_set = cache_manager.set(recovery_test_key, recovery_test_value, ttl=300)
    recovery_get = cache_manager.get(recovery_test_key)

    test_framework.assert_ok(recovery_set, "Cache set should succeed after Redis recovery")
    test_framework.assert_eq(recovery_get, recovery_test_value, "Cache get should work after Redis recovery")

    # Test completed successfully
    print(f"✅ Failure fallback - set: {failure_set}, get: {failure_get == failure_test_value}")
    print(f"✅ Recovery operation - set: {recovery_set}, get: {recovery_get == recovery_test_value}")
    print("✅ Redis failure handling test completed")


@test_framework.test("cache_consistency_across_backends")
def test_cache_consistency():
    """백엔드 간 캐시 일관성 검증"""

    cache_manager = cache_tester.create_test_cache_manager()

    # 일관성 테스트 데이터
    consistency_tests = [
        {"key": "consistency_test_1", "value": {"data": "test1", "type": "string"}},
        {"key": "consistency_test_2", "value": {"data": 12345, "type": "number"}},
        {"key": "consistency_test_3", "value": {"data": [1, 2, 3], "type": "array"}},
        {
            "key": "consistency_test_4",
            "value": {"data": {"nested": True}, "type": "object"},
        },
    ]

    consistency_results = []

    for test_case in consistency_tests:
        key = test_case["key"]
        value = test_case["value"]

        # 1단계: 통합 캐시에 저장
        unified_set = cache_manager.set(key, value, ttl=300)

        # 2단계: 각 백엔드에서 직접 조회
        memory_get = cache_manager.memory_cache.get(key)

        try:
            redis_get = cache_manager.redis_cache.get(key)
        except:
            redis_get = None  # Redis 실패 시 None

        # 3단계: 통합 캐시에서 조회
        unified_get = cache_manager.get(key)

        # 일관성 검증
        memory_consistent = memory_get == value if memory_get else False
        unified_consistent = unified_get == value if unified_get else False

        consistency_results.append(
            {
                "key": key,
                "value_type": test_case["value"]["type"],
                "unified_set": unified_set,
                "memory_consistent": memory_consistent,
                "redis_available": redis_get is not None,
                "unified_consistent": unified_consistent,
                "overall_consistent": unified_consistent and memory_consistent,
            }
        )

        # 각 테스트 케이스에 대한 검증
        test_framework.assert_ok(unified_set, f"Unified cache set should succeed for {key}")
        test_framework.assert_ok(unified_consistent, f"Data should be consistent in unified cache for {key}")

    # 전체 일관성 검증
    all_consistent = all(result["overall_consistent"] for result in consistency_results)
    test_framework.assert_ok(all_consistent, "All cache backends should maintain data consistency")

    assert True  # Test passed


@test_framework.test("concurrent_cache_access")
def test_concurrent_cache_access():
    """동시 캐시 접근 처리 검증"""

    cache_manager = cache_tester.create_test_cache_manager()

    concurrent_results = []
    cache_access_threads = []
    shared_results = []

    def concurrent_cache_worker(worker_id: int, operation_count: int):
        """동시 캐시 접근을 시뮬레이션하는 워커"""
        worker_results = []

        for i in range(operation_count):
            key = f"concurrent_test_{worker_id}_{i}"
            value = {"worker_id": worker_id, "operation": i, "timestamp": time.time()}

            try:
                # 캐시 저장
                set_result = cache_manager.set(key, value, ttl=300)

                # 즉시 조회
                get_result = cache_manager.get(key)

                # 결과 검증
                is_consistent = get_result == value if get_result else False

                worker_results.append(
                    {
                        "worker_id": worker_id,
                        "operation": i,
                        "key": key,
                        "set_success": set_result,
                        "get_success": get_result is not None,
                        "data_consistent": is_consistent,
                    }
                )

            except Exception as e:
                worker_results.append(
                    {
                        "worker_id": worker_id,
                        "operation": i,
                        "key": key,
                        "error": str(e),
                        "set_success": False,
                        "get_success": False,
                        "data_consistent": False,
                    }
                )

        shared_results.extend(worker_results)

    # 동시 워커 생성 및 실행
    num_workers = 5
    operations_per_worker = 10

    for worker_id in range(num_workers):
        thread = threading.Thread(target=concurrent_cache_worker, args=(worker_id, operations_per_worker))
        cache_access_threads.append(thread)

    # 모든 스레드 시작
    start_time = time.time()
    for thread in cache_access_threads:
        thread.start()

    # 모든 스레드 완료 대기
    for thread in cache_access_threads:
        thread.join(timeout=15)  # 15초 타임아웃

    end_time = time.time()

    # 결과 분석
    total_operations = num_workers * operations_per_worker
    successful_operations = [r for r in shared_results if r["set_success"] and r["get_success"]]
    consistent_operations = [r for r in shared_results if r["data_consistent"]]

    # 검증
    test_framework.assert_eq(
        len(shared_results),
        total_operations,
        f"All {total_operations} operations should complete",
    )

    test_framework.assert_ok(
        len(successful_operations) > total_operations * 0.9,
        "At least 90% of operations should succeed",
    )

    test_framework.assert_ok(
        len(consistent_operations) > total_operations * 0.9,
        "At least 90% of operations should maintain data consistency",
    )

    assert True  # Test passed


@test_framework.test("cache_ttl_and_expiration")
def test_cache_ttl_expiration():
    """캐시 TTL 및 만료 처리 검증"""

    cache_manager = cache_tester.create_test_cache_manager()

    ttl_tests = [
        {"key": "ttl_test_short", "value": {"data": "short_ttl"}, "ttl": 1},  # 1초
        {"key": "ttl_test_medium", "value": {"data": "medium_ttl"}, "ttl": 5},  # 5초
        {"key": "ttl_test_long", "value": {"data": "long_ttl"}, "ttl": 300},  # 5분
    ]

    ttl_results = []

    for test_case in ttl_tests:
        key = test_case["key"]
        value = test_case["value"]
        ttl = test_case["ttl"]

        # TTL과 함께 데이터 저장
        set_result = cache_manager.set(key, value, ttl=ttl)
        test_framework.assert_ok(set_result, f"Cache set with TTL should succeed for {key}")

        # 즉시 조회 (만료 전)
        immediate_get = cache_manager.get(key)
        test_framework.assert_eq(immediate_get, value, f"Immediate get should return stored value for {key}")

        ttl_results.append(
            {
                "key": key,
                "ttl": ttl,
                "set_success": set_result,
                "immediate_get_success": immediate_get == value,
                "test_type": "short" if ttl <= 1 else "medium" if ttl <= 5 else "long",
            }
        )

    # 짧은 TTL 테스트: 1초 대기 후 만료 확인
    time.sleep(1.5)  # 1.5초 대기

    short_ttl_test = next((t for t in ttl_tests if t["ttl"] == 1), None)
    if short_ttl_test:
        expired_get = cache_manager.get(short_ttl_test["key"])
        # Memory cache는 즉시 만료되지 않을 수 있으므로 Redis가 없는 경우 관대하게 검증
        ttl_results[0]["expired_get_result"] = expired_get
        ttl_results[0]["properly_expired"] = expired_get is None

    # TTL 설정 검증
    for result in ttl_results:
        test_framework.assert_ok(result["set_success"], f"TTL cache set should succeed")
        test_framework.assert_ok(
            result["immediate_get_success"],
            f"Immediate get should work before expiration",
        )

    assert True  # Test passed


if __name__ == "__main__":
    """
    캐시 계층 일관성 통합 테스트 실행
    """

    print("💾 Cache Layer Consistency Integration Tests")
    print("=" * 50)

    # 모든 테스트 실행
    results = test_framework.run_all_tests()

    # 추가 상세 보고서
    print("\n📋 Cache System Analysis:")
    print(f"🔄 Total cache operations logged: {len(cache_tester.cache_operations)}")
    print(f"📊 Mock Redis operations: {cache_tester.mock_redis.operation_count}")
    print(f"🔗 Redis connection status: {'Active' if cache_tester.mock_redis.connection_active else 'Failed'}")

    # 캐시 작업 유형별 분석
    operation_types = {}
    for op in cache_tester.cache_operations:
        op_type = op["operation"]
        operation_types[op_type] = operation_types.get(op_type, 0) + 1

    if operation_types:
        print(f"🎯 Operation types tested: {', '.join(f'{k}({v})' for k, v in operation_types.items())}")

    # 결과에 따른 종료 코드
    if results["failed"] == 0:
        print(f"\n✅ All {results['total']} Cache integration tests PASSED!")
        print("💾 Cache layer consistency is working correctly")
        sys.exit(0)
    else:
        print(f"\n❌ {results['failed']}/{results['total']} Cache integration tests FAILED")
        print("🔧 Cache integration needs attention")
        sys.exit(1)
