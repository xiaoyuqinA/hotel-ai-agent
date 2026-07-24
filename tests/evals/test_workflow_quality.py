"""Workflow golden dataset quality tests.

Runs the 20-case golden dataset through the full review_operation workflow
and verifies reply quality via rule-based checks.

Requires --run-llm flag.
"""

import pytest

from tests.evals.runner_workflow import evaluate_workflow_replies


@pytest.mark.needs_llm
class TestWorkflowQuality:
    @pytest.mark.asyncio
    async def test_workflow_golden_dataset(self):
        """All Low severity cases should pass their checks."""
        report = await evaluate_workflow_replies()
        assert report["failed"] == 0, f"评测失败: {report['results']}"

    @pytest.mark.asyncio
    async def test_workflow_pass_rate(self):
        """At least 80% pass rate (LLM output has variance, 100% not required)."""
        report = await evaluate_workflow_replies()
        assert report["pass_rate"] >= 0.8, f"通过率 {report['pass_rate']:.0%} < 80%"
