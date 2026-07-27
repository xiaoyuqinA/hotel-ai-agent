"""工作流事件类型枚举 — 业务层与 LangGraph Runtime 的解耦层。"""

from enum import Enum


class EventKind(str, Enum):
    """Workflow Event 类型枚举。

    Chrome Extension 通过 WebSocket 接收这些事件，
    不需要知道 LangGraph / LangChain 的任何概念。
    """

    # Workflow 生命周期

    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"

    # Node 生命周期

    NODE_STARTED = "node_started"
    NODE_COMPLETED = "node_completed"
    NODE_FAILED = "node_failed"

    # LLM Streaming

    TOKEN_DELTA = "token_delta"

    # 自定义业务事件

    CUSTOM_EVENT = "custom_event"

    # State

    STATE_UPDATED = "state_updated"
