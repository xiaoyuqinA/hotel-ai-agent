"""Comparison runner — with-context vs without-context.

Runs the same 20 cases through:
1. Without context: run_agent("review_reply_agent", review) — no HotelContext
2. With context: WorkflowRuntime.run("review_operation", (hotel_id, review)) — full workflow with HotelContext

Outputs a side-by-side comparison table showing which checks pass/fail
for each approach.

Usage:
    python -m tests.evals.runner_comparison
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from uuid import uuid4

from shared.runtime.runtime import run_agent
from shared.runtime.workflow_runtime import WorkflowRuntime
from tests.evals.runner_workflow import run_checks, load_cases


def build_input_no_context(review: str) -> str:
    """Build input for review_reply_agent without HotelContext.

    The existing evaluator_reply.build_input constructs:
    '客户评论：{review}\n\n评论分析：\n{json}'

    For the baseline, we pass just the review as a plain string.
    The agent will still run but without hotel context.
    """
    return f"客户评论：{review}"


async def run_without_context(review: str) -> str:
    """Run review_reply_agent directly without HotelContext."""
    user_input = build_input_no_context(review)
    raw = await run_agent("review_reply_agent", user_input)
    # Agent may return ReplyResult or string
    if isinstance(raw, str):
        return raw
    if hasattr(raw, "reply_content"):
        return raw.reply_content
    return str(raw)


async def run_with_context(hotel_id: str, review: str) -> str:
    """Run review_operation workflow with HotelContext."""
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


async def compare_case(case: dict) -> dict[str, Any]:
    """Run a single case through both variants and compare checks."""
    review = case["review"]
    hotel_id = case["hotel_id"]
    checks = case.get("checks", {})

    # Only Low severity cases complete the full workflow
    if case.get("severity") != "Low":
        return {
            "name": case.get("name", "unknown"),
            "severity": case.get("severity", "Unknown"),
            "skipped": True,
            "reason": f"Only Low severity cases tested (got {case.get('severity')})",
        }

    # Run without context
    reply_no_ctx = await run_without_context(review)
    failures_no_ctx = run_checks(reply_no_ctx, checks)

    # Run with context
    reply_with_ctx = await run_with_context(hotel_id, review)
    failures_with_ctx = run_checks(reply_with_ctx, checks)

    return {
        "name": case.get("name", "unknown"),
        "severity": case.get("severity", "Unknown"),
        "skipped": False,
        "without_context": {
            "passed": len(failures_no_ctx) == 0,
            "failures": failures_no_ctx,
            "reply_preview": reply_no_ctx[:80] if reply_no_ctx else "(empty)",
        },
        "with_context": {
            "passed": len(failures_with_ctx) == 0,
            "failures": failures_with_ctx,
            "reply_preview": reply_with_ctx[:80] if reply_with_ctx else "(empty)",
        },
    }


async def run_comparison(
    dataset_path: str | Path | None = None,
) -> dict[str, Any]:
    """Run all cases through both variants and return comparison report."""
    cases = load_cases(dataset_path) if dataset_path else load_cases()
    results = []

    for case in cases:
        result = await compare_case(case)
        results.append(result)

    # Count results (only non-skipped cases)
    active = [r for r in results if not r.get("skipped")]
    without_pass = sum(1 for r in active if r["without_context"]["passed"])
    with_pass = sum(1 for r in active if r["with_context"]["passed"])
    total = len(active)

    return {
        "total": total,
        "skipped": len(results) - total,
        "without_context": {
            "passed": without_pass,
            "failed": total - without_pass,
            "pass_rate": without_pass / total if total else 0,
        },
        "with_context": {
            "passed": with_pass,
            "failed": total - with_pass,
            "pass_rate": with_pass / total if total else 0,
        },
        "results": results,
    }


def print_comparison_table(report: dict[str, Any]) -> None:
    """Print a side-by-side comparison table."""
    print("=" * 120)
    print("HotelContext Workflow Evaluation — Comparison Report")
    print("=" * 120)
    print(f"Total cases: {report['total']} (skipped: {report['skipped']})")
    print()

    # Summary
    print("-" * 120)
    print(f"{'Variant':<30} {'Passed':<10} {'Failed':<10} {'Pass Rate':<10}")
    print("-" * 120)
    wc = report["without_context"]
    wctx = report["with_context"]
    print(f"{'Without Context (run_agent)':<30} {wc['passed']:<10} {wc['failed']:<10} {wc['pass_rate']:.0%}")
    print(f"{'With Context (workflow)':<30} {wctx['passed']:<10} {wctx['failed']:<10} {wctx['pass_rate']:.0%}")
    print()

    # Detailed results
    print("-" * 120)
    print(f"{'Case':<35} {'Without':<12} {'With':<12} {'Improvement':<12}")
    print("-" * 120)

    for r in report["results"]:
        if r.get("skipped"):
            print(f"{r['name']:<35} {'SKIP':<12} {'SKIP':<12} {'N/A':<12} ({r.get('reason', '')})")
            continue

        no_pass = "PASS" if r["without_context"]["passed"] else "FAIL"
        with_pass = "PASS" if r["with_context"]["passed"] else "FAIL"

        if r["without_context"]["passed"] and not r["with_context"]["passed"]:
            improvement = "REGRESS"
        elif not r["without_context"]["passed"] and r["with_context"]["passed"]:
            improvement = "IMPROVED"
        elif r["without_context"]["passed"] and r["with_context"]["passed"]:
            improvement = "BOTH OK"
        else:
            improvement = "BOTH FAIL"

        print(f"{r['name']:<35} {no_pass:<12} {with_pass:<12} {improvement:<12}")

    print()
    print("=" * 120)
    improvement_count = sum(
        1 for r in report["results"]
        if not r.get("skipped")
        and not r["without_context"]["passed"]
        and r["with_context"]["passed"]
    )
    print(f"Cases improved by context injection: {improvement_count}/{report['total']}")
    print(f"Without context pass rate: {wc['pass_rate']:.0%}")
    print(f"With context pass rate: {wctx['pass_rate']:.0%}")
    print("=" * 120)


if __name__ == "__main__":
    report = asyncio.run(run_comparison())
    print_comparison_table(report)
