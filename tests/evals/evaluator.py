"""Evaluation engine — rule-based comparison of Agent output against golden data."""

import json
from pathlib import Path
from typing import Any

from capabilities.guest_experience.agents.review_analysis_agent.schemas import ReviewAnalysisResult
from shared.runtime.runtime import run_agent


async def evaluate_review_analysis(
    dataset_path: str | Path = "tests/evals/datasets/review_cases.json",
) -> dict[str, Any]:
    """Run all cases and return evaluation results."""
    cases = json.loads(Path(dataset_path).read_text(encoding="utf-8"))
    results = []

    for case in cases:
        raw = await run_agent("review_analysis_agent", case["input"])

        # Agent 设置了 output_type，SDK 返回 Pydantic 实例
        if isinstance(raw, ReviewAnalysisResult):
            result = raw
        else:
            # 兼容自由文本模式，尝试解析 JSON
            if isinstance(raw, dict):
                result = ReviewAnalysisResult.model_validate(raw)
            else:
                result = ReviewAnalysisResult.model_validate_json(raw)

        expected = case["expected"]
        passed = (
            result.issue_severity.level == expected["severity"]
            and result.customer_sentiment.label == expected["sentiment"]
            and result.customer_intent == expected["intent"]
        )
        results.append({
            "id": case.get("id", "unknown"),
            "passed": passed,
            "expected": expected,
            "actual": {
                "severity": result.issue_severity.level,
                "sentiment": result.customer_sentiment.label,
                "intent": result.customer_intent,
            },
        })

    total = len(results)
    passed_count = sum(1 for r in results if r["passed"])
    return {
        "total": total,
        "passed": passed_count,
        "failed": total - passed_count,
        "pass_rate": passed_count / total if total else 0,
        "results": results,
    }