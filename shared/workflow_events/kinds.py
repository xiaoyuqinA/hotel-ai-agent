"""工作流事件类型枚举 — 业务层与 LangGraph Runtime 的解耦层。"""

from enum import Enum


class EventKind(str, Enum):
    """Workflow Event 类型枚举。

    Chrome Extension 通过 WebSocket 接收这些事件，
    不需要知道 LangGraph / LangChain 的任何概念。
    """

    # Workflow 生命周期

    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"

    # Node 生命周期

    NODE_STARTED = "node_started"
    NODE_COMPLETED = "node_completed"
    NODE_FAILED = "node_failed"

    # LLM Streaming

    TOKEN_DELTA = "token_delta"

    # 工具调用 (v3)

    TOOL_CALL = "tool_call"

    # 自定义业务事件

    CUSTOM_EVENT = "custom_event"

    # State

    STATE_UPDATED = "state_updated"


class BusinessEvent(str, Enum):
    """Agent Workflow 业务事件类型。

    Agent 在 node 内通过 get_stream_writer() 发送这些事件，
    用于表达业务进度状态（对 Chrome Extension 有意义）。

    命名规则：{phase}_{operation}

    Phase:
        - analysis: 分析阶段
        - generation: 生成阶段
        - review: 审核阶段
    """

    # ── Analysis 阶段 ───────────────────────────────────────────────────

    ANALYSIS_STARTED = "analysis_started"
    """分析开始 — 正在分析客户评论"""

    ANALYSIS_PROGRESS = "analysis_progress"
    """分析进度 — 分析进度更新（可选）"""

    ANALYSIS_COMPLETED = "analysis_completed"
    """分析完成 — 分析已完成"""

    ANALYSIS_FAILED = "analysis_failed"
    """分析失败 — 分析过程中发生错误"""

    # ── Generation 阶段 ─────────────────────────────────────────────────

    GENERATION_STARTED = "generation_started"
    """生成开始 — 正在生成回复"""

    GENERATION_PROGRESS = "generation_progress"
    """生成进度 — 生成进度更新（可选）"""

    GENERATION_COMPLETED = "generation_completed"
    """生成完成 — 回复已生成"""

    GENERATION_FAILED = "generation_failed"
    """生成失败 — 生成过程中发生错误"""

    # ── Review 阶段 ─────────────────────────────────────────────────────

    REVIEW_STARTED = "review_started"
    """审核开始 — 正在审核回复"""

    REVIEW_COMPLETED = "review_completed"
    """审核完成 — 审核已通过"""

    REVIEW_FAILED = "review_failed"
    """审核失败 — 审核未通过"""

    # ── 评论接入 ───────────────────────────────────────────────────────

    COMMENT_RECEIVED = "comment_received"
    """评论接入 — 新评论已进入处理流程"""
