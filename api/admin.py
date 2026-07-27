"""Admin API — Phase 3: 管理后台 API。

端点：
1. GET  /admin/runs — 历史 run 列表
2. GET  /admin/runs/{run_id} — run 详情
3. POST /admin/runs/{run_id}/replay — Event Replay
4. GET  /admin/approvals — 待审批列表
5. POST /admin/approvals/{approval_id}/resolve — 审批决策
6. GET  /admin/approvals/{approval_id} — 审批详情
7. GET  /admin/statistics — 统计信息
"""

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from shared.workflow_events.history_service import (
    list_runs,
    get_run_detail,
    get_run_events,
    replay_events,
    get_statistics,
    get_pending_approvals_count,
)
from shared.workflow_events.approval_service import (
    get_approval,
    list_pending_approvals,
    resolve_approval,
    get_approvals_by_run,
)
from shared.workflow_events.observer_service import (
    get_observer_service,
)
from shared.workflow_events.models import WorkflowEvent

router = APIRouter(prefix="/admin", tags=["admin"])


# ════════════════════════════════════════════════════════════════════════════════
# Workflow History
# ════════════════════════════════════════════════════════════════════════════════


async def admin_list_runs(
    request: Request,
    workflow_name: str | None = None,
    status: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict:
    """查询历史 run 列表。

    GET /admin/runs
    """
    return await list_runs(
        workflow_name=workflow_name,
        status=status,
        limit=limit,
        offset=offset,
    )


router.add_api_route(
    "/runs",
    admin_list_runs,
    methods=["GET"],
    summary="查询历史 Run 列表",
    description="分页查询 workflow run 记录",
)


async def admin_get_run(request: Request, run_id: str) -> dict:
    """获取 run 详情（包含完整事件流）。

    GET /admin/runs/{run_id}
    """
    detail = await get_run_detail(run_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    return detail


router.add_api_route(
    "/runs/{run_id}",
    admin_get_run,
    methods=["GET"],
    summary="获取 Run 详情",
    description="查询指定 run 的完整信息",
)


async def admin_get_run_events(
    request: Request,
    run_id: str,
    last_sequence: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
) -> dict:
    """获取 run 的事件。

    GET /admin/runs/{run_id}/events
    """
    events = await get_run_events(run_id, last_sequence, limit)
    return {"run_id": run_id, "events": events, "count": len(events)}


router.add_api_route(
    "/runs/{run_id}/events",
    admin_get_run_events,
    methods=["GET"],
    summary="获取 Run 事件",
    description="查询指定 run 的事件（支持分页）",
)


async def admin_replay_events(request: Request, run_id: str) -> StreamingResponse:
    """Event Replay：重放指定 run 的事件。

    POST /admin/runs/{run_id}/replay
    Body: {"from_sequence": 0, "to_sequence": 100}
    """
    body = await request.json()
    from_sequence = body.get("from_sequence", 0)
    to_sequence = body.get("to_sequence")  # None 表示重放到最后

    events = await replay_events(run_id, from_sequence, to_sequence)

    async def event_generator():
        for event in events:
            yield f"data: {event}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


router.add_api_route(
    "/runs/{run_id}/replay",
    admin_replay_events,
    methods=["POST"],
    summary="Event Replay",
    description="重放指定 run 的事件流",
)


# ════════════════════════════════════════════════════════════════════════════════
# Human Approval
# ════════════════════════════════════════════════════════════════════════════════


async def admin_list_approvals(request: Request) -> dict:
    """查询待审批列表。

    GET /admin/approvals
    """
    approvals = await list_pending_approvals()
    pending_count = await get_pending_approvals_count()
    return {"approvals": approvals, "pending_count": pending_count}


router.add_api_route(
    "/approvals",
    admin_list_approvals,
    methods=["GET"],
    summary="查询待审批列表",
    description="获取所有待人工审批的任务",
)


async def admin_get_approval(request: Request, approval_id: str) -> dict:
    """获取审批详情。

    GET /admin/approvals/{approval_id}
    """
    approval = await get_approval(approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail=f"Approval not found: {approval_id}")
    return approval


router.add_api_route(
    "/approvals/{approval_id}",
    admin_get_approval,
    methods=["GET"],
    summary="获取审批详情",
    description="查询指定审批的完整信息",
)


async def admin_resolve_approval(request: Request, approval_id: str) -> dict:
    """审批决策。

    POST /admin/approvals/{approval_id}/resolve
    Body: {
        "action": "approve" | "reject",
        "resolution": {"reply_content": "..."}
    }
    """
    body = await request.json()
    action = body.get("action")
    resolution = body.get("resolution", {})

    if action not in ("approve", "reject"):
        raise HTTPException(
            status_code=400,
            detail="action must be 'approve' or 'reject'",
        )

    result = await resolve_approval(approval_id, action, resolution)
    if not result:
        raise HTTPException(status_code=404, detail=f"Approval not found: {approval_id}")

    return result


router.add_api_route(
    "/approvals/{approval_id}/resolve",
    admin_resolve_approval,
    methods=["POST"],
    summary="审批决策",
    description="批准或拒绝人工审批任务",
)


# ════════════════════════════════════════════════════════════════════════════════
# Observer
# ════════════════════════════════════════════════════════════════════════════════


async def admin_list_observers(request: Request, run_id: str) -> dict:
    """获取 run 的 observer 列表。

    GET /admin/runs/{run_id}/observers
    """
    service = get_observer_service()
    observers = await service.list_observers(run_id)
    count = await service.count(run_id)
    return {"run_id": run_id, "observers": observers, "count": count}


router.add_api_route(
    "/runs/{run_id}/observers",
    admin_list_observers,
    methods=["GET"],
    summary="获取 Observer 列表",
    description="获取订阅指定 run 的客户端列表",
)


# ════════════════════════════════════════════════════════════════════════════════
# Statistics
# ════════════════════════════════════════════════════════════════════════════════


async def admin_statistics(
    request: Request,
    workflow_name: str | None = None,
    days: int = Query(default=7, ge=1, le=90),
) -> dict:
    """获取统计信息。

    GET /admin/statistics
    """
    stats = await get_statistics(workflow_name=workflow_name, days=days)
    stats["pending_approvals"] = await get_pending_approvals_count()
    return stats


router.add_api_route(
    "/statistics",
    admin_statistics,
    methods=["GET"],
    summary="获取统计信息",
    description="获取 workflow 运行统计",
)


# ════════════════════════════════════════════════════════════════════════════════
# Run Events SSE（Admin Panel 订阅）
# ════════════════════════════════════════════════════════════════════════════════

from shared.workflow_events.event_store import subscribe_with_history


def format_sse(data: dict) -> str:
    return f"data: {data}\n\n"


async def admin_subscribe_run(request: Request, run_id: str) -> StreamingResponse:
    """Admin Panel 订阅 run 事件。

    GET /admin/runs/{run_id}/subscribe
    """
    last_sequence = int(request.query_params.get("last_sequence", 0))

    async def event_generator():
        async for event in subscribe_with_history(run_id, last_sequence):
            yield format_sse(event.model_dump())

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


router.add_api_route(
    "/runs/{run_id}/subscribe",
    admin_subscribe_run,
    methods=["GET"],
    summary="订阅 Run 事件（Admin）",
    description="Admin Panel 实时订阅指定 run 的事件流",
)
