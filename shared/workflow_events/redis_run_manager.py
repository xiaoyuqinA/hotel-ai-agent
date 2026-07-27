"""Workflow Run Manager — Phase 2: PostgreSQL + Redis Pub/Sub 模式。

Phase 1: 内存 asyncio.Queue
Phase 2: PostgreSQL（持久化）+ Redis（实时推送）

架构：
┌─────────────────┐
│  POST /review/run │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│  PostgreSQL     │
│  workflow_runs  │
└─────────────────┘
        │
        ▼
  asyncio.create_task(
    LangGraph → event
        │
        ├─► PostgreSQL (save_event)
        │
        └─► Redis (publish)
                │
                ▼
┌─────────────────┐
│  SSE Client    │
│  (断线恢复)      │
└─────────────────┘
        │
        ▼
  PostgreSQL ← 历史事件
  Redis ← 实时事件
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any, AsyncGenerator

from shared.workflow_events.models import (
    WorkflowEvent,
    WorkflowStartedEvent,
    WorkflowCompletedEvent,
    WorkflowFailedEvent,
)
from shared.workflow_events.event_store import (
    save_and_publish,
    create_run_record,
    update_run_status,
    get_run_record,
    get_events_after,
    subscribe_events,
)


class RunStatus:
    """Run 状态（兼容 Phase 1）。"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# ── Run Manager ─────────────────────────────────────────────────────────────────

_manager: "WorkflowRunManager" | None = None


def get_run_manager() -> "WorkflowRunManager":
    """获取 WorkflowRunManager 单例。"""
    global _manager
    if _manager is None:
        _manager = WorkflowRunManager()
    return _manager


class WorkflowRunManager:
    """Workflow Run 管理器（Phase 2: PostgreSQL + Redis）。

    职责：
    - 创建/管理 WorkflowRun
    - 持久化事件到 PostgreSQL
    - 发布事件到 Redis Pub/Sub
    - 提供 SSE 消费接口（支持断线恢复）
    """

    async def create_run(
        self,
        workflow_name: str,
        input_data: Any,
        thread_id: str | None = None,
    ) -> dict:
        """创建新的 Workflow Run。

        Args:
            workflow_name: workflow 名称
            input_data: 工作流输入
            thread_id: 可选的 thread_id

        Returns:
            Run 信息字典
        """
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        thread_id = thread_id or f"thread_{uuid.uuid4().hex[:12]}"

        # 持久化到 PostgreSQL
        await create_run_record(
            run_id=run_id,
            workflow_name=workflow_name,
            thread_id=thread_id,
            input_data=input_data,
        )

        return {
            "id": run_id,
            "workflow_name": workflow_name,
            "status": RunStatus.PENDING,
            "thread_id": thread_id,
            "input_data": input_data,
        }

    async def get_run(self, run_id: str) -> dict | None:
        """获取 WorkflowRun 信息。"""
        return await get_run_record(run_id)

    async def publish_event(self, event: WorkflowEvent) -> None:
        """发布事件（持久化 + 发布）。"""
        await save_and_publish(event)

    async def update_status(
        self,
        run_id: str,
        status: str,
        result: Any = None,
        error: str = None,
    ) -> None:
        """更新 run 状态。"""
        await update_run_status(run_id, status, result, error)

    async def subscribe(
        self,
        run_id: str,
        last_sequence: int = 0,
    ) -> AsyncGenerator[WorkflowEvent, None]:
        """订阅事件流（支持断线恢复）。

        1. 先发送 last_sequence 之后的历史事件（PostgreSQL）
        2. 然后订阅 Redis 实时事件

        Args:
            run_id: Run ID
            last_sequence: 起始序列号（用于断线恢复）

        Yields:
            WorkflowEvent 序列
        """
        # 1. 发送历史事件
        historical = await get_events_after(run_id, last_sequence)
        for event in historical:
            yield event

        # 2. 订阅实时事件
        async for event in subscribe_events(run_id):
            # 跳过已发送的历史事件
            if event.sequence > last_sequence:
                yield event


# ── 后台任务 ──────────────────────────────────────────────────────────────────

async def run_workflow_background(
    run_id: str,
    workflow_name: str,
    input_data: dict,
    config: dict,
) -> None:
    """后台任务：运行 LangGraph 并发布事件。

    Args:
        run_id: WorkflowRun ID
        workflow_name: workflow 名称
        input_data: 工作流输入
        config: LangGraph config
    """
    from shared.runtime.workflow_runtime import _runtime
    from shared.workflow_events.models import WorkflowRunner

    try:
        # 更新状态为 running
        await update_run_status(run_id, RunStatus.RUNNING)

        # 发布 workflow_started
        started_event = WorkflowStartedEvent.create(run_id)
        await save_and_publish(started_event)

        # 获取 workflow graph
        runtime = _runtime()
        workflow = runtime.get_workflow(workflow_name)

        # 运行 workflow
        runner = WorkflowRunner(workflow_id=run_id)

        result = None
        async for event in runner.run(workflow.graph, input_data, config):
            await save_and_publish(event)

            # 收集最终 result
            if event.kind == "workflow_completed":
                result = event.payload.get("result")

        # 更新状态为 completed
        await update_run_status(run_id, RunStatus.COMPLETED, result=result)

    except Exception as e:
        # 发布 workflow_failed
        failed_event = WorkflowFailedEvent.create(run_id, str(e))
        await save_and_publish(failed_event)

        # 更新状态为 failed
        await update_run_status(run_id, RunStatus.FAILED, error=str(e))
