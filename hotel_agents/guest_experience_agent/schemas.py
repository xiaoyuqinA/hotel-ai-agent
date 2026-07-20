from pydantic import BaseModel
from typing import Literal


class IssueSeverity(BaseModel):
    level: Literal["Low", "Medium", "High"]
    reason: str


class CustomerSentiment(BaseModel):
    label: Literal["positive", "neutral", "negative"]
    confidence: float


class ReviewAnalysisResult(BaseModel):
    original_comment: str
    issue_severity: IssueSeverity
    customer_sentiment: CustomerSentiment
    customer_intent: Literal["praise", "complaint", "suggestion", "inquiry", "request", "mixed"]