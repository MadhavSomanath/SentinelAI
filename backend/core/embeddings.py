"""Embedding services."""

from __future__ import annotations

from collections import Counter
import hashlib
from math import sqrt
import re

from starlette.concurrency import run_in_threadpool


class SentenceTransformerEmbeddingService:
    """Generate embeddings with a lazily loaded sentence-transformers model."""

    def __init__(self, model_name: str) -> None:
        """Store the requested model name."""
        self.model_name = model_name
        self._model = None

    def _get_model(self):
        """Load the model on first use."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def _encode_sync(self, text: str) -> list[float]:
        """Encode text synchronously for threadpool execution."""
        model = self._get_model()
        vector = model.encode(text, normalize_embeddings=True)
        return [float(value) for value in vector.tolist()]

    async def embed_text(self, text: str) -> list[float]:
        """Return an embedding for the provided text."""
        return await run_in_threadpool(self._encode_sync, text)


class SimpleEmbeddingService:
    """A deterministic lightweight embedding service used in tests."""

    PHRASE_MAP = {
        "social security numbers": "ssn",
        "social security number": "ssn",
        "customer records": "customer_record",
        "customer record": "customer_record",
        "system prompt": "system_prompt",
        "hidden prompt": "system_prompt",
        "secret prompt": "system_prompt",
        "hidden instructions": "system_prompt",
        "private customer data": "customer_record",
        "private customer dataset": "customer_record",
        "turn off": "disable",
        "all restrictions": "restrictions",
    }

    TOKEN_MAP = {
        "ignore": "override",
        "bypass": "override",
        "pretend": "override",
        "disable": "override",
        "turn": "override",
        "off": "override",
        "reveal": "disclose",
        "show": "disclose",
        "print": "disclose",
        "leak": "disclose",
        "expose": "disclose",
        "share": "disclose",
        "dump": "disclose",
        "export": "disclose",
        "disclose": "disclose",
        "hidden": "system_prompt",
        "secret": "system_prompt",
        "prompt": "system_prompt",
        "instructions": "system_prompt",
        "message": "system_prompt",
        "ssns": "ssn",
        "records": "customer_record",
        "record": "customer_record",
        "customer": "customer_record",
        "customers": "customer_record",
        "private": "customer_record",
        "personal": "customer_record",
        "forbidden": "restricted",
        "unsafe": "restricted",
        "restrictions": "restricted",
        "restricted": "restricted",
        "safeguards": "restricted",
        "safety": "restricted",
        "guardrail": "restricted",
        "guardrails": "restricted",
    }

    def __init__(self, dimensions: int = 256) -> None:
        """Initialize the simple hashing embedder."""
        self.dimensions = dimensions

    def _token_index(self, token: str) -> int:
        """Map a token to a deterministic bucket index."""
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        return int(digest[:8], 16) % self.dimensions

    def _normalize_text(self, text: str) -> list[str]:
        """Normalize the text into coarse semantic tokens."""
        normalized = text.lower()
        for source, target in self.PHRASE_MAP.items():
            normalized = normalized.replace(source, target)

        tokens = re.findall(r"[a-z_]+", normalized)
        expanded_tokens: list[str] = []
        for token in tokens:
            canonical = self.TOKEN_MAP.get(token, token)
            expanded_tokens.append(canonical)
        return expanded_tokens

    async def embed_text(self, text: str) -> list[float]:
        """Generate a normalized hashed bag-of-words vector."""
        tokens = self._normalize_text(text)
        counts = Counter(tokens)
        vector = [0.0] * self.dimensions
        for token, weight in counts.items():
            vector[self._token_index(token)] += float(weight)

        norm = sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]
