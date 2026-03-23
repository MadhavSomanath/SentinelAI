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

    def __init__(self, repository: BaseRepository, embedding_service) -> None:
        """Store repository and embedder dependencies."""
        self.repository = repository
        self.embedding_service = embedding_service

    async def evaluate_prompt(self, prompt: str) -> FirewallDecision:
        """Evaluate the prompt and return the blocking decision."""
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
