"""评论运营工作流 — 基于 LangGraph StateGraph 编排。"""

from langgraph.graph import StateGraph, END

from .state import ReviewReplyState
from .nodes.analysis_node import analysis_node
from .nodes.strategy_node import strategy_node, strategy_router, reply_router
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
        {"low": "generate_reply", "medium": "generate_reply", "high": "human_process"},
    )

    # generate_reply -> reply_router -> publish / human_review
    workflow.add_conditional_edges(
        "generate_reply",
        reply_router,
        {"low": "publish", "medium": "human_review"},
    )

    # 各分支汇聚到 publish
    workflow.add_edge("human_review", "publish")
    workflow.add_edge("human_process", "publish")
    workflow.add_edge("publish", END)

    return workflow


def build_compiled_graph(checkpointer):
    """返回编译后的 graph。由 WorkflowRuntime 在 startup 时调用。"""
    return _build_graph().compile(checkpointer=checkpointer)


def print_graph() -> None:
    """打印工作流图结构（Mermaid 格式）。"""
    from shared.registry.workflow_registry import get_workflow

    workflow = get_workflow("review_operation")
    print(workflow.graph.get_graph().draw_mermaid())
