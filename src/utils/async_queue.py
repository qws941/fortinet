#!/usr/bin/env python3
"""
비동기 큐 처리 최적화
대용량 데이터 처리를 위한 고성능 비동기 큐 시스템
"""

import asyncio
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class QueuePriority(Enum):
    """큐 우선순위"""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class QueueItem:
    """큐 아이템"""

    data: Any
    callback: Optional[Callable] = None
    priority: QueuePriority = QueuePriority.NORMAL
    retry_count: int = 0
    max_retries: int = 3
    created_at: float = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()


class AsyncQueue:
    """비동기 고성능 큐"""

    def __init__(self, max_size: int = 10000, worker_count: int = 10):
        self.max_size = max_size
        self.worker_count = worker_count

        # 우선순위별 큐
        self.queues = {
            QueuePriority.CRITICAL: deque(),
            QueuePriority.HIGH: deque(),
            QueuePriority.NORMAL: deque(),
            QueuePriority.LOW: deque(),
        }

        self._queue_lock = asyncio.Lock()
        self._workers = []
        self._running = False
        self._stats = {"processed": 0, "failed": 0, "pending": 0}

        # 성능 모니터링
        self._processing_times = deque(maxlen=1000)
        self._last_cleanup = time.time()

    async def start(self):
        """큐 처리 시작"""
        if self._running:
            return

        self._running = True

        # 워커 스레드 시작
        for i in range(self.worker_count):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self._workers.append(worker)

        logger.info(f"AsyncQueue started with {self.worker_count} workers")

    async def stop(self):
        """큐 처리 중단"""
        if not self._running:
            return

        self._running = False

        # 모든 워커 중단 대기
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)

        self._workers.clear()
        logger.info("AsyncQueue stopped")

    async def put(self, item: QueueItem) -> bool:
        """큐에 아이템 추가"""
        async with self._queue_lock:
            current_size = sum(len(q) for q in self.queues.values())

            if current_size >= self.max_size:
                # 큐가 가득 찬 경우 오래된 낮은 우선순위 아이템 제거
                if self.queues[QueuePriority.LOW]:
                    self.queues[QueuePriority.LOW].popleft()
                elif self.queues[QueuePriority.NORMAL]:
                    self.queues[QueuePriority.NORMAL].popleft()
                else:
                    logger.warning("Queue is full, dropping item")
                    return False

            self.queues[item.priority].append(item)
            self._stats["pending"] += 1

            return True

    async def get(self) -> Optional[QueueItem]:
        """큐에서 아이템 가져오기 (우선순위 순)"""
        async with self._queue_lock:
            # 우선순위 순으로 확인
            for priority in [
                QueuePriority.CRITICAL,
                QueuePriority.HIGH,
                QueuePriority.NORMAL,
                QueuePriority.LOW,
            ]:
                if self.queues[priority]:
                    item = self.queues[priority].popleft()
                    self._stats["pending"] -= 1
                    return item

            return None

    async def _worker(self, worker_name: str):
        """워커 루프"""
        logger.debug(f"Worker {worker_name} started")

        while self._running:
            try:
                item = await self.get()

                if item is None:
                    # 큐가 비어있으면 잠시 대기
                    await asyncio.sleep(0.1)
                    continue

                # 아이템 처리
                await self._process_item(item, worker_name)

                # 주기적 정리
                if time.time() - self._last_cleanup > 300:  # 5분마다
                    await self._cleanup()
                    self._last_cleanup = time.time()

            except Exception as e:
                logger.error(f"Worker {worker_name} error: {e}")
                await asyncio.sleep(1)

        logger.debug(f"Worker {worker_name} stopped")

    async def _process_item(self, item: QueueItem, worker_name: str):
        """아이템 처리"""
        start_time = time.time()

        try:
            if item.callback:
                if asyncio.iscoroutinefunction(item.callback):
                    await item.callback(item.data)
                else:
                    # 동기 함수를 비동기로 실행
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, item.callback, item.data)

            self._stats["processed"] += 1

            # 처리 시간 기록
            processing_time = time.time() - start_time
            self._processing_times.append(processing_time)

            logger.debug(f"Worker {worker_name} processed item in {processing_time:.3f}s")

        except Exception as e:
            logger.error(f"Error processing item in {worker_name}: {e}")

            # 재시도 로직
            if item.retry_count < item.max_retries:
                item.retry_count += 1
                # 지수 백오프로 재시도
                await asyncio.sleep(2**item.retry_count)
                await self.put(item)
                logger.info(f"Retrying item (attempt {item.retry_count}/{item.max_retries})")
            else:
                self._stats["failed"] += 1
                logger.error(f"Item failed after {item.max_retries} retries")

    async def _cleanup(self):
        """주기적 정리 작업"""
        # 통계 정리
        if len(self._processing_times) > 500:
            # 오래된 처리 시간 기록 정리
            for _ in range(250):
                if self._processing_times:
                    self._processing_times.popleft()

        logger.debug("Queue cleanup completed")

    def get_stats(self) -> Dict[str, Any]:
        """큐 통계 반환"""
        current_size = sum(len(q) for q in self.queues.values())

        avg_processing_time = 0
        if self._processing_times:
            avg_processing_time = sum(self._processing_times) / len(self._processing_times)

        return {
            "current_size": current_size,
            "max_size": self.max_size,
            "processed": self._stats["processed"],
            "failed": self._stats["failed"],
            "pending": self._stats["pending"],
            "worker_count": self.worker_count,
            "avg_processing_time": avg_processing_time,
            "queue_by_priority": {priority.name: len(queue) for priority, queue in self.queues.items()},
        }

    async def drain(self) -> int:
        """큐 비우기 (모든 아이템 처리 대기)"""
        drained_count = 0

        while True:
            current_size = sum(len(q) for q in self.queues.values())
            if current_size == 0:
                break

            await asyncio.sleep(0.1)
            drained_count += 1

            # 무한 대기 방지
            if drained_count > 600:  # 1분 대기
                logger.warning("Queue drain timeout")
                break

        return drained_count


class BatchQueueProcessor:
    """배치 큐 처리기"""

    def __init__(self, batch_size: int = 100, flush_interval: float = 1.0):
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.batch = []
        self.last_flush = time.time()
        self._lock = asyncio.Lock()
        self._processor_callback = None

    def set_processor(self, callback: Callable):
        """배치 처리 콜백 설정"""
        self._processor_callback = callback

    async def add_item(self, item: Any):
        """배치에 아이템 추가"""
        async with self._lock:
            self.batch.append(item)

            # 배치 크기에 도달하거나 시간이 경과한 경우 플러시
            should_flush = len(self.batch) >= self.batch_size or time.time() - self.last_flush >= self.flush_interval

            if should_flush:
                await self._flush_batch()

    async def _flush_batch(self):
        """배치 플러시"""
        if not self.batch or not self._processor_callback:
            return

        batch_to_process = self.batch[:]
        self.batch.clear()
        self.last_flush = time.time()

        try:
            if asyncio.iscoroutinefunction(self._processor_callback):
                await self._processor_callback(batch_to_process)
            else:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._processor_callback, batch_to_process)

            logger.debug(f"Processed batch of {len(batch_to_process)} items")

        except Exception as e:
            logger.error(f"Error processing batch: {e}")

    async def force_flush(self):
        """강제 배치 플러시"""
        async with self._lock:
            await self._flush_batch()


# 전역 큐 관리자
class QueueManager:
    """전역 큐 관리자"""

    def __init__(self):
        self._queues = {}
        self._lock = threading.Lock()

    def get_queue(self, name: str, **kwargs) -> AsyncQueue:
        """큐 가져오기 또는 생성"""
        with self._lock:
            if name not in self._queues:
                self._queues[name] = AsyncQueue(**kwargs)
            return self._queues[name]

    def remove_queue(self, name: str):
        """큐 제거"""
        with self._lock:
            if name in self._queues:
                queue = self._queues.pop(name)
                # 큐 정리 (비동기 작업이므로 별도 처리 필요)
                return queue

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """모든 큐 통계"""
        with self._lock:
            return {name: queue.get_stats() for name, queue in self._queues.items()}


# 전역 큐 매니저 인스턴스
queue_manager = QueueManager()


# 편의 함수들
async def create_queue(name: str, max_size: int = 10000, worker_count: int = 10) -> AsyncQueue:
    """큐 생성 및 시작"""
    queue = queue_manager.get_queue(name, max_size=max_size, worker_count=worker_count)
    await queue.start()
    return queue


async def add_to_queue(
    queue_name: str,
    data: Any,
    callback: Optional[Callable] = None,
    priority: QueuePriority = QueuePriority.NORMAL,
) -> bool:
    """큐에 아이템 추가"""
    queue = queue_manager.get_queue(queue_name)

    if not queue._running:
        await queue.start()

    item = QueueItem(data=data, callback=callback, priority=priority)
    return await queue.put(item)
