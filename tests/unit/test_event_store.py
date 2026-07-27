"""Phase 2 Event Store 测试。

验证 PostgreSQL + Redis Pub/Sub 流程。
需要在 .env 中配置 POSTGRES_HOST, REDIS_HOST。
"""

import pytest

# 跳过测试如果 Event Store 依赖未安装
try:
    from shared.workflow_events.event_store import (
        init_db,
        close_db,
        close_redis,
        save_event,
        get_events_after,
        create_run_record,
        update_run_status,
        get_run_record,
        publish_event,
        subscribe_events,
    )
    from shared.workflow_events.redis_run_manager import (
        get_run_manager,
        RunStatus,
    )
    from shared.workflow_events.models import WorkflowEvent, WorkflowStartedEvent
    EVENT_STORE_AVAILABLE = True
except ImportError:
    EVENT_STORE_AVAILABLE = False


pytestmark = pytest.mark.skipif(
    not EVENT_STORE_AVAILABLE,
    reason="Event Store dependencies not installed",
)


@pytest.fixture
async def setup_event_store():
    """初始化 Event Store。"""
    await init_db()
    yield
    await close_redis()
    await close_db()


@pytest.mark.asyncio
async def test_run_lifecycle(setup_event_store):
    """测试 Run 生命周期：创建 → 更新状态 → 查询。"""
    run_id = "test_run_001"

    # 创建 run
    await create_run_record(
        run_id=run_id,
        workflow_name="review_operation",
        thread_id="thread_test",
        input_data={"reviews": "test"},
    )

    # 查询 run
    run = await get_run_record(run_id)
    assert run is not None
    assert run["id"] == run_id
    assert run["workflow_name"] == "review_operation"
    assert run["status"] == "pending"

    # 更新状态
    await update_run_status(run_id, "running")
    run = await get_run_record(run_id)
    assert run["status"] == "running"

    # 更新为完成
    await update_run_status(run_id, "completed", result={"reply": "test reply"})
    run = await get_run_record(run_id)
    assert run["status"] == "completed"
    assert run["result"] == {"reply": "test reply"}


@pytest.mark.asyncio
async def test_event_persistence(setup_event_store):
    """测试事件持久化。"""
    run_id = "test_run_event_001"

    # 创建事件
    event = WorkflowEvent(
        workflow_id=run_id,
        sequence=1,
        category="system",
        kind="workflow_started",
        source="system",
        payload={},
    )

    # 保存
    await save_event(event)

    # 查询
    events = await get_events_after(run_id, 0)
    assert len(events) == 1
    assert events[0].kind == "workflow_started"
    assert events[0].sequence == 1

    # 断线恢复：查询 last_sequence=1 之后
    events = await get_events_after(run_id, 1)
    assert len(events) == 0


@pytest.mark.asyncio
async def test_redis_pubsub(setup_event_store):
    """测试 Redis Pub/Sub。"""
    import asyncio

    run_id = "test_run_pubsub_001"
    event = WorkflowStartedEvent.create(run_id)

    # 启动订阅任务（延迟启动确保订阅在前）
    received = []

    async def subscriber():
        async for evt in subscribe_events(run_id):
            received.append(evt)
            if len(received) >= 1:
                break

    # 先订阅，再发布
    sub_task = asyncio.create_task(subscriber())
    await asyncio.sleep(0.1)  # 等待订阅建立

    # 发布事件
    await publish_event(event)

    # 等待订阅完成
    await asyncio.wait_for(sub_task, timeout=5)

    assert len(received) == 1
    assert received[0].kind == "workflow_started"


@pytest.mark.asyncio
async def test_run_manager(setup_event_store):
    """测试 WorkflowRunManager。"""
    manager = get_run_manager()

    # 创建 run
    run = await manager.create_run(
        workflow_name="review_operation",
        input_data={"reviews": "test"},
        thread_id="thread_test",
    )

    assert "id" in run
    assert run["workflow_name"] == "review_operation"
    assert run["status"] == RunStatus.PENDING

    # 获取 run
    run2 = await manager.get_run(run["id"])
    assert run2 is not None
    assert run2["id"] == run["id"]

    # 更新状态
    await manager.update_status(run["id"], RunStatus.RUNNING)
    run3 = await manager.get_run(run["id"])
    assert run3["status"] == RunStatus.RUNNING


@pytest.mark.asyncio
async def test_subscribe_with_history(setup_event_store):
    """测试订阅时包含历史事件。"""
    import asyncio

    from shared.workflow_events.event_store import subscribe_with_history

    run_id = "test_run_history_001"

    # 预先保存事件
    for i in range(3):
        event = WorkflowEvent(
            workflow_id=run_id,
            sequence=i + 1,
            category="system",
            kind=f"event_{i}",
            payload={"index": i},
        )
        await save_event(event)

    # 订阅（从 sequence=2 开始，应该只收到 event_2, event_3）
    received = []
    async for event in subscribe_with_history(run_id, last_sequence=1):
        received.append(event)
        if len(received) >= 3:
            break

    assert len(received) == 3
    # 前 2 个是历史事件
    assert received[0].sequence == 2
    assert received[1].sequence == 3
