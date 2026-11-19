"""Trace and metric routes for the dashboard."""

from fastapi import APIRouter, Depends, Query

from backend.core.auth import require_admin
from backend.core.dependencies import get_repository
from backend.db.repository import BaseRepository
from backend.schemas.responses import OverviewMetricsResponse, TraceListResponse, TraceRecord

router = APIRouter(prefix="/api/v1", tags=["dashboard"], dependencies=[Depends(require_admin)])


@router.get("/metrics/overview", response_model=OverviewMetricsResponse)
async def overview_metrics(
    ignore_first_n: int = Query(default=0, ge=0, le=25),
    repository: BaseRepository = Depends(get_repository),
) -> OverviewMetricsResponse:
    """Return top-level dashboard metrics."""
    return OverviewMetricsResponse(
        **await repository.get_overview_metrics(ignore_first_n=ignore_first_n)
    )


@router.get("/traces", response_model=TraceListResponse)
async def list_traces(
    provider: str | None = Query(default=None),
    blocked: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    repository: BaseRepository = Depends(get_repository),
) -> TraceListResponse:
    """Return recent trace records."""
    rows = await repository.list_request_logs(provider=provider, blocked=blocked, limit=limit)
    items = [TraceRecord(**row) for row in rows]
    return TraceListResponse(items=items, total=len(items))
