"""Analysis Node — 调用 review_analysis_agent 进行评论分析。"""

from shared.runtime.runtime import run_agent

from capabilities.guest_experience.agents.review_analysis_agent.schemas import ReviewAnalysisResult

from ..state import ReviewReplyState, WorkflowError


async def analysis_node(state: ReviewReplyState) -> ReviewReplyState:
    reviews_content = state.get("reviews_content", "")

    result = await run_agent("review_analysis_agent", reviews_content)

    if isinstance(result, ReviewAnalysisResult):
        return {"anaylay_result": result}
    if isinstance(result, str):
        try:
            return {"anaylay_result": ReviewAnalysisResult.model_validate_json(result)}
        except Exception:
            pass

    raise WorkflowError("analysis failed: unable to parse result")