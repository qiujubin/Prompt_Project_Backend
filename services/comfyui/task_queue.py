"""
ComfyUI Task Queue Management

Provides optimized task queue management with priority support,
task tracking, and automatic cleanup.

Performance Optimizations:
- Priority-based task scheduling
- Efficient task lookup with indexing
- Automatic timeout handling
- Memory-efficient cleanup of completed tasks
- Metrics collection for monitoring
"""
import asyncio
import time
import uuid
from typing import Dict, Any, Optional, List, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
from heapq import heappush, heappop
import threading

from core.comfyui_config import get_comfyui_settings
from core.logger import get_logger

logger = get_logger(__name__)


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class TaskPriority(Enum):
    """任务优先级枚举"""
    LOW = 3
    NORMAL = 2
    HIGH = 1
    URGENT = 0


@dataclass
class TaskInfo:
    """任务信息"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    prompt_id: Optional[str] = None
    user_id: Optional[int] = None
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    params: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3
    callbacks: List[Callable] = field(default_factory=list)

    def __lt__(self, other):
        """用于优先级队列比较"""
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return self.created_at < other.created_at


class TaskQueue:
    """优化的任务队列

    特性：
    - 优先级支持
    - 任务超时处理
    - 自动重试
    - 任务状态追踪
    - 回调通知
    """

    def __init__(self, max_size: int = None):
        self.settings = get_comfyui_settings()
        self.max_size = max_size or self.settings.max_queue_size

        self._queue: List[TaskInfo] = []  # 优先级队列
        self._tasks: Dict[str, TaskInfo] = {}  # 任务索引
        self._lock = asyncio.Lock()
        self._not_empty = asyncio.Condition()
        self._running = False
        self._cleanup_task: Optional[asyncio.Task] = None
        self._timeout_task: Optional[asyncio.Task] = None

    async def start(self):
        """启动任务队列"""
        if self._running:
            return

        self._running = True
        logger.info("Task queue started")

        # 启动清理任务
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        # 启动超时检查任务
        self._timeout_task = asyncio.create_task(self._timeout_check_loop())

    async def stop(self):
        """停止任务队列"""
        self._running = False

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        if self._timeout_task:
            self._timeout_task.cancel()
            try:
                await self._timeout_task
            except asyncio.CancelledError:
                pass

        logger.info("Task queue stopped")

    async def enqueue(
        self,
        params: Dict[str, Any],
        user_id: int = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        callbacks: List[Callable] = None
    ) -> TaskInfo:
        """添加任务到队列

        Args:
            params: 任务参数
            user_id: 用户 ID
            priority: 任务优先级
            callbacks: 任务完成回调函数列表

        Returns:
            TaskInfo: 创建的任务信息

        Raises:
            RuntimeError: 队列已满
        """
        async with self._lock:
            if len(self._queue) >= self.max_size:
                raise RuntimeError(f"Task queue is full (max: {self.max_size})")

            task = TaskInfo(
                user_id=user_id,
                priority=priority,
                params=params,
                callbacks=callbacks or [],
                max_retries=self.settings.max_retry_attempts
            )

            heappush(self._queue, task)
            self._tasks[task.id] = task

            logger.info(f"Task {task.id} enqueued with priority {priority.name}")

        # 通知等待的消费者
        async with self._not_empty:
            self._not_empty.notify()

        return task

    async def dequeue(self, timeout: float = None) -> Optional[TaskInfo]:
        """从队列获取任务

        Args:
            timeout: 等待超时时间

        Returns:
            TaskInfo: 获取的任务，如果超时返回 None
        """
        async with self._not_empty:
            while not self._queue and self._running:
                try:
                    await asyncio.wait_for(
                        self._not_empty.wait(),
                        timeout=timeout or 1.0
                    )
                except asyncio.TimeoutError:
                    if timeout:
                        return None
                    continue

            if not self._queue:
                return None

            async with self._lock:
                task = heappop(self._queue)
                task.status = TaskStatus.RUNNING
                task.started_at = time.time()

                logger.debug(f"Task {task.id} dequeued")
                return task

    async def complete_task(
        self,
        task_id: str,
        result: Dict[str, Any] = None,
        error: str = None
    ):
        """完成任务

        Args:
            task_id: 任务 ID
            result: 任务结果
            error: 错误信息（如果失败）
        """
        async with self._lock:
            if task_id not in self._tasks:
                logger.warning(f"Task {task_id} not found")
                return

            task = self._tasks[task_id]
            task.completed_at = time.time()

            if error:
                task.status = TaskStatus.FAILED
                task.error = error
                logger.warning(f"Task {task_id} failed: {error}")
            else:
                task.status = TaskStatus.COMPLETED
                task.result = result
                logger.info(f"Task {task_id} completed")

            # 执行回调
            await self._execute_callbacks(task)

    async def retry_task(self, task_id: str) -> bool:
        """重试任务

        Args:
            task_id: 任务 ID

        Returns:
            bool: 是否成功加入重试队列
        """
        async with self._lock:
            if task_id not in self._tasks:
                return False

            task = self._tasks[task_id]

            if task.retry_count >= task.max_retries:
                logger.warning(f"Task {task_id} exceeded max retries ({task.max_retries})")
                task.status = TaskStatus.FAILED
                task.error = f"Exceeded max retries ({task.max_retries})"
                await self._execute_callbacks(task)
                return False

            task.retry_count += 1
            task.status = TaskStatus.PENDING
            task.started_at = None
            task.error = None

            heappush(self._queue, task)
            logger.info(f"Task {task_id} queued for retry (attempt {task.retry_count})")

        async with self._not_empty:
            self._not_empty.notify()

        return True

    async def cancel_task(self, task_id: str) -> bool:
        """取消任务

        Args:
            task_id: 任务 ID

        Returns:
            bool: 是否成功取消
        """
        async with self._lock:
            if task_id not in self._tasks:
                return False

            task = self._tasks[task_id]

            if task.status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
                return False

            task.status = TaskStatus.CANCELLED
            task.completed_at = time.time()

            # 从队列中移除（如果还在队列中）
            self._queue = [t for t in self._queue if t.id != task_id]

            logger.info(f"Task {task_id} cancelled")
            await self._execute_callbacks(task)

            return True

    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """获取任务信息"""
        return self._tasks.get(task_id)

    def get_task_by_prompt_id(self, prompt_id: str) -> Optional[TaskInfo]:
        """通过 prompt_id 获取任务"""
        for task in self._tasks.values():
            if task.prompt_id == prompt_id:
                return task
        return None

    def update_prompt_id(self, task_id: str, prompt_id: str):
        """更新任务的 prompt_id"""
        if task_id in self._tasks:
            self._tasks[task_id].prompt_id = prompt_id

    async def _execute_callbacks(self, task: TaskInfo):
        """执行任务回调"""
        for callback in task.callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(task)
                else:
                    callback(task)
            except Exception as e:
                logger.error(f"Error executing callback for task {task.id}: {e}")

    async def _cleanup_loop(self):
        """清理已完成任务的循环"""
        while self._running:
            try:
                await asyncio.sleep(self.settings.cleanup_interval)
                await self._cleanup_completed_tasks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup error: {e}")

    async def _cleanup_completed_tasks(self, max_age: int = 3600):
        """清理已完成的任务"""
        current_time = time.time()
        to_remove = []

        async with self._lock:
            for task_id, task in self._tasks.items():
                if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED, TaskStatus.TIMEOUT]:
                    if task.completed_at and current_time - task.completed_at > max_age:
                        to_remove.append(task_id)

            for task_id in to_remove:
                del self._tasks[task_id]

        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} completed tasks")

    async def _timeout_check_loop(self):
        """超时检查循环"""
        while self._running:
            try:
                await asyncio.sleep(30)  # 每 30 秒检查一次
                await self._check_timeouts()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Timeout check error: {e}")

    async def _check_timeouts(self):
        """检查超时任务"""
        current_time = time.time()
        timeout_threshold = self.settings.task_timeout

        async with self._lock:
            for task in self._tasks.values():
                if task.status == TaskStatus.RUNNING and task.started_at:
                    elapsed = current_time - task.started_at
                    if elapsed > timeout_threshold:
                        task.status = TaskStatus.TIMEOUT
                        task.completed_at = current_time
                        task.error = f"Task timed out after {elapsed:.1f}s"
                        logger.warning(f"Task {task.id} timed out")
                        await self._execute_callbacks(task)

    def get_stats(self) -> Dict[str, Any]:
        """获取队列统计信息"""
        stats = {
            "queue_size": len(self._queue),
            "total_tasks": len(self._tasks),
            "max_size": self.max_size,
            "by_status": {},
            "by_priority": {}
        }

        for status in TaskStatus:
            stats["by_status"][status.value] = 0

        for priority in TaskPriority:
            stats["by_priority"][priority.name] = 0

        for task in self._tasks.values():
            stats["by_status"][task.status.value] += 1
            stats["by_priority"][task.priority.name] += 1

        return stats

    def get_user_tasks(self, user_id: int) -> List[TaskInfo]:
        """获取用户的所有任务"""
        return [task for task in self._tasks.values() if task.user_id == user_id]

    def get_pending_count(self) -> int:
        """获取待处理任务数量"""
        return len(self._queue)


# 任务队列性能指标收集器
class TaskQueueMetrics:
    """任务队列性能指标收集器

    收集和报告任务队列的性能指标
    """

    def __init__(self):
        self._metrics: Dict[str, Any] = {
            "tasks_enqueued": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "tasks_cancelled": 0,
            "tasks_timeout": 0,
            "tasks_retried": 0,
            "total_wait_time": 0.0,
            "total_execution_time": 0.0,
            "last_reset": time.time()
        }
        self._lock = asyncio.Lock()

    async def record_enqueue(self):
        """记录任务入队"""
        async with self._lock:
            self._metrics["tasks_enqueued"] += 1

    async def record_complete(self, wait_time: float, execution_time: float):
        """记录任务完成"""
        async with self._lock:
            self._metrics["tasks_completed"] += 1
            self._metrics["total_wait_time"] += wait_time
            self._metrics["total_execution_time"] += execution_time

    async def record_failed(self):
        """记录任务失败"""
        async with self._lock:
            self._metrics["tasks_failed"] += 1

    async def record_cancelled(self):
        """记录任务取消"""
        async with self._lock:
            self._metrics["tasks_cancelled"] += 1

    async def record_timeout(self):
        """记录任务超时"""
        async with self._lock:
            self._metrics["tasks_timeout"] += 1

    async def record_retry(self):
        """记录任务重试"""
        async with self._lock:
            self._metrics["tasks_retried"] += 1

    def get_metrics(self) -> Dict[str, Any]:
        """获取所有指标"""
        metrics = self._metrics.copy()

        # 计算平均等待时间
        if metrics["tasks_completed"] > 0:
            metrics["avg_wait_time"] = (
                metrics["total_wait_time"] / metrics["tasks_completed"]
            )
            metrics["avg_execution_time"] = (
                metrics["total_execution_time"] / metrics["tasks_completed"]
            )
        else:
            metrics["avg_wait_time"] = 0.0
            metrics["avg_execution_time"] = 0.0

        # 计算成功率
        total_finished = (
            metrics["tasks_completed"] +
            metrics["tasks_failed"] +
            metrics["tasks_cancelled"] +
            metrics["tasks_timeout"]
        )
        if total_finished > 0:
            metrics["success_rate"] = metrics["tasks_completed"] / total_finished
        else:
            metrics["success_rate"] = 0.0

        return metrics

    async def reset(self):
        """重置指标"""
        async with self._lock:
            for key in self._metrics:
                if key == "last_reset":
                    self._metrics[key] = time.time()
                elif isinstance(self._metrics[key], float):
                    self._metrics[key] = 0.0
                else:
                    self._metrics[key] = 0


# 全局任务队列指标收集器
_queue_metrics = TaskQueueMetrics()


def get_queue_metrics() -> TaskQueueMetrics:
    """获取全局任务队列指标收集器"""
    return _queue_metrics


# 全局任务队列实例
_global_task_queue: Optional[TaskQueue] = None
_queue_lock = asyncio.Lock()


async def get_task_queue() -> TaskQueue:
    """获取全局任务队列实例"""
    global _global_task_queue

    async with _queue_lock:
        if _global_task_queue is None:
            _global_task_queue = TaskQueue()
            await _global_task_queue.start()
        return _global_task_queue


async def shutdown_task_queue():
    """关闭全局任务队列"""
    global _global_task_queue

    async with _queue_lock:
        if _global_task_queue:
            await _global_task_queue.stop()
            _global_task_queue = None
