"""Node 事件发射器 — 类型安全的 Node 事件发送辅助。

用途：
    emitter = NodeEventEmitter(get_stream_writer())
    emitter.generation_started()
    emitter.token_delta("你好")
    emitter.generation_completed(reply_content="回复文本")
    emitter.generation_failed("出错了")
"""

from shared.workflow_events.models import (
    NodeStartedEvent,
    NodeCompletedEvent,
    NodeFailedEvent,
    TokenDeltaEvent,
)
from shared.workflow_events.kinds import BusinessEvent


class NodeEventEmitter:
    """Node 内的类型安全事件发射器。

    封装 get_stream_writer()，提供类型安全的事件发射方法。
    """

    def __init__(self, writer):
        self._writer = writer

    def _emit(self, event) -> None:
        self._writer(event.model_dump(mode="json", exclude_none=True))

    # ── Generation 阶段 ─────────────────────────────────────────

    def generation_started(self) -> None:
        """发射 generation 开始事件。"""
        self._emit(
            NodeStartedEvent.create(
                workflow_id="",
                node_name="generation",
                display_name="生成开始",
            )
        )

    def generation_completed(self, reply_content: str) -> None:
        """发射 generation 完成事件。

        Args:
            reply_content: 生成的回复纯文本
        """
        self._emit(
            NodeCompletedEvent.create(
                workflow_id="",
                node_name="generation",
                display_name="回复生成完成",
            )
        )

    def generation_failed(self, error: str) -> None:
        """发射 generation 失败事件。

        Args:
            error: 错误信息
        """
        self._emit(
            NodeFailedEvent.create(
                workflow_id="",
                node_name="generation",
                error=error,
                display_name="生成失败",
            )
        )

    def token_delta(self, delta: str) -> None:
        """发射 token 增量事件。

        Args:
            delta: token 文本片段
        """
        self._emit(
            TokenDeltaEvent.create(
                workflow_id="",
                delta=delta,
                source="generation",
            )
        )

    # ── Analysis 阶段 ─────────────────────────────────────────

    def analysis_started(self) -> None:
        """发射 analysis 开始事件。"""
        self._emit(
            NodeStartedEvent.create(
                workflow_id="",
                node_name="analysis",
                display_name="分析开始",
            )
        )

    def analysis_completed(self) -> None:
        """发射 analysis 完成事件。"""
        self._emit(
            NodeCompletedEvent.create(
                workflow_id="",
                node_name="analysis",
                display_name="分析完成",
            )
        )

    def analysis_failed(self, error: str) -> None:
        """发射 analysis 失败事件。

        Args:
            error: 错误信息
        """
        self._emit(
            NodeFailedEvent.create(
                workflow_id="",
                node_name="analysis",
                error=error,
                display_name="分析失败",
            )
        )
