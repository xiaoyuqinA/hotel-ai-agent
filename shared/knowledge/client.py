"""酒店知识查询客户端 — 调用向量数据库检索酒店信息。"""

from typing import List


class KnowledgeClient:
    """酒店知识检索客户端。

    当前为存根实现，后续接入真实的向量数据库。
    """

    async def search(self, query: str, top_k: int = 3) -> List[str]:
        """根据问题检索相关知识片段。"""
        # TODO: 接入真实向量数据库
        return []


_default_client: KnowledgeClient | None = None


def get_knowledge_client() -> KnowledgeClient:
    """获取全局 KnowledgeClient 单例。"""
    global _default_client
    if _default_client is None:
        _default_client = KnowledgeClient()
    return _default_client