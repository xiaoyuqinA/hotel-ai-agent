"""
Agent Definition

Agent 的静态定义。
描述：
- Agent是谁
- 能做什么
- 使用什么模型
- 有哪些工具
- 如何运行
"""

from dataclasses import dataclass, field
from typing import (
    Optional,
    List,
    Dict,
    Any,
    Type,
)
from enum import Enum

# =====================================================
# Agent 类型
# =====================================================

class AgentType(str, Enum):
    """
    Agent角色类型
    """

    CHAT = "chat"

    PLANNER = "planner"

    EXECUTOR = "executor"

    RESEARCHER = "researcher"

    CODER = "coder"

    REVIEWER = "reviewer"

    SUPERVISOR = "supervisor"

# =====================================================
# Memory模式
# =====================================================

class MemoryMode(str, Enum):

    """
    Agent Memory策略
    """

    NONE = "none"

    SESSION = "session"

    LONG_TERM = "long_term"

    HYBRID = "hybrid"

# =====================================================
# Agent生命周期
# =====================================================

class AgentStatus(str, Enum):

    ENABLED = "enabled"

    DISABLED = "disabled"

    TESTING = "testing"

# =====================================================
# Model配置
# =====================================================

@dataclass
class ModelConfig:

    provider: str

    model_name: str

    temperature: float = 0.7

    max_tokens: Optional[int] = None

    # 其他模型参数

    extra: Dict[str, Any] = field(
        default_factory=dict
    )

# =====================================================
# Prompt配置
# =====================================================

@dataclass
class PromptConfig:

    """
    Prompt来源

    可以支持:

    1. 文件
    2. 数据库
    3. Prompt Hub
    """

    template_id: Optional[str] = None

    version: str = "1.0"

    system_prompt: Optional[str] = None

    variables: Dict[str, Any] = field(
        default_factory=dict
    )

# =====================================================
# Tool配置
# =====================================================

@dataclass
class ToolConfig:

    """
    Agent允许使用的工具
    """

    tools: List[str] = field(
        default_factory=list
    )

    # 是否允许动态选择工具

    allow_dynamic_tools: bool = False

# =====================================================
# Memory配置
# =====================================================

@dataclass
class MemoryConfig:

    mode: MemoryMode = MemoryMode.NONE

    # 最大上下文长度

    max_context_tokens: int = 8000

    # 是否自动摘要

    enable_summary: bool = True

    # 外部memory

    provider: Optional[str] = None

# =====================================================
# Skill配置
# =====================================================

@dataclass
class SkillConfig:

    """
    Agent技能

    类似 DeepAgents 的 skills
    """

    skills: List[str] = field(
        default_factory=list
    )

# =====================================================
# Permission
# =====================================================

@dataclass
class PermissionConfig:

    """
    Agent权限控制
    """

    allow_tools: List[str] = field(
        default_factory=list
    )

    deny_tools: List[str] = field(
        default_factory=list
    )

    allow_network: bool = False

# =====================================================
# Agent Definition
# =====================================================

@dataclass
class AgentDefinition:

    """
    Agent完整定义

    Runtime加载这个对象创建真正Agent
    """

    # ==========================
    # Identity
    # ==========================

    id: str

    name: str

    description: str

    # Agent类别

    type: AgentType = AgentType.CHAT

    # 当前状态

    status: AgentStatus = AgentStatus.ENABLED

    # ==========================
    # LLM
    # ==========================

    model: Optional[ModelConfig] = None

    # ==========================
    # Prompt
    # ==========================

    prompt: Optional[PromptConfig] = None

    # ==========================
    # Tools
    # ==========================

    tools: Optional[ToolConfig] = None

    # ==========================
    # Memory
    # ==========================

    memory: Optional[MemoryConfig] = None

    # ==========================
    # Skills
    # ==========================

    skills: Optional[SkillConfig] = None

    # ==========================
    # Permission
    # ==========================

    permissions: Optional[PermissionConfig] = None

    # ==========================
    # Multi Agent
    # ==========================

    # 可以调用哪些Agent

    sub_agents: List[str] = field(
        default_factory=list
    )

    # ==========================
    # Output
    # ==========================

    output_schema: Optional[Type] = None

    # ==========================
    # Runtime
    # ==========================

    runtime_config: Dict[str, Any] = field(
        default_factory=dict
    )

    # ==========================
    # Metadata
    # ==========================

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    version: str = "1.0"

    def can_use_tool(
        self,
        tool_name: str
    ) -> bool:

        if self.permissions is None:
            return True

        if tool_name in self.permissions.deny_tools:
            return False

        if (
            self.permissions.allow_tools
            and tool_name not in self.permissions.allow_tools
        ):
            return False

        return True

    def get_system_prompt(self) -> str:

        if self.prompt is None:
            return ""

        return (
            self.prompt.system_prompt
            or ""
        )

    def to_dict(self):

        return {

            "id": self.id,

            "name": self.name,

            "description": self.description,

            "type": self.type.value,

            "status": self.status.value,

            "version": self.version,

            "model": self.model.__dict__
            if self.model else None,

            "tools": self.tools.__dict__
            if self.tools else None,

            "memory": self.memory.__dict__
            if self.memory else None,

            "skills": self.skills.__dict__
            if self.skills else None,

            "metadata": self.metadata

        }