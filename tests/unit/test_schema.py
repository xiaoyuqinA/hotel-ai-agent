import pytest
from capabilities.guest_experience.agents.review_analysis_agent.schemas import (
    ReviewAnalysisResult,
    IssueSeverity,
    CustomerSentiment,
)


class TestIssueSeverity:
    def test_valid_levels(self):
        for level in ["Low", "Medium", "High"]:
            s = IssueSeverity(level=level, reason="test")
            assert s.level == level

    def test_invalid_level(self):
        with pytest.raises(Exception):
            IssueSeverity(level="Critical", reason="test")


class TestCustomerSentiment:
    def test_valid_labels(self):
        for label in ["positive", "neutral", "negative"]:
            s = CustomerSentiment(label=label, confidence=0.9)
            assert s.label == label


class TestReviewAnalysisResult:
    def test_full_model(self):
        result = ReviewAnalysisResult(
            original_comment="test",
            issue_severity=IssueSeverity(level="Low", reason="test"),
            customer_sentiment=CustomerSentiment(label="positive", confidence=0.9),
            customer_intent="praise",
        )
        assert result.customer_intent == "praise"

    def test_valid_intents(self):
        for intent in ["praise", "complaint", "suggestion", "inquiry", "request", "mixed"]:
            result = ReviewAnalysisResult(
                original_comment="test",
                issue_severity=IssueSeverity(level="Low", reason="r"),
                customer_sentiment=CustomerSentiment(label="positive", confidence=1.0),
                customer_intent=intent,
            )
            assert result.customer_intent == intent

    def test_model_dump_json(self):
        result = ReviewAnalysisResult(
            original_comment="test",
            issue_severity=IssueSeverity(level="Low", reason="r"),
            customer_sentiment=CustomerSentiment(label="positive", confidence=0.9),
            customer_intent="praise",
        )
        json_str = result.model_dump_json()
        assert "original_comment" in json_str