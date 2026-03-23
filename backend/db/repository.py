"""Repository implementations for SentinelAI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import sqrt
from typing import Any

from starlette.concurrency import run_in_threadpool
from supabase import Client, create_client

from backend.core.config import Settings


def cosine_similarity(left: list[float], right: list[float]) -> float:
    """Compute cosine similarity for two vectors."""
    if not left or not right or len(left) != len(right):
        return 0.0

    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = sqrt(sum(a * a for a in left))
    right_norm = sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


@dataclass
class MatchResult:
    """Policy match data returned by the firewall query."""

    policy_id: str
    intent_text: str
    category: str
    similarity_score: float


class BaseRepository:
    """Repository interface."""

    async def get_threshold(self) -> float:
        """Return the active firewall threshold."""
        raise NotImplementedError

    async def update_threshold(self, threshold: float) -> float:
        """Persist a new firewall threshold."""
        raise NotImplementedError

    async def list_policies(self) -> list[dict[str, Any]]:
        """Return all stored policies."""
        raise NotImplementedError

    async def create_policy(
        self,
        *,
        policy_id: str,
        intent_text: str,
        category: str,
        is_active: bool,
        embedding: list[float],
    ) -> dict[str, Any]:
        """Create a policy record."""
        raise NotImplementedError

    async def update_policy(
        self,
        *,
        policy_id: str,
        intent_text: str | None,
        category: str | None,
        is_active: bool | None,
        embedding: list[float] | None,
    ) -> dict[str, Any]:
        """Update a policy record."""
        raise NotImplementedError

    async def delete_policy(self, policy_id: str) -> None:
        """Delete a policy."""
        raise NotImplementedError

    async def find_policy_match(self, embedding: list[float], threshold: float) -> MatchResult | None:
        """Find the closest policy match above the requested threshold."""
        raise NotImplementedError

    async def insert_audit_log(self, record: dict[str, Any]) -> None:
        """Insert an audit log row."""
        raise NotImplementedError

    async def insert_request_log(self, record: dict[str, Any]) -> None:
        """Insert a request log row."""
        raise NotImplementedError

    async def list_request_logs(
        self,
        *,
        provider: str | None = None,
        blocked: bool | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """List request log rows for the dashboard."""
        raise NotImplementedError

    async def get_overview_metrics(self, ignore_first_n: int = 0) -> dict[str, float | int]:
        """Return aggregated overview metrics."""
        raise NotImplementedError


class SupabaseRepository(BaseRepository):
    """Supabase-backed repository."""

    def __init__(self, settings: Settings) -> None:
        """Initialize the Supabase client."""
        self.settings = settings
        self.client: Client = create_client(
            settings.supabase_url,
            settings.supabase_service_key.get_secret_value(),
        )

    async def get_threshold(self) -> float:
        """Return the active firewall threshold."""
        return await run_in_threadpool(self._get_threshold_sync)

    def _get_threshold_sync(self) -> float:
        """Read the threshold from the singleton settings row."""
        result = (
            self.client.table("app_settings")
            .select("firewall_threshold")
            .eq("id", 1)
            .limit(1)
            .execute()
        )
        if not result.data:
            return self.settings.firewall_threshold
        return float(result.data[0]["firewall_threshold"])

    async def update_threshold(self, threshold: float) -> float:
        """Persist a new threshold."""
        return await run_in_threadpool(self._update_threshold_sync, threshold)

    def _update_threshold_sync(self, threshold: float) -> float:
        """Persist the threshold via upsert."""
        self.client.table("app_settings").upsert(
            {"id": 1, "firewall_threshold": threshold}
        ).execute()
        return threshold

    async def list_policies(self) -> list[dict[str, Any]]:
        """Return stored policies."""
        return await run_in_threadpool(self._list_policies_sync)

    def _list_policies_sync(self) -> list[dict[str, Any]]:
        """Read policies from Supabase."""
        result = (
            self.client.table("blocked_intents")
            .select("policy_id,intent_text,category,is_active,created_at")
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []

    async def create_policy(
        self,
        *,
        policy_id: str,
        intent_text: str,
        category: str,
        is_active: bool,
        embedding: list[float],
    ) -> dict[str, Any]:
        """Insert a policy."""
        return await run_in_threadpool(
            self._create_policy_sync,
            policy_id,
            intent_text,
            category,
            is_active,
            embedding,
        )

    def _create_policy_sync(
        self,
        policy_id: str,
        intent_text: str,
        category: str,
        is_active: bool,
        embedding: list[float],
    ) -> dict[str, Any]:
        """Insert a policy row into Supabase."""
        result = (
            self.client.table("blocked_intents")
            .insert(
                {
                    "policy_id": policy_id,
                    "intent_text": intent_text,
                    "category": category,
                    "is_active": is_active,
                    "embedding": embedding,
                }
            )
            .execute()
        )
        return result.data[0]

    async def update_policy(
        self,
        *,
        policy_id: str,
        intent_text: str | None,
        category: str | None,
        is_active: bool | None,
        embedding: list[float] | None,
    ) -> dict[str, Any]:
        """Update a policy row."""
        return await run_in_threadpool(
            self._update_policy_sync,
            policy_id,
            intent_text,
            category,
            is_active,
            embedding,
        )

    def _update_policy_sync(
        self,
        policy_id: str,
        intent_text: str | None,
        category: str | None,
        is_active: bool | None,
        embedding: list[float] | None,
    ) -> dict[str, Any]:
        """Update a Supabase policy row."""
        payload: dict[str, Any] = {}
        if intent_text is not None:
            payload["intent_text"] = intent_text
        if category is not None:
            payload["category"] = category
        if is_active is not None:
            payload["is_active"] = is_active
        if embedding is not None:
            payload["embedding"] = embedding

        result = (
            self.client.table("blocked_intents")
            .update(payload)
            .eq("policy_id", policy_id)
            .execute()
        )
        return result.data[0]

    async def delete_policy(self, policy_id: str) -> None:
        """Delete a policy row."""
        await run_in_threadpool(self._delete_policy_sync, policy_id)

    def _delete_policy_sync(self, policy_id: str) -> None:
        """Delete a row in Supabase."""
        self.client.table("blocked_intents").delete().eq("policy_id", policy_id).execute()

    async def find_policy_match(self, embedding: list[float], threshold: float) -> MatchResult | None:
        """Find the nearest blocked intent via pgvector RPC."""
        return await run_in_threadpool(self._find_policy_match_sync, embedding, threshold)

    def _find_policy_match_sync(
        self, embedding: list[float], threshold: float
    ) -> MatchResult | None:
        """Call the `match_blocked_intents` RPC."""
        result = self.client.rpc(
            "match_blocked_intents",
            {
                "query_embedding": embedding,
                "match_threshold": threshold,
                "match_count": 1,
            },
        ).execute()
        if not result.data:
            return None

        row = result.data[0]
        return MatchResult(
            policy_id=row["policy_id"],
            intent_text=row["intent_text"],
            category=row["category"],
            similarity_score=float(row["similarity_score"]),
        )

    async def insert_audit_log(self, record: dict[str, Any]) -> None:
        """Insert an audit log row."""
        await run_in_threadpool(self._insert_audit_log_sync, record)

    def _insert_audit_log_sync(self, record: dict[str, Any]) -> None:
        """Persist an audit row."""
        self.client.table("audit_log").insert(record).execute()

    async def insert_request_log(self, record: dict[str, Any]) -> None:
        """Insert a request log row."""
        await run_in_threadpool(self._insert_request_log_sync, record)

    def _insert_request_log_sync(self, record: dict[str, Any]) -> None:
        """Persist a request log row."""
        self.client.table("request_logs").upsert(record).execute()

    async def list_request_logs(
        self,
        *,
        provider: str | None = None,
        blocked: bool | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Return dashboard trace rows."""
        return await run_in_threadpool(self._list_request_logs_sync, provider, blocked, limit)

    def _list_request_logs_sync(
        self, provider: str | None, blocked: bool | None, limit: int
    ) -> list[dict[str, Any]]:
        """Query request logs from Supabase."""
        query = (
            self.client.table("request_logs")
            .select(
                "trace_id,session_id,user_id,prompt,output,provider,model,feature_tag,"
                "prompt_version,blocked,policy_id,similarity_score,latency_ms,"
                "total_cost_usd,created_at"
            )
            .order("created_at", desc=True)
            .limit(limit)
        )
        if provider:
            query = query.eq("provider", provider)
        if blocked is not None:
            query = query.eq("blocked", blocked)
        result = query.execute()
        return result.data or []

    async def get_overview_metrics(self, ignore_first_n: int = 0) -> dict[str, float | int]:
        """Compute overview metrics from request logs."""
        rows = await self.list_request_logs(limit=500 + ignore_first_n)
        ordered_rows = sorted(rows, key=lambda row: row.get("created_at") or "")
        measured_rows = ordered_rows[ignore_first_n:] if ignore_first_n > 0 else ordered_rows
        total_requests = len(ordered_rows)
        blocked_requests = sum(1 for row in ordered_rows if row["blocked"])
        measured_count = len(measured_rows)
        average_latency_ms = (
            round(sum(float(row["latency_ms"]) for row in measured_rows) / measured_count, 2)
            if measured_count
            else 0.0
        )
        total_estimated_cost_usd = round(
            sum(float(row.get("total_cost_usd") or 0.0) for row in ordered_rows), 6
        )
        return {
            "total_requests": total_requests,
            "blocked_requests": blocked_requests,
            "average_latency_ms": average_latency_ms,
            "total_estimated_cost_usd": total_estimated_cost_usd,
            "latency_sample_size": measured_count,
            "ignored_latency_runs": min(ignore_first_n, total_requests),
        }


class InMemoryRepository(BaseRepository):
    """Test-friendly in-memory repository."""

    def __init__(self, threshold: float = 0.6) -> None:
        """Initialize in-memory stores."""
        self.threshold = threshold
        self.policies: list[dict[str, Any]] = []
        self.audit_log: list[dict[str, Any]] = []
        self.request_logs: list[dict[str, Any]] = []

    async def get_threshold(self) -> float:
        """Return the current threshold."""
        return self.threshold

    async def update_threshold(self, threshold: float) -> float:
        """Persist a new threshold."""
        self.threshold = threshold
        return threshold

    async def list_policies(self) -> list[dict[str, Any]]:
        """Return policies sorted by recency."""
        return list(reversed(self.policies))

    async def create_policy(
        self,
        *,
        policy_id: str,
        intent_text: str,
        category: str,
        is_active: bool,
        embedding: list[float],
    ) -> dict[str, Any]:
        """Create a policy in memory."""
        record = {
            "policy_id": policy_id,
            "intent_text": intent_text,
            "category": category,
            "is_active": is_active,
            "embedding": embedding,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.policies.append(record)
        return record

    async def update_policy(
        self,
        *,
        policy_id: str,
        intent_text: str | None,
        category: str | None,
        is_active: bool | None,
        embedding: list[float] | None,
    ) -> dict[str, Any]:
        """Update an in-memory policy."""
        for record in self.policies:
            if record["policy_id"] == policy_id:
                if intent_text is not None:
                    record["intent_text"] = intent_text
                if category is not None:
                    record["category"] = category
                if is_active is not None:
                    record["is_active"] = is_active
                if embedding is not None:
                    record["embedding"] = embedding
                return record
        raise KeyError(f"Policy not found: {policy_id}")

    async def delete_policy(self, policy_id: str) -> None:
        """Delete a policy from memory."""
        self.policies = [record for record in self.policies if record["policy_id"] != policy_id]

    async def find_policy_match(self, embedding: list[float], threshold: float) -> MatchResult | None:
        """Return the closest active in-memory policy match above threshold."""
        best_match: MatchResult | None = None
        for record in self.policies:
            if not record["is_active"]:
                continue
            score = cosine_similarity(record["embedding"], embedding)
            if score < threshold:
                continue
            if best_match is None or score > best_match.similarity_score:
                best_match = MatchResult(
                    policy_id=record["policy_id"],
                    intent_text=record["intent_text"],
                    category=record["category"],
                    similarity_score=score,
                )
        return best_match

    async def insert_audit_log(self, record: dict[str, Any]) -> None:
        """Insert an audit row into memory."""
        self.audit_log.append(record)

    async def insert_request_log(self, record: dict[str, Any]) -> None:
        """Insert a request log row into memory."""
        if "created_at" not in record:
            record = {**record, "created_at": datetime.now(timezone.utc).isoformat()}
        self.request_logs = [row for row in self.request_logs if row["trace_id"] != record["trace_id"]]
        self.request_logs.append(record)

    async def list_request_logs(
        self,
        *,
        provider: str | None = None,
        blocked: bool | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Return request logs filtered like the production repository."""
        rows = list(reversed(self.request_logs))
        if provider:
            rows = [row for row in rows if row["provider"] == provider]
        if blocked is not None:
            rows = [row for row in rows if row["blocked"] == blocked]
        return rows[:limit]

    async def get_overview_metrics(self, ignore_first_n: int = 0) -> dict[str, float | int]:
        """Return aggregate metrics."""
        ordered_rows = list(self.request_logs)
        measured_rows = ordered_rows[ignore_first_n:] if ignore_first_n > 0 else ordered_rows
        total_requests = len(ordered_rows)
        blocked_requests = sum(1 for row in ordered_rows if row["blocked"])
        measured_count = len(measured_rows)
        average_latency_ms = (
            round(sum(float(row["latency_ms"]) for row in measured_rows) / measured_count, 2)
            if measured_count
            else 0.0
        )
        total_estimated_cost_usd = round(
            sum(float(row.get("total_cost_usd") or 0.0) for row in ordered_rows), 6
        )
        return {
            "total_requests": total_requests,
            "blocked_requests": blocked_requests,
            "average_latency_ms": average_latency_ms,
            "total_estimated_cost_usd": total_estimated_cost_usd,
            "latency_sample_size": measured_count,
            "ignored_latency_runs": min(ignore_first_n, total_requests),
        }
