"""评论运营工作流注册。

导入此模块即自动注册 review_operation workflow。
"""

from shared.registry.workflow_registry import register_workflow

from .review_operation_flow import graph

register_workflow(
    "review_operation",
    graph,
    input_mapper=lambda x: {"reviews_content": x},
)