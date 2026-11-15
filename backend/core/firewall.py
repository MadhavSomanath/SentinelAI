"""Semantic firewall service."""

from dataclasses import dataclass

from backend.db.repository import BaseRepository


@dataclass
class FirewallDecision:
    """Result of a firewall evaluation."""

    blocked: bool
    similarity_score: float
    threshold: float
    policy_id: str | None = None
    category: str | None = None
    message: str = "Prompt passed firewall checks."


class FirewallService:
    """Screen prompts against blocked intents."""

    def __init__(self, repository: BaseRepository, embedding_service, classifier=None) -> None:
        """Store repository, embedder and optional layer-1 classifier."""
        self.repository = repository
        self.embedding_service = embedding_service
        self.classifier = classifier

    async def evaluate_prompt(self, prompt: str) -> FirewallDecision:
        """Layer 1: injection classifier. Layer 2: similarity to blocked-intent policies."""
        if self.classifier is not None:
            score = await self.classifier.score(prompt)
            if score >= self.classifier.threshold:
                return FirewallDecision(
                    blocked=True,
                    similarity_score=round(score, 4),
                    threshold=self.classifier.threshold,
                    policy_id="classifier_injection",
                    category="prompt_injection",
                    message="Prompt flagged by the injection classifier.",
                )

        threshold = await self.repository.get_threshold()
        embedding = await self.embedding_service.embed_text(prompt)
        match = await self.repository.find_policy_match(embedding, threshold)

        if match is None:
            return FirewallDecision(
                blocked=False,
                similarity_score=0.0,
                threshold=threshold,
            )

        return FirewallDecision(
            blocked=True,
            similarity_score=round(match.similarity_score, 4),
            threshold=threshold,
            policy_id=match.policy_id,
            category=match.category,
            message=f"Prompt matched blocked policy {match.policy_id}.",
        )
