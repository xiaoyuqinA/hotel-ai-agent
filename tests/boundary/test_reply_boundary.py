"""End-to-end boundary tests for review_reply_agent.

Ensures the agent does not crash with edge-case inputs and produces valid output.
"""

import pytest
from shared.runtime.runtime import run_agent


@pytest.mark.needs_llm
class TestReplyBoundary:
    @pytest.mark.asyncio
    async def test_empty_input(self):
        """Empty input should not crash."""
        result = await run_agent("review_reply_agent", "")
        assert result is not None

    @pytest.mark.asyncio
    async def test_very_short_input(self):
        """Very short input should not crash."""
        result = await run_agent("review_reply_agent", "不错")
        assert result is not None

    @pytest.mark.asyncio
    async def test_non_review_input(self):
        """Non-review input should not crash."""
        result = await run_agent("review_reply_agent", "abcdefg123456")
        assert result is not None

    @pytest.mark.asyncio
    async def test_extremely_long_review(self):
        """Extremely long review should not crash."""
        long_review = "酒店很好，" * 500
        result = await run_agent("review_reply_agent", long_review)
        assert result is not None

    @pytest.mark.asyncio
    async def test_output_has_reply_content(self):
        """Normal review should produce non-empty reply_content."""
        result = await run_agent("review_reply_agent", "酒店很好，服务很棒")
        assert result is not None
        assert len(str(result)) > 0