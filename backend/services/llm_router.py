"""Provider routing service."""

from __future__ import annotations

from dataclasses import dataclass

from backend.core.config import Settings
from backend.schemas.prompt_contract import PromptContract


@dataclass
class GenerationResult:
    """Normalized provider result."""

    output: str
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_cost_usd: float


class ProviderError(RuntimeError):
    """Raised when the downstream provider call fails."""


class LLMRouter:
    """Minimal router that supports mock mode and one real provider path."""

    def __init__(self, settings: Settings) -> None:
        """Store settings for routing decisions."""
        self.settings = settings

    async def generate(
        self, contract: PromptContract, *, force_mock: bool = False
    ) -> GenerationResult:
        """Route the request to the selected provider."""
        if force_mock or self.settings.default_provider == "mock" or contract.provider.value == "mock":
            return self._mock_response(contract)

        return await self._real_response(contract)

    def _mock_response(self, contract: PromptContract) -> GenerationResult:
        """Return a deterministic mock completion."""
        preview = contract.prompt.strip().replace("\n", " ")
        output = (
            "Mock response from SentinelAI. The request passed validation and the "
            f"semantic firewall. Prompt preview: {preview[:180]}"
        )
        estimated_prompt_tokens = max(1, min(512, len(contract.prompt.split()) * 2))
        estimated_completion_tokens = max(12, min(contract.max_tokens, len(output.split()) * 2))
        return GenerationResult(
            output=output,
            provider="mock",
            model="sentinel-mock-v1",
            prompt_tokens=estimated_prompt_tokens,
            completion_tokens=estimated_completion_tokens,
            total_cost_usd=0.0,
        )

    async def _real_response(self, contract: PromptContract) -> GenerationResult:
        """Call LiteLLM for a real provider completion."""
        try:
            from litellm import acompletion
        except Exception as exc:  # pragma: no cover - defensive runtime branch
            raise ProviderError("LiteLLM is unavailable in the current environment.") from exc

        try:
            response = await acompletion(
                model=contract.model,
                messages=[{"role": "user", "content": contract.prompt}],
                max_tokens=contract.max_tokens,
            )
        except Exception as exc:
            raise ProviderError(str(exc)) from exc

        message = response.choices[0].message.content or ""
        usage = getattr(response, "usage", None)
        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)

        return GenerationResult(
            output=message,
            provider=contract.provider.value,
            model=contract.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_cost_usd=0.0,
        )
