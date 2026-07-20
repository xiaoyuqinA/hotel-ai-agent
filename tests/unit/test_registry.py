from shared.registry.agent_registry import get_agent, list_agents


def test_list_agents():
    agents = list_agents()
    assert "review_analysis_agent" in agents


def test_get_agent():
    agent = get_agent("review_analysis_agent")
    assert agent is not None
    assert hasattr(agent, "name")