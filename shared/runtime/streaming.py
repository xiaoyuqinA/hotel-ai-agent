"""流式 Agent 工具 — 带 Workflow Event 的 async streaming。"""

from typing import AsyncGenerator, TypeVar

from pydantic import BaseModel

from shared.conversation.session import InMemorySession
from shared.runtime.runtime import _runtime, stream_agent


T = TypeVar("T", bound=BaseModel)


async def stream_agent_with_events(
    agent_name: str,
    user_input: str,
    session: InMemorySession | None = None,
    session_id: str | None = None,
) -> AsyncGenerator[tuple[str, str], None]:
    """流式运行 Agent，yield (event_type, token) 供 Node 写入 stream_writer。

    Node 用法：
        async for event_type, delta in stream_agent_with_events("review_reply_agent", input):
            writer({  # 写入 LangGraph extensions channel
                "type": event_type,
                "delta": delta,
            })
            if event_type == "token":
                reply_content += delta

    Args:
        agent_name: Agent 名称
        user_input: 用户输入
        session: 可选 session
        session_id: 可选 session_id

    Yields:
        (event_type, token) 元组
        - event_type: "token" | "node_started" | "node_completed"
        - token: 对应 token 值
    """
    yield "node_started", ""

    try:
        async for chunk in stream_agent(agent_name, user_input, session, session_id):
            yield "token", chunk
    except Exception as e:
        yield "node_error", str(e)
        raise
    finally:
        yield "node_completed", ""


async def stream_agent_typed(
    agent_name: str,
    user_input: str,
    output_type: type[T],
    session: InMemorySession | None = None,
    session_id: str | None = None,
) -> AsyncGenerator[tuple[str, T | None], None]:
    """流式运行 Agent 并逐步构建最终结果。

    适用于需要流式 token 显示 + 最终解析结果的场景。

    Args:
        agent_name: Agent 名称
        user_input: 用户输入
        output_type: 最终输出类型
        session: 可选 session
        session_id: 可选 session_id

    Yields:
        (event_type, data) 元组
        - "token", str: token 增量
        - "result", T: 最终解析结果（仅在最后 yield）
    """
    accumulated = ""

    async for event_type, chunk in stream_agent_with_events(
        agent_name, user_input, session, session_id
    ):
        if event_type == "token":
            accumulated += chunk
            yield "token", chunk
        elif event_type == "node_completed":
            # 尝试解析最终结果
            result = None
            try:
                result = output_type.model_validate_json(accumulated)
            except Exception:
                # 解析失败，返回字符串
                pass
            if result is not None:
                yield "result", result
