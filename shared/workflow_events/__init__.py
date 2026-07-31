"""Workflow Event Streaming 模块。

事件流设计：
- LangGraph astream_events(version="v3") → ProtocolEvent
- ProjectionMapper.transform() → WorkflowEvent
- SSE → Chrome Extension

主要组件：
- ProjectionMapper: LangGraph 事件 → WorkflowEvent 转换器
- WorkflowEvent: 标准化事件模型
- WorkflowRunner: 工作流执行器
"""

from shared.workflow_events.models import (
    WorkflowEvent,
    WorkflowCategory,
    NodeStartedEvent,
    NodeCompletedEvent,
    NodeFailedEvent,
    TokenDeltaEvent,
    StateUpdatedEvent,
    WorkflowStartedEvent,
    WorkflowCompletedEvent,
    WorkflowFailedEvent,
    CustomEvent,
    ToolCallEvent,
    parse_workflow_event,
)

from shared.workflow_events.kinds import (
    EventKind,
    BusinessEvent,
)

from shared.workflow_events.mapper import ProjectionMapper
