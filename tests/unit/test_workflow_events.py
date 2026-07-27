"""Workflow Event Streaming 模块测试。"""

import pytest
from langgraph.graph import StateGraph
from typing import TypedDict

from shared.workflow_events.kinds import EventKind, BusinessEvent
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
    CustomEvent,
    ToolCallEvent,
    WorkflowCategory,
)
from shared.streaming.runner import WorkflowRunner, create_runner
from shared.workflow_events.mapper import ProjectionMapper


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
        event = WorkflowEvent(workflow_id="wf-001", kind="test_event", category="progress", payload={"key": "value"})
        assert event.workflow_id == "wf-001"
        assert event.kind == "test_event"
        assert event.category == "progress"
        assert event.id is not None
        assert event.timestamp > 0

    def test_token_delta_event_create(self):
        """测试 TokenDeltaEvent 创建。"""
        event = TokenDeltaEvent.create("wf-001", "hello ")
        assert event.kind == "token_delta"
        assert event.payload["delta"] == "hello "
        assert event.workflow_id == "wf-001"

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
        """测试 state 更新事件。

        注意：v3 updates 投影不产生 state_updated 事件，
        state 更新通过 messages 投影的 chunk 机制处理。
        此测试仅验证 runner 能正常消费事件流。
        """
        runner = create_runner("test-state-wf")
        events = []

        async for event in runner.run(simple_graph, {"value": "input"}):
            events.append(event)

        # 验证至少有事开始和结束事件
        assert len(events) >= 2
        assert events[0].kind == "workflow_started"
        assert events[-1].kind == "workflow_completed"

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
            "TOOL_CALL": "tool_call",
            "CUSTOM_EVENT": "custom_event",
            "STATE_UPDATED": "state_updated",
        }

        for name, value in expected.items():
            assert getattr(EventKind, name).value == value

    def test_event_kind_is_string(self):
        """验证 EventKind 是字符串枚举。"""
        for kind in EventKind:
            assert isinstance(kind.value, str)


class TestBusinessEvent:
    """BusinessEvent 枚举测试。"""

    def test_business_event_values(self):
        """验证所有 BusinessEvent 值。"""
        expected = {
            "ANALYSIS_STARTED": "analysis_started",
            "ANALYSIS_PROGRESS": "analysis_progress",
            "ANALYSIS_COMPLETED": "analysis_completed",
            "ANALYSIS_FAILED": "analysis_failed",
            "GENERATION_STARTED": "generation_started",
            "GENERATION_PROGRESS": "generation_progress",
            "GENERATION_COMPLETED": "generation_completed",
            "GENERATION_FAILED": "generation_failed",
            "REVIEW_STARTED": "review_started",
            "REVIEW_COMPLETED": "review_completed",
            "REVIEW_FAILED": "review_failed",
            "COMMENT_RECEIVED": "comment_received",
        }

        for name, value in expected.items():
            assert getattr(BusinessEvent, name).value == value

    def test_business_event_is_string(self):
        """验证 BusinessEvent 是字符串枚举。"""
        for event in BusinessEvent:
            assert isinstance(event.value, str)


class TestWorkflowCategory:
    """WorkflowCategory 枚举测试。"""

    def test_category_values(self):
        """验证所有 category 值。"""
        expected = {
            "PROGRESS": "progress",
            "MESSAGE": "message",
            "TOOL": "tool",
            "STATE": "state",
            "SYSTEM": "system",
        }

        for name, value in expected.items():
            assert getattr(WorkflowCategory, name).value == value


class TestProjectionMapperCustom:
    """ProjectionMapper custom 事件转换测试。"""

    def test_analysis_started_transforms_to_node_started(self):
        """analysis_started → NodeStartedEvent"""
        mapper = ProjectionMapper(workflow_id="test-wf")
        raw_event = {
            "method": "custom",
            "params": {
                "data": {
                    "event": BusinessEvent.ANALYSIS_STARTED,
                    "message": "正在分析客户评论",
                }
            },
        }

        result = mapper.transform(raw_event)

        assert result is not None
        assert isinstance(result, NodeStartedEvent)
        assert result.kind == "node_started"
        assert result.source == "analysis"
        assert result.payload["display_name"] == "基础分析"
        assert result.category == "progress"

    def test_generation_completed_transforms_to_node_completed(self):
        """generation_completed → NodeCompletedEvent"""
        mapper = ProjectionMapper(workflow_id="test-wf")
        raw_event = {
            "method": "custom",
            "params": {
                "data": {
                    "event": BusinessEvent.GENERATION_COMPLETED,
                }
            },
        }

        result = mapper.transform(raw_event)

        assert result is not None
        assert isinstance(result, NodeCompletedEvent)
        assert result.kind == "node_completed"
        assert result.source == "generation"
        assert result.category == "progress"

    def test_analysis_failed_transforms_to_node_failed(self):
        """analysis_failed → NodeFailedEvent"""
        mapper = ProjectionMapper(workflow_id="test-wf")
        raw_event = {
            "method": "custom",
            "params": {
                "data": {
                    "event": BusinessEvent.ANALYSIS_FAILED,
                    "error": "LLM API 超时",
                }
            },
        }

        result = mapper.transform(raw_event)

        assert result is not None
        assert isinstance(result, NodeFailedEvent)
        assert result.kind == "node_failed"
        assert result.source == "analysis"
        assert result.payload["error"] == "LLM API 超时"
        assert result.category == "progress"

    def test_review_started_transforms_to_node_started(self):
        """review_started → NodeStartedEvent"""
        mapper = ProjectionMapper(workflow_id="test-wf")
        raw_event = {
            "method": "custom",
            "params": {
                "data": {
                    "event": BusinessEvent.REVIEW_STARTED,
                    "message": "正在审核回复",
                }
            },
        }

        result = mapper.transform(raw_event)

        assert result is not None
        assert isinstance(result, NodeStartedEvent)
        assert result.source == "review"
        assert result.payload["display_name"] == "审核回复"

    def test_unknown_custom_event_transforms_to_custom_event(self):
        """未知 custom 事件 → CustomEvent"""
        mapper = ProjectionMapper(workflow_id="test-wf")
        raw_event = {
            "method": "custom",
            "params": {
                "data": {
                    "event": "custom_action",
                    "message": "自定义消息",
                }
            },
        }

        result = mapper.transform(raw_event)

        assert result is not None
        assert isinstance(result, CustomEvent)
        assert result.kind == "custom_event"
        assert result.payload["event_type"] == "custom_action"

    def test_values_event_transforms_to_state_updated(self):
        """values → StateUpdatedEvent"""
        mapper = ProjectionMapper(workflow_id="test-wf")
        raw_event = {
            "method": "values",
            "params": {
                "data": {"value": "test_result"},
            },
        }

        result = mapper.transform(raw_event)

        assert result is not None
        assert isinstance(result, StateUpdatedEvent)
        assert result.kind == "state_updated"
        assert result.payload["state"]["value"] == "test_result"
        assert result.category == "state"

    def test_events_have_sequence(self):
        """验证事件有 sequence 号"""
        mapper = ProjectionMapper(workflow_id="test-wf")
        raw_event = {
            "seq": 42,
            "method": "custom",
            "params": {
                "data": {
                    "event": BusinessEvent.ANALYSIS_STARTED,
                }
            },
        }

        result = mapper.transform(raw_event)

        assert result is not None
        assert result.sequence == 42
