"""评论运营工作流注册。

导入此模块即自动注册 review_operation workflow（延迟编译）。
"""

from shared.registry.workflow_registry import register_workflow

from .review_operation_flow import build_compiled_graph

register_workflow(
    "review_operation",
    factory=build_compiled_graph,
    input_mapper=lambda x: {
        "reviews_content": x if isinstance(x, str) else x[1],
        "hotel_id": x[0] if isinstance(x, tuple) else "hotel_001",
        "anaylay_result": None,
        "reply_content": None,
        "strategy": None,
        "human_task_type": None,
        "publish_status": None,
    },
)
