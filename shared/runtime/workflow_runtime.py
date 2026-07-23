"""Workflow runtime — the single execution entry point for all LangGraph workflows.

与 AgentRuntime 完全分离：
- AgentRuntime 管"智能体执行"（Adapter → LLM）
- WorkflowRuntime 管"流程编排执行"（LangGraph）
"""

from typing import Any

from langgraph.types import Command

from shared.registry.workflow_registry import get_workflow


class WorkflowRuntime:
    """统一工作流执行入口。

    职责：
    - 通过名称获取编译后的 graph
    - invoke（启动工作流）
    - resume（恢复人工任务）
    """

    async def run(
        self,
        workflow_name: str,
        user_input: Any,
        thread_id: str,
    ) -> dict[str, Any]:
        """运行一个工作流。

        Args:
            workflow_name: 已注册的 workflow 名称
            user_input: 原始用户输入（由 workflow 的 input_mapper 转换为 state）
            thread_id: 会话 ID，用于 interrupt 后恢复

        Returns:
            工作流最终 state
        """
        workflow = get_workflow(workflow_name)
        input_data = workflow.input_mapper(user_input)
        config = {"configurable": {"thread_id": thread_id}}
        return await workflow.graph.ainvoke(input_data, config=config)

    async def resume(
        self,
        workflow_name: str,
        thread_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """恢复被 interrupt 暂停的工作流。

        Args:
            workflow_name: 已注册的 workflow 名称
            thread_id: 工作流会话 ID
            data: 人工处理后的数据

        Returns:
            工作流最终 state
        """
        graph = get_workflow(workflow_name)
        config = {"configurable": {"thread_id": thread_id}}
        return await graph.graph.ainvoke(
            Command(resume=data),
            config=config,
        )


# 模块级便捷函数
_default_runtime: WorkflowRuntime | None = None


def _runtime() -> WorkflowRuntime:
    global _default_runtime
    if _default_runtime is None:
        _default_runtime = WorkflowRuntime()
    return _default_runtime


async def run_workflow(
    workflow_name: str,
    user_input: Any,
    thread_id: str,
) -> dict[str, Any]:
    """运行一个工作流。"""
    return await _runtime().run(workflow_name, user_input, thread_id)


async def resume_workflow(
    workflow_name: str,
    thread_id: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    """恢复被 interrupt 暂停的工作流。"""
    return await _runtime().resume(workflow_name, thread_id, data)