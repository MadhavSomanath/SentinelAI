"""Layer 1: prompt-injection classifier."""

from __future__ import annotations

from starlette.concurrency import run_in_threadpool


class InjectionClassifier:
    """Score prompts with an open injection/jailbreak classifier, loaded lazily."""

    def __init__(self, model_name: str, threshold: float) -> None:
        """Store model settings."""
        self.model_name = model_name
        self.threshold = threshold
        self._pipeline = None

    def _score_sync(self, text: str) -> float:
        """Return the probability that the text is an injection attempt."""
        if self._pipeline is None:
            from transformers import pipeline

            self._pipeline = pipeline(
                "text-classification", model=self.model_name, truncation=True, max_length=512
            )
        result = self._pipeline(text)[0]
        return result["score"] if result["label"] == "INJECTION" else 1 - result["score"]

    async def score(self, text: str) -> float:
        """Score text off the event loop."""
        return await run_in_threadpool(self._score_sync, text)
