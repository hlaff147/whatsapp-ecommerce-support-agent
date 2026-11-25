"""Fábrica da aplicação FastAPI desacoplada do composition root."""

from fastapi import FastAPI

from pawdesk.adapters.inbound.http.deps import HttpDependencies
from pawdesk.adapters.inbound.http.routers import (
    admin,
    health,
    helpdesk_webhook,
    simulator,
    whatsapp_webhook,
)


def create_app_from_deps(deps: HttpDependencies) -> FastAPI:
    """Cria a aplicação FastAPI conectando todos os roteadores às dependências injetadas."""
    app = FastAPI(title="PawDesk API", version="0.1.0")
    app.state.deps = deps

    app.include_router(health.router)
    app.include_router(whatsapp_webhook.router)
    app.include_router(helpdesk_webhook.router)
    app.include_router(admin.router)
    if deps.enable_simulator:
        app.include_router(simulator.router)
    return app
