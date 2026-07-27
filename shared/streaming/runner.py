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

from typing import Any, AsyncGenerator, AsyncIterator

from shared.workflow_events.mapper import ProjectionMapper
from shared.workflow_events.models import WorkflowEvent


class WorkflowRunner:
    """工作流事件流执行器。

    单 iterator 消费 LangGraph v3 事件流。
    """

    def __init__(self, workflow_id: str | None = None):
        self.workflow_id = workflow_id

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
        """内部实现：单 iterator 消费 v3 事件流。"""
        mapper = ProjectionMapper(workflow_id=self.workflow_id)
        async for event in mapper.map_stream(graph, input, config):
            yield event


def create_runner(workflow_id: str | None = None) -> WorkflowRunner:
    """创建 WorkflowRunner 的工厂函数。"""
    return WorkflowRunner(workflow_id=workflow_id)
