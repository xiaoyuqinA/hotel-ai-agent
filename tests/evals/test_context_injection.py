"""Context injection verification tests.

Proves that HotelContext injection actually improves reply quality —
not just that the code runs. Tests verify:
1. Hotel name appears in replies (context injection works)
2. Policy accuracy (breakfast time, parking policy reflected)
3. Brand voice tone (not mechanical template)
4. Interrupt behavior for Medium/High severity cases
"""

import pytest

from tests.evals.runner_workflow import (
    run_workflow_case,
    run_workflow_case_with_interrupt,
)


@pytest.mark.needs_llm
class TestContextInjection:
    """Verify HotelContext is injected and affects reply content."""

    @pytest.mark.asyncio
    async def test_hotel_name_in_reply(self):
        """HotelContext should cause the hotel name to appear in replies."""
        case = {
            "review": "房间卫生差，希望改善",
            "hotel_id": "hotel_001",
            "severity": "Low",
            "checks": {},
        }
        reply = await run_workflow_case(case)
        assert "深圳湾XX酒店" in reply, f"酒店名称未出现在回复中: {reply}"

    @pytest.mark.asyncio
    async def test_policy_accuracy_breakfast(self):
        """Breakfast policy should be accurately reflected in replies."""
        case = {
            "review": "早餰几点开始？",
            "hotel_id": "hotel_001",
            "severity": "Low",
            "checks": {},
        }
        reply = await run_workflow_case(case)
        assert "7:00" in reply, f"早餐时间未出现在回复中: {reply}"

    @pytest.mark.asyncio
    async def test_policy_accuracy_parking(self):
        """Parking policy should be accurately reflected in replies."""
        case = {
            "review": "停车场怎么样？免费吗？",
            "hotel_id": "hotel_001",
            "severity": "Low",
            "checks": {},
        }
        reply = await run_workflow_case(case)
        assert "免费" in reply, f"免费停车未出现在回复中: {reply}"
        assert "地下" in reply, f"地下停车场未出现在回复中: {reply}"

    @pytest.mark.asyncio
    async def test_brand_voice_tone(self):
        """Reply should reflect brand voice: professional, warm, sincere."""
        case = {
            "review": "房间太吵，影响睡眠",
            "hotel_id": "hotel_001",
            "severity": "Low",
            "checks": {},
        }
        reply = await run_workflow_case(case)
        # Should not be a generic template — should be substantive
        assert len(reply) > 30, f"回复过短，可能是模板: {reply}"
        # Should express apology for complaints (brand voice rule)
        assert "歉意" in reply or "抱歉" in reply or "感谢" in reply, (
            f"回复未体现品牌语音: {reply}"
        )

    @pytest.mark.asyncio
    async def test_brand_voice_no_mechanical_template(self):
        """Reply should not be a mechanical template."""
        case = {
            "review": "卫生差",
            "hotel_id": "hotel_001",
            "severity": "Low",
            "checks": {},
        }
        reply = await run_workflow_case(case)
        # Should be a personalized reply, not a generic template
        assert len(reply) > 40, f"回复可能是机械化模板: {reply}"

    @pytest.mark.asyncio
    async def test_no_internal_process_exposure(self):
        """Reply should not expose internal processes (work order, etc.)."""
        case = {
            "review": "空调坏了，报修了两天都没人来修",
            "hotel_id": "hotel_001",
            "severity": "Low",
            "checks": {},
        }
        reply = await run_workflow_case(case)
        forbidden = ["工单", "工程部", "维修流程", "报修单"]
        for word in forbidden:
            assert word not in reply, f"回复暴露内部流程: '{word}' in {reply}"

    @pytest.mark.asyncio
    async def test_no_compensation_promise(self):
        """Reply should not promise unconfirmed compensation."""
        case = {
            "review": "吃了酒店早餐后拉肚子，要求赔偿医疗费",
            "hotel_id": "hotel_001",
            "severity": "Low",
            "checks": {},
        }
        reply = await run_workflow_case(case)
        forbidden = ["赔偿", "补偿", "报销", "医疗费"]
        for word in forbidden:
            assert word not in reply, f"回复承诺补偿: '{word}' in {reply}"


@pytest.mark.needs_llm
class TestInterruptBehavior:
    """Verify Medium/High severity cases pause at the correct interrupt point."""

    @pytest.mark.asyncio
    async def test_medium_severity_interrupts_at_human_review(self):
        """Medium severity should interrupt at human_review with reply_content."""
        case = {
            "review": "前台态度差，对我大声说话",
            "hotel_id": "hotel_001",
            "severity": "Medium",
            "checks": {},
        }
        interrupt_type, reply_content = await run_workflow_case_with_interrupt(case)
        assert interrupt_type == "human_review", (
            f"Expected human_review interrupt, got: {interrupt_type}"
        )
        # Medium severity: AI generates reply before human review, so
        # reply_content should be present in the interrupt payload
        assert reply_content is not None, (
            "Medium severity should have reply_content in interrupt payload"
        )
        assert len(reply_content) > 0, "reply_content should not be empty"

    @pytest.mark.asyncio
    async def test_high_severity_interrupts_at_human_process(self):
        """High severity should interrupt at human_process without reply_content."""
        case = {
            "review": "房间卫生很差，投诉后没人处理，希望退款",
            "hotel_id": "hotel_001",
            "severity": "High",
            "checks": {},
        }
        interrupt_type, reply_content = await run_workflow_case_with_interrupt(case)
        assert interrupt_type == "human_process", (
            f"Expected human_process interrupt, got: {interrupt_type}"
        )
        # High severity: human_process runs BEFORE generate_reply, so
        # reply_content should be None in the interrupt payload
        assert reply_content is None, (
            "High severity should not have reply_content in interrupt payload"
        )
