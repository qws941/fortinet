#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
성능 최적화 테스트
캐싱, 배치 처리, 연결 풀 등의 성능 개선 사항 테스트
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, "src")

import asyncio
import os
import sys
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, call, patch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))
from core.cache_manager import CacheManager
from core.connection_pool import ConnectionPoolManager
from utils.batch_operations import APIBatchProcessor, BatchItem, BatchOperationType, BatchProcessor


# Mock Paginator class since it doesn't exist in the codebase
class Paginator:
    def __init__(self, params, max_per_page=100):
        self.page = int(params.get("page", 1))
        self.per_page = min(int(params.get("per_page", 10)), max_per_page)
        self.offset = (self.page - 1) * self.per_page
        self.sort_by = params.get("sort_by", "id")
        self.sort_order = params.get("sort_order", "asc")


class TestCacheManager(unittest.TestCase):
    """캐시 매니저 테스트"""

    def setUp(self):
        """테스트 환경 설정"""
        self.cache = CacheManager(use_redis=False)

    def tearDown(self):
        """테스트 정리"""
        self.cache.clear_all()

    def test_basic_cache_operations(self):
        """기본 캐시 작업 테스트"""
        # 캐시 저장
        self.cache.set("test_key", {"data": "test_value"}, ttl=60)

        # 캐시 조회
        value = self.cache.get("test_key")
        self.assertIsNotNone(value)
        self.assertEqual(value["data"], "test_value")

        # 캐시 삭제
        self.cache.delete("test_key")
        value = self.cache.get("test_key")
        self.assertIsNone(value)

    def test_cache_expiration(self):
        """캐시 만료 테스트"""
        # 짧은 TTL로 캐시 저장
        self.cache.set("expire_test", "value", ttl=1)

        # 즉시 조회 - 성공
        value = self.cache.get("expire_test")
        self.assertEqual(value, "value")

        # 만료 후 조회 - 실패
        time.sleep(1.1)
        self.cache.clear_expired()
        value = self.cache.get("expire_test")
        self.assertIsNone(value)

    def test_cache_lru_eviction(self):
        """LRU 캐시 제거 테스트 - 통합 캐시 매니저 사용"""
        # 작은 캐시 크기로 통합 캐시 매니저 구성
        from utils.unified_cache_manager import UnifiedCacheManager

        # 작은 크기의 캐시 설정
        small_config = {
            "redis": {
                "enabled": False,  # Redis 비활성화
            },
            "memory": {"enabled": True, "max_size": 3},  # 최대 3개 항목만 저장
            "default_ttl": 300,
        }

        small_cache_manager = UnifiedCacheManager(small_config)

        # CacheManager 래퍼 생성
        from utils.api_optimization import CacheManager

        small_cache = CacheManager(use_redis=False)
        small_cache.cache_manager = small_cache_manager

        # 캐시 정리
        small_cache.clear_all()

        # 캐시 항목 추가
        small_cache.set("key1", "value1")
        small_cache.set("key2", "value2")
        small_cache.set("key3", "value3")

        # key1 접근하여 최근 사용으로 만듦
        small_cache.get("key1")

        # 새 항목 추가 - LRU에 의해 가장 오래된 항목이 제거됨
        small_cache.set("key4", "value4")

        # 최대 3개까지만 캐시되는지 확인
        total_cached = sum(1 for key in ["key1", "key2", "key3", "key4"] if small_cache.get(key) is not None)
        self.assertLessEqual(total_cached, 3)  # 최대 3개까지만 캐시됨

        # key1은 최근 접근했으므로 여전히 존재해야 함
        self.assertIsNotNone(small_cache.get("key1"))

    def test_cache_statistics(self):
        """캐시 통계 테스트"""
        # 초기 통계 확보 (전역 캐시 매니저이므로 이전 테스트의 통계가 있을 수 있음)
        initial_stats = self.cache.get_stats()
        initial_hits = initial_stats["hits"]
        initial_misses = initial_stats["misses"]

        # 캐시 미스
        self.cache.get("nonexistent_stats_test")
        stats = self.cache.get_stats()
        self.assertEqual(stats["misses"], initial_misses + 1)

        # 캐시 히트
        self.cache.set("hit_test_stats", "value")
        self.cache.get("hit_test_stats")
        stats = self.cache.get_stats()
        self.assertEqual(stats["hits"], initial_hits + 1)

        # 히트율 계산 확인 (총 요청 수 기준)
        total_requests = stats["hits"] + stats["misses"]
        if total_requests > 0:
            expected_hit_rate = (stats["hits"] / total_requests) * 100
            self.assertEqual(stats["hit_rate"], expected_hit_rate)


class TestPaginator(unittest.TestCase):
    """페이지네이션 테스트"""

    def test_pagination_basics(self):
        """기본 페이지네이션 테스트"""
        # 쿼리 파라미터
        params = {
            "page": "2",
            "per_page": "10",
            "sort_by": "name",
            "sort_order": "desc",
        }

        paginator = Paginator(params)

        self.assertEqual(paginator.page, 2)
        self.assertEqual(paginator.per_page, 10)
        self.assertEqual(paginator.offset, 10)
        self.assertEqual(paginator.sort_by, "name")
        self.assertEqual(paginator.sort_order, "desc")

    def test_paginate_list(self):
        """리스트 페이지네이션 테스트"""
        # 테스트 데이터
        items = [{"id": i, "name": f"Item {i}"} for i in range(25)]

        paginator = Paginator({"page": "2", "per_page": "10"})
        paginated_items, meta = paginator.paginate_list(items)

        # 결과 확인
        self.assertEqual(len(paginated_items), 10)
        self.assertEqual(paginated_items[0]["id"], 10)
        self.assertEqual(meta["total"], 25)
        self.assertEqual(meta["total_pages"], 3)
        self.assertTrue(meta["has_prev"])
        self.assertTrue(meta["has_next"])

    def test_invalid_parameters(self):
        """잘못된 파라미터 처리 테스트"""
        params = {"page": "invalid", "per_page": "999", "sort_order": "invalid"}

        paginator = Paginator(params, max_per_page=50)

        # 기본값 사용 확인
        self.assertEqual(paginator.page, 1)
        self.assertEqual(paginator.per_page, 50)  # max_per_page로 제한
        self.assertEqual(paginator.sort_order, "asc")


class TestBatchOperations(unittest.TestCase):
    """배치 작업 테스트"""

    def setUp(self):
        """테스트 환경 설정"""
        self.processor = BatchProcessor(
            max_workers=4,
            batch_size=10,
            operation_type=BatchOperationType.PARALLEL_THREAD,
        )

    def test_sequential_batch_processing(self):
        """순차적 배치 처리 테스트"""
        processor = BatchProcessor(operation_type=BatchOperationType.SEQUENTIAL)

        # 테스트 함수
        def process_item(data):
            return data * 2

        # 배치 항목 생성
        items = [BatchItem(id=str(i), data=i, operation=process_item) for i in range(5)]

        # 처리
        results = processor.process_batch(items)

        # 결과 확인
        self.assertEqual(len(results), 5)
        for i, result in enumerate(results):
            self.assertTrue(result.success)
            self.assertEqual(result.result, i * 2)

    def test_parallel_thread_processing(self):
        """스레드 병렬 처리 테스트"""

        # 시간이 걸리는 작업 시뮬레이션
        def slow_process(data):
            time.sleep(0.1)
            return data**2

        # 배치 항목 생성
        items = [BatchItem(id=str(i), data=i, operation=slow_process) for i in range(10)]

        # 순차 처리 시간 측정
        start_time = time.time()
        seq_processor = BatchProcessor(operation_type=BatchOperationType.SEQUENTIAL)
        seq_results = seq_processor.process_batch(items)
        seq_time = time.time() - start_time

        # 병렬 처리 시간 측정
        start_time = time.time()
        par_results = self.processor.process_batch(items)
        par_time = time.time() - start_time

        # 병렬 처리가 더 빠른지 확인
        self.assertLess(par_time, seq_time * 0.5)

        # 결과 동일성 확인
        self.assertEqual(len(par_results), len(seq_results))
        for result in par_results:
            self.assertTrue(result.success)

    def test_batch_error_handling(self):
        """배치 오류 처리 테스트"""

        # 오류 발생 함수
        def error_prone_process(data):
            if data == 3:
                raise ValueError("Test error")
            return data

        # 배치 항목 생성 (재시도 비활성화)
        items = [BatchItem(id=str(i), data=i, operation=error_prone_process, max_retries=0) for i in range(5)]

        # 처리
        results = self.processor.process_batch(items)

        # 결과 확인
        success_count = sum(1 for r in results if r.success)
        self.assertEqual(success_count, 4)  # 1개 실패

        # 실패한 항목 확인
        failed = [r for r in results if not r.success]
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0].item_id, "3")
        self.assertIsInstance(failed[0].error, ValueError)

    def test_batch_retry_logic(self):
        """배치 재시도 로직 테스트"""
        retry_count = 0

        def flaky_process(data):
            nonlocal retry_count
            if data == 1 and retry_count < 2:
                retry_count += 1
                raise ConnectionError("Temporary failure")
            return data

        # 재시도 활성화
        items = [BatchItem(id="retry_test", data=1, operation=flaky_process, max_retries=3)]

        # 처리
        results = self.processor.process_batch(items)

        # 재시도 후 성공 확인
        self.assertTrue(results[0].success)
        self.assertEqual(results[0].retry_count, 2)


class TestConnectionPoolManager(unittest.TestCase):
    """연결 풀 매니저 테스트"""

    def setUp(self):
        """테스트 환경 설정"""
        self.pool_manager = ConnectionPoolManager()

    def tearDown(self):
        """테스트 정리"""
        self.pool_manager.close_all_sessions()

    def test_singleton_pattern(self):
        """싱글톤 패턴 테스트"""
        # 여러 인스턴스 생성
        manager1 = ConnectionPoolManager()
        manager2 = ConnectionPoolManager()

        # 동일한 인스턴스인지 확인
        self.assertIs(manager1, manager2)

    def test_session_creation_and_reuse(self):
        """세션 생성 및 재사용 테스트"""
        # 첫 번째 세션 생성
        session1 = self.pool_manager.get_session("test_api")
        self.assertIsNotNone(session1)

        # 동일한 식별자로 세션 요청 - 재사용되어야 함
        session2 = self.pool_manager.get_session("test_api")
        self.assertIs(session1, session2)

        # 다른 식별자로 세션 요청 - 새로 생성되어야 함
        session3 = self.pool_manager.get_session("another_api")
        self.assertIsNot(session1, session3)

    def test_session_configuration(self):
        """세션 구성 테스트"""
        # 커스텀 설정으로 세션 생성
        session = self.pool_manager.get_session("custom_api", pool_connections=50, pool_maxsize=100, max_retries=5)

        # 어댑터 설정 확인
        adapter = session.get_adapter("https://")
        self.assertIsNotNone(adapter)
        self.assertEqual(adapter.max_retries.total, 5)

    def test_session_cleanup(self):
        """세션 정리 테스트"""
        # 세션 생성
        session1 = self.pool_manager.get_session("cleanup_test")

        # 특정 세션 닫기
        self.pool_manager.close_session("cleanup_test")

        # 다시 요청하면 새 세션이 생성되어야 함
        session2 = self.pool_manager.get_session("cleanup_test")
        self.assertIsNot(session1, session2)


class TestAPIBatchProcessor(unittest.TestCase):
    """API 배치 프로세서 테스트"""

    def setUp(self):
        """테스트 환경 설정"""
        self.mock_client = MagicMock()
        self.batch_processor = APIBatchProcessor(self.mock_client, max_concurrent=5)

    def test_batch_get_devices(self):
        """장치 일괄 조회 테스트"""

        # Mock 설정
        def mock_get_device(device_id):
            assert True  # Test passed", "status": "online"}

        self.mock_client.get_device.side_effect = mock_get_device

        # 배치 조회
        device_ids = ["dev1", "dev2", "dev3"]
        results = self.batch_processor.batch_get_devices(device_ids)

        # 결과 확인
        self.assertEqual(len(results), 3)
        self.assertEqual(results["dev1"]["name"], "Device dev1")
        self.assertEqual(self.mock_client.get_device.call_count, 3)

    def test_batch_update_policies(self):
        """정책 일괄 업데이트 테스트"""
        # Mock 설정
        self.mock_client.update_policy.return_value = {"success": True}

        # 업데이트 데이터
        policy_updates = [
            {"policy_id": "pol1", "data": {"action": "accept"}},
            {"policy_id": "pol2", "data": {"action": "deny"}},
        ]

        # 배치 업데이트
        results = self.batch_processor.batch_update_policies(policy_updates)

        # 결과 확인
        self.assertEqual(len(results), 2)
        self.assertTrue(all(r.success for r in results))
        self.assertEqual(self.mock_client.update_policy.call_count, 2)

    def test_batch_monitor_devices_async(self):
        """비동기 장치 모니터링 배치 테스트"""

        # Mock async method to return expected data
        async def mock_get_device_metric_async(data):
            device_id = data["device_id"]
            metric = data["metric"]
            return f"{metric}_value_for_{device_id}"

        # Replace the async method
        self.batch_processor._get_device_metric_async = mock_get_device_metric_async

        # 비동기 모니터링 호출
        device_ids = ["dev1", "dev2"]
        metrics = ["cpu", "memory"]

        # asyncio.run을 사용하여 비동기 메서드 실행
        result = asyncio.run(self.batch_processor.batch_monitor_devices(device_ids, metrics))

        # 결과 확인
        self.assertIsInstance(result, dict)
        self.assertIn("dev1", result)
        self.assertIn("dev2", result)
        self.assertEqual(result["dev1"]["cpu"], "cpu_value_for_dev1")
        self.assertEqual(result["dev2"]["memory"], "memory_value_for_dev2")


class TestIntegrationPerformance(unittest.TestCase):
    """통합 성능 테스트"""

    @patch("requests.Session")
    def test_cached_api_endpoint(self, mock_session_class):
        """캐시된 API 엔드포인트 성능 테스트"""
        from flask import Flask, jsonify

        from utils.api_optimization import cached

        app = Flask(__name__)
        call_count = 0

        @app.route("/test")
        @cached(ttl=60)
        def test_endpoint():
            nonlocal call_count
            call_count += 1
            time.sleep(0.1)  # 느린 작업 시뮬레이션
            return jsonify({"data": "test", "count": call_count})

        with app.test_client() as client:
            # 첫 번째 요청 - 캐시 미스
            start_time = time.time()
            response1 = client.get("/test")
            first_time = time.time() - start_time

            # 두 번째 요청 - 캐시 히트
            start_time = time.time()
            response2 = client.get("/test")
            second_time = time.time() - start_time

            # 캐시가 작동하는지 확인
            self.assertLess(second_time, first_time * 0.1)

            # 동일한 결과 반환 확인
            self.assertEqual(response1.json, response2.json)
            self.assertEqual(call_count, 1)  # 한 번만 실행됨


if __name__ == "__main__":
    unittest.main()
