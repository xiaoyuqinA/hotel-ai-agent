"""工作流事件模型 — WebSocket 传输的标准化事件对象。"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

import uuid
import time


class WorkflowCategory(str, Enum):
    """事件分类 — 用于 Chrome Extension 区分事件类型。"""

    PROGRESS = "progress"
    """进度事件 — analysis/generation/review 等业务阶段状态"""

    MESSAGE = "message"
    """消息事件 — LLM token 流式输出"""

    TOOL = "tool"
    """工具事件 — 工具调用"""

    STATE = "state"
    """状态事件 — LangGraph State 快照"""

    SYSTEM = "system"
    """系统事件 — workflow 生命周期"""


class WorkflowEvent(BaseModel):
    """标准化工作流事件。

    所有事件通过 WebSocket 推送给 Chrome Extension。
    字段设计对 Extension 友好，不需要了解 LangGraph。

    Attributes:
        id: 事件唯一 ID（UUID）
        workflow_id: 所属工作流 ID
        sequence: 事件序号（用于追踪，类似 Kafka offset）
        category: 事件分类（progress/message/tool/state/system）
        kind: 事件类型
        timestamp: Unix 时间戳（毫秒）
        source: 事件来源（node 名称或 "system"）
        payload: 事件负载（类型相关）
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    workflow_id: str

    sequence: int = 0

    category: str

    kind: str

    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000))

    source: str | None = None

    payload: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}


class NodeStartedEvent(WorkflowEvent):
    """节点开始事件。"""

    kind: str = Field(default="node_started")
    category: str = Field(default="progress")
    source: str

    @classmethod
    def create(
        cls,
        workflow_id: str,
        node_name: str,
        display_name: str | None = None,
        sequence: int = 0,
    ) -> "NodeStartedEvent":
        """创建节点开始事件。

        Args:
            workflow_id: 工作流 ID
            node_name: 节点名称
            display_name: 显示名称（Extension 用）
            sequence: 事件序列号
        """
        return cls(
            workflow_id=workflow_id,
            category="progress",
            kind="node_started",
            source=node_name,
            sequence=sequence,
            payload={"node": node_name, "display_name": display_name or node_name},
        )


class NodeCompletedEvent(WorkflowEvent):
    """节点完成事件。"""

    kind: str = Field(default="node_completed")
    category: str = Field(default="progress")
    source: str

    @classmethod
    def create(cls, workflow_id: str, node_name: str, sequence: int = 0) -> "NodeCompletedEvent":
        """创建节点完成事件。

        Args:
            workflow_id: 工作流 ID
            node_name: 节点名称
            sequence: 事件序列号
        """
        return cls(
            workflow_id=workflow_id,
            category="progress",
            kind="node_completed",
            source=node_name,
            sequence=sequence,
            payload={"node": node_name},
        )


class TokenDeltaEvent(WorkflowEvent):
    """Token 流式输出事件。"""

    kind: str = Field(default="token_delta")
    category: str = Field(default="message")
    source: str | None = None

    @classmethod
    def create(
        cls,
        workflow_id: str,
        delta: str,
        source: str | None = None,
    ) -> "TokenDeltaEvent":
        """创建 token 增量事件。

        Args:
            workflow_id: 工作流 ID
            delta: 增量文本
            source: 来源（agent 名称或 node 名称）
        """
        return cls(
            workflow_id=workflow_id,
            category="message",
            kind="token_delta",
            source=source,
            payload={"delta": delta},
        )


class StateUpdatedEvent(WorkflowEvent):
    """State 快照更新事件。"""

    kind: str = Field(default="state_updated")
    category: str = Field(default="state")

    @classmethod
    def create(
        cls,
        workflow_id: str,
        state: dict[str, Any],
    ) -> "StateUpdatedEvent":
        """创建 state 更新事件。

        Args:
            workflow_id: 工作流 ID
            state: 当前 state 快照
        """
        return cls(
            workflow_id=workflow_id,
            category="state",
            kind="state_updated",
            payload={"state": state},
        )


class WorkflowStartedEvent(WorkflowEvent):
    """工作流开始事件。"""

    kind: str = Field(default="workflow_started")
    category: str = Field(default="system")

    @classmethod
    def create(cls, workflow_id: str) -> "WorkflowStartedEvent":
        """创建工作流开始事件。"""
        return cls(
            workflow_id=workflow_id,
            category="system",
            kind="workflow_started",
            source="system",
        )


class WorkflowCompletedEvent(WorkflowEvent):
    """工作流完成事件。"""

    kind: str = Field(default="workflow_completed")
    category: str = Field(default="system")

    @classmethod
    def create(
        cls,
        workflow_id: str,
        result: dict[str, Any] | None = None,
    ) -> "WorkflowCompletedEvent":
        """创建工作流完成事件。

        Args:
            workflow_id: 工作流 ID
            result: 最终结果
        """
        return cls(
            workflow_id=workflow_id,
            category="system",
            kind="workflow_completed",
            source="system",
            payload={"result": result} if result else {},
        )


class WorkflowFailedEvent(WorkflowEvent):
    """工作流失败事件。"""

    kind: str = Field(default="workflow_failed")
    category: str = Field(default="system")

    @classmethod
    def create(
        cls,
        workflow_id: str,
        error: str,
    ) -> "WorkflowFailedEvent":
        """创建工作流失败事件。

        Args:
            workflow_id: 工作流 ID
            error: 错误信息
        """
        return cls(
            workflow_id=workflow_id,
            category="system",
            kind="workflow_failed",
            source="system",
            payload={"error": error},
        )


class NodeFailedEvent(WorkflowEvent):
    """节点失败事件。"""

    kind: str = Field(default="node_failed")
    category: str = Field(default="progress")
    source: str

    @classmethod
    def create(
        cls,
        workflow_id: str,
        node_name: str,
        error: str,
        sequence: int = 0,
    ) -> "NodeFailedEvent":
        """创建节点失败事件。

        Args:
            workflow_id: 工作流 ID
            node_name: 节点名称
            error: 错误信息
            sequence: 事件序列号
        """
        return cls(
            workflow_id=workflow_id,
            category="progress",
            kind="node_failed",
            source=node_name,
            sequence=sequence,
            payload={"node": node_name, "error": error},
        )


class CustomEvent(WorkflowEvent):
    """自定义业务事件。"""

    kind: str = Field(default="custom_event")
    category: str = Field(default="progress")
    source: str | None = None

    @classmethod
    def create(
        cls,
        workflow_id: str,
        event_type: str,
        data: dict[str, Any],
        source: str | None = None,
        sequence: int = 0,
    ) -> "CustomEvent":
        """创建自定义业务事件。

        Args:
            workflow_id: 工作流 ID
            event_type: 事件子类型
            data: 事件数据
            source: 来源
            sequence: 事件序列号
        """
        return cls(
            workflow_id=workflow_id,
            category="progress",
            kind="custom_event",
            source=source,
            sequence=sequence,
            payload={"event_type": event_type, **data},
        )


class ToolCallEvent(WorkflowEvent):
    """工具调用事件 (v3)。"""

    kind: str = Field(default="tool_call")
    category: str = Field(default="tool")
    source: str | None = None

    @classmethod
    def create(
        cls,
        workflow_id: str,
        tool_name: str,
        tool_input: dict[str, Any],
    ) -> "ToolCallEvent":
        """创建工具调用事件。

        Args:
            workflow_id: 工作流 ID
            tool_name: 工具名称
            tool_input: 工具输入参数
        """
        return cls(
            workflow_id=workflow_id,
            category="tool",
            kind="tool_call",
            source=tool_name,
            payload={"tool_name": tool_name, "tool_input": tool_input},
        )
