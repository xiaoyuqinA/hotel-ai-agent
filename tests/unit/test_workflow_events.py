"""Workflow Event Streaming 模块测试。"""

import pytest
from langgraph.graph import StateGraph
from typing import TypedDict

from shared.workflow_events.kinds import EventKind
from shared.workflow_events.models import (
    WorkflowEvent,
    NodeStartedEvent,
    NodeCompletedEvent,
    TokenDeltaEvent,
    StateUpdatedEvent,
    WorkflowStartedEvent,
    WorkflowCompletedEvent,
    WorkflowFailedEvent,
    NodeFailedEvent,
)
from shared.streaming.runner import WorkflowRunner, create_runner


class TestState(TypedDict):
    value: str


@pytest.fixture
def simple_graph():
    """构建简单测试 graph。"""
    builder = StateGraph(TestState)
    builder.add_node("step1", lambda x: {"value": "step1_done"})
    builder.add_node("step2", lambda x: {"value": "step2:" + x.get("value", "")})
    builder.set_entry_point("step1")
    builder.add_edge("step1", "step2")
    builder.set_finish_point("step2")
    return builder.compile()


class TestWorkflowEventModel:
    """WorkflowEvent 模型测试。"""

    def test_workflow_event_create(self):
        """测试基本 WorkflowEvent 创建。"""
        event = WorkflowEvent(workflow_id="wf-001", kind="test_event", payload={"key": "value"})
        assert event.workflow_id == "wf-001"
        assert event.kind == "test_event"
        assert event.id is not None
        assert event.timestamp > 0

    def test_token_delta_event_create(self):
        """测试 TokenDeltaEvent 创建。"""
        event = TokenDeltaEvent.create("wf-001", "hello ", "llm")
        assert event.kind == "token_delta"
        assert event.payload["delta"] == "hello "
        assert event.source == "llm"

    def test_node_started_event_create(self):
        """测试 NodeStartedEvent 创建。"""
        event = NodeStartedEvent.create("wf-001", "analysis", "AI分析评论")
        assert event.kind == "node_started"
        assert event.source == "analysis"
        assert event.payload["display_name"] == "AI分析评论"

    def test_workflow_completed_event_create(self):
        """测试 WorkflowCompletedEvent 创建。"""
        event = WorkflowCompletedEvent.create("wf-001", {"result": "success"})
        assert event.kind == "workflow_completed"
        assert event.payload == {"result": {"result": "success"}}

    def test_workflow_failed_event_create(self):
        """测试 WorkflowFailedEvent 创建。"""
        event = WorkflowFailedEvent.create("wf-001", "timeout error")
        assert event.kind == "workflow_failed"
        assert event.payload["error"] == "timeout error"


class TestWorkflowRunner:
    """WorkflowRunner 集成测试。"""

    @pytest.mark.asyncio
    async def test_runner_basic_flow(self, simple_graph):
        """测试基本工作流事件流。"""
        runner = WorkflowRunner(workflow_id="test-wf-001")
        events = []

        async for event in runner.run(simple_graph, {"value": "start"}):
            events.append(event)

        # 验证事件序列
        assert len(events) >= 2  # 至少 workflow_started 和 workflow_completed

        assert events[0].kind == "workflow_started"
        assert events[0].workflow_id == "test-wf-001"

        assert events[-1].kind == "workflow_completed"
        assert events[-1].workflow_id == "test-wf-001"

    @pytest.mark.asyncio
    async def test_runner_state_updates(self, simple_graph):
        """测试 state 更新事件。"""
        runner = create_runner("test-state-wf")
        state_events = []

        async for event in runner.run(simple_graph, {"value": "input"}):
            if event.kind == "state_updated":
                state_events.append(event)

        assert len(state_events) > 0
        assert all(e.kind == "state_updated" for e in state_events)

    @pytest.mark.asyncio
    async def test_runner_custom_workflow_id(self, simple_graph):
        """测试自定义 workflow_id。"""
        custom_id = "my-custom-workflow-id"
        runner = WorkflowRunner(workflow_id=custom_id)

        async for event in runner.run(simple_graph, {"value": "test"}):
            assert event.workflow_id == custom_id


class TestEventKind:
    """EventKind 枚举测试。"""

    def test_event_kind_values(self):
        """验证所有 EventKind 值。"""
        expected = {
            "WORKFLOW_STARTED": "workflow_started",
            "WORKFLOW_COMPLETED": "workflow_completed",
            "WORKFLOW_FAILED": "workflow_failed",
            "NODE_STARTED": "node_started",
            "NODE_COMPLETED": "node_completed",
            "NODE_FAILED": "node_failed",
            "TOKEN_DELTA": "token_delta",
            "CUSTOM_EVENT": "custom_event",
            "STATE_UPDATED": "state_updated",
        }

        for name, value in expected.items():
            assert getattr(EventKind, name).value == value

    def test_event_kind_is_string(self):
        """验证 EventKind 是字符串枚举。"""
        for kind in EventKind:
            assert isinstance(kind.value, str)
