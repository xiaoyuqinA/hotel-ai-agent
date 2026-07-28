"""Hotel Configuration — Agent 回复配置领域模型。"""

from dataclasses import dataclass, field


@dataclass
class ReplySettings:
    """Agent 回复配置 — 控制 AI 回复的语气、风格和行为规则。

    可以被 Chrome Extension 在线修改。
    后端通过 HotelConfigRepository 持久化（当前为 YAML 文件）。
    """

    tone: str = ""
    style: str = ""
    rules: list[str] = field(default_factory=list)
