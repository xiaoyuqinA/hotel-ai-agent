from pydantic import BaseModel
from typing import Literal

class DecisionResult(BaseModel):
    action: Literal["auto_reply", "human_review"]
    reason: str