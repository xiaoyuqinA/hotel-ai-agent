"""Typed Projection Mapper — LangGraph v3 Projection → WorkflowEvent 转换器。

基于 LangGraph 官方 Event Streaming 文档：
https://docs.langchain.com/oss/python/langgraph/event-streaming

v3 Typed Projections:
    stream.messages    → LLM 消息/token (AIMessageChunk)
    stream.values      → 状态快照
    stream.output      → 最终输出（属性，非方法）
    stream.subgraphs   → 子图
    stream.extensions  → 自定义事件（get_stream_writer 写入）
"""

from typing import Any, AsyncIterator

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


class ProjectionMapper:
    """LangGraph v3 Typed Projection → WorkflowEvent 转换器。

    使用方法：
        mapper = ProjectionMapper(workflow_id="xxx")
        async for event in mapper.map_stream(graph, input, config):
            yield event

    v3 Projection 映射：
        - messages       → TOKEN_DELTA (LLM token 流)
        - values         → STATE_UPDATED (状态快照)
        - extensions     → TOKEN_DELTA / NODE_STARTED (Node 写入的自定义事件)
    """

    def __init__(self, workflow_id: str | None = None):
        self.workflow_id = workflow_id or str(uuid.uuid4())

    def map_stream(
        self,
        graph,
        input: dict[str, Any],
        config: dict[str, Any] | None = None,
    ) -> AsyncIterator[WorkflowEvent]:
        """将 LangGraph astream_events(v3) 转换为 WorkflowEvent 流。

        调用 graph.astream_events(version="v3")，返回 AsyncGraphRunStream。

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
        """内部实现：消费 v3 Typed Projections。"""
        import asyncio

        yield WorkflowStartedEvent.create(self.workflow_id)

        try:
            # v3: astream_events 返回 Awaitable[AsyncGraphRunStream]
            stream = await graph.astream_events(input, config=config, version="v3")

            # 并发消费所有 projections
            tasks = [
                self._consume_messages(stream.messages),
                self._consume_values(stream.values),
                self._consume_extensions(stream.extensions),
            ]

            async for event in _merge_async_iterators(*tasks):
                yield event

            # v3: stream.output 是属性，不是方法
            output = stream.output
            if output:
                output_dict = dict(output) if hasattr(output, 'keys') else output
            else:
                output_dict = None

            yield WorkflowCompletedEvent.create(self.workflow_id, output_dict)

        except Exception as e:
            yield WorkflowFailedEvent.create(self.workflow_id, str(e))
            raise

    async def _consume_messages(self, channel) -> AsyncIterator[WorkflowEvent]:
        """消费 messages projection → TOKEN_DELTA。

        v3 messages 事件类型：
        - message-start         → 消息开始
        - content-block-start   → 内容块开始
        - content-block-delta   → token delta
        - content-block-finish  → 内容块完成
        - message-finish        → 消息完成
        """
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

    async def _consume_extensions(
        self, extensions
    ) -> AsyncIterator[WorkflowEvent]:
        """消费 extensions projection → WorkflowEvent。

        extensions 包含 Node 通过 get_stream_writer() 写入的自定义事件。
        常见事件格式：
        - {"type": "node_started", "node": "analysis"}
        - {"type": "token", "delta": "hello"}
        - {"type": "node_completed", "node": "analysis"}
        """
        if not extensions:
            return

        for name, channel in extensions.items():
            if name in ("values", "messages", "lifecycle", "subgraphs"):
                continue

            try:
                async for event in _safe_channel_iter(channel):
                    if event is None:
                        continue
                    async for mapped in self._parse_extension_event(event):
                        yield mapped
            except TypeError:
                pass

    async def _parse_extension_event(
        self, event: Any
    ) -> AsyncIterator[WorkflowEvent]:
        """解析 extensions 中的自定义事件。"""
        try:
            if isinstance(event, dict):
                event_type = event.get("type", event.get("kind", ""))
                data = event
            elif hasattr(event, "type"):
                event_type = event.type
                data = getattr(event, "data", {})
            else:
                event_type = "custom"
                data = {"raw": str(event)}

            if event_type == "node_started":
                yield NodeStartedEvent.create(
                    workflow_id=self.workflow_id,
                    node_name=data.get("node", "unknown"),
                    display_name=data.get("display_name"),
                )
            elif event_type == "node_completed":
                yield NodeCompletedEvent.create(
                    workflow_id=self.workflow_id,
                    node_name=data.get("node", "unknown"),
                )
            elif event_type == "node_error":
                yield NodeFailedEvent.create(
                    workflow_id=self.workflow_id,
                    node_name=data.get("node", "unknown"),
                    error=data.get("error", "unknown"),
                )
            elif event_type in ("token", "content-block-delta"):
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
    """从 LangChain AIMessageChunk 提取 token delta。

    v3 messages channel 返回 AIMessageChunk，内容可能是：
    - str: 直接是文本
    - list: [{"type": "text", "text": "..."}]
    """
    if not hasattr(msg, "content"):
        return None

    content = msg.content
    if not content:
        return None

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    return block.get("text", "")
            elif hasattr(block, "text"):
                return str(block.text)
        if content:
            first = content[0]
            if isinstance(first, dict):
                return str(first.get("text", ""))
            return str(first)
    return None


async def _safe_channel_iter(channel) -> AsyncIterator[Any]:
    """安全迭代 channel，处理 sync/async 差异。"""
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
