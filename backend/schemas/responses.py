"""Response schemas."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    default_provider: str


class GatewayResponse(BaseModel):
    """Successful gateway response."""

    trace_id: str
    output: str
    provider: str
    model: str
    latency_ms: float
    blocked: bool = False
    similarity_score: float | None = None


class PolicyViolationResponse(BaseModel):
    """Blocked request response."""

    code: str
    message: str
    trace_id: str
    policy_id: str | None = None
    similarity_score: float
    latency_ms: float


class ErrorResponse(BaseModel):
    """Structured error response."""

    code: str
    message: str
    errors: list[dict[str, str]] | None = None


class TraceRecord(BaseModel):
    """Dashboard trace record."""

    trace_id: str
    session_id: str
    user_id: str
    prompt: str
    output: str | None = None
    provider: str
    model: str
    feature_tag: str
    prompt_version: str
    blocked: bool
    policy_id: str | None = None
    similarity_score: float | None = None
    latency_ms: float
    total_cost_usd: float
    created_at: str | None = None


class TraceListResponse(BaseModel):
    """List response for traces."""

    items: list[TraceRecord]
    total: int


class OverviewMetricsResponse(BaseModel):
    """Home page metrics payload."""

    total_requests: int
    blocked_requests: int
    average_latency_ms: float
    total_estimated_cost_usd: float
    latency_sample_size: int
    ignored_latency_runs: int
