"""Reply evaluation engine — rule-based reply quality checks."""

import json
from pathlib import Path
from typing import Any

import yaml
from capabilities.guest_experience.agents.review_reply_agent.schemas import ReplyResult
from shared.runtime.runtime import run_agent


def build_input(case: dict) -> str:
    """Build the input message for review_reply_agent."""
    inp = case["input"]
    review = inp["review"]
    analysis = inp.get("analysis", {})
    return f"客户评论：{review}\n\n评论分析：\n{json.dumps(analysis, ensure_ascii=False, indent=2)}"


def parse_output(raw: Any) -> str:
    """Parse agent output to reply_content string."""
    if isinstance(raw, ReplyResult):
        return raw.reply_content
    if isinstance(raw, dict):
        return raw.get("reply_content", "")
    try:
        data = json.loads(raw)
        return data.get("reply_content", "")
    except (json.JSONDecodeError, AttributeError):
        return str(raw)


def run_checks(reply: str, checks: dict) -> list[str]:
    """Run keyword/length checks and return list of failures."""
    failures = []

    for keyword in checks.get("must_contain", []):
        if keyword not in reply:
            failures.append(f"缺少关键词: '{keyword}'")

    for keyword in checks.get("must_not_contain", []):
        if keyword in reply:
            failures.append(f"不应包含: '{keyword}'")

    min_len = checks.get("min_length", 0)
    if len(reply) < min_len:
        failures.append(f"长度不足: {len(reply)} < {min_len}")

    max_len = checks.get("max_length", 500)
    if len(reply) > max_len:
        failures.append(f"长度过长: {len(reply)} > {max_len}")

    return failures


async def evaluate_review_reply(
    dataset_path: str | Path = "tests/evals/datasets/reply_cases.yaml",
) -> dict[str, Any]:
    """Run all reply test cases and return an evaluation report."""
    cases = yaml.safe_load(Path(dataset_path).read_text(encoding="utf-8"))
    results = []

    for case in cases:
        user_input = build_input(case)
        raw = await run_agent("review_reply_agent", user_input)
        reply = parse_output(raw)
        failures = run_checks(reply, case.get("checks", {}))

        results.append({
            "name": case.get("name", "unknown"),
            "passed": len(failures) == 0,
            "failures": failures,
            "reply_preview": reply[:100] if reply else "(empty)",
        })

    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": passed / total if total else 0,
        "results": results,
    }