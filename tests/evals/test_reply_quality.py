"""Quality evaluation tests for review_reply_agent.

Runs golden dataset checks via the reply evaluation engine.
Requires --run-llm flag.
"""

import pytest
from tests.evals.evaluator_reply import evaluate_review_reply


@pytest.mark.needs_llm
class TestReviewReplyQuality:
    @pytest.mark.asyncio
    async def test_golden_dataset(self):
        report = await evaluate_review_reply()
        assert report["failed"] == 0, f"评测失败: {report['results']}"

    @pytest.mark.asyncio
    async def test_pass_rate_threshold(self):
        """At least 80% pass rate (LLM output has variance, 100% not required)."""
        report = await evaluate_review_reply()
        assert report["pass_rate"] >= 0.8, f"通过率 {report['pass_rate']:.0%} < 80%"