import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--run-llm",
        action="store_true",
        default=False,
        help="运行需要 LLM 的测试（boundary + evals）",
    )


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-llm"):
        skip_llm = pytest.mark.skip(reason="需要 --run-llm 参数")
        for item in items:
            if "needs_llm" in item.keywords:
                item.add_marker(skip_llm)