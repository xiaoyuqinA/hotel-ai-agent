"""Workflow registry — central module lookup for all LangGraph workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List

# Graph 是编译后的 LangGraph CompiledGraph
Graph = object
Factory = Callable[[], Graph]


@dataclass
class WorkflowDefinition:
    graph: Graph
    input_mapper: Callable[[Any], Any]


_REGISTRY: Dict[str, WorkflowDefinition] = {}


def register_workflow(
    name: str,
    graph_or_factory: Graph | Factory,
    input_mapper: Callable[[Any], Any] = lambda x: x,
) -> None:
    """注册一个 workflow。

    支持两种形式：
    - 直接注册 compiled graph 实例：register_workflow("name", graph)
    - 注册 factory 函数：register_workflow("name", lambda: _build_graph().compile())

    Args:
        name: 唯一标识符（如 "review_operation"）
        graph_or_factory: compiled graph 实例或零参数 factory 函数
        input_mapper: 将原始用户输入转换为 workflow state 的函数
    """
    if name in _REGISTRY:
        raise ValueError(f"Workflow '{name}' is already registered.")
    if callable(graph_or_factory):
        graph = graph_or_factory()
    else:
        graph = graph_or_factory
    _REGISTRY[name] = WorkflowDefinition(graph=graph, input_mapper=input_mapper)


def get_workflow(name: str) -> WorkflowDefinition:
    """通过名称获取 workflow 定义（包含 graph 和 input_mapper）。

    Raises:
        KeyError: 未找到该 workflow
    """
    definition = _REGISTRY.get(name)
    if definition is None:
        raise KeyError(
            f"Workflow '{name}' not registered. "
            f"Available: {list_workflows()}"
        )
    return definition


def list_workflows() -> List[str]:
    """返回所有已注册的 workflow 名称列表。"""
    return sorted(_REGISTRY.keys())


def is_registered(name: str) -> bool:
    """检查是否有该名称的 workflow 已注册。"""
    return name in _REGISTRY