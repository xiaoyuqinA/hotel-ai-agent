"""Workflow Streaming Runner — 基于 LangGraph v3 Typed Projection 的事件流执行器。"""

from typing import Any, AsyncGenerator, AsyncIterator

from shared.workflow_events.mapper import ProjectionMapper
from shared.workflow_events.models import WorkflowEvent


class WorkflowRunner:
    """工作流事件流执行器。

    基于 LangGraph v3 Typed Projection 的 WorkflowRunner。
    消费 graph.astream_events(version="v3") 的各个 projection，
    转换为标准 WorkflowEvent 并 yield。

    使用方法：
        runner = WorkflowRunner()
        async for event in runner.run(graph, input, config):
            await websocket.send(event)

    特性：
        - 并发消费 v3 projections（messages, values, lifecycle, extensions）
        - 自动发送 WORKFLOW_STARTED / WORKFLOW_COMPLETED / WORKFLOW_FAILED
        - NODE 生命周期事件（NODE_STARTED / NODE_COMPLETED / NODE_FAILED）
        - LLM Token 流（TOKEN_DELTA）
        - State 快照（STATE_UPDATED）
        - 自定义业务事件（CUSTOM_EVENT）
    """

    def __init__(self, workflow_id: str | None = None):
        """初始化 Runner。

        Args:
            workflow_id: 可选的工作流 ID，不提供则自动生成 UUID
        """
        self.workflow_id = workflow_id

    def run(
        self,
        graph,
        input: dict[str, Any],
        config: dict[str, Any] | None = None,
    ) -> AsyncGenerator[WorkflowEvent, None]:
        """执行工作流并产出事件流。

        Args:
            graph: 编译后的 LangGraph
            input: 工作流输入
            config: LangGraph config（包含 thread_id 等）

        Yields:
            WorkflowEvent 序列
        """
        return self._run_impl(graph, input, config)

    async def _run_impl(
        self,
        graph,
        input: dict[str, Any],
        config: dict[str, Any] | None = None,
    ) -> AsyncIterator[WorkflowEvent]:
        """内部异步实现。"""
        mapper = ProjectionMapper(workflow_id=self.workflow_id)
        async for event in mapper.map_stream(graph, input, config):
            yield event


def create_runner(workflow_id: str | None = None) -> WorkflowRunner:
    """创建 WorkflowRunner 的工厂函数。

    Args:
        workflow_id: 可选的工作流 ID

    Returns:
        WorkflowRunner 实例
    """
    return WorkflowRunner(workflow_id=workflow_id)
