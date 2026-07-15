hotel-ai-agents
│
├── shared                          # 公共基础能力
│
│   ├── knowledge                   # Knowledge Client 查询知识
│   │   └── client.py
│   │
│   ├── tools                       # 通用工具
│   │   ├── registry.py
│   │   └── common_tools.py
│   │
│   ├── prompts                     # Prompt加载 
│   │   ├── loader.py
│   │   └── manager.py
│   │
│   ├── memory                      # Memory管理
│   │   └── client.py
│   │
│   ├── llm                         # LLM配置，LLM调用
│   │   └── config.py
│   │
│   └── config                      # 系统配置
│       └── settings.py
│
│
├── agents                          # 业务 Agent
│
│   ├── guest_experience_agent
│   │
│   │   ├── main.py                 # 启动入口
│   │   ├── agent.py                # OpenAI Agent定义
│   │   ├── tools.py                # Agent专属Tool
│   │   ├── prompt.py               # System Prompt
│   │   └── config.yaml
│   │
│   │
│   ├── hotel_knowledge_agent
│   │
│   │   ├── main.py
│   │   ├── agent.py
│   │   ├── tools.py
│   │   ├── prompt.py
│   │   └── config.yaml
│   │
│   │
│   ├── revenue_intelligence_agent
│   │
│   │   ├── main.py
│   │   ├── agent.py
│   │   ├── tools.py
│   │   └── config.yaml
│   │
│   │
│   ├── ota_operations_agent
│   │
│   └── marketing_content_agent
│
│
├── api                             # 服务入口
│
│   ├── main.py
│   ├── routes.py
│   └── schemas.py
│
│
├── tests
│
├── requirements.txt
│
└── README.md