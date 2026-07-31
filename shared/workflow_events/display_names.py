"""display_name 常量定义 — 所有 WorkflowEvent 的 display_name 集中管理。"""

from enum import StrEnum


class DisplayName(StrEnum):
    """各事件类型对应的前端显示文案。"""

    # ── Workflow 生命周期 ──
    WORKFLOW_STARTED = "工作流开始"
    WORKFLOW_COMPLETED = "工作流完成"
    WORKFLOW_FAILED = "工作流失败"
    WORKFLOW_CANCELLED = "工作流取消"

    # ── Analysis 节点 ──
    ANALYSIS_STARTED = "分析开始"
    ANALYSIS_COMPLETED = "分析完成"
    ANALYSIS_FAILED = "分析失败"

    # ── Generation 节点 ──
    GENERATION_STARTED = "生成开始"
    GENERATION_COMPLETED = "生成完成"
    GENERATION_FAILED = "生成失败"

    # ── Review 节点 ──
    REVIEW_STARTED = "审核开始"
    REVIEW_COMPLETED = "审核完成"
    REVIEW_FAILED = "审核失败"
