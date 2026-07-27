"""Interrupt Handler — Phase 3: 捕获 LangGraph interrupt 并创建审批记录。

功能：
1. 包装 WorkflowRunner，捕获 interrupt 异常
2. 创建 Approval 记录
3. 发布 approval_requested 事件
4. 支持从 Approval 恢复 workflow

架构：
┌─────────────────┐
│  InterruptHandler │
│  (包装 WorkflowRunner) │
└─────────────────┘
        │
        ▼
  workflow.astream_events()
        │
        ├──► 正常事件 → yield
        │
        └──► Interrupt →
                │
                ▼
        create_approval()
                │
                ▼
        publish_event(approval_requested)
                │
                ▼
        抛出 InterruptPending
"""

import asyncio
from typing import Any, AsyncGenerator

from shared.workflow_events.models import (
    WorkflowEvent,
    WorkflowFailedEvent,
)
from shared.workflow_events.event_store import publish_event


class InterruptPending(Exception):
    """Workflow 被 interrupt 暂停。

    Attributes:
        approval_id: 审批记录 ID
        payload: interrupt 携带的数据
    """

    def __init__(self, approval_id: str, payload: dict[str, Any]):
        self.approval_id = approval_id
        self.payload = payload
        super().__init__(f"Workflow interrupted, approval_id={approval_id}")


async def handle_interrupt(
    run_id: str,
    workflow_name: str,
    thread_id: str,
    error: Exception,
) -> str:
    """处理 LangGraph interrupt。

    捕获 interrupt 异常，提取 payload，创建 Approval 记录。

    Args:
        run_id: WorkflowRun ID
        workflow_name: workflow 名称
        thread_id: LangGraph thread ID
        error: LangGraph 抛出的 interrupt 异常

    Returns:
        approval_id
    """
    from shared.workflow_events.approval_service import create_approval

    # 从 error 中提取 interrupt payload
    # LangGraph interrupt 异常格式：Interrupt(value={...})
    payload = _extract_interrupt_payload(error)

    task_type = payload.get("task_type", "unknown")

    # 创建审批记录
    approval = await create_approval(
        run_id=run_id,
        thread_id=thread_id,
        workflow_name=workflow_name,
        task_type=task_type,
        payload=payload,
    )

    # 发布 approval_requested 事件
    from shared.workflow_events.models import CustomEvent
    event = CustomEvent.create(
        workflow_id=run_id,
        event_type="approval_requested",
        data={
            "approval_id": approval["id"],
            "task_type": task_type,
            "payload": payload,
        },
    )
    await publish_event(event)

    return approval["id"]


def _extract_interrupt_payload(error: Exception) -> dict[str, Any]:
    """从异常中提取 interrupt payload。

    LangGraph interrupt 会将 payload 存储在异常中。
    格式：Interrupt(value={...})
    """
    # 检查是否是 Interrupt 类型
    if hasattr(error, "args") and len(error.args) > 0:
        arg = error.args[0]
        if isinstance(arg, dict):
            return arg
        if hasattr(arg, "values") and hasattr(arg, "type"):
            # 可能是 CheckpointTuple 或其他类型
            if hasattr(arg, "metadata"):
                return arg.metadata or {}
            return {}

    # 直接检查异常属性
    if hasattr(error, "value"):
        value = error.value
        if isinstance(value, dict):
            return value
        if hasattr(value, "values"):
            return getattr(value, "values", {})

    if hasattr(error, "metadata"):
        return error.metadata or {}

    # 兜底：返回空 payload
    return {}


class InterruptAwareRunner:
    """支持 interrupt 的 WorkflowRunner。

    使用方式：
    runner = InterruptAwareRunner()
    async for event in runner.run(...):
        yield event
    # 如果 workflow 被 interrupt，会抛出 InterruptPending
    """

    def __init__(self, workflow_id: str | None = None, workflow_name: str = ""):
        self.workflow_id = workflow_id
        self.workflow_name = workflow_name

    async def run(
        self,
        graph,
        input_data: dict[str, Any],
        config: dict[str, Any] | None = None,
    ) -> AsyncGenerator[WorkflowEvent, None]:
        """运行 workflow，捕获 interrupt。"""
        from shared.streaming.runner import WorkflowRunner
        from langgraph.types import Interrupt

        thread_id = config.get("configurable", {}).get("thread_id", "") if config else ""
        run_id = self.workflow_id or "unknown"

        runner = WorkflowRunner(workflow_id=run_id)

        try:
            async for event in runner.run(graph, input_data, config):
                yield event

        except Exception as e:
            # 检查是否是 interrupt
            if _is_interrupt_exception(e):
                # 处理 interrupt，创建 approval
                approval_id = await handle_interrupt(
                    run_id=run_id,
                    workflow_name=self.workflow_name,
                    thread_id=thread_id,
                    error=e,
                )

                # 从 error 中提取 payload 抛出 InterruptPending
                payload = _extract_interrupt_payload(e)
                raise InterruptPending(approval_id, payload)
            else:
                # 其他异常，发布 failed 事件
                yield WorkflowFailedEvent.create(run_id, str(e))
                raise


def _is_interrupt_exception(e: Exception) -> bool:
    """检查是否是 interrupt 异常。"""
    # LangGraph interrupt 类型检查
    if isinstance(e, Exception):
        # 检查类型名称
        type_name = type(e).__name__
        if "Interrupt" in type_name:
            return True

        # 检查 message
        if "interrupt" in str(e).lower():
            return True

    return False
