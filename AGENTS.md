# AGENTS.md — Hotel AI Agents

Agentic coding guidelines for the hotel-ai-agents repository.

## Project Overview

A Python 3.10+ hotel AI agents project using the OpenAI Agents SDK and LangGraph for workflow orchestration. Organized into four top-level packages: `capabilities/` (domain agents), `shared/` (infrastructure), `api/` (FastAPI HTTP layer), and `launcher/` (CLI entry point).

## Build / Install

```bash
# Install in development mode (with test dependencies)
pip install -e ".[test]"

# Install without test deps
pip install -e .
```

No Makefile exists. All operations use Python module invocation.

## Running the Application

```bash
# Interactive chat mode
python -m launcher.main --agent review_analysis_agent --interactive

# One-shot mode
python -m launcher.main --agent review_analysis_agent --input "hello"

# List agents / workflows
python -m launcher.main --list
python -m launcher.main --list-workflows

# Run a workflow
python -m launcher.main --workflow review_operation --input "房间卫生很差"
```

**Always use `python -m launcher.main`** (not `python launcher/main.py`) because the project is package-structured and Python needs the root directory in `sys.path`.

## Testing

Framework: **pytest** with **pytest-asyncio**.

### Test Structure

```
tests/
├── conftest.py                 # --run-llm flag, needs_llm marker skip logic
├── boundary/                   # E2E boundary tests (needs_llm)
├── evals/                      # Quality evaluation tests (needs_llm)
└── unit/                       # Unit tests (no LLM required)
```

### Running Tests

```bash
# Run all unit tests (no LLM required)
python -m pytest tests/unit/ -v

# Run a single test file
python -m pytest tests/unit/test_registry.py -v

# Run a single test class
python -m pytest tests/unit/test_schema.py::TestIssueSeverity -v

# Run a single test function
python -m pytest tests/unit/test_registry.py::test_list_agents -v

# Run all tests including LLM tests
python -m pytest --run-llm -v

# Run only boundary tests (requires LLM)
python -m pytest tests/boundary/ --run-llm -v

# Run only eval tests (requires LLM)
python -m pytest tests/evals/ --run-llm -v
```

### LLM Test Marker

Tests that require LLM API calls are marked with `@pytest.mark.needs_llm`. By default (without `--run-llm`), these tests are automatically skipped.

## Code Style

### Imports

- Use **absolute imports** for cross-package references (e.g., `from shared.registry.agent_registry import register_agent`)
- Use **relative imports** within the same package (e.g., `from .schemas import ReviewAnalysisResult`)
- Import order: standard library → third-party → local
- Use `# noqa: F401` for side-effect imports (e.g., `import capabilities  # noqa: F401`)

### Formatting

- 4-space indentation
- Double quotes for strings
- No explicit line length limit configured (no formatter)
- No linter is configured (no ruff, flake8, pylint, black)

### Types

- **Pydantic v2** models (`BaseModel`) for all schemas
- Modern union syntax: `X | None` (not `Optional[X]`)
- Lowercase generics: `dict`, `list`, `str`
- `TypedDict` for workflow state (e.g., `ReviewReplyState`)
- `Protocol` for interfaces (e.g., `RuntimeAdapter`, `SessionStore`)
- `dataclass` for metadata containers (e.g., `AgentMetadata`)
- `Enum` / `Literal` for enumerations (e.g., `IssueSeverity.level: Literal["Low", "Medium", "High"]`)
- Use `from __future__ import annotations` in registry modules

### Naming Conventions

- **snake_case** for functions, variables, modules
- **PascalCase** for classes
- **UPPER_CASE** for module-level constants (e.g., `DB_PATH`, `LLM_PROVIDER`)
- Agent names use `snake_case` with `_agent` suffix (e.g., `review_analysis_agent`)
- Workflow names use `snake_case` (e.g., `review_operation`)
- Config files: `config.yaml`, `prompt.md`

### Docstrings

- Every Python module must have a module-level docstring
- Public functions and classes must have docstrings
- Docstrings are in **Chinese** (matching the project's language)
- Use Google-style format with `Args:` and `Returns:` sections

### Patterns

- **Factory pattern**: Each agent has a `create_agent()` function returning a configured `Agent`
- **Auto-registration**: Agents register themselves on module import via `register_agent()`
- **Singleton pattern**: Used for `KnowledgeClient` (`get_knowledge_client()`) and runtime instances
- **Adapter pattern**: `RuntimeAdapter` protocol with `OpenAIAdapter` implementation
- **Registry pattern**: Central registries in `shared/registry/`
- **Lazy imports**: Heavy imports inside functions to control side effects (e.g., `import capabilities` in `launcher/main.py`)
- **Config loading**: Each agent loads `config.yaml` via `Path(__file__).resolve().parent`

### Error Handling

- Raise `ValueError` for registration conflicts (e.g., duplicate agent name)
- Raise `KeyError` with helpful message for missing agent/workflow lookups
- Use `parser.error()` for CLI argument validation errors
- No broad `except` clauses — let exceptions propagate naturally

## Architecture Notes

### Agent Registration Flow

1. `capabilities/__init__.py` imports all agent modules
2. Each agent module calls `register_agent()` at module level
3. `launcher/main.py` triggers registration via `import capabilities  # noqa: F401`
4. `shared/registry/agent_registry.py` maintains `_REGISTRY` dict

### Runtime Flow

1. CLI/API calls `run_agent()` or `AgentRuntime.run()`
2. `get_agent()` fetches the factory from the registry and creates a fresh `Agent`
3. `OpenAIAdapter` wraps `Runner.run()` / `Runner.run_streamed()` from the OpenAI Agents SDK
4. Session management via `ConversationManager` when `session_id` is provided

### Workflow Flow (LangGraph)

1. Workflows defined as `StateGraph` in `capabilities/guest_experience/workflows/`
2. Registered via `register_workflow()` in `registry.py`
3. `WorkflowRuntime` manages LangGraph checkpointer lifecycle (SQLite)
4. `launcher/workflow.py` runs workflows via CLI

### Workflow Event Streaming (v3)

工作流事件流通过 SSE 推送给 Chrome Extension：

```
Agent (get_stream_writer)
          │
          │ custom event: {event: "analysis_started", message: "正在分析..."}
          ▼
LangGraph astream_events(version="v3")
          │
          │ ProtocolEvent: {method: "custom", seq: 1, params.data: {...}}
          ▼
ProjectionMapper.transform()
          │
          ├─ values   → StateUpdatedEvent (category="state")
          ├─ messages → TokenDeltaEvent (category="message")
          └─ custom   → BusinessEvent 映射 ⭐
               │
               ├─ analysis_started    → NodeStartedEvent
               ├─ generation_completed → NodeCompletedEvent
               ├─ *_failed           → NodeFailedEvent
               └─ 其他               → CustomEvent 透传
          │
          ▼
       WorkflowEvent
          │ {category, kind, sequence, payload}
          ▼
         SSE → Chrome Extension
```

**关键组件：**
- `shared/workflow_events/kinds.py` — `BusinessEvent` 枚举定义业务事件类型
- `shared/workflow_events/models.py` — `WorkflowCategory` 枚举和事件模型
- `shared/workflow_events/mapper.py` — `ProjectionMapper` 事件转换器
- `shared/streaming/runner.py` — `WorkflowRunner` 工作流执行器
- `api/sse.py` — SSE 端点 `/review/stream`

**Agent 内发送业务事件：**
```python
from langgraph.config import get_stream_writer

def analysis_agent(state):
    writer = get_stream_writer()

    writer({"event": "analysis_started", "message": "正在分析客户评论"})

    try:
        result = analyze(state)
        writer({"event": "analysis_completed", "result": result})
    except Exception as e:
        writer({"event": "analysis_failed", "error": str(e)})
        raise
```

## Environment

- `.env` file at project root (gitignored)
- `config/settings.py` is the single entry point for `load_dotenv()`
- Key env vars: `LLM_PROVIDER`, `OPENAI_API_KEY`, `OPENAI_MODEL`, `LANGFUSE_*`

## Cursor / Copilot Rules

No `.cursor/rules/`, `.cursorrules`, or `.github/copilot-instructions.md` files exist in this repository.
