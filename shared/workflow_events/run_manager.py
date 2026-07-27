"""Workflow Run 管理器 — 管理 run 生命周期和事件队列。

Phase 1: 内存 Queue
Phase 2: PostgreSQL + Redis
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator

from shared.workflow_events.models import WorkflowEvent


class RunStatus(str, Enum):
    """Run 状态。"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class WorkflowRun:
    """单个 Workflow Run 实例。"""

    id: str
    workflow_name: str
    status: RunStatus = RunStatus.PENDING
    thread_id: str = ""
    input_data: Any = None
    result: Any = None
    error: str | None = None
    queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    started_at: float = field(default_factory=lambda: asyncio.get_event_loop().time())


class WorkflowRunManager:
    """Workflow Run 管理器。

    职责：
    - 创建/管理 WorkflowRun 实例
    - 管理事件队列
    - 提供 SSE 消费接口

    Phase 1 使用内存 asyncio.Queue。
    Phase 2 替换为 Redis Pub/Sub + PostgreSQL。
    """

    def __init__(self):
        self._runs: dict[str, WorkflowRun] = {}
        self._lock = asyncio.Lock()

    async def create_run(
        self,
        workflow_name: str,
        input_data: Any,
        thread_id: str | None = None,
    ) -> WorkflowRun:
        """创建新的 Workflow Run。

        Args:
            workflow_name: workflow 名称
            input_data: 工作流输入
            thread_id: 可选的 thread_id

        Returns:
            WorkflowRun 实例
        """
        async with self._lock:
            run = WorkflowRun(
                id=f"run_{uuid.uuid4().hex[:12]}",
                workflow_name=workflow_name,
                thread_id=thread_id or f"thread_{uuid.uuid4().hex[:12]}",
                input_data=input_data,
                status=RunStatus.PENDING,
            )
            self._runs[run.id] = run
            return run

    async def get_run(self, run_id: str) -> WorkflowRun | None:
        """获取 WorkflowRun 实例。"""
        return self._runs.get(run_id)

    async def publish_event(self, run_id: str, event: WorkflowEvent) -> None:
        """发布事件到指定 run 的队列。

        Args:
            run_id: Run ID
            event: WorkflowEvent 事件
        """
        run = await self.get_run(run_id)
        if run:
            await run.queue.put(event)

    async def subscribe(self, run_id: str) -> AsyncGenerator[WorkflowEvent, None]:
        """订阅指定 run 的事件流。

        Args:
            run_id: Run ID

        Yields:
            WorkflowEvent 序列

        Raises:
            ValueError: Run 不存在
        """
        run = await self.get_run(run_id)
        if not run:
            raise ValueError(f"Run not found: {run_id}")

        while True:
            event = await run.queue.get()
            yield event

            # 如果是最终状态，退出
            if event.kind in ("workflow_completed", "workflow_failed"):
                break

    async def set_status(self, run_id: str, status: RunStatus) -> None:
        """更新 run 状态。"""
        run = await self.get_run(run_id)
        if run:
            run.status = status

    async def set_result(self, run_id: str, result: Any) -> None:
        """设置 run 结果。"""
        run = await self.get_run(run_id)
        if run:
            run.result = result

    async def set_error(self, run_id: str, error: str) -> None:
        """设置 run 错误。"""
        run = await self.get_run(run_id)
        if run:
            run.error = error

    async def cleanup(self, run_id: str) -> None:
        """清理完成的 run（释放内存）。"""
        async with self._lock:
            self._runs.pop(run_id, None)


# 模块级单例
_manager: WorkflowRunManager | None = None


def get_run_manager() -> WorkflowRunManager:
    """获取 WorkflowRunManager 单例。"""
    global _manager
    if _manager is None:
        _manager = WorkflowRunManager()
    return _manager
