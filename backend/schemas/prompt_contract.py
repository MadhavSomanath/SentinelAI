"""Request schemas for gateway traffic."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ProviderName(str, Enum):
    """Supported provider identifiers."""

    MOCK = "mock"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"


class PromptContract(BaseModel):
    """Input contract for all gateway requests."""

    session_id: str = Field(min_length=1, max_length=128)
    prompt: str = Field(min_length=1, max_length=8000)
    provider: ProviderName
    model: str = Field(min_length=1, max_length=256)
    max_tokens: int = Field(ge=1, le=4096)
    feature_tag: str = Field(min_length=1, max_length=128)
    prompt_version: str = Field(min_length=1, max_length=64)
    metadata: dict[str, Any] | None = None
