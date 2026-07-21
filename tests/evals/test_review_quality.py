import pytest
from tests.evals.evaluator import evaluate_review_analysis


@pytest.mark.needs_llm
class TestReviewAnalysisQuality:
    @pytest.mark.asyncio
    async def test_golden_dataset(self):
        report = await evaluate_review_analysis()
        assert report["failed"] == 0, f"评测失败: {report['results']}"

    @pytest.mark.asyncio
    async def test_pass_rate_threshold(self):
        """至少 80% 通过（LLM 输出有方差，不要求 100%）"""
        report = await evaluate_review_analysis()
        assert report["pass_rate"] >= 0.8, f"通过率 {report['pass_rate']:.0%} < 80%"