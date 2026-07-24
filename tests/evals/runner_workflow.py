"""Workflow eval runner — runs review_operation workflow and extracts reply_content.

Uses the real WorkflowRuntime (with checkpointer) so the full pipeline is tested:
load_hotel_context_node → analysis_node → strategy_node → generate_reply_node → publish_node.

Severity routing:
- Low: full workflow completes, result["reply_content"] contains the final reply.
- Medium: workflow pauses at human_review_node (interrupt). Interrupted state
  contains reply_content (generated before the interrupt).
- High: workflow pauses at human_process_node (interrupt). No reply_content in
  the interrupted state.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml
from langgraph.types import Interrupt

from shared.runtime.workflow_runtime import WorkflowRuntime


DATASET_PATH = Path(__file__).parent / "datasets" / "workflow_cases.yaml"


async def run_workflow_case(case: dict) -> str:
    """Run review_operation workflow for a single case and extract reply_content.

    Only Low severity cases complete the full workflow. Medium/High cases
    raise an Interrupt — the caller should use run_workflow_case_with_interrupt
    for those.
    """
    hotel_id = case["hotel_id"]
    review = case["review"]
    runtime = WorkflowRuntime()
    await runtime.startup()
    try:
        result = await runtime.run(
            "review_operation",
            (hotel_id, review),
            thread_id=f"eval-{uuid4()}",
        )
        return result.get("reply_content", "")
    finally:
        await runtime.shutdown()


async def run_workflow_case_with_interrupt(
    case: dict,
) -> tuple[str, str | None]:
    """Run a workflow case that is expected to interrupt (Medium/High severity).

    Returns (interrupt_type, reply_content) where interrupt_type is the
    task_type from the interrupt payload, and reply_content may be None
    for High severity (human_process runs before generate_reply).
    """
    hotel_id = case["hotel_id"]
    review = case["review"]
    runtime = WorkflowRuntime()
    await runtime.startup()
    try:
        await runtime.run(
            "review_operation",
            (hotel_id, review),
            thread_id=f"eval-{uuid4()}",
        )
        # If no interrupt was raised, return empty interrupt type
        return ("none", "")
    except Interrupt as exc:
        payload = exc.args[0] if exc.args else {}
        if isinstance(payload, dict):
            interrupt_type = payload.get("task_type", "unknown")
            reply_content = payload.get("reply_content")
        else:
            interrupt_type = "unknown"
            reply_content = None
        return (interrupt_type, reply_content)
    finally:
        await runtime.shutdown()


def run_checks(reply: str, checks: dict) -> list[str]:
    """Run keyword/length checks and return list of failures.

    Reuses the same check logic as evaluator_reply.run_checks.
    """
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


def load_cases(dataset_path: str | Path = DATASET_PATH) -> list[dict]:
    """Load workflow test cases from the golden dataset YAML."""
    return yaml.safe_load(Path(dataset_path).read_text(encoding="utf-8"))


def get_low_severity_cases(
    dataset_path: str | Path = DATASET_PATH,
) -> list[dict]:
    """Filter to only Low severity cases (full workflow completes)."""
    cases = load_cases(dataset_path)
    return [c for c in cases if c.get("severity") == "Low"]


async def evaluate_workflow_replies(
    dataset_path: str | Path = DATASET_PATH,
) -> dict[str, Any]:
    """Run all Low severity workflow cases and return an evaluation report.

    Only Low severity cases are tested here — they complete the full workflow
    without interruption. Medium/High cases are tested separately via
    interrupt detection.
    """
    cases = get_low_severity_cases(dataset_path)
    results = []

    for case in cases:
        reply = await run_workflow_case(case)
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


if __name__ == "__main__":
    report = asyncio.run(evaluate_workflow_replies())
    print(f"Total: {report['total']}")
    print(f"Passed: {report['passed']}")
    print(f"Failed: {report['failed']}")
    print(f"Pass rate: {report['pass_rate']:.0%}")
    for r in report["results"]:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"  [{status}] {r['name']}: {r['reply_preview']}")
        for f in r["failures"]:
            print(f"        - {f}")
