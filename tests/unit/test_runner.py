import inspect
from shared.runtime.runtime import run_agent, stream_agent


def test_run_agent_is_async():
    assert inspect.iscoroutinefunction(run_agent)


def test_stream_agent_is_async_generator():
    assert inspect.isasyncgenfunction(stream_agent)