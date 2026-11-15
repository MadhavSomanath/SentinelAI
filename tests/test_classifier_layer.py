"""Layer-1 classifier runs before the embedding policy check."""

import asyncio

from backend.core.embeddings import SimpleEmbeddingService
from backend.core.firewall import FirewallService
from backend.db.repository import InMemoryRepository


class FakeClassifier:
    threshold = 0.5

    def __init__(self, score: float) -> None:
        self._score = score

    async def score(self, text: str) -> float:
        return self._score


def evaluate(score: float, prompt: str = "Summarize this report."):
    service = FirewallService(InMemoryRepository(threshold=0.6), SimpleEmbeddingService(), FakeClassifier(score))
    return asyncio.run(service.evaluate_prompt(prompt))


def test_classifier_blocks_above_threshold() -> None:
    decision = evaluate(0.97)
    assert decision.blocked
    assert decision.policy_id == "classifier_injection"
    assert decision.similarity_score == 0.97


def test_classifier_below_threshold_falls_through_to_policies() -> None:
    decision = evaluate(0.1)
    assert not decision.blocked  # no policies seeded, so layer 2 passes it too
