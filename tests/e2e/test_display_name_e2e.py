"""display_name 全链路端到端集成测试。

从 WorkflowRuntime 初始化 → WorkflowRunner 执行 → Event 输出，
验证每一步的 display_name 正确传递。

不使用 HTTP API（避免 asyncio.create_task 在 TestClient 中不执行的
事件循环冲突问题），而是直接通过 Python API 驱动整个后端流水线：

1. 初始化 WorkflowRuntime（编译 LangGraph graph + 启动 checkpointer）
2. 直接调用 WorkflowRunner.run() 执行工作流
3. 通过 mock 的 event_store 捕获所有 save_and_publish 调用
4. 验证事件序列和 display_name

测试范围：
1. 正常流程（Low severity）：完整事件序列的 display_name
2. 异常流程：工作流执行失败 → WorkflowFailedEvent(display_name="工作流失败")
3. JSON 序列化：所有事件的 model_dump_json 包含 display_name 字段

依赖：
- mock_agents：mock LLM agent 调用（无需 LLM）
- captured_event_store：mock Event Store，捕获所有 save_and_publish 调用
- init_runtime：初始化 WorkflowRuntime（编译 LangGraph graph）
"""

import asyncio
import json
import time
from unittest.mock import AsyncMock, patch

import pytest

from api.main import _runtime
from shared.streaming.runner import WorkflowRunner
from shared.workflow_events.display_names import DisplayName


@pytest.fixture(scope="module")
def event_loop():
    """创建模块级 event loop。"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    # 等待所有 pending 任务完成
    pending = asyncio.all_tasks(loop)
    for task in pending:
        task.cancel()
    loop.run_until_complete(asyncio.sleep(0))
    loop.close()
    asyncio.set_event_loop(None)


@pytest.fixture(scope="module")
def init_runtime(event_loop):
    """初始化 WorkflowRuntime（编译 LangGraph graph + 启动 checkpointer）。

    模块级 fixture，所有测试共享已编译的 graph。
    """
    event_loop.run_until_complete(_runtime.startup())
    yield
    event_loop.run_until_complete(_runtime.shutdown())


@pytest.fixture(autouse=True)
def no_db():
    """Mock 所有 PostgreSQL 和 Redis 调用，防止 tests 连接真实数据库。

    runner.py 使用 `from ...event_store import is_workflow_cancelled`，
    绑定的是模块级局部引用，所以需要在 runner 模块上 patch。
    """
    patches = [
        patch("shared.workflow_events.event_store.save_event", AsyncMock()),
        patch("shared.workflow_events.event_store.publish_event", AsyncMock()),
        patch(
            "shared.streaming.runner.is_workflow_cancelled",
            AsyncMock(return_value=False),
        ),
    ]
    for p in patches:
        p.start()
    yield
    for p in patches:
        p.stop()


@pytest.fixture(autouse=False)
def captured_event_store():
    """捕获所有 save_and_publish 调用。"""

    published = []

    async def mock_save_and_publish(event):
        published.append(event)

    with patch(
        "shared.workflow_events.event_store.save_and_publish",
        side_effect=mock_save_and_publish,
    ):
        yield published


@pytest.fixture(autouse=False)
def mock_agents():
    """Mock LLM agent 调用。"""

    async def _mock_analysis_stream(
        agent_name, user_input, session=None, session_id=None
    ):
        yield "node_started", ""
        yield "token", '{"issue_severity": {"level": "Low", "reason": "正面评论"}, '
        yield (
            "token",
            '"customer_sentiment": {"label": "positive", "confidence": 0.95}, ',
        )
        yield "token", '"customer_intent": "praise"}'
        yield "node_completed", ""

    async def _mock_reply_stream(agent_name, user_input, session=None, session_id=None):
        yield "node_started", ""
        yield "token", '{"reply_content": "感谢您的反馈，很高兴您满意！"}'
        yield "node_completed", ""

    import shared.runtime.streaming as streaming_module

    original_fn = streaming_module.stream_agent_with_events

    async def _mock_stream_with_events(
        agent_name, user_input, session=None, session_id=None
    ):
        if agent_name == "review_analysis_agent":
            async for chunk in _mock_analysis_stream(
                agent_name, user_input, session, session_id
            ):
                yield chunk
        elif agent_name == "review_reply_agent":
            async for chunk in _mock_reply_stream(
                agent_name, user_input, session, session_id
            ):
                yield chunk
        else:
            async for chunk in original_fn(agent_name, user_input, session, session_id):
                yield chunk

    patcher = patch(
        "shared.runtime.streaming.stream_agent_with_events",
        _mock_stream_with_events,
    )
    patcher.start()
    yield
    patcher.stop()


class TestDisplayNameE2E:
    """display_name 全链路端到端测试。"""

    @pytest.mark.asyncio
    async def test_normal_flow_event_sequence(
        self, init_runtime, mock_agents, captured_event_store
    ):
        """正常流程（Low severity）完整事件序列的 display_name。

        直接通过 WorkflowRuntime + WorkflowRunner 执行工作流，
        验证每一步的 display_name 正确传递。
        """
        import shared.workflow_events.event_store as store_events

        workflow = _runtime.get_workflow("review_operation")
        input_data = workflow.input_mapper(("hotel_001", "房间很干净，服务很好"))
        config = {"configurable": {"thread_id": "test_thread_001"}}

        runner = WorkflowRunner(workflow_id="test_run_001")

        events = []
        async for event in runner.run(workflow.graph, input_data, config):
            events.append(event)
            await store_events.save_and_publish(event)

        # 验证事件序列
        assert len(events) >= 3, f"事件数量不足: {len(events)}"

        # workflow_started 由 _run_workflow_background 发布，WorkflowRunner 不生成
        # 验证第一个事件是 state_updated 或 node_started
        # 查找各阶段事件
        analysis_started = self._find_event(events, "node_started", "analysis")
        assert analysis_started is not None
        assert analysis_started.display_name == DisplayName.ANALYSIS_STARTED
        assert analysis_started.category == "progress"

        analysis_completed = self._find_event(events, "node_completed", "analysis")
        assert analysis_completed is not None
        assert analysis_completed.display_name == DisplayName.ANALYSIS_COMPLETED

        gen_started = self._find_event(events, "node_started", "generation")
        assert gen_started is not None
        assert gen_started.display_name == DisplayName.GENERATION_STARTED

        gen_completed = self._find_event(events, "node_completed", "generation")
        assert gen_completed is not None
        assert gen_completed.display_name == DisplayName.GENERATION_COMPLETED

        # 最后一个事件必须是 workflow_completed（由 ProjectionMapper 生成）
        assert events[-1].kind == "workflow_completed"
        assert events[-1].display_name == DisplayName.WORKFLOW_COMPLETED
        assert events[-1].category == "system"

    @pytest.mark.asyncio
    async def test_display_name_in_json(
        self, init_runtime, mock_agents, captured_event_store
    ):
        """所有事件的 model_dump_json 包含 display_name 字段。"""
        workflow = _runtime.get_workflow("review_operation")
        input_data = workflow.input_mapper(("hotel_001", "服务很好"))
        config = {"configurable": {"thread_id": "test_thread_002"}}

        runner = WorkflowRunner(workflow_id="test_run_002")

        async for event in runner.run(workflow.graph, input_data, config):
            json_str = event.model_dump_json()
            parsed = json.loads(json_str)
            assert "display_name" in parsed, f"事件 {event.kind} 缺少 display_name 字段"

    @pytest.mark.asyncio
    async def test_workflow_failed_display_name(
        self, init_runtime, captured_event_store
    ):
        """工作流执行失败 → WorkflowFailedEvent(display_name=DisplayName.WORKFLOW_FAILED)。

        通过 mock stream_agent_with_events 抛出异常模拟节点失败。
        """
        import shared.workflow_events.event_store as store_events

        async def _failing_stream(
            agent_name, user_input, session=None, session_id=None
        ):
            yield "node_started", ""
            raise ValueError("模拟分析失败")

        with patch(
            "shared.runtime.streaming.stream_agent_with_events",
            _failing_stream,
        ):
            workflow = _runtime.get_workflow("review_operation")
            input_data = workflow.input_mapper(("hotel_001", "测试失败"))
            config = {"configurable": {"thread_id": "test_thread_003"}}

            runner = WorkflowRunner(workflow_id="test_run_003")

            events = []
            async for event in runner.run(workflow.graph, input_data, config):
                events.append(event)
                await store_events.save_and_publish(event)

            # 最后一个事件必须是 workflow_failed
            assert events[-1].kind == "workflow_failed"
            assert events[-1].display_name == DisplayName.WORKFLOW_FAILED
            assert events[-1].category == "system"
            assert "error" in events[-1].model_dump()

    # ── HTTP API 层测试（轻量，只验证请求/响应） ──────────────────────────

    def test_create_review_run_returns_run_id(self, init_runtime):
        """HTTP API：POST /review/run 返回正确的 run_id 和 status。

        这是一个轻量级测试，只验证 HTTP 请求/响应格式正确，
        不等待后台任务完成（后台任务由 asyncio.create_task 管理，
        在 TestClient 的 anyio event loop 中执行）。
        """
        from fastapi.testclient import TestClient
        from api.main import app

        with patch("api.sse.create_run_record", AsyncMock(return_value=None)):
            with patch("api.sse.save_and_publish", AsyncMock(return_value=None)):
                client = TestClient(app)
                response = client.post(
                    "/review/run",
                    json={
                        "reviews_content": "房间很干净，服务很好",
                        "hotel_id": "hotel_001",
                    },
                )

        assert response.status_code == 200
        data = response.json()
        assert "run_id" in data
        assert data["run_id"].startswith("run_")
        assert data["status"] == "pending"
        assert "thread_id" in data

    # ── Helper 方法 ────────────────────────────────────────────────────────

    @staticmethod
    def _find_event(events, kind, source=None):
        for e in events:
            if e.kind == kind:
                if source is None or e.source == source:
                    return e
        return None
