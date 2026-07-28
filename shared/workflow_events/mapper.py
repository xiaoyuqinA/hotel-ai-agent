"""ProjectionMapper — LangGraph v3 单事件流 → WorkflowEvent 转换器。

设计原则：
1. astream_events(version="v3") 返回单个 async iterator
2. 通过 transform() 将每个 LangGraph 事件转换为 WorkflowEvent
3. sequence 使用事件自带的 seq 字段保证顺序

事件分类：
- values:   LangGraph State 快照 (category="state")
- messages: LLM 流式输出 (category="message")
- custom:   Agent 业务事件 (category="progress") ⭐ 核心

文档：https://docs.langchain.com/oss/python/langgraph/event-streaming
"""

from typing import Any, AsyncIterator

from shared.workflow_events.models import (
    WorkflowEvent,
    NodeStartedEvent,
    NodeCompletedEvent,
    NodeFailedEvent,
    TokenDeltaEvent,
    StateUpdatedEvent,
    WorkflowStartedEvent,
    WorkflowCompletedEvent,
    WorkflowFailedEvent,
    CustomEvent,
)
from shared.workflow_events.kinds import BusinessEvent

import uuid


class ProjectionMapper:
    """将 LangGraph v3 单事件流转换为 WorkflowEvent。

    v3 事件格式 (ProtocolEvent):
        {
            "type": "event",
            "seq": 1,
            "method": "values" | "messages" | "custom",
            "params": {
                "namespace": [...],
                "timestamp": ...,
                "data": {...}
            }
        }

    custom 事件格式 (Agent 发送):
        {
            "event": "analysis_started" | "analysis_completed" | ...,
            "message": "正在分析...",
            "result": {...},
            "error": "..."
        }
    """

    def __init__(self, workflow_id: str | None = None):
        self.workflow_id = workflow_id or str(uuid.uuid4())
        self._sequence = 0

    def next_sequence(self) -> int:
        """获取下一个序列号（用于事件追踪）。"""
        self._sequence += 1
        return self._sequence

    def transform(self, raw_event: dict[str, Any]) -> WorkflowEvent | None:
        """将 LangGraph v3 ProtocolEvent 转换为 WorkflowEvent。

        Args:
            raw_event: LangGraph v3 原始事件 (ProtocolEvent)

        Returns:
            WorkflowEvent 或 None（事件被过滤）
        """
        method = raw_event.get("method", "")
        params = raw_event.get("params", {})
        data = params.get("data", {})

        # 使用 v3 事件自带的 seq，如果不存在或为 0 则自增。
        # custom 事件的 seq 总是 0（由 writer() 发送，非 astream_events 原生）
        v3_seq = raw_event.get("seq")
        if v3_seq and v3_seq > 0:
            sequence = v3_seq
        else:
            sequence = self.next_sequence()

        # ── values 事件 (State 更新) ───────────────────────────────────
        if method == "values":
            event = StateUpdatedEvent.create(
                workflow_id=self.workflow_id,
                state=data,
            )
            event.sequence = sequence
            return event

        # ── messages 事件 (LLM 消息) ─────────────────────────────────────
        if method == "messages":
            content = self._extract_message_content(data)
            if content:
                return TokenDeltaEvent.create(
                    workflow_id=self.workflow_id,
                    delta=content,
                )
            return None

        # ── custom 事件 (业务进度) ⭐ 核心 ────────────────────────────────
        if method == "custom":
            return self._transform_custom_event(data, sequence)

        return None

    def _extract_message_content(self, data: Any) -> str:
        """从消息对象中提取文本内容。"""
        content = ""
        if hasattr(data, "content"):
            if isinstance(data.content, list):
                for item in data.content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        content += item.get("text", "")
                    elif isinstance(item, str):
                        content += item
            elif isinstance(data.content, str):
                content = data.content
            elif hasattr(data.content, "text"):
                content = data.content.text
        return content

    def _transform_custom_event(
        self, data: dict[str, Any], sequence: int
    ) -> WorkflowEvent | None:
        """将 custom 事件转换为业务 WorkflowEvent。

        Agent 通过 get_stream_writer() 发送的事件格式:
            {
                "event": "analysis_started",
                "message": "正在分析客户评论",
                "result": {...},
                "error": "..."
            }

        Args:
            data: custom 事件的数据部分

        Returns:
            转换后的 WorkflowEvent
        """
        event_type = data.get("event", "")
        message = data.get("message", "")

        # ── Analysis 阶段 ──────────────────────────────────────────────
        if event_type == BusinessEvent.ANALYSIS_STARTED:
            return NodeStartedEvent.create(
                workflow_id=self.workflow_id,
                node_name="analysis",
                display_name="分析评论中",
                sequence=sequence,
            )

        if event_type == BusinessEvent.ANALYSIS_COMPLETED:
            return NodeCompletedEvent.create(
                workflow_id=self.workflow_id,
                node_name="analysis",
                sequence=sequence,
            )

        if event_type == BusinessEvent.ANALYSIS_FAILED:
            error = data.get("error", "unknown")
            return NodeFailedEvent.create(
                workflow_id=self.workflow_id,
                node_name="analysis",
                error=error,
                sequence=sequence,
            )

        # ── Generation 阶段 ─────────────────────────────────────────────
        if event_type == BusinessEvent.GENERATION_STARTED:
            return NodeStartedEvent.create(
                workflow_id=self.workflow_id,
                node_name="generation",
                display_name="回复生成中",
                sequence=sequence,
            )

        if event_type == BusinessEvent.GENERATION_COMPLETED:
            return NodeCompletedEvent.create(
                workflow_id=self.workflow_id,
                node_name="generation",
                sequence=sequence,
            )

        if event_type == BusinessEvent.GENERATION_FAILED:
            error = data.get("error", "unknown")
            return NodeFailedEvent.create(
                workflow_id=self.workflow_id,
                node_name="generation",
                error=error,
                sequence=sequence,
            )

        # ── Review 阶段 ─────────────────────────────────────────────────
        if event_type == BusinessEvent.REVIEW_STARTED:
            return NodeStartedEvent.create(
                workflow_id=self.workflow_id,
                node_name="review",
                display_name="审核回复中",
                sequence=sequence,
            )

        if event_type == BusinessEvent.REVIEW_COMPLETED:
            return NodeCompletedEvent.create(
                workflow_id=self.workflow_id,
                node_name="review",
                sequence=sequence,
            )

        if event_type == BusinessEvent.REVIEW_FAILED:
            error = data.get("error", "unknown")
            return NodeFailedEvent.create(
                workflow_id=self.workflow_id,
                node_name="review",
                error=error,
                sequence=sequence,
            )

        # ── Token Delta（流式输出）──────────────────────────────────────
        if event_type == "token_delta":
            delta = data.get("delta", "")
            if delta:
                event = TokenDeltaEvent.create(
                    workflow_id=self.workflow_id,
                    delta=delta,
                    source="generation",
                )
                event.sequence = sequence
                return event

        # ── 其他 custom 事件（透传）──────────────────────────────────────
        if event_type:
            return CustomEvent.create(
                workflow_id=self.workflow_id,
                event_type=event_type,
                data={"message": message, **data},
            )

        return None

    async def map_stream(
        self,
        graph,
        input: dict[str, Any],
        config: dict[str, Any] | None = None,
    ) -> AsyncIterator[WorkflowEvent]:
        """单 iterator 消费 LangGraph v3 事件流。

        简化设计：astream_events 返回 async iterator。

        Args:
            graph: 编译后的 LangGraph
            input: 工作流输入
            config: LangGraph config

        Yields:
            WorkflowEvent 序列
        """
        # workflow_started 由上游负责发布（sse.py 中 _run_workflow_background 统一管理）
        try:
            # astream_events 是 coroutine，需要先 await 获取 async iterator
            stream = await graph.astream_events(
                input,
                config=config,
                version="v3",
            )
            final_state: dict[str, Any] = {}
            async for raw_event in stream:
                event = self.transform(raw_event)
                if event:
                    yield event
                # 记录最后一个 values 事件的 state（包含节点返回的完整结果）
                if raw_event.get("method") == "values":
                    final_state = raw_event.get("params", {}).get("data", {})

            yield WorkflowCompletedEvent.create(self.workflow_id, final_state or None)

        except Exception as e:
            yield WorkflowFailedEvent.create(self.workflow_id, str(e))
