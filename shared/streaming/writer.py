"""Stream Writer 辅助工具 — OpenAI Agents SDK 与 LangGraph v3 的桥接层。"""

from contextlib import contextmanager
from typing import Any, AsyncGenerator


class StreamWriter:
    """简化的 Stream Writer 封装。

    提供与 LangGraph get_stream_writer() 兼容的接口，
    用于在 Node 内向 extensions channel 写入自定义事件。

    使用方法（Node 内）：
        async for event in stream_agent(agent, input):
            writer.emit({"kind": "token", "delta": event})

    或者配合 LangGraph get_stream_writer()：
        from langgraph.config import get_stream_writer as langgraph_writer

        def node(state):
            writer = langgraph_writer()
            # ... agent streaming logic
            writer({"kind": "token", "delta": token})
    """

    def __init__(self):
        self._events: list[dict[str, Any]] = []

    def emit(self, event: dict[str, Any]) -> None:
        """发射一个自定义事件。

        Args:
            event: 事件 dict，应包含 kind, delta 等字段
        """
        self._events.append(event)

    def __call__(self, event: dict[str, Any]) -> None:
        """兼容 get_stream_writer() 的调用方式。"""
        self.emit(event)

    def get_events(self) -> list[dict[str, Any]]:
        """获取所有已发射的事件。"""
        return self._events.copy()

    def clear(self) -> None:
        """清空事件缓冲区。"""
        self._events.clear()


def get_stream_writer() -> StreamWriter:
    """获取当前上下文的 StreamWriter。

    此函数在与 LangGraph astream_events 配合时，
    返回 LangGraph 内部的 writer。
    在独立测试时，返回内存 writer。

    注意：
        实际项目中应使用 from langgraph.config import get_stream_writer
        此函数仅作为类型提示和独立运行的兼容层。
    """
    try:
        from langgraph.config import get_stream_writer as _writer

        return _writer()
    except ImportError:
        return StreamWriter()


@contextmanager
def stream_writer_context() -> AsyncGenerator[StreamWriter, None]:
    """为独立测试创建的 stream writer context。

    在 LangGraph astream_events 环境中，
    stream writer 由 LangGraph 自动管理，无需此 context。
    """
    writer = StreamWriter()
    yield writer
