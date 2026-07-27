"""Phase 3 功能测试。

验证：
1. Human Approval 流程
2. Interrupt Handler
3. Workflow History
4. Observer Service
"""

import pytest

pytestmark = pytest.mark.skipif(
    True,  # 需要 PostgreSQL + Redis
    reason="Phase 3 requires PostgreSQL + Redis",
)


@pytest.mark.asyncio
async def test_approval_lifecycle():
    """测试审批生命周期：创建 → 审批 → resume。"""
    from shared.workflow_events.approval_service import (
        create_approval,
        get_approval,
        resolve_approval,
        ApprovalStatus,
    )

    # 创建审批
    approval = await create_approval(
        run_id="run_test",
        thread_id="thread_test",
        workflow_name="review_operation",
        task_type="human_review",
        payload={"reply_content": "test reply"},
    )

    assert approval["status"] == ApprovalStatus.PENDING.value
    assert approval["task_type"] == "human_review"

    # 获取审批
    fetched = await get_approval(approval["id"])
    assert fetched["id"] == approval["id"]

    # 审批通过
    result = await resolve_approval(
        approval["id"],
        action="approve",
        resolution={"reply_content": "approved reply"},
    )
    assert result["status"] == ApprovalStatus.APPROVED.value


@pytest.mark.asyncio
async def test_history_service():
    """测试历史记录查询。"""
    from shared.workflow_events.history_service import (
        list_runs,
        replay_events,
        get_statistics,
    )

    # 列出 run
    result = await list_runs(limit=10)
    assert "runs" in result
    assert "total" in result

    # 统计信息
    stats = await get_statistics(days=7)
    assert "total_runs" in stats
    assert "completed_runs" in stats


@pytest.mark.asyncio
async def test_observer_service():
    """测试多人订阅。"""
    from shared.workflow_events.observer_service import (
        get_observer_service,
        ObserverContext,
    )

    service = get_observer_service()
    run_id = "run_test"

    # Observer A 加入
    obs_a = await service.join(run_id, client_type="chrome_extension")
    count_a = await service.count(run_id)
    assert count_a == 1

    # Observer B 加入
    obs_b = await service.join(run_id, client_type="admin_panel")
    count_b = await service.count(run_id)
    assert count_b == 2

    # Observer A 离开
    await service.leave(run_id, obs_a)
    count_c = await service.count(run_id)
    assert count_c == 1


@pytest.mark.asyncio
async def test_observer_context():
    """测试 Observer 上下文管理器。"""
    from shared.workflow_events.observer_service import ObserverContext

    run_id = "run_test"

    async with ObserverContext(run_id, "test_client") as obs_id:
        assert obs_id is not None

    # 离开后自动清理
    service = get_observer_service()
    count = await service.count(run_id)
    assert count == 0


@pytest.mark.asyncio
async def test_interrupt_handler():
    """测试 interrupt 处理。"""
    from shared.workflow_events.interrupt_handler import (
        InterruptPending,
        InterruptAwareRunner,
    )

    # InterruptPending 异常
    exc = InterruptPending("approval_123", {"task_type": "human_review"})
    assert exc.approval_id == "approval_123"
    assert exc.payload["task_type"] == "human_review"
