"""Policy-related schemas."""

from pydantic import BaseModel, Field


class PolicyCreate(BaseModel):
    """Payload for creating a policy."""

    policy_id: str = Field(min_length=1, max_length=128)
    intent_text: str = Field(min_length=1, max_length=4000)
    category: str = Field(min_length=1, max_length=128)
    is_active: bool = True


class PolicyUpdate(BaseModel):
    """Payload for updating an existing policy."""

    intent_text: str | None = Field(default=None, min_length=1, max_length=4000)
    category: str | None = Field(default=None, min_length=1, max_length=128)
    is_active: bool | None = None


class PolicyRecord(BaseModel):
    """Stored policy representation."""

    policy_id: str
    intent_text: str
    category: str
    is_active: bool
    created_at: str | None = None


class PolicyListResponse(BaseModel):
    """List response for policies."""

    items: list[PolicyRecord]
    threshold: float


class FirewallThresholdResponse(BaseModel):
    """Threshold response payload."""

    firewall_threshold: float


class FirewallThresholdUpdate(BaseModel):
    """Payload for updating the firewall threshold."""

    firewall_threshold: float = Field(ge=0.5, le=1.0)


class FirewallSimulationRequest(BaseModel):
    """Prompt simulation payload."""

    prompt: str = Field(min_length=1, max_length=4000)


class FirewallSimulationResponse(BaseModel):
    """Simulation result payload."""

    blocked: bool
    similarity_score: float
    threshold: float
    policy_id: str | None = None
    category: str | None = None
