"""Typed Projection Mapper — LangGraph v3 Projection → WorkflowEvent 转换器。"""

from typing import Any, AsyncIterator

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
    CustomEvent,
)

import uuid


# Node 发出的自定义事件类型
AGENT_NODE_EVENTS = frozenset(["node_started", "node_completed", "node_error", "token"])


class ProjectionMapper:
    """LangGraph v3 Typed Projection 到 WorkflowEvent 的转换器。

    使用方法：
        mapper = ProjectionMapper(workflow_id="xxx")
        async for event in mapper.map_stream(graph, input, config):
            yield event

    v3 Projection 映射关系：
        - messages       → TOKEN_DELTA (LangChain ChatModel)
        - values         → STATE_UPDATED (state 快照)
        - lifecycle      → NODE_STARTED / NODE_COMPLETED (LangGraph 内置)
        - extensions     → TOKEN_DELTA / CUSTOM_EVENT (OpenAI Agents SDK)

    对于 extensions channel 中的 agent 事件：
        Node 通过 get_stream_writer() 写入 {"type": "token", "delta": "..."} 或
        {"type": "node_started", "node": "generate_reply"} 等。
        这些事件在 extensions channel 中被消费并转换为 WorkflowEvent。
    """

    def __init__(self, workflow_id: str | None = None):
        self.workflow_id = workflow_id or str(uuid.uuid4())
        self._pending_nodes: set[str] = set()

    def map_stream(
        self,
        graph,
        input: dict[str, Any],
        config: dict[str, Any] | None = None,
    ) -> AsyncIterator[WorkflowEvent]:
        """将 LangGraph astream_events(v3) 转换为 WorkflowEvent 流。

        Args:
            graph: 编译后的 LangGraph
            input: 工作流输入
            config: LangGraph config

        Yields:
            WorkflowEvent 事件序列
        """
        return self._map_stream_impl(graph, input, config)

    async def _map_stream_impl(
        self,
        graph,
        input: dict[str, Any],
        config: dict[str, Any] | None = None,
    ) -> AsyncIterator[WorkflowEvent]:
        """内部实现：并发消费所有 v3 projections。"""
        import asyncio

        # 1. 发送 WORKFLOW_STARTED
        yield WorkflowStartedEvent.create(self.workflow_id)

        try:
            stream = await graph.astream_events(input, config=config, version="v3")

            # 并发消费所有 projections
            tasks = [
                self._consume_messages(stream.messages),
                self._consume_values(stream.values),
                self._consume_lifecycle(stream.lifecycle),
                self._consume_extensions(stream.extensions),
            ]

            # 使用并发迭代器收集所有事件
            async for event in _merge_async_iterators(*tasks):
                yield event

            # 获取最终输出
            output = await stream.output()
            yield WorkflowCompletedEvent.create(self.workflow_id, output)

        except Exception as e:
            yield WorkflowFailedEvent.create(self.workflow_id, str(e))
            raise

    async def _consume_messages(self, channel) -> AsyncIterator[WorkflowEvent]:
        """消费 messages projection → TOKEN_DELTA。"""
        try:
            async for msg in channel:
                delta = _extract_message_delta(msg)
                if delta:
                    yield TokenDeltaEvent.create(
                        workflow_id=self.workflow_id,
                        delta=delta,
                        source="llm",
                    )
        except TypeError:
            pass

    async def _consume_values(self, channel) -> AsyncIterator[WorkflowEvent]:
        """消费 values projection → STATE_UPDATED。"""
        try:
            async for value in channel:
                if value and isinstance(value, dict):
                    yield StateUpdatedEvent.create(self.workflow_id, value)
        except TypeError:
            pass

    async def _consume_lifecycle(
        self, channel
    ) -> AsyncIterator[WorkflowEvent]:
        """消费 lifecycle projection → NODE_STARTED / NODE_COMPLETED / NODE_FAILED。"""
        try:
            async for event in channel:
                for mapped in self._parse_lifecycle_event(event):
                    yield mapped
        except TypeError:
            pass

    def _parse_lifecycle_event(self, event: Any) -> AsyncIterator[WorkflowEvent]:
        """解析 lifecycle 事件。"""
        if isinstance(event, dict):
            event_type = event.get("type", "")
            name = event.get("name", "")
            error = event.get("error")
        else:
            event_type = getattr(event, "type", "")
            name = getattr(event, "name", "")
            error = getattr(event, "error")

        if "start" in str(event_type).lower():
            self._pending_nodes.add(name)
            yield NodeStartedEvent.create(
                workflow_id=self.workflow_id,
                node_name=name,
            )
        elif "end" in str(event_type).lower():
            self._pending_nodes.discard(name)
            yield NodeCompletedEvent.create(
                workflow_id=self.workflow_id,
                node_name=name,
            )
        elif "error" in str(event_type).lower() or "fail" in str(event_type).lower():
            yield NodeFailedEvent.create(
                workflow_id=self.workflow_id,
                node_name=name,
                error=str(error) if error else "unknown",
            )

    async def _consume_extensions(
        self, extensions
    ) -> AsyncIterator[WorkflowEvent]:
        """消费 extensions projection → WorkflowEvent。

        处理 Node 通过 get_stream_writer() 写入的自定义事件。
        支持两种格式：
        1. dict: {"type": "token", "delta": "..."} 或 {"type": "node_started", "node": "..."}
        2. LangGraph StreamPart 格式
        """
        if not extensions:
            return

        for name, channel in extensions.items():
            if name in ("values", "messages", "lifecycle"):
                continue

            async for event in _safe_channel_iter(channel):
                if event is None:
                    continue

                # 尝试解析事件
                async for mapped in self._parse_extension_event(event):
                    yield mapped

    async def _parse_extension_event(
        self, event: Any
    ) -> AsyncIterator[WorkflowEvent]:
        """解析 extensions channel 中的事件。"""
        try:
            if isinstance(event, dict):
                event_type = event.get("type", event.get("kind", ""))
                data = event
            elif hasattr(event, "type"):
                event_type = event.type
                data = getattr(event, "data", {})
                if isinstance(data, dict):
                    data = {"raw": data}
                else:
                    data = {"raw": str(data)}
            else:
                event_type = "custom"
                data = {"raw": str(event)}

            # 处理 agent node 事件
            if event_type == "node_started":
                yield NodeStartedEvent.create(
                    workflow_id=self.workflow_id,
                    node_name=data.get("node", data.get("name", "unknown")),
                    display_name=data.get("display_name"),
                )
            elif event_type == "node_completed":
                yield NodeCompletedEvent.create(
                    workflow_id=self.workflow_id,
                    node_name=data.get("node", data.get("name", "unknown")),
                )
            elif event_type == "node_error":
                yield NodeFailedEvent.create(
                    workflow_id=self.workflow_id,
                    node_name=data.get("node", data.get("name", "unknown")),
                    error=data.get("error", "unknown"),
                )
            elif event_type == "token":
                delta = data.get("delta", data.get("content", ""))
                if delta:
                    yield TokenDeltaEvent.create(
                        workflow_id=self.workflow_id,
                        delta=str(delta),
                        source=data.get("source", "agent"),
                    )
            elif event_type == "custom":
                yield CustomEvent.create(
                    workflow_id=self.workflow_id,
                    event_type=data.get("event_type", "custom"),
                    data=data,
                    source=data.get("source"),
                )
        except Exception:
            pass


def _extract_message_delta(msg: Any) -> str | None:
    """从 LangChain message 对象提取 token delta。"""
    if hasattr(msg, "content") and msg.content:
        content = msg.content
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        return block.get("text", "")
                elif hasattr(block, "text"):
                    return block.text
            return str(content[0]) if content else None
        return str(content)
    return None


async def _safe_channel_iter(channel) -> AsyncIterator[Any]:
    """安全地迭代 channel，处理 sync/async 差异。"""
    try:
        async for item in channel:
            yield item
    except TypeError:
        for item in channel:
            yield item


async def _merge_async_iterators(
    *iterators,
) -> AsyncIterator[WorkflowEvent]:
    """合并多个 AsyncIterator，按 yield 顺序输出。"""
    import asyncio

    async def iter_to_queue(it, queue):
        try:
            async for item in it:
                await queue.put(item)
        except Exception as e:
            await queue.put(e)
        finally:
            await queue.put(None)

    queue = asyncio.Queue()
    iterators = [it for it in iterators if it is not None]

    if not iterators:
        return

    tasks = [asyncio.create_task(iter_to_queue(it, queue)) for it in iterators]
    pending = len(tasks)

    while pending > 0:
        item = await queue.get()
        if item is None:
            pending -= 1
        elif isinstance(item, Exception):
            raise item
        else:
            yield item
            queue.task_done()
