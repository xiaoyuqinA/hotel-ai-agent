import pytest
from shared.runtime.runtime import run_agent


@pytest.mark.needs_llm
class TestReviewBoundary:
    @pytest.mark.asyncio
    async def test_empty_input(self):
        # 不应崩溃，应返回结构化的结果
        result = await run_agent("review_analysis_agent", "")
        assert result is not None

    @pytest.mark.asyncio
    async def test_very_short_input(self):
        result = await run_agent("review_analysis_agent", "不错")
        assert result is not None

    @pytest.mark.asyncio
    async def test_non_review_input(self):
        # 非评论输入不应崩溃
        result = await run_agent("review_analysis_agent", "abcdefg123456")
        assert result is not None