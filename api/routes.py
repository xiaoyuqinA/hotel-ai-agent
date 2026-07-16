"""API routes for interacting with hotel agents."""

import asyncio

from fastapi import APIRouter, HTTPException
from agents import Runner

from shared.registry.agent_registry import get_agent, list_agents, is_registered
from api.schemas import ChatRequest, ChatResponse

router = APIRouter()


@router.post("/chat/{agent_name}", response_model=ChatResponse)
async def chat(agent_name: str, req: ChatRequest) -> ChatResponse:
    if not is_registered(agent_name):
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{agent_name}' not registered. "
            f"Available: {list_agents()}",
        )
    agent = get_agent(agent_name)
    result = await Runner.run(agent, req.input)
    return ChatResponse(agent_name=agent_name, output=result.final_output)