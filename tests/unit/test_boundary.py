"""边界测试 — 验证边界条件下的行为。"""

from asyncio import new_event_loop


# --- KnowledgeClient 边界测试 ---

class TestKnowledgeClientBoundary:

    def _reset_singleton(self):
        """重置全局单例，确保每次测试独立。"""
        import shared.knowledge.client as mod
        mod._default_client = None

    def test_search_empty_query(self):
        from shared.knowledge.client import KnowledgeClient
        client = KnowledgeClient()
        result = new_event_loop().run_until_complete(client.search(""))
        assert isinstance(result, list)

    def test_search_top_k_zero(self):
        from shared.knowledge.client import KnowledgeClient
        client = KnowledgeClient()
        result = new_event_loop().run_until_complete(client.search("test", top_k=0))
        assert isinstance(result, list)

    def test_search_top_k_negative(self):
        from shared.knowledge.client import KnowledgeClient
        client = KnowledgeClient()
        result = new_event_loop().run_until_complete(client.search("test", top_k=-1))
        assert isinstance(result, list)

    def test_search_very_long_query(self):
        from shared.knowledge.client import KnowledgeClient
        client = KnowledgeClient()
        long_query = "a" * 10000
        result = new_event_loop().run_until_complete(client.search(long_query))
        assert isinstance(result, list)

    def test_search_unicode_query(self):
        from shared.knowledge.client import KnowledgeClient
        client = KnowledgeClient()
        result = new_event_loop().run_until_complete(client.search("🏨 酒店设施"))
        assert isinstance(result, list)

    def test_get_knowledge_client_returns_singleton(self):
        self._reset_singleton()
        from shared.knowledge.client import get_knowledge_client
        c1 = get_knowledge_client()
        c2 = get_knowledge_client()
        assert c1 is c2

    def test_search_returns_empty_list(self):
        from shared.knowledge.client import KnowledgeClient
        client = KnowledgeClient()
        result = new_event_loop().run_until_complete(client.search("nonexistent"))
        assert result == []


# --- query_hotel_knowledge 工具边界测试 ---

class TestQueryHotelKnowledgeBoundary:

    def _reset_singleton(self):
        import shared.knowledge.client as mod
        mod._default_client = None

    def test_tool_returns_no_knowledge_message(self):
        """知识库为空时，返回'未找到相关知识'。"""
        self._reset_singleton()
        from capabilities.guest_experience.agents.review_reply_agent.tools import query_hotel_knowledge_impl
        result = new_event_loop().run_until_complete(query_hotel_knowledge_impl("早餐时间"))
        assert "未找到相关知识" in result

    def test_tool_accepts_empty_question(self):
        self._reset_singleton()
        from capabilities.guest_experience.agents.review_reply_agent.tools import query_hotel_knowledge_impl
        result = new_event_loop().run_until_complete(query_hotel_knowledge_impl(""))
        assert isinstance(result, str)

    def test_tool_accepts_unicode_question(self):
        self._reset_singleton()
        from capabilities.guest_experience.agents.review_reply_agent.tools import query_hotel_knowledge_impl
        result = new_event_loop().run_until_complete(query_hotel_knowledge_impl("酒店早餐几点 🍳"))
        assert isinstance(result, str)


# --- ReplyResult 边界测试 ---

class TestReplyResultBoundary:

    def test_empty_reply_content(self):
        from capabilities.guest_experience.agents.review_reply_agent.schemas import ReplyResult
        r = ReplyResult(reply_content="")
        assert r.reply_content == ""

    def test_very_long_reply_content(self):
        from capabilities.guest_experience.agents.review_reply_agent.schemas import ReplyResult
        long_content = "a" * 100000
        r = ReplyResult(reply_content=long_content)
        assert len(r.reply_content) == 100000

    def test_unicode_reply_content(self):
        from capabilities.guest_experience.agents.review_reply_agent.schemas import ReplyResult
        r = ReplyResult(reply_content="尊敬的宾客，感谢您的认可 🏨")
        assert "🏨" in r.reply_content

    def test_reply_content_with_newlines(self):
        from capabilities.guest_experience.agents.review_reply_agent.schemas import ReplyResult
        r = ReplyResult(reply_content="第一行\n第二行\n第三行")
        assert r.reply_content.count("\n") == 2

    def test_serialization(self):
        from capabilities.guest_experience.agents.review_reply_agent.schemas import ReplyResult
        r = ReplyResult(reply_content="test")
        json_str = r.model_dump_json()
        assert "test" in json_str