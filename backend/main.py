"""FastAPI application entrypoint."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.api.v1.routes.gateway import router as gateway_router
from backend.api.v1.routes.policies import router as policies_router
from backend.api.v1.routes.traces import router as traces_router
from backend.core.config import Settings, get_settings
from backend.core.demo_data import DEMO_POLICIES, EXTRA_SEED_POLICIES
from backend.core.dependencies import build_container


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    active_settings = settings or get_settings()
    logging.basicConfig(level=active_settings.log_level.upper())

    app = FastAPI(
        title=active_settings.app_name,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.state.container = build_container(active_settings)

    @app.on_event("startup")
    async def ensure_memory_demo_policies() -> None:
        """Seed demo policies automatically when running in memory mode."""
        container = app.state.container
        if container.settings.repository_mode != "memory":
            return

        existing = await container.repository.list_policies()
        if existing:
            return

        for policy_id, intent_text, category in [*DEMO_POLICIES, *EXTRA_SEED_POLICIES]:
            embedding = await container.embedding_service.embed_text(intent_text)
            await container.repository.create_policy(
                policy_id=policy_id,
                intent_text=intent_text,
                category=category,
                is_active=True,
                embedding=embedding,
            )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_, exc: RequestValidationError) -> JSONResponse:
        """Normalize request validation errors."""
        errors = []
        for item in exc.errors():
            location = ".".join(str(part) for part in item.get("loc", []))
            errors.append({"field": location, "type": item.get("type", "validation_error")})
        return JSONResponse(
            status_code=422,
            content={
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed.",
                "errors": errors,
            },
        )

    app.include_router(gateway_router)
    app.include_router(policies_router)
    app.include_router(traces_router)
    return app


app = create_app()
