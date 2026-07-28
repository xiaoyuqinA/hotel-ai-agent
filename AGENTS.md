# AGENTS.md — Hotel AI Agents

Agentic coding guidelines for the hotel-ai-agents repository.

## Project Overview

Python 3.10+ hotel AI agents project. Uses **OpenAI Agents SDK** for agent execution and **LangGraph** for workflow orchestration. Four top-level packages: `capabilities/` (domain agents), `shared/` (infrastructure), `api/` (FastAPI HTTP), `launcher/` (CLI).

Key dependencies: `openai-agents`, `langgraph`, `fastapi`, `pydantic v2`, `uvicorn`, `pyyaml`.

## Quick Start

```bash
pip install -e ".[test]"
uvicorn api.main:app --reload
curl -X POST http://localhost:8000/review/run \
  -H "Content-Type: application/json" \
  -d '{"reviews_content": "房间卫生很差", "thread_id": "test-1"}'
```

## Running Agents

```bash
python -m launcher.main --agent review_analysis_agent --interactive
python -m launcher.main --agent review_analysis_agent --input "hello"
python -m launcher.main --list
python -m launcher.main --list-workflows
python -m launcher.main --workflow review_operation --input "房间卫生很差"
```

**Always use `python -m launcher.main`** (not `python launcher/main.py`) — package structure requires root in `sys.path`.

## Testing

Framework: **pytest** with **pytest-asyncio**. Tests marked `@pytest.mark.needs_llm` are auto-skipped without `--run-llm`.

```bash
python -m pytest tests/unit/ -v                                              # unit tests
python -m pytest tests/unit/test_registry.py -v                              # single file
python -m pytest tests/unit/test_schema.py::TestIssueSeverity -v             # single class
python -m pytest tests/unit/test_registry.py::test_list_agents -v            # single function
python -m pytest --run-llm -v                                                # all including LLM
python -m pytest tests/boundary/ --run-llm -v                                # boundary only
python -m pytest tests/evals/ --run-llm -v                                   # evals only
```

## Code Style

### Imports

- **Absolute imports** for cross-package: `from shared.registry.agent_registry import register_agent`
- **Relative imports** within same package: `from .schemas import ReviewAnalysisResult`
- Order: stdlib → third-party → local
- `# noqa: F401` for side-effect imports only

### Formatting

- 4-space indentation, double quotes, no line length limit configured
- No linter/formatter configured (no ruff, flake8, black)

### Types

- **Pydantic v2** (`BaseModel`) for all schemas; use `model_validate_json()`, `model_dump()`
- Modern union: `X | None` (not `Optional[X]`)
- Lowercase generics: `dict`, `list`, `str`
- `TypedDict` for workflow state (`ReviewReplyState`)
- `Protocol` for interfaces (`RuntimeAdapter`, `SessionStore`)
- `dataclass(frozen=True)` for immutable data (`HotelContext`, `AgentMetadata`)
- `Enum` / `Literal` for enumerations

### Naming

- `snake_case` for functions, variables, modules
- `PascalCase` for classes
- `UPPER_CASE` for module constants (`DB_PATH`, `LLM_PROVIDER`)
- Agent names: `snake_case` + `_agent` suffix (e.g., `review_analysis_agent`)
- Workflow names: `snake_case` (e.g., `review_operation`)

### Docstrings

- **Chinese** for all docstrings — mandatory for all modules, classes, and public functions
- Google-style with `Args:` and `Returns:` sections
- Every Python module **must** have a module-level docstring

### Patterns

| Pattern | Usage | Example |
|---------|-------|---------|
| Factory | Agent creation | `create_agent() -> Agent` in each agent module |
| Auto-registration | Module-level `register_agent()` | Agent `__init__.py` imports `agent.py` |
| Singleton | Infrastructure clients | `get_knowledge_client()`, `_runtime()` |
| Adapter | SDK abstraction | `RuntimeAdapter` Protocol → `OpenAIAdapter` |
| Registry | Central lookup | `shared/registry/{agent,workflow}_registry.py` |
| Lazy imports | Heavy deps inside functions | `import capabilities` in `launcher/main.py` |
| Config loading | Per-agent | `Path(__file__).resolve().parent / "config.yaml"` |

### Error Handling

- `ValueError` for registration conflicts (duplicate agent/workflow name)
- `KeyError` with `list_agents()`/`list_workflows()` hint for missing lookups
- `parser.error()` for CLI argument validation
- Workflow nodes: `try/except` → write error event via `get_stream_writer()` → **always `raise`**
- No broad `except` clauses

## Architecture

### Agent Registration

```
capabilities/__init__.py → imports all agent modules
  └─ each agent/agent.py calls register_agent() at module level
launcher/main.py → `import capabilities  # noqa: F401`
  └─ shared/registry/agent_registry.py maintains _REGISTRY dict
```

### Runtime

```
CLI/API → run_agent() / AgentRuntime.run()
  └─ get_agent() creates fresh Agent from registry
     └─ OpenAIAdapter wraps Runner.run() / Runner.run_streamed()
        └─ ConversationManager handles session when session_id provided
```

### Workflow (LangGraph)

```
capabilities/guest_experience/workflows/
  └─ <workflow>_flow.py → StateGraph definition
  └─ registry.py → register_workflow()
  └─ nodes/ → Node functions (analysis, generate_reply, strategy, etc.)
  └─ state.py → ReviewReplyState TypedDict
```

`WorkflowRuntime` manages LangGraph checkpointer (SQLite), `launcher/workflow.py` runs via CLI.

### Event Streaming (LangGraph v3)

Node → `get_stream_writer()` → write dict → `astream_events(version="v3")` → `ProjectionMapper` → `WorkflowEvent` → SSE → Chrome Extension.

Key components:
- `shared/workflow_events/kinds.py` — `BusinessEvent` enum
- `shared/workflow_events/models.py` — `WorkflowEvent` subclasses
- `shared/workflow_events/mapper.py` — `ProjectionMapper` (v3 projections → WorkflowEvent)
- `shared/streaming/runner.py` — `WorkflowRunner`
- `api/sse.py` — SSE endpoint `/review/stream`

Event types: `WORKFLOW_STARTED|COMPLETED|FAILED`, `NODE_STARTED|COMPLETED|FAILED`, `TOKEN_DELTA`, `STATE_UPDATED`, `CUSTOM_EVENT`.

## Environment

- `.env` at project root (gitignored); `config/settings.py` is the single `load_dotenv()` entry
- Key vars: `LLM_PROVIDER`, `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_API_TYPE` (`responses` | `chat_completions`), `LANGFUSE_*`, `POSTGRES_*`, `REDIS_*`

## Dependencies

| Package | Purpose |
|---------|---------|
| `openai-agents` ≥0.18.2 | Agent SDK (Agent, Runner) |
| `langgraph` ≥1.0.0 | Workflow StateGraph + checkpointing |
| `fastapi` ≥0.115.0 | HTTP API |
| `pydantic` ≥2.0 | Schema validation (`BaseModel`, `model_validate_json`) |
| `pyyaml` ≥6.0 | Agent config loading |
| `prompt-toolkit` ≥3.0.0 | Interactive CLI |

Test: `pytest` ≥8.0, `pytest-asyncio` ≥0.24.0.
