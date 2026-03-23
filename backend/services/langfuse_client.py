"""Langfuse tracing wrapper."""

from __future__ import annotations

import logging

from starlette.concurrency import run_in_threadpool

from backend.core.config import Settings

logger = logging.getLogger(__name__)


class LangfuseTraceService:
    """Best-effort Langfuse tracer."""

    def __init__(self, settings: Settings) -> None:
        """Store tracing configuration."""
        self.settings = settings
        self.enabled = bool(
            settings.enable_langfuse
            and settings.langfuse_public_key
            and settings.langfuse_secret_key
        )
        self._client = None

    def _get_client(self):
        """Create the Langfuse client lazily."""
        if not self.enabled:
            return None
        if self._client is None:
            from langfuse import Langfuse

            self._client = Langfuse(
                public_key=self.settings.langfuse_public_key.get_secret_value(),
                secret_key=self.settings.langfuse_secret_key.get_secret_value(),
                host=self.settings.langfuse_host,
            )
        return self._client

    async def log_gateway_event(self, record: dict) -> None:
        """Send a gateway trace to Langfuse without affecting the request."""
        if not self.enabled:
            return
        await run_in_threadpool(self._log_gateway_event_sync, record)

    def _log_gateway_event_sync(self, record: dict) -> None:
        """Write trace data to Langfuse and swallow tracing errors."""
        try:
            client = self._get_client()
            if client is None:
                return

            trace = client.trace(
                id=record["trace_id"],
                name="sentinelai.gateway",
                user_id=record["user_id"],
                session_id=record["session_id"],
                metadata={
                    "provider": record["provider"],
                    "model": record["model"],
                    "feature_tag": record["feature_tag"],
                    "prompt_version": record["prompt_version"],
                    "blocked": record["blocked"],
                    "policy_id": record.get("policy_id"),
                    "similarity_score": record.get("similarity_score"),
                    "latency_ms": record["latency_ms"],
                },
            )

            trace.span(
                name="firewall",
                metadata={
                    "blocked": record["blocked"],
                    "policy_id": record.get("policy_id"),
                    "similarity_score": record.get("similarity_score"),
                },
            )

            trace.generation(
                name="completion",
                model=record["model"],
                input=record["prompt"],
                output=record.get("output"),
                usage={
                    "prompt_tokens": record.get("prompt_tokens", 0),
                    "completion_tokens": record.get("completion_tokens", 0),
                },
                metadata={"total_cost_usd": record.get("total_cost_usd", 0.0)},
            )
            client.flush()
        except Exception as exc:  # pragma: no cover - defensive runtime branch
            logger.warning("Failed to write Langfuse trace: %s", exc)


class NoOpTraceService:
    """Tracer used in tests."""

    async def log_gateway_event(self, record: dict) -> None:
        """Discard the trace event."""
        return None
