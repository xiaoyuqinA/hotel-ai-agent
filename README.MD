hotel-ai-agents
│
├── shared                          # 公共基础能力
│   │
│   ├── knowledge                   # Knowledge Client 查询知识
│   │   ├── __init__.py
│   │   └── client.py
│   │
│   ├── tools                       # 通用工具
│   │   ├── __init__.py
│   │   ├── registry.py
│   │   └── common_tools.py
│   │
│   ├── prompts                     # Prompt 加载与管理
│   │   ├── __init__.py
│   │   ├── loader.py
│   │   └── manager.py
│   │
│   ├── memory                      # Memory 管理
│   │   ├── __init__.py
│   │   └── client.py
│   │
│   ├── conversation                # 会话管理
│   │   ├── __init__.py
│   │   ├── session.py              # InMemorySession 实现
│   │   └── manager.py              # 多 session 管理
│   │
│   ├── llm                         # LLM 配置、工厂、调用
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── factory.py
│   │
│   ├── config                      # 系统配置
│   │   ├── __init__.py
│   │   └── settings.py
│   │
│   └── runtime                     # Agent Runtime 抽象层
│       ├── __init__.py
│       ├── base.py
│       ├── openai_adapter.py
│       ├── deep_adapter.py
│       └── launcher.py
│
├── hotel_agents                    # 业务 Agent
│   │
│   ├── guest_experience_agent      # OpenAI Agents SDK
│   │   ├── __init__.py
│   │   ├── agent.py                # Agent 定义 + 启动入口
│   │   ├── definition.py           # Agent 定义
│   │   ├── tools.py                # Agent 专属 Tool
│   │   ├── prompt.py               # System Prompt
│   │   └── config.yaml
│   │
│   ├── hotel_knowledge_agent       # OpenAI Agents SDK
│   │   ├── __init__.py
│   │   ├── definition.py
│   │   ├── tools.py
│   │   ├── prompt.py
│   │   └── config.yaml
│   │
│   ├── revenue_intelligence_agent  # Deep Agents
│   │   ├── __init__.py
│   │   ├── definition.py
│   │   ├── tools.py
│   │   ├── prompt.py
│   │   └── config.yaml
│   │
│   ├── ota_operations_agent        # OpenAI Agents SDK
│   │   ├── __init__.py
│   │   ├── definition.py
│   │   ├── tools.py
│   │   ├── prompt.py
│   │   └── config.yaml
│   │
│   └── marketing_content_agent     # OpenAI Agents SDK
│       ├── __init__.py
│       ├── definition.py
│       ├── tools.py
│       ├── prompt.py
│       └── config.yaml
│
├── launcher                        # 统一入口
│   ├── __init__.py
│   └── main.py
│
├── api                             # 服务入口
│   ├── __init__.py
│   ├── main.py
│   ├── routes.py
│   └── schemas.py
│
├── tests                           # 测试
│   └── __init__.py
│
├── pyproject.toml                  # 项目构建配置（setuptools）
├── requirements.txt
│
└── README.md


## Agent选型

| Agent                      | 推荐框架                                | 原因                 |
| -------------------------- | ----------------------------------- | ------------------ |
| Guest Experience Agent     | OpenAI Agents SDK                   | 问答 + Tool Calling  |
| Hotel Knowledge Agent      | OpenAI Agents SDK                   | RAG + Tool Calling |
| Marketing Content Agent    | **OpenAI Agents SDK（当前）**           | 文案生成流程简单，不需要规划     |
| OTA Operations Agent       | OpenAI Agents SDK → Deep Agents（后续） | 初期查数据即可，复杂运营流程再升级  |
| Revenue Intelligence Agent | **Deep Agents**                     | 天然属于多步骤分析和规划任务     |


## 使用方式

```bash
# 交互模式（多轮对话）
python -m launcher.main --agent guest_experience_agent --interactive

# 一次性模式
python -m launcher.main --agent guest_experience_agent --input "hello"

# 列出 agent
python -m launcher.main --list
```