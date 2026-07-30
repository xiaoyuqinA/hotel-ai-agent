"""工作流事件模型 — WebSocket 传输的标准化事件对象。

所有事件字段直接平铺在事件类上，不再使用 payload 字典。
每个事件类是独立的 Pydantic Model，字段类型安全。
"""

import json
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class WorkflowCategory(str):
    """事件分类。"""

    PROGRESS = "progress"
    MESSAGE = "message"
    TOOL = "tool"
    STATE = "state"
    SYSTEM = "system"


class EventKind(str):
    """Workflow Event 类型。"""

    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    WORKFLOW_CANCELLED = "workflow_cancelled"
    NODE_STARTED = "node_started"
    NODE_COMPLETED = "node_completed"
    NODE_FAILED = "node_failed"
    TOKEN_DELTA = "token_delta"
    TOOL_CALL = "tool_call"
    STATE_UPDATED = "state_updated"
    CUSTOM_EVENT = "custom_event"


class WorkflowEvent(BaseModel):
    """标准化工作流事件。

    所有事件通过 WebSocket 推送给 Chrome Extension。
    字段设计对 Extension 友好，不需要了解 LangGraph。
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str
    sequence: int = 0
    category: str = WorkflowCategory.PROGRESS
    kind: str = EventKind.NODE_STARTED
    display_name: str | None = None
    timestamp: int = Field(
        default_factory=lambda: int(datetime.now().timestamp() * 1000)
    )
    source: str | None = None

    model_config = {"extra": "forbid"}


class NodeStartedEvent(WorkflowEvent):
    """节点开始事件。"""

    kind: str = EventKind.NODE_STARTED
    category: str = WorkflowCategory.PROGRESS
    node_name: str

    @classmethod
    def create(
        cls,
        workflow_id: str,
        node_name: str,
        display_name: str | None = None,
        sequence: int = 0,
    ) -> "NodeStartedEvent":
        return cls(
            workflow_id=workflow_id,
            node_name=node_name,
            display_name=display_name or node_name,
            source=node_name,
            sequence=sequence,
        )


class NodeCompletedEvent(WorkflowEvent):
    """节点完成事件。"""

    kind: str = EventKind.NODE_COMPLETED
    category: str = WorkflowCategory.PROGRESS
    node_name: str

    @classmethod
    def create(
        cls,
        workflow_id: str,
        node_name: str,
        display_name: str | None = None,
        sequence: int = 0,
    ) -> "NodeCompletedEvent":
        return cls(
            workflow_id=workflow_id,
            node_name=node_name,
            display_name=display_name or node_name,
            source=node_name,
            sequence=sequence,
        )


class NodeFailedEvent(WorkflowEvent):
    """节点失败事件。"""

    kind: str = EventKind.NODE_FAILED
    category: str = WorkflowCategory.PROGRESS
    node_name: str
    error: str

    @classmethod
    def create(
        cls,
        workflow_id: str,
        node_name: str,
        error: str,
        display_name: str | None = None,
        sequence: int = 0,
    ) -> "NodeFailedEvent":
        return cls(
            workflow_id=workflow_id,
            node_name=node_name,
            error=error,
            display_name=display_name,
            source=node_name,
            sequence=sequence,
        )


class TokenDeltaEvent(WorkflowEvent):
    """Token 流式输出事件。"""

    kind: str = EventKind.TOKEN_DELTA
    category: str = WorkflowCategory.MESSAGE
    source: str | None = None
    delta: str = ""

    @classmethod
    def create(
        cls,
        workflow_id: str,
        delta: str,
        source: str | None = None,
    ) -> "TokenDeltaEvent":
        return cls(
            workflow_id=workflow_id,
            delta=delta,
            source=source,
        )


class StateUpdatedEvent(WorkflowEvent):
    """State 快照更新事件。"""

    kind: str = EventKind.STATE_UPDATED
    category: str = WorkflowCategory.STATE
    state: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def create(
        cls,
        workflow_id: str,
        state: dict[str, Any],
    ) -> "StateUpdatedEvent":
        serializable_state: dict[str, Any] = {}
        for key, value in state.items():
            try:
                json.dumps({"test": value})
                serializable_state[key] = value
            except (TypeError, ValueError):
                serializable_state[key] = f"<{type(value).__name__}>"

        return cls(
            workflow_id=workflow_id,
            state=serializable_state,
        )


class WorkflowStartedEvent(WorkflowEvent):
    """工作流开始事件。"""

    kind: str = EventKind.WORKFLOW_STARTED
    category: str = WorkflowCategory.SYSTEM

    @classmethod
    def create(
        cls,
        workflow_id: str,
        display_name: str | None = None,
    ) -> "WorkflowStartedEvent":
        return cls(
            workflow_id=workflow_id,
            display_name=display_name,
            source="system",
        )


class WorkflowCompletedEvent(WorkflowEvent):
    """工作流完成事件。"""

    kind: str = EventKind.WORKFLOW_COMPLETED
    category: str = WorkflowCategory.SYSTEM
    result: dict[str, Any] | None = None

    @classmethod
    def create(
        cls,
        workflow_id: str,
        result: dict[str, Any] | None = None,
        display_name: str | None = None,
    ) -> "WorkflowCompletedEvent":
        return cls(
            workflow_id=workflow_id,
            result=result,
            display_name=display_name,
            source="system",
        )


class WorkflowFailedEvent(WorkflowEvent):
    """工作流失败事件。"""

    kind: str = EventKind.WORKFLOW_FAILED
    category: str = WorkflowCategory.SYSTEM
    error: str

    @classmethod
    def create(
        cls,
        workflow_id: str,
        error: str,
        display_name: str | None = None,
    ) -> "WorkflowFailedEvent":
        return cls(
            workflow_id=workflow_id,
            error=error,
            display_name=display_name,
            source="system",
        )


class WorkflowCancelledEvent(WorkflowEvent):
    """工作流被取消事件。"""

    kind: str = EventKind.WORKFLOW_CANCELLED
    category: str = WorkflowCategory.SYSTEM

    @classmethod
    def create(
        cls,
        workflow_id: str,
        display_name: str | None = None,
    ) -> "WorkflowCancelledEvent":
        return cls(
            workflow_id=workflow_id,
            display_name=display_name,
            source="system",
        )


class CustomEvent(WorkflowEvent):
    """自定义业务事件。"""

    kind: str = EventKind.CUSTOM_EVENT
    category: str = WorkflowCategory.PROGRESS
    source: str | None = None
    event_type: str = ""
    data: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def create(
        cls,
        workflow_id: str,
        event_type: str,
        data: dict[str, Any],
        source: str | None = None,
        sequence: int = 0,
    ) -> "CustomEvent":
        return cls(
            workflow_id=workflow_id,
            event_type=event_type,
            data=data,
            source=source,
            sequence=sequence,
        )


class ToolCallEvent(WorkflowEvent):
    """工具调用事件 (v3)。"""

    kind: str = EventKind.TOOL_CALL
    category: str = WorkflowCategory.TOOL
    source: str | None = None
    tool_name: str = ""
    tool_input: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def create(
        cls,
        workflow_id: str,
        node_name: str,
        tool_name: str,
        tool_input: dict[str, Any] | None = None,
        display_name: str | None = None,
        sequence: int = 0,
    ) -> "ToolCallEvent":
        return cls(
            workflow_id=workflow_id,
            tool_name=tool_name,
            tool_input=tool_input or {},
            display_name=display_name,
            source=node_name,
            sequence=sequence,
        )


_EVENT_CLASS_BY_KIND: dict[str, type[WorkflowEvent]] = {
    EventKind.WORKFLOW_STARTED: WorkflowStartedEvent,
    EventKind.WORKFLOW_COMPLETED: WorkflowCompletedEvent,
    EventKind.WORKFLOW_FAILED: WorkflowFailedEvent,
    EventKind.WORKFLOW_CANCELLED: WorkflowCancelledEvent,
    EventKind.NODE_STARTED: NodeStartedEvent,
    EventKind.NODE_COMPLETED: NodeCompletedEvent,
    EventKind.NODE_FAILED: NodeFailedEvent,
    EventKind.TOKEN_DELTA: TokenDeltaEvent,
    EventKind.TOOL_CALL: ToolCallEvent,
    EventKind.STATE_UPDATED: StateUpdatedEvent,
    EventKind.CUSTOM_EVENT: CustomEvent,
}


def parse_workflow_event(data: dict[str, Any] | str) -> WorkflowEvent:
    """按 kind 还原为对应的 WorkflowEvent 子类。

    Args:
        data: 事件字典或 JSON 字符串

    Returns:
        对应 kind 的事件实例；未知 kind 时回退为 CustomEvent
    """
    if isinstance(data, str):
        payload = json.loads(data)
    else:
        payload = dict(data)

    kind = payload.get("kind", EventKind.CUSTOM_EVENT)
    event_cls = _EVENT_CLASS_BY_KIND.get(kind, CustomEvent)
    return event_cls.model_validate(payload)
