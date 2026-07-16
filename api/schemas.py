"""Request / response schemas for the hotel agents API."""

from pydantic import BaseModel


class ChatRequest(BaseModel):
    input: str


class ChatResponse(BaseModel):
    agent_name: str
    output: str