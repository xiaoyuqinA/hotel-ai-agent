"""Workflow Streaming Runner — LangGraph v3 事件流消费。

简化设计原则：
1. astream_events(version="v3") 返回单个 async iterator
2. 通过 ProjectionMapper.transform() 逐个转换事件
3. 事件天然有序（sequence 由转换时分配）

事件链示例：
    on_chain_start        → NodeStartedEvent
    on_chat_model_stream  → TokenDeltaEvent
    on_chat_model_stream  → TokenDeltaEvent
    on_chain_end          → NodeCompletedEvent

使用方法：
    runner = WorkflowRunner()
    async for event in runner.run(graph, input, config):
        await websocket.send(event)
"""

import asyncio
from typing import Any, AsyncGenerator, AsyncIterator

from shared.workflow_events.mapper import ProjectionMapper
from shared.workflow_events.models import WorkflowEvent
from shared.workflow_events.event_store import is_workflow_cancelled


class WorkflowRunner:
    """工作流事件流执行器。

    单 iterator 消费 LangGraph v3 事件流。
    支持取消检测（通过 is_workflow_cancelled 轮询）。
    """

    def __init__(
        self, workflow_id: str | None = None, check_cancel_interval: float = 0.5
    ):
        self.workflow_id = workflow_id
        self.check_cancel_interval = check_cancel_interval
        self._cancelled = False

    @property
    def is_cancelled(self) -> bool:
        """是否已收到取消信号。"""
        return self._cancelled

    def run(
        self,
        graph,
        input: dict[str, Any],
        config: dict[str, Any] | None = None,
    ) -> AsyncGenerator[WorkflowEvent, None]:
        """执行工作流并产出事件流。"""
        return self._run_impl(graph, input, config)

    async def _run_impl(
        self,
        graph,
        input: dict[str, Any],
        config: dict[str, Any] | None = None,
    ) -> AsyncIterator[WorkflowEvent]:
        """内部实现：单 iterator 消费 v3 事件流，支持取消检测。"""
        mapper = ProjectionMapper(workflow_id=self.workflow_id)

        # 如果没有 workflow_id，跳过取消检测
        if not self.workflow_id:
            async for event in mapper.map_stream(graph, input, config):
                yield event
            return

        # 并行运行：主循环 + 取消检测
        cancel_check_task = asyncio.create_task(self._cancel_checker())

        try:
            async for event in mapper.map_stream(graph, input, config):
                # 检查是否已取消
                if self._cancelled:
                    break
                yield event
        finally:
            cancel_check_task.cancel()
            try:
                await cancel_check_task
            except asyncio.CancelledError:
                pass

    async def _cancel_checker(self) -> None:
        """定期检查取消状态。"""
        while not self._cancelled:
            await asyncio.sleep(self.check_cancel_interval)
            if self.workflow_id:
                self._cancelled = await is_workflow_cancelled(self.workflow_id)


def create_runner(workflow_id: str | None = None) -> WorkflowRunner:
    """创建 WorkflowRunner 的工厂函数。"""
    return WorkflowRunner(workflow_id=workflow_id)
