"""Analysis Node — 调用 review_analysis_agent 进行评论分析。"""

from shared.runtime.runtime import run_agent_typed

from capabilities.guest_experience.agents.review_analysis_agent.schemas import ReviewAnalysisResult

from ..state import ReviewReplyState


async def analysis_node(state: ReviewReplyState) -> ReviewReplyState:
    reviews_content = state.get("reviews_content", "")

    result = await run_agent_typed("review_analysis_agent", reviews_content, ReviewAnalysisResult)

    return {"anaylay_result": result}
