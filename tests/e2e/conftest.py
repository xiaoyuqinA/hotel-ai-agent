"""E2E 测试共享 fixtures。

提供：
1. `hotel_config_service` fixture：使用临时目录隔离酒店配置
2. `app` fixture：FastAPI app 实例，配置替换为临时目录
3. SSE mock fixtures：模拟 Event Store（PostgreSQL/Redis）
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from shared.hotel_config import (
    HotelConfigService,
    YamlHotelConfigRepository,
)


@pytest.fixture
def temp_hotel_base():
    """创建临时酒店配置目录，测试结束后自动清理。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def hotel_config_service(temp_hotel_base):
    """创建使用临时目录的 HotelConfigService。"""
    repo = YamlHotelConfigRepository(temp_hotel_base)
    return HotelConfigService(repo=repo)


@pytest.fixture
def test_client(hotel_config_service):
    """创建 TestClient，注入临时目录的 HotelConfigService。"""
    # 替换 app 中的 _config_service 全局单例
    import api.hotel_config as hotel_config_module

    # 保存原始 _get_service
    original_get_service = hotel_config_module._get_service

    def _get_service_override():
        return hotel_config_service

    hotel_config_module._get_service = _get_service_override

    # 因为从 main 导入 app，lifespan 不在此处执行
    # 需要手动清理 testclient 的 asyncio 循环
    client = TestClient(app)

    yield client

    # 恢复原始 _get_service
    hotel_config_module._get_service = original_get_service


# ── SSE Event Store Mock ──────────────────────────────────────────────────


@pytest.fixture(autouse=False)
def mock_event_store():
    """Mock shared.workflow_events.event_store 所有异步函数。

    由于 api.sse 在模块顶层直接 import 了这些函数（不是延迟 import），
    mock 必须作用于 api.sse 模块的命名空间，而不是 event_store 模块。
    """

    async def mock_get_run_record(run_id):
        mock_data = {
            "run_test_001": {
                "id": "run_test_001",
                "workflow_name": "review_operation",
                "status": "pending",
                "thread_id": "thread_test_001",
            },
            "run_completed": {
                "id": "run_completed",
                "status": "completed",
            },
        }
        return mock_data.get(run_id)

    patches = [
        # Mock api.sse 模块中导入的函数名称
        patch("api.sse.create_run_record", AsyncMock(return_value=None)),
        patch("api.sse.get_run_record", AsyncMock(side_effect=mock_get_run_record)),
        patch("api.sse.save_and_publish", AsyncMock(return_value=None)),
        patch("api.sse.subscribe_with_history", AsyncMock(return_value=None)),
        patch("api.sse.cancel_workflow_run", AsyncMock(return_value=True)),
    ]
    for p in patches:
        p.start()
    yield
    for p in patches:
        p.stop()


@pytest.fixture(autouse=False)
def mock_event_store_update_run_status():
    """Mock update_run_status（在 _run_workflow_background 内部延迟导入）。"""
    with patch("api.sse.update_run_status", AsyncMock(return_value=None), create=True):
        yield


# ── Capturing save_and_publish fixture ────────────────────────────────────


@pytest.fixture(autouse=False)
def captured_event_store():
    """Mock Event Store 并捕获所有 save_and_publish 调用。

    提供 published_events 列表供测试验证。
    """

    async def mock_get_run_record(run_id):
        return {
            "id": run_id,
            "workflow_name": "review_operation",
            "status": "running",
            "thread_id": "thread_test_001",
        }

    published = []

    async def mock_save_and_publish(event):
        published.append(event)

    patches = [
        patch("api.sse.create_run_record", AsyncMock(return_value=None)),
        patch("api.sse.get_run_record", AsyncMock(side_effect=mock_get_run_record)),
        patch("api.sse.save_and_publish", AsyncMock(side_effect=mock_save_and_publish)),
        patch("api.sse.subscribe_with_history", AsyncMock(return_value=None)),
        patch("api.sse.cancel_workflow_run", AsyncMock(return_value=True)),
    ]
    for p in patches:
        p.start()
    yield published
    for p in patches:
        p.stop()


# ── Agent Mock Fixtures ───────────────────────────────────────────────────


@pytest.fixture(autouse=False)
def mock_agents():
    """Mock 所有 LLM Agent 调用（analysis_node + generate_reply_node）。

    analysis_node 需要 stream_agent_with_events 产生可被 ReviewAnalysisResult
    model_validate_json 解析的 token 序列。这里直接 yield 完整的 JSON token，
    表示 Low severity 评论。

    generate_reply_node 需要产生一个 JSON 格式的回复。
    """

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

    p = patch(
        "shared.runtime.streaming.stream_agent_with_events",
        _mock_stream_with_events,
    )
    p.start()
    yield
    p.stop()
