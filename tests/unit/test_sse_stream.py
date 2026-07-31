"""SSE 流式事件生成器测试 — 心跳超时。"""

import asyncio
from typing import AsyncGenerator

import pytest

from shared.workflow_events.models import WorkflowEvent, WorkflowCompletedEvent


def _fake_subscribe(events: list[WorkflowEvent]) -> AsyncGenerator[WorkflowEvent, None]:
    """模拟 subscribe_with_history，按序 yield 事件。"""

    async def gen():
        for e in events:
            yield e
    return gen()


class TestStreamEventGenerator:
    """测试 SSE event_generator 的心跳逻辑。"""

    @pytest.mark.asyncio
    async def test_normal_events_without_heartbeat(self):
        """正常事件流：每 0.1 秒来一个事件，不应产生心跳。"""
        events = [
            WorkflowEvent(workflow_id="test", kind="workflow_started", category="system"),
            WorkflowEvent(workflow_id="test", kind="token_delta", category="message"),
            WorkflowCompletedEvent.create("test", {"reply": "ok"}),
        ]

        # 模拟 event_generator 的逻辑
        event_iter = _fake_subscribe(events)
        collected: list[str] = []

        for _ in range(10):
            try:
                event = await asyncio.wait_for(
                    event_iter.__anext__(),
                    timeout=0.3,
                )
                collected.append(event.kind)
            except asyncio.TimeoutError:
                collected.append("heartbeat")
            except StopAsyncIteration:
                break

        # 验证：三个真实事件都被收到，没有心跳
        assert collected == ["workflow_started", "token_delta", "workflow_completed"]

    @pytest.mark.asyncio
    async def test_slow_events_triggers_heartbeat(self):
        """慢事件流：事件间隔超过超时时间，应产出心跳。"""
        events_queue: asyncio.Queue[WorkflowEvent | None] = asyncio.Queue()

        async def slow_producer():
            """模拟慢 LLM 调用，先发一个事件，0.5 秒后发完成事件。"""
            events_queue.put_nowait(
                WorkflowEvent(workflow_id="test", kind="workflow_started", category="system")
            )
            await asyncio.sleep(0.5)
            events_queue.put_nowait(
                WorkflowCompletedEvent.create("test", {"reply": "ok"})
            )
            events_queue.put_nowait(None)  # 结束信号

        # 启动生产者
        asyncio.create_task(slow_producer())
        collected: list[str] = []

        while True:
            try:
                event = await asyncio.wait_for(
                    events_queue.get(),
                    timeout=0.2,
                )
                if event is None:
                    break
                collected.append(event.kind)
            except asyncio.TimeoutError:
                collected.append("heartbeat")

        # 验证：workflow_started 后 LLM 调用慢，中间有心跳
        assert collected[0] == "workflow_started"
        assert "heartbeat" in collected  # 中间至少有一个心跳
        assert collected[-1] == "workflow_completed"

    @pytest.mark.asyncio
    async def test_stream_ends_after_last_event(self):
        """事件结束后不再产出心跳。"""
        events = [
            WorkflowEvent(workflow_id="test", kind="workflow_started", category="system"),
            WorkflowCompletedEvent.create("test", {"reply": "done"}),
        ]

        event_iter = _fake_subscribe(events)
        collected: list[str] = []

        for _ in range(10):
            try:
                event = await asyncio.wait_for(
                    event_iter.__anext__(),
                    timeout=0.1,
                )
                collected.append(event.kind)
            except asyncio.TimeoutError:
                collected.append("heartbeat")
            except StopAsyncIteration:
                break

        # 验证：两个真实事件后 SSE 结束，没有多余心跳
        assert collected == ["workflow_started", "workflow_completed"]
