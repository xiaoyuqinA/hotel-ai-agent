import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from agents import Agent, Runner

from shared.llm.factory import create_agent_model

# Load environment variables from .env file
load_dotenv(Path(__file__).resolve().parent / ".env")

model = create_agent_model()

agent = Agent(
    name=os.environ["AGENT_NAME"],
    instructions="You are a hotel guest experience assistant. Help guests with inquiries about rooms, amenities, bookings, and hotel services.",
    model=model,
)


async def main() -> None:
    result = await Runner.run(agent, "酒店今天的价格是多少?")
    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())