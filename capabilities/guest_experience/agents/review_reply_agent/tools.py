"""Review Reply Agent 工具定义。"""

from agents import function_tool
from shared.knowledge.client import get_knowledge_client


# 原始异步函数 — 供测试直接调用
async def query_hotel_knowledge_impl(question: str) -> str:
    """酒店知识查询核心逻辑。

    Args:
        question: 需要查询的问题

    Returns:
        相关知识片段
    """
    client = get_knowledge_client()
    results = await client.search(question)
    if results:
        return "\n---\n".join(results)
    return "未找到相关知识。"


# 注册为 Agent SDK 的 FunctionTool
query_hotel_knowledge = function_tool(query_hotel_knowledge_impl)


def get_reply_tools():
    """获取回复工具列表。"""
    return [query_hotel_knowledge]