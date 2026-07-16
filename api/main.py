"""FastAPI application entry point."""

from fastapi import FastAPI

from api.routes import router

app = FastAPI(title="Hotel AI Agents API")

app.include_router(router)