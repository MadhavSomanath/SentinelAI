"""Seed demo firewall policies."""

import asyncio

from backend.core.config import get_settings
from backend.core.demo_data import DEMO_POLICIES, EXTRA_SEED_POLICIES
from backend.core.embeddings import SentenceTransformerEmbeddingService
from backend.db.repository import SupabaseRepository



async def main() -> None:
    """Insert seed policies into Supabase."""
    settings = get_settings()
    repository = SupabaseRepository(settings)
    embedder = SentenceTransformerEmbeddingService(settings.embedding_model_name)

    existing = {record["policy_id"] for record in await repository.list_policies()}
    for policy_id, intent_text, category in [*DEMO_POLICIES, *EXTRA_SEED_POLICIES]:
        if policy_id in existing:
            continue
        embedding = await embedder.embed_text(intent_text)
        await repository.create_policy(
            policy_id=policy_id,
            intent_text=intent_text,
            category=category,
            is_active=True,
            embedding=embedding,
        )
        print(f"Seeded {policy_id}")

    await repository.update_threshold(settings.firewall_threshold)
    print("Seeding complete.")


if __name__ == "__main__":
    asyncio.run(main())
