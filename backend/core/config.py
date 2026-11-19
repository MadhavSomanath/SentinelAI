"""Application configuration."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "SentinelAI"
    environment: str = "development"
    log_level: str = "INFO"
    default_provider: str = "mock"
    enable_langfuse: bool = True
    api_base_url: str = "http://localhost:8000"
    streamlit_server_port: int = 8501
    firewall_threshold: float = 0.55  # best recall at <=5% false positives in evals/ run 1
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    injection_classifier_enabled: bool = True
    injection_classifier_model: str = "protectai/deberta-v3-base-prompt-injection-v2"
    injection_classifier_threshold: float = 0.5
    repository_mode: Literal["supabase", "memory"] = "memory"

    supabase_url: str | None = None
    supabase_service_key: SecretStr | None = None
    supabase_db_url: SecretStr | None = None

    langfuse_public_key: SecretStr | None = None
    langfuse_secret_key: SecretStr | None = None
    langfuse_host: str = "https://cloud.langfuse.com"

    openai_api_key: SecretStr | None = None

    # API_KEYS='{"<key>": "<user_id>"}'. The caller's identity comes from its key, never the request body.
    api_keys: dict[str, str] = Field(default_factory=dict, repr=False)
    admin_api_key: SecretStr | None = None

    @model_validator(mode="after")
    def validate_configuration(self) -> "Settings":
        """Validate settings combinations required for the selected mode."""
        if self.repository_mode == "supabase":
            if not self.supabase_url:
                raise ValueError("SUPABASE_URL is required when repository_mode=supabase.")
            if not self.supabase_service_key:
                raise ValueError(
                    "SUPABASE_SERVICE_KEY is required when repository_mode=supabase."
                )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()
