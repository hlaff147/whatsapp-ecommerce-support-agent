"""Entrypoint da API FastAPI para Uvicorn."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from pawdesk.adapters.inbound.http.app import create_app_from_deps
from pawdesk.adapters.outbound.observability.logging import configure_logging
from pawdesk.adapters.outbound.observability.otel import configure_otel
from pawdesk.bootstrap.container import Container
from pawdesk.bootstrap.settings import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Constrói a aplicação FastAPI conectada ao MySQL/Redis ou ao modo em memória."""
    effective = settings or get_settings()
    configure_logging(effective.log_level)
    configure_otel("pawdesk-api", effective.otel_endpoint)
    container = Container(effective)

    if effective.storage_backend == "memory":
        wired = container.build_for_dev()
        return create_app_from_deps(wired.http_dependencies())

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with container.scope(null_pool=False) as wired:
            app.state.deps = wired.http_dependencies()
            yield

    # Placeholder substituído no startup pelo lifespan
    placeholder_deps = container.build_for_dev().http_dependencies()
    app = create_app_from_deps(placeholder_deps)
    app.router.lifespan_context = lifespan
    return app
