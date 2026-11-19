"""Gateway routes."""

from __future__ import annotations

import hashlib
from time import perf_counter
from uuid import uuid4

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from backend.core.auth import require_user
from backend.core.firewall import FirewallService
from backend.core.dependencies import (
    get_firewall_service,
    get_llm_router,
    get_repository,
    get_trace_service,
)
from backend.db.repository import BaseRepository
from backend.schemas.prompt_contract import PromptContract
from backend.schemas.responses import GatewayResponse, HealthResponse, PolicyViolationResponse
from backend.services.llm_router import LLMRouter, ProviderError

router = APIRouter(tags=["gateway"])


def prompt_hash(prompt: str) -> str:
    """Return a stable hash for audit logging."""
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


async def process_gateway_request(
    contract: PromptContract,
    *,
    user_id: str,
    force_mock: bool,
    firewall_service: FirewallService,
    repository: BaseRepository,
    trace_service,
    llm_router: LLMRouter,
) -> JSONResponse | GatewayResponse:
    """Handle the shared request flow for chat and mock routes."""
    started_at = perf_counter()
    trace_id = str(uuid4())

    try:
        decision = await firewall_service.evaluate_prompt(contract.prompt)
    except Exception:
        latency_ms = round((perf_counter() - started_at) * 1000, 2)
        return JSONResponse(
            status_code=503,
            content={
                "code": "FIREWALL_UNAVAILABLE",
                "message": "Semantic firewall is unavailable.",
                "errors": [{"type": "runtime_error", "field": "firewall"}],
            },
        )

    if decision.blocked:
        latency_ms = round((perf_counter() - started_at) * 1000, 2)
        await repository.insert_audit_log(
            {
                "trace_id": trace_id,
                "session_id": contract.session_id,
                "user_id": user_id,
                "policy_id": decision.policy_id,
                "similarity_score": decision.similarity_score,
                "prompt_hash": prompt_hash(contract.prompt),
                "blocked": True,
            }
        )
        request_record = {
            "trace_id": trace_id,
            "session_id": contract.session_id,
            "user_id": user_id,
            "prompt": f"[blocked] sha256:{prompt_hash(contract.prompt)}",
            "output": None,
            "provider": "mock" if force_mock else contract.provider.value,
            "model": contract.model,
            "feature_tag": contract.feature_tag,
            "prompt_version": contract.prompt_version,
            "blocked": True,
            "policy_id": decision.policy_id,
            "similarity_score": decision.similarity_score,
            "latency_ms": latency_ms,
            "total_cost_usd": 0.0,
        }
        await repository.insert_request_log(request_record)
        await trace_service.log_gateway_event(
            {
                **request_record,
                "prompt_tokens": 0,
                "completion_tokens": 0,
            }
        )
        response = PolicyViolationResponse(
            code="POLICY_VIOLATION",
            message=decision.message,
            trace_id=trace_id,
            policy_id=decision.policy_id,
            similarity_score=decision.similarity_score,
            latency_ms=latency_ms,
        )
        return JSONResponse(status_code=403, content=response.model_dump())

    try:
        generation = await llm_router.generate(contract, force_mock=force_mock)
    except ProviderError as exc:
        return JSONResponse(
            status_code=502,
            content={
                "code": "PROVIDER_ERROR",
                "message": str(exc),
                "errors": [{"type": "provider_error", "field": contract.provider.value}],
            },
        )

    latency_ms = round((perf_counter() - started_at) * 1000, 2)
    request_record = {
        "trace_id": trace_id,
        "session_id": contract.session_id,
        "user_id": user_id,
        "prompt": contract.prompt,
        "output": generation.output,
        "provider": generation.provider,
        "model": generation.model,
        "feature_tag": contract.feature_tag,
        "prompt_version": contract.prompt_version,
        "blocked": False,
        "policy_id": None,
        "similarity_score": None,
        "latency_ms": latency_ms,
        "total_cost_usd": generation.total_cost_usd,
    }
    await repository.insert_request_log(request_record)
    await trace_service.log_gateway_event(
        {
            **request_record,
            "prompt_tokens": generation.prompt_tokens,
            "completion_tokens": generation.completion_tokens,
        }
    )

    return GatewayResponse(
        trace_id=trace_id,
        output=generation.output,
        provider=generation.provider,
        model=generation.model,
        latency_ms=latency_ms,
        similarity_score=decision.similarity_score if decision.similarity_score else None,
    )


@router.get("/health", response_model=HealthResponse)
async def health(llm_router: LLMRouter = Depends(get_llm_router)) -> HealthResponse:
    """Return a simple health payload."""
    return HealthResponse(status="ok", default_provider=llm_router.settings.default_provider)


@router.post(
    "/api/v1/gateway/chat",
    response_model=GatewayResponse,
    responses={403: {"model": PolicyViolationResponse}},
)
async def gateway_chat(
    contract: PromptContract,
    user_id: str = Depends(require_user),
    firewall_service: FirewallService = Depends(get_firewall_service),
    repository: BaseRepository = Depends(get_repository),
    trace_service=Depends(get_trace_service),
    llm_router: LLMRouter = Depends(get_llm_router),
) -> JSONResponse | GatewayResponse:
    """Validate, screen, and route a regular gateway request."""
    return await process_gateway_request(
        contract,
        user_id=user_id,
        force_mock=False,
        firewall_service=firewall_service,
        repository=repository,
        trace_service=trace_service,
        llm_router=llm_router,
    )


@router.post(
    "/api/v1/gateway/mock",
    response_model=GatewayResponse,
    responses={403: {"model": PolicyViolationResponse}},
)
async def gateway_mock(
    contract: PromptContract,
    user_id: str = Depends(require_user),
    firewall_service: FirewallService = Depends(get_firewall_service),
    repository: BaseRepository = Depends(get_repository),
    trace_service=Depends(get_trace_service),
    llm_router: LLMRouter = Depends(get_llm_router),
) -> JSONResponse | GatewayResponse:
    """Force the request through mock mode."""
    return await process_gateway_request(
        contract,
        user_id=user_id,
        force_mock=True,
        firewall_service=firewall_service,
        repository=repository,
        trace_service=trace_service,
        llm_router=llm_router,
    )
