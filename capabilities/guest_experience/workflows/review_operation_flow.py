"""评论运营工作流 — 基于 LangGraph StateGraph 编排。"""

from typing import Any

from langgraph.graph import StateGraph, END
from langgraph.types import Command

from .state import ReviewReplyState, WorkflowError
from .nodes.analysis_node import analysis_node
from .nodes.strategy_node import strategy_node, strategy_router
from .nodes.generate_reply_node import generate_reply_node
from .nodes.human_review_node import human_review_node
from .nodes.human_process_node import human_process_node
from .nodes.publish_node import publish_node


def _build_graph() -> StateGraph:
    workflow = StateGraph(ReviewReplyState)

    # 注册节点
    workflow.add_node("analysis", analysis_node)
    workflow.add_node("strategy", strategy_node)
    workflow.add_node("generate_reply", generate_reply_node)
    workflow.add_node("human_review", human_review_node)
    workflow.add_node("human_process", human_process_node)
    workflow.add_node("publish", publish_node)

    # 入口
    workflow.set_entry_point("analysis")

    # analysis -> strategy
    workflow.add_edge("analysis", "strategy")

    # 条件路由：strategy -> low / medium / high
    workflow.add_conditional_edges(
        "strategy",
        strategy_router,
        {"low": "generate_reply", "medium": "human_review", "high": "human_process"},
    )

    # 各分支汇聚到 publish
    workflow.add_edge("generate_reply", "publish")
    workflow.add_edge("human_review", "publish")
    workflow.add_edge("human_process", "publish")
    workflow.add_edge("publish", END)

    return workflow


graph = _build_graph().compile()


def print_graph() -> None:
    """打印工作流图结构（Mermaid 格式）。"""
    print(graph.get_graph().draw_mermaid())


async def run_review_workflow(
    comment: str,
    thread_id: str | None = None,
) -> ReviewReplyState:
    """运行评论运营工作流。

    Low 分支直接返回完整结果。
    Medium 分支在 human_review_node 处暂停，等待 resume_review 恢复。
    High 分支在 human_process_node 处暂停，等待 resume_process 恢复。

    Args:
        comment: 待处理的评论文本
        thread_id: 会话 ID，用于 Medium/High 分支人工处理后恢复

    Returns:
        ReviewReplyState: 包含策略、回复内容和发布状态的字典

    Raises:
        WorkflowError: 节点执行失败时抛出
    """
    config: dict[str, Any] = {}
    if thread_id is not None:
        config["configurable"] = {"thread_id": thread_id}

    initial_state = ReviewReplyState(
        reviews_content=comment,
        anaylay_result=None,
        reply_content=None,
        strategy=None,
        human_task_type=None,
        publish_status=None,
    )
    result = await graph.ainvoke(initial_state, config=config)
    return result


async def resume_human_task(
    thread_id: str,
    task_type: str,
    reply_content: str,
) -> ReviewReplyState:
    """恢复人工任务后的工作流。

    统一入口，覆盖 Medium（人工确认）和 High（人工处理）分支。

    Args:
        thread_id: 工作流会话 ID
        task_type: 任务类型（"human_review" / "human_process"）
        reply_content: 人工处理后的最终回复内容

    Returns:
        ReviewReplyState: 包含最终状态的字典
    """
    result = await graph.ainvoke(
        Command(resume={"task_type": task_type, "reply_content": reply_content}),
        config={"configurable": {"thread_id": thread_id}},
    )
    return result