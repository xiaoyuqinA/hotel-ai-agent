"""流式工作流执行 — 整合 WorkflowRunner 和 WorkflowRuntime。"""

from typing import Any, AsyncGenerator

from shared.registry.workflow_registry import get_workflow
from shared.streaming.runner import WorkflowRunner


def stream_workflow(
    workflow_name: str,
    user_input: Any,
    thread_id: str,
) -> AsyncGenerator:
    """流式运行工作流，返回 WorkflowEvent 事件流。

    整合 WorkflowRuntime 和 WorkflowRunner：
    - WorkflowRuntime 提供编译后的 graph
    - WorkflowRunner 负责事件流转换

    Args:
        workflow_name: 工作流名称
        user_input: 用户输入
        thread_id: 会话 ID

    Yields:
        WorkflowEvent 事件序列
    """
    return _stream_workflow_impl(workflow_name, user_input, thread_id)


async def _stream_workflow_impl(
    workflow_name: str,
    user_input: Any,
    thread_id: str,
):
    """内部异步实现。"""
    workflow = get_workflow(workflow_name)
    input_data = workflow.input_mapper(user_input)
    config = {"configurable": {"thread_id": thread_id}}

    runner = WorkflowRunner()
    async for event in runner.run(workflow.graph, input_data, config):
        yield event
