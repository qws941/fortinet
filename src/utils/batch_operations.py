#!/usr/bin/env python3
"""
Batch Operations Utility
일괄 작업 처리 및 최적화
"""

import asyncio
import logging
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from config.constants import BATCH_SETTINGS
from utils.performance_optimizer import measure_time, profile

logger = logging.getLogger(__name__)


class BatchOperationType(Enum):
    """배치 작업 유형"""

    SEQUENTIAL = "sequential"
    PARALLEL_THREAD = "parallel_thread"
    PARALLEL_PROCESS = "parallel_process"
    ASYNC = "async"


@dataclass
class BatchItem:
    """배치 작업 항목"""

    id: str
    data: Any
    operation: Callable
    args: Optional[Tuple] = None
    kwargs: Optional[Dict] = None
    retry_count: int = 0
    max_retries: int = BATCH_SETTINGS["MAX_RETRIES"]


@dataclass
class BatchResult:
    """배치 작업 결과"""

    item_id: str
    success: bool
    result: Any
    error: Optional[Exception] = None
    execution_time: float = 0.0
    retry_count: int = 0


class BatchProcessor:
    """
    배치 작업 처리기
    대량의 작업을 효율적으로 처리
    """

    def __init__(
        self,
        max_workers: int = None,
        batch_size: int = None,
        operation_type: BatchOperationType = BatchOperationType.PARALLEL_THREAD,
    ):
        """
        초기화

        Args:
            max_workers: 최대 워커 수
            batch_size: 배치 크기
            operation_type: 작업 유형
        """
        self.max_workers = max_workers or BATCH_SETTINGS["MAX_WORKERS"]
        self.batch_size = batch_size or BATCH_SETTINGS["CHUNK_SIZE"]
        self.operation_type = operation_type
        self.results = []
        self.failed_items = []

    @profile
    @measure_time
    def process_batch(
        self,
        items: List[BatchItem],
        progress_callback: Optional[Callable] = None,
    ) -> List[BatchResult]:
        """
        배치 작업 처리

        Args:
            items: 처리할 항목 리스트
            progress_callback: 진행 상황 콜백

        Returns:
            list: BatchResult 리스트
        """
        start_time = time.time()
        total_items = len(items)

        logger.info(f"Starting batch processing: {total_items} items, type={self.operation_type.value}")

        # 작업 유형에 따라 처리
        if self.operation_type == BatchOperationType.SEQUENTIAL:
            results = self._process_sequential(items, progress_callback)
        elif self.operation_type == BatchOperationType.PARALLEL_THREAD:
            results = self._process_parallel_thread(items, progress_callback)
        elif self.operation_type == BatchOperationType.PARALLEL_PROCESS:
            results = self._process_parallel_process(items, progress_callback)
        elif self.operation_type == BatchOperationType.ASYNC:
            results = asyncio.run(self._process_async(items, progress_callback))
        else:
            raise ValueError(f"Unknown operation type: {self.operation_type}")

        # 결과 통계
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        elapsed_time = time.time() - start_time

        logger.info(
            f"Batch processing completed: {successful} successful, {failed} failed, " f"time={elapsed_time:.2f}s"
        )

        return results

    def _process_sequential(self, items: List[BatchItem], progress_callback: Optional[Callable]) -> List[BatchResult]:
        """순차적 처리"""
        results = []
        total = len(items)

        for idx, item in enumerate(items):
            result = self._execute_item(item)
            results.append(result)

            if progress_callback:
                progress_callback(idx + 1, total, result)

        return results

    def _process_parallel_thread(
        self, items: List[BatchItem], progress_callback: Optional[Callable]
    ) -> List[BatchResult]:
        """스레드 병렬 처리"""
        results = []
        total = len(items)
        completed = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 배치 단위로 작업 제출
            future_to_item = {}

            for i in range(0, len(items), self.batch_size):
                batch = items[i : i + self.batch_size]
                for item in batch:
                    future = executor.submit(self._execute_item, item)
                    future_to_item[future] = item

            # 결과 수집
            for future in as_completed(future_to_item):
                result = future.result()
                results.append(result)
                completed += 1

                if progress_callback:
                    progress_callback(completed, total, result)

        return results

    def _process_parallel_process(
        self, items: List[BatchItem], progress_callback: Optional[Callable]
    ) -> List[BatchResult]:
        """프로세스 병렬 처리"""
        results = []
        total = len(items)
        completed = 0

        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # 프로세스 풀에서는 함수만 전달 가능
            future_to_item = {}

            for item in items:
                # 프로세스에서 실행할 수 있는 형태로 변환
                future = executor.submit(
                    _execute_item_wrapper,
                    item.operation,
                    item.data,
                    item.args,
                    item.kwargs,
                )
                future_to_item[future] = item

            # 결과 수집
            for future in as_completed(future_to_item):
                item = future_to_item[future]
                try:
                    success, result_data, error, exec_time = future.result()
                    result = BatchResult(
                        item_id=item.id,
                        success=success,
                        result=result_data,
                        error=error,
                        execution_time=exec_time,
                        retry_count=item.retry_count,
                    )
                except Exception as e:
                    result = BatchResult(
                        item_id=item.id,
                        success=False,
                        result=None,
                        error=e,
                        retry_count=item.retry_count,
                    )

                results.append(result)
                completed += 1

                if progress_callback:
                    progress_callback(completed, total, result)

        return results

    async def _process_async(self, items: List[BatchItem], progress_callback: Optional[Callable]) -> List[BatchResult]:
        """비동기 처리"""
        results = []
        total = len(items)

        # 배치 단위로 처리
        for i in range(0, len(items), self.batch_size):
            batch = items[i : i + self.batch_size]

            # 비동기 작업 생성
            tasks = []
            for item in batch:
                task = self._execute_item_async(item)
                tasks.append(task)

            # 배치 실행
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # 결과 처리
            for idx, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    result = BatchResult(
                        item_id=batch[idx].id,
                        success=False,
                        result=None,
                        error=result,
                        retry_count=batch[idx].retry_count,
                    )
                results.append(result)

                if progress_callback:
                    progress_callback(i + idx + 1, total, result)

        return results

    def _execute_item(self, item: BatchItem) -> BatchResult:
        """
        단일 항목 실행

        Args:
            item: 실행할 항목

        Returns:
            BatchResult: 실행 결과
        """
        start_time = time.time()

        try:
            # 함수 실행
            args = item.args or ()
            kwargs = item.kwargs or {}
            result = item.operation(item.data, *args, **kwargs)

            execution_time = time.time() - start_time

            return BatchResult(
                item_id=item.id,
                success=True,
                result=result,
                execution_time=execution_time,
                retry_count=item.retry_count,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Error executing item {item.id}: {e}")

            # 재시도 로직
            if item.retry_count < item.max_retries:
                item.retry_count += 1
                logger.info(f"Retrying item {item.id} (attempt {item.retry_count}/{item.max_retries})")
                time.sleep(2**item.retry_count)  # Exponential backoff
                return self._execute_item(item)

            return BatchResult(
                item_id=item.id,
                success=False,
                result=None,
                error=e,
                execution_time=execution_time,
                retry_count=item.retry_count,
            )

    async def _execute_item_async(self, item: BatchItem) -> BatchResult:
        """
        비동기 단일 항목 실행

        Args:
            item: 실행할 항목

        Returns:
            BatchResult: 실행 결과
        """
        start_time = time.time()

        try:
            # 함수가 코루틴인지 확인
            args = item.args or ()
            kwargs = item.kwargs or {}

            if asyncio.iscoroutinefunction(item.operation):
                result = await item.operation(item.data, *args, **kwargs)
            else:
                # 동기 함수를 비동기로 실행
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, item.operation, item.data, *args)

            execution_time = time.time() - start_time

            return BatchResult(
                item_id=item.id,
                success=True,
                result=result,
                execution_time=execution_time,
                retry_count=item.retry_count,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Error executing async item {item.id}: {e}")

            return BatchResult(
                item_id=item.id,
                success=False,
                result=None,
                error=e,
                execution_time=execution_time,
                retry_count=item.retry_count,
            )


def _execute_item_wrapper(
    operation: Callable,
    data: Any,
    args: Optional[Tuple],
    kwargs: Optional[Dict],
) -> Tuple[bool, Any, Optional[Exception], float]:
    """
    프로세스 풀에서 실행할 래퍼 함수

    Returns:
        tuple: (success, result, error, execution_time)
    """
    start_time = time.time()

    try:
        args = args or ()
        kwargs = kwargs or {}
        result = operation(data, *args, **kwargs)
        execution_time = time.time() - start_time
        return True, result, None, execution_time

    except Exception as e:
        execution_time = time.time() - start_time
        return False, None, e, execution_time


# API 일괄 작업 헬퍼
class APIBatchProcessor:
    """
    API 호출 전용 배치 프로세서
    """

    def __init__(self, api_client, max_concurrent: int = 10):
        """
        초기화

        Args:
            api_client: API 클라이언트 인스턴스
            max_concurrent: 최대 동시 요청 수
        """
        self.api_client = api_client
        self.max_concurrent = max_concurrent
        self.processor = BatchProcessor(
            max_workers=max_concurrent,
            operation_type=BatchOperationType.PARALLEL_THREAD,
        )

    def batch_get_devices(self, device_ids: List[str]) -> Dict[str, Any]:
        """
        여러 장치 정보 일괄 조회

        Args:
            device_ids: 장치 ID 리스트

        Returns:
            dict: {device_id: device_info}
        """
        # 배치 항목 생성
        items = [
            BatchItem(
                id=device_id,
                data=device_id,
                operation=self.api_client.get_device,
            )
            for device_id in device_ids
        ]

        # 처리
        results = self.processor.process_batch(items)

        # 결과 매핑
        device_map = {}
        for result in results:
            if result.success:
                device_map[result.item_id] = result.result
            else:
                logger.error(f"Failed to get device {result.item_id}: {result.error}")

        return device_map

    def batch_update_policies(self, policy_updates: List[Dict[str, Any]]) -> List[BatchResult]:
        """
        여러 정책 일괄 업데이트

        Args:
            policy_updates: 정책 업데이트 정보 리스트

        Returns:
            list: BatchResult 리스트
        """
        # 배치 항목 생성
        items = [
            BatchItem(
                id=update["policy_id"],
                data=update,
                operation=self.api_client.update_policy,
                kwargs={"data": update["data"]},
            )
            for update in policy_updates
        ]

        # 처리
        return self.processor.process_batch(items)

    async def batch_monitor_devices(self, device_ids: List[str], metrics: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        여러 장치 모니터링 데이터 일괄 수집

        Args:
            device_ids: 장치 ID 리스트
            metrics: 수집할 메트릭 리스트

        Returns:
            dict: {device_id: {metric: value}}
        """
        # 비동기 배치 프로세서 사용
        async_processor = BatchProcessor(
            max_workers=self.max_concurrent,
            operation_type=BatchOperationType.ASYNC,
        )

        # 배치 항목 생성
        items = []
        for device_id in device_ids:
            for metric in metrics:
                items.append(
                    BatchItem(
                        id=f"{device_id}_{metric}",
                        data={"device_id": device_id, "metric": metric},
                        operation=self._get_device_metric_async,
                    )
                )

        # 처리
        results = await async_processor._process_async(items, None)

        # 결과 정리
        device_metrics = {}
        for result in results:
            if result.success:
                device_id, metric = result.item_id.split("_", 1)
                if device_id not in device_metrics:
                    device_metrics[device_id] = {}
                device_metrics[device_id][metric] = result.result

        return device_metrics

    async def _get_device_metric_async(self, data: Dict[str, Any]) -> Any:
        """비동기 메트릭 수집"""
        # 실제 구현은 API 클라이언트에 따라 다름
        device_id = data["device_id"]
        metric = data["metric"]

        # 시뮬레이션
        await asyncio.sleep(0.1)
        return f"{metric}_value_for_{device_id}"
