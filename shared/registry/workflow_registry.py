"""Workflow registry — central module lookup for all LangGraph workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

# Graph 是编译后的 LangGraph CompiledGraph
Graph = object


@dataclass
class WorkflowDefinition:
    graph: Optional[Graph]  # 延迟编译时为 None
    input_mapper: Callable[[Any], Any]
    factory: Optional[Callable[[Any], Graph]] = None  # 延迟编译 factory


_REGISTRY: Dict[str, WorkflowDefinition] = {}


def register_workflow(
    name: str,
    graph=None,
    input_mapper: Callable[[Any], Any] = lambda x: x,
    factory: Optional[Callable[[Any], Graph]] = None,
) -> None:
    """注册一个 workflow。

    支持两种形式：
    - 直接注册 compiled graph 实例：register_workflow("name", graph)
    - 注册 factory 函数延迟编译：register_workflow("name", factory=build_compiled_graph)

    Args:
        name: 唯一标识符（如 "review_operation"）
        graph: compiled graph 实例（factory 指定时为 None）
        input_mapper: 将原始用户输入转换为 workflow state 的函数
        factory: 接收 checkpointer 参数返回 compiled graph 的函数
    """
    if name in _REGISTRY:
        raise ValueError(f"Workflow '{name}' is already registered.")
    _REGISTRY[name] = WorkflowDefinition(
        graph=graph,
        input_mapper=input_mapper,
        factory=factory,
    )


def compile_all(checkpointer) -> None:
    """编译所有延迟注册的 workflow。

    Args:
        checkpointer: 已激活的 AsyncSqliteSaver 实例
    """
    for _name, defn in _REGISTRY.items():
        if defn.factory:
            defn.graph = defn.factory(checkpointer)
            defn.factory = None


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