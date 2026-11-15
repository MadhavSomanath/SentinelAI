"""Dependency and container helpers."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from backend.core.classifier import InjectionClassifier
from backend.core.config import Settings, get_settings
from backend.core.embeddings import SentenceTransformerEmbeddingService
from backend.core.firewall import FirewallService
from backend.db.repository import BaseRepository, InMemoryRepository, SupabaseRepository
from backend.services.langfuse_client import LangfuseTraceService
from backend.services.llm_router import LLMRouter


@dataclass
class AppContainer:
    """Runtime dependency container."""

    settings: Settings
    repository: BaseRepository
    embedding_service: object
    trace_service: object
    llm_router: LLMRouter
    classifier: InjectionClassifier | None = None


def build_container(
    settings: Settings | None = None,
    *,
    repository: BaseRepository | None = None,
    embedding_service: object | None = None,
    trace_service: object | None = None,
    llm_router: LLMRouter | None = None,
    classifier: InjectionClassifier | None = None,
) -> AppContainer:
    """Build the default application container."""
    active_settings = settings or get_settings()

    active_repository = repository
    if active_repository is None:
        active_repository = (
            InMemoryRepository(threshold=active_settings.firewall_threshold)
            if active_settings.repository_mode == "memory"
            else SupabaseRepository(active_settings)
        )

    if classifier is None and active_settings.injection_classifier_enabled:
        classifier = InjectionClassifier(
            active_settings.injection_classifier_model,
            active_settings.injection_classifier_threshold,
        )

    return AppContainer(
        settings=active_settings,
        repository=active_repository,
        embedding_service=embedding_service
        or SentenceTransformerEmbeddingService(active_settings.embedding_model_name),
        trace_service=trace_service or LangfuseTraceService(active_settings),
        llm_router=llm_router or LLMRouter(active_settings),
        classifier=classifier,
    )


def get_container(request: Request) -> AppContainer:
    """Return the per-app dependency container."""
    return request.app.state.container


def get_repository(request: Request) -> BaseRepository:
    """Return the configured repository."""
    return get_container(request).repository


def get_embedding_service(request: Request) -> object:
    """Return the configured embedding service."""
    return get_container(request).embedding_service


def get_firewall_service(request: Request) -> FirewallService:
    """Construct a firewall service from the active dependencies."""
    container = get_container(request)
    return FirewallService(container.repository, container.embedding_service, container.classifier)


def get_trace_service(request: Request) -> object:
    """Return the trace service."""
    return get_container(request).trace_service


def get_llm_router(request: Request) -> LLMRouter:
    """Return the LLM router."""
    return get_container(request).llm_router
