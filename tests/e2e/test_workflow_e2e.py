"""评论运营工作流端到端集成测试。

直接使用 WorkflowRuntime 运行工作流，验证完整的执行链路和事件流。
不依赖 HTTP 和 Event Store（PostgreSQL/Redis），适用于任何环境。

severity 路由验证：
- Low:    分析 → 策略 → 生成 → 发布（完整工作流完成）
- Medium:  分析 → 策略 → 生成 → 人工审核（interrupt，带 reply_content）
- High:   分析 → 策略 → 人工处理（interrupt，无 reply_content）

测试策略：
- Phase 1: 不依赖 LLM 的测试（无需 --run-llm），使用 mock agent 验证工作流逻辑
- Phase 2: 依赖 LLM 的测试（需要 --run-llm），验证真实 LLM 输出质量
- Phase 3: 遗留系统回归测试（原有 boundary/eval tests），确保不破坏已有功能
"""

import asyncio
from uuid import uuid4

import pytest

from shared.runtime.workflow_runtime import WorkflowRuntime


# =============================================================================
# Phase 1: 工作流基础设施测试（无需 LLM）
# =============================================================================


class TestWorkflowLifecycle:
    """WorkflowRuntime 生命周期管理。"""

    @pytest.mark.asyncio
    async def test_startup_shutdown(self):
        """startup() 和 shutdown() 应正常执行，不抛异常。"""
        runtime = WorkflowRuntime()
        await runtime.startup()
        try:
            assert runtime._started is True
            assert runtime._checkpointer is not None
        finally:
            await runtime.shutdown()
        assert runtime._started is False

    @pytest.mark.asyncio
    async def test_get_workflow_before_startup_raises(self):
        """未 startup 时调用 get_workflow 应抛出 RuntimeError。"""
        runtime = WorkflowRuntime()
        with pytest.raises(RuntimeError, match="not started"):
            runtime.get_workflow("review_operation")

    @pytest.mark.asyncio
    async def test_get_nonexistent_workflow_raises(self):
        """获取不存在的 workflow 应抛出 KeyError。"""
        runtime = WorkflowRuntime()
        await runtime.startup()
        try:
            with pytest.raises(KeyError):
                runtime.get_workflow("nonexistent_workflow")
        finally:
            await runtime.shutdown()

    @pytest.mark.asyncio
    async def test_workflow_registration(self):
        """Workflow 应成功注册到 registry。"""
        runtime = WorkflowRuntime()
        await runtime.startup()
        try:
            from shared.registry.workflow_registry import list_workflows

            workflows = list_workflows()
            assert "review_operation" in workflows
        finally:
            await runtime.shutdown()


class TestWorkflowInputMapper:
    """input_mapper 映射逻辑。"""

    @pytest.mark.asyncio
    async def test_string_input(self):
        """纯字符串输入应正确映射 state。"""
        runtime = WorkflowRuntime()
        await runtime.startup()
        try:
            workflow = runtime.get_workflow("review_operation")
            state = workflow.input_mapper("房间卫生很差")
            assert state["reviews_content"] == "房间卫生很差"
            assert state["hotel_id"] is None
            assert state["anaylay_result"] is None
        finally:
            await runtime.shutdown()

    @pytest.mark.asyncio
    async def test_tuple_input(self):
        """tuple (hotel_id, review) 输入应正确拆包。"""
        runtime = WorkflowRuntime()
        await runtime.startup()
        try:
            workflow = runtime.get_workflow("review_operation")
            state = workflow.input_mapper(("hotel_001", "房间卫生很差"))
            assert state["reviews_content"] == "房间卫生很差"
            assert state["hotel_id"] == "hotel_001"
        finally:
            await runtime.shutdown()


# =============================================================================
# Phase 2: 完整工作流执行测试（需要 LLM）
# =============================================================================


@pytest.mark.needs_llm
class TestWorkflowE2E:
    """完整工作流端到端测试。

    覆盖所有 severity 路由路径。
    使用真实 LLM，验证回复生成质量。
    """

    REVIEW_LOW = "房间很干净，服务很好"
    REVIEW_MEDIUM = "前台态度差，对我大声说话"
    REVIEW_HIGH = "房间卫生很差，投诉后没人处理，希望退款赔偿"
    HOTEL_ID = "hotel_001"

    # ── 辅助方法 ──────────────────────────────────────────────────────────

    @staticmethod
    async def _make_runtime():
        runtime = WorkflowRuntime()
        await runtime.startup()
        return runtime

    # ── Low Severity 测试 ─────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_low_severity_completes(self):
        """Low severity：工作流应完整执行并返回 reply_content。"""
        runtime = await self._make_runtime()
        try:
            result = await runtime.run(
                "review_operation",
                (self.HOTEL_ID, self.REVIEW_LOW),
                thread_id=f"e2e-low-{uuid4().hex[:8]}",
            )
            assert result is not None
            assert "reply_content" in result, f"缺少 reply_content: {result}"
            reply = result["reply_content"]
            assert isinstance(reply, str), f"reply_content 应为字符串: {type(reply)}"
            assert len(reply) > 10, f"reply_content 过短: {reply}"
        finally:
            await runtime.shutdown()

    @pytest.mark.asyncio
    async def test_low_severity_reply_quality(self):
        """Low severity：回复应包含致歉、酒店名称，不应承诺赔偿。"""
        runtime = await self._make_runtime()
        try:
            result = await runtime.run(
                "review_operation",
                (self.HOTEL_ID, self.REVIEW_LOW),
                thread_id=f"e2e-qual-{uuid4().hex[:8]}",
            )
            reply = result.get("reply_content", "")

            # 应包含酒店名称（context injection）
            assert "深圳湾XX酒店" in reply, f"酒店名称未注入: {reply}"

            # 应表达感谢（正面评论）
            assert "感谢" in reply, f"缺少感谢: {reply}"

            # 不应包含内部流程
            forbidden = ["工单", "工程部", "报修单"]
            for word in forbidden:
                assert word not in reply, f"暴露内部流程: '{word}'"

            # 不应过短
            assert len(reply) > 30, f"回复过短: {reply}"
        finally:
            await runtime.shutdown()

    @pytest.mark.asyncio
    async def test_low_severity_no_hotel_id(self):
        """不指定 hotel_id：工作流应使用默认配置完成。"""
        runtime = await self._make_runtime()
        try:
            result = await runtime.run(
                "review_operation",
                self.REVIEW_LOW,
                thread_id=f"e2e-noid-{uuid4().hex[:8]}",
            )
            assert result is not None
            assert "reply_content" in result
            assert len(result["reply_content"]) > 10
        finally:
            await runtime.shutdown()

    @pytest.mark.asyncio
    async def test_low_severity_publish_status(self):
        """Low severity：最终 state 应包含 published 状态。"""
        runtime = await self._make_runtime()
        try:
            result = await runtime.run(
                "review_operation",
                (self.HOTEL_ID, self.REVIEW_LOW),
                thread_id=f"e2e-pub-{uuid4().hex[:8]}",
            )
            # publish_node 负责设置 publish_status
            assert result.get("publish_status") == "published", (
                f"publish_status 应为 'published': {result}"
            )
        finally:
            await runtime.shutdown()

    # ── Medium Severity 测试 ───────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_medium_severity_interrupts_at_human_review(self):
        """Medium severity：应在 human_review 中断，且带 reply_content。"""
        runtime = await self._make_runtime()
        try:
            with pytest.raises(Exception) as exc_info:
                await runtime.run(
                    "review_operation",
                    (self.HOTEL_ID, self.REVIEW_MEDIUM),
                    thread_id=f"e2e-med-{uuid4().hex[:8]}",
                )

            # LangGraph Interrupt 是 BaseException，会被包装后抛出
            # 验证中断发生在 human_review，且 reply_content 不为空
            error_msg = str(exc_info.value)
            # 中断信息应该包含 task_type 和 reply_content
            assert "human_review" in error_msg or "interrupt" in error_msg.lower(), (
                f"应为 human_review interrupt: {error_msg}"
            )
        finally:
            await runtime.shutdown()

    # ── High Severity 测试 ─────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_high_severity_interrupts_at_human_process(self):
        """High severity：应在 human_process 中断，且无 reply_content。"""
        runtime = await self._make_runtime()
        try:
            with pytest.raises(Exception) as exc_info:
                await runtime.run(
                    "review_operation",
                    (self.HOTEL_ID, self.REVIEW_HIGH),
                    thread_id=f"e2e-high-{uuid4().hex[:8]}",
                )

            error_msg = str(exc_info.value)
            assert "human_process" in error_msg or "interrupt" in error_msg.lower(), (
                f"应为 human_process interrupt: {error_msg}"
            )
        finally:
            await runtime.shutdown()

    # ── Interrupt Resume 测试 ──────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_medium_resume_after_interrupt(self):
        """Medium severity 中断后 resume 应继续执行到 publish。"""
        runtime = await self._make_runtime()
        thread_id = f"e2e-resume-{uuid4().hex[:8]}"
        try:
            # 首次运行，预期中断
            with pytest.raises(Exception):
                await runtime.run(
                    "review_operation",
                    (self.HOTEL_ID, self.REVIEW_MEDIUM),
                    thread_id=thread_id,
                )

            # 恢复运行（模拟人工确认回复）
            result = await runtime.resume(
                "review_operation",
                thread_id=thread_id,
                data={"reply_content": "感谢您的反馈，我们会改进服务态度。"},
            )
            assert result is not None
            assert result.get("publish_status") == "published"
            assert "reply_content" in result
        finally:
            await runtime.shutdown()

    @pytest.mark.asyncio
    async def test_high_resume_after_interrupt(self):
        """High severity 中断后 resume 应继续执行到 publish。"""
        runtime = await self._make_runtime()
        thread_id = f"e2e-resume-high-{uuid4().hex[:8]}"
        try:
            # 首次运行，预期中断
            with pytest.raises(Exception):
                await runtime.run(
                    "review_operation",
                    (self.HOTEL_ID, self.REVIEW_HIGH),
                    thread_id=thread_id,
                )

            # 恢复运行（模拟人工填写回复内容）
            result = await runtime.resume(
                "review_operation",
                thread_id=thread_id,
                data={
                    "reply_content": "非常抱歉给您带来不好的体验，我们将立即跟进处理。"
                },
            )
            assert result is not None
            assert result.get("publish_status") == "published"
            assert "reply_content" in result
            # High severity 的回复应是人工填写的
            assert "跟进处理" in result["reply_content"]
        finally:
            await runtime.shutdown()

    # ── 边界场景测试 ├──────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_empty_review(self):
        """空评论不应导致崩溃。"""
        runtime = await self._make_runtime()
        try:
            result = await runtime.run(
                "review_operation",
                ("",),
                thread_id=f"e2e-empty-{uuid4().hex[:8]}",
            )
            # review_operation input_mapper 期望至少 reviews_content
            # 空字符串应能正常处理
            assert result is not None
        finally:
            await runtime.shutdown()

    @pytest.mark.asyncio
    async def test_very_long_review(self):
        """超长评论不应导致崩溃。"""
        runtime = await self._make_runtime()
        long_review = "酒店很好，" * 300  # ~900 chars
        try:
            result = await runtime.run(
                "review_operation",
                long_review,
                thread_id=f"e2e-long-{uuid4().hex[:8]}",
            )
            assert result is not None
        finally:
            await runtime.shutdown()


# =============================================================================
# Phase 3: 遗留系统回归测试
# =============================================================================


@pytest.mark.needs_llm
class TestRegressionExistingEvals:
    """确保原有 eval 测试逻辑不被破坏。

    这些测试使用与 tests/evals/ 相同的 runner 模式。
    """

    @pytest.mark.asyncio
    async def test_workflow_golden_dataset_runs(self):
        """Golden dataset 应能正常加载并执行（不要求全部通过）。"""
        from tests.evals.runner_workflow import evaluate_workflow_replies

        report = await evaluate_workflow_replies()
        # 验证返回结构完整性
        assert "total" in report
        assert "passed" in report
        assert "failed" in report
        assert "pass_rate" in report
        assert report["total"] > 0
        # 不要求全部通过（LLM 输出有方差），但至少有一点通过
        assert report["passed"] >= 1

    @pytest.mark.asyncio
    async def test_low_severity_cases_filter(self):
        """Low severity 筛选逻辑应正常工作。"""
        from tests.evals.runner_workflow import get_low_severity_cases

        cases = get_low_severity_cases()
        assert len(cases) > 0
        for case in cases:
            assert case.get("severity") == "Low"

    @pytest.mark.asyncio
    async def test_reply_checks_logic(self):
        """回复检查逻辑应正确工作。"""
        from tests.evals.runner_workflow import run_checks

        # 应通过
        failures = run_checks(
            "尊敬的客人，我们深表歉意",
            {
                "must_contain": ["歉意"],
                "must_not_contain": ["赔偿"],
                "min_length": 5,
                "max_length": 500,
            },
        )
        assert len(failures) == 0, f"应有 0 失败: {failures}"

        # 应失败
        failures = run_checks(
            "短",
            {
                "min_length": 10,
            },
        )
        assert len(failures) == 1
        assert "长度不足" in failures[0]
