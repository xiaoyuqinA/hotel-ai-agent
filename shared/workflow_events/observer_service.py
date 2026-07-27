"""Multi User Observer Service — Phase 3: 多人同时订阅同一 run。

功能：
1. 跟踪每个 run 的 observer 数量
2. 提供 observer 计数 API
3. 支持 observer 加入/离开事件

架构：
┌─────────────────┐
│  Chrome Ext A  │──► Redis Pub/Sub ──► 事件
│  Chrome Ext B  │──► Redis Pub/Sub ──► 事件
│  Admin Panel    │──► Redis Pub/Sub ──► 事件
└─────────────────┘
        │
        ▼
┌─────────────────┐
│  ObserverStore  │
│  (内存计数器)    │
└─────────────────┘
"""

import asyncio
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator

from shared.workflow_events.models import WorkflowEvent


@dataclass
class Observer:
    """订阅者。"""

    id: str
    run_id: str
    client_type: str = "unknown"  # "chrome_extension" | "admin_panel" | "api_client"
    metadata: dict[str, Any] = field(default_factory=dict)
    connected_at: float = field(default_factory=lambda: asyncio.get_event_loop().time())


class ObserverService:
    """Observer 管理服务。

    使用 Redis 实现多人订阅同一 run。

    原理：
    - 每个 run 有一个 Redis 频道（已实现）
    - ObserverService 跟踪 observer 数量
    - 提供 observer_join / observer_leave 事件
    """

    def __init__(self):
        # run_id -> set of observer_ids
        self._observers: dict[str, dict[str, Observer]] = defaultdict(dict)
        self._lock = asyncio.Lock()

    async def join(
        self,
        run_id: str,
        client_type: str = "unknown",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Observer 加入订阅。

        Args:
            run_id: Workflow Run ID
            client_type: 客户端类型
            metadata: 附加信息

        Returns:
            observer_id
        """
        observer_id = f"obs_{uuid.uuid4().hex[:12]}"

        async with self._lock:
            self._observers[run_id][observer_id] = Observer(
                id=observer_id,
                run_id=run_id,
                client_type=client_type,
                metadata=metadata or {},
            )

        # 发布 observer_join 事件
        await self._publish_observer_event(run_id, "observer_join", observer_id, client_type)

        return observer_id

    async def leave(self, run_id: str, observer_id: str) -> None:
        """Observer 离开订阅。"""
        async with self._lock:
            self._observers[run_id].pop(observer_id, None)
            # 如果没有 observer 了，清理
            if not self._observers[run_id]:
                self._observers.pop(run_id, None)

        # 发布 observer_leave 事件
        await self._publish_observer_event(run_id, "observer_leave", observer_id)

    async def count(self, run_id: str) -> int:
        """获取 observer 数量。"""
        async with self._lock:
            return len(self._observers.get(run_id, {}))

    async def list_observers(self, run_id: str) -> list[dict]:
        """列出所有 observer。"""
        async with self._lock:
            observers = self._observers.get(run_id, {})
            return [
                {
                    "id": obs.id,
                    "client_type": obs.client_type,
                    "metadata": obs.metadata,
                }
                for obs in observers.values()
            ]

    async def get_observer(self, run_id: str, observer_id: str) -> dict | None:
        """获取指定 observer 信息。"""
        async with self._lock:
            obs = self._observers.get(run_id, {}).get(observer_id)
            if obs:
                return {
                    "id": obs.id,
                    "run_id": obs.run_id,
                    "client_type": obs.client_type,
                    "metadata": obs.metadata,
                }
            return None

    async def _publish_observer_event(
        self,
        run_id: str,
        event_type: str,
        observer_id: str,
        client_type: str | None = None,
    ) -> None:
        """发布 observer 事件。"""
        from shared.workflow_events.event_store import publish_event
        from shared.workflow_events.models import CustomEvent

        data = {"event_type": event_type, "observer_id": observer_id}
        if client_type:
            data["client_type"] = client_type

        event = CustomEvent.create(
            workflow_id=run_id,
            event_type=f"observer_{event_type}",
            data=data,
        )
        await publish_event(event)


# ── Observer Context Manager ─────────────────────────────────────────────────

class ObserverContext:
    """Observer 上下文管理器。

    使用方式：
    async with ObserverContext(run_id, client_type) as obs_id:
        async for event in subscribe_events(run_id):
            yield event
    # 自动离开
    """

    def __init__(
        self,
        run_id: str,
        client_type: str = "unknown",
        metadata: dict[str, Any] | None = None,
    ):
        self.run_id = run_id
        self.client_type = client_type
        self.metadata = metadata
        self.observer_id: str | None = None

    async def __aenter__(self) -> str:
        service = get_observer_service()
        self.observer_id = await service.join(
            self.run_id,
            self.client_type,
            self.metadata,
        )
        return self.observer_id

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.observer_id:
            service = get_observer_service()
            await service.leave(self.run_id, self.observer_id)


# ── 模块级单例 ────────────────────────────────────────────────────────────────

_service: ObserverService | None = None


def get_observer_service() -> ObserverService:
    """获取 ObserverService 单例。"""
    global _service
    if _service is None:
        _service = ObserverService()
    return _service
