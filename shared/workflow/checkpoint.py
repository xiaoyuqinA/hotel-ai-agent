"""Shared workflow checkpoint storage."""

from pathlib import Path

DB_PATH = (
    Path(__file__).resolve().parents[2]
    / "storage"
    / "langgraph_checkpoints.db"
)

DB_PATH.parent.mkdir(
    parents=True,
    exist_ok=True,
)