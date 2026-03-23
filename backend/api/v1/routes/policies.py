"""Policy management routes."""

from fastapi import APIRouter, Depends, HTTPException

from backend.core.dependencies import get_embedding_service, get_firewall_service, get_repository
from backend.core.firewall import FirewallService
from backend.db.repository import BaseRepository
from backend.schemas.policies import (
    FirewallSimulationRequest,
    FirewallSimulationResponse,
    FirewallThresholdResponse,
    FirewallThresholdUpdate,
    PolicyCreate,
    PolicyListResponse,
    PolicyRecord,
    PolicyUpdate,
)

router = APIRouter(prefix="/api/v1/policies", tags=["policies"])


@router.get("", response_model=PolicyListResponse)
async def list_policies(repository: BaseRepository = Depends(get_repository)) -> PolicyListResponse:
    """Return all policies and the current threshold."""
    items = [PolicyRecord(**record) for record in await repository.list_policies()]
    threshold = await repository.get_threshold()
    return PolicyListResponse(items=items, threshold=threshold)


@router.post("", response_model=PolicyRecord)
async def create_policy(
    payload: PolicyCreate,
    repository: BaseRepository = Depends(get_repository),
    embedding_service=Depends(get_embedding_service),
) -> PolicyRecord:
    """Create a policy and store its embedding."""
    embedding = await embedding_service.embed_text(payload.intent_text)
    record = await repository.create_policy(
        policy_id=payload.policy_id,
        intent_text=payload.intent_text,
        category=payload.category,
        is_active=payload.is_active,
        embedding=embedding,
    )
    return PolicyRecord(**record)


@router.patch("/{policy_id}", response_model=PolicyRecord)
async def update_policy(
    policy_id: str,
    payload: PolicyUpdate,
    repository: BaseRepository = Depends(get_repository),
    embedding_service=Depends(get_embedding_service),
) -> PolicyRecord:
    """Update a policy and refresh its embedding when needed."""
    embedding = None
    if payload.intent_text is not None:
        embedding = await embedding_service.embed_text(payload.intent_text)

    try:
        record = await repository.update_policy(
            policy_id=policy_id,
            intent_text=payload.intent_text,
            category=payload.category,
            is_active=payload.is_active,
            embedding=embedding,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "POLICY_NOT_FOUND", "message": str(exc)},
        ) from exc
    return PolicyRecord(**record)


@router.delete("/{policy_id}")
async def delete_policy(
    policy_id: str, repository: BaseRepository = Depends(get_repository)
) -> dict[str, str]:
    """Delete a policy."""
    await repository.delete_policy(policy_id)
    return {"status": "deleted", "policy_id": policy_id}


@router.get("/settings", response_model=FirewallThresholdResponse)
async def get_threshold(
    repository: BaseRepository = Depends(get_repository),
) -> FirewallThresholdResponse:
    """Return the active threshold."""
    return FirewallThresholdResponse(firewall_threshold=await repository.get_threshold())


@router.patch("/settings", response_model=FirewallThresholdResponse)
async def update_threshold(
    payload: FirewallThresholdUpdate,
    repository: BaseRepository = Depends(get_repository),
) -> FirewallThresholdResponse:
    """Update the active threshold."""
    threshold = await repository.update_threshold(payload.firewall_threshold)
    return FirewallThresholdResponse(firewall_threshold=threshold)


@router.post("/simulate", response_model=FirewallSimulationResponse)
async def simulate_prompt(
    payload: FirewallSimulationRequest,
    firewall_service: FirewallService = Depends(get_firewall_service),
) -> FirewallSimulationResponse:
    """Simulate a prompt against the current policy set."""
    decision = await firewall_service.evaluate_prompt(payload.prompt)
    return FirewallSimulationResponse(
        blocked=decision.blocked,
        similarity_score=decision.similarity_score,
        threshold=decision.threshold,
        policy_id=decision.policy_id,
        category=decision.category,
    )
