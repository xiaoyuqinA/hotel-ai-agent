"""API routes for interacting with hotel agents."""

from fastapi import APIRouter, HTTPException

from api.schemas import ChatRequest, ChatResponse
from shared.registry.agent_registry import list_agents, is_registered
from shared.runtime.runtime import run_agent

router = APIRouter()


@router.post("/chat/{agent_name}", response_model=ChatResponse)
async def chat(agent_name: str, req: ChatRequest) -> ChatResponse:
    if not is_registered(agent_name):
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{agent_name}' not registered. "
            f"Available: {list_agents()}",
        )
    output = await run_agent(agent_name, req.input)
    return ChatResponse(agent_name=agent_name, output=output)