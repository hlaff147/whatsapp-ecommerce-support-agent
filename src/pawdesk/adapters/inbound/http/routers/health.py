"""Endpoints de saúde (liveness e readiness)."""

from fastapi import APIRouter, Request, Response

from pawdesk.adapters.inbound.http.deps import HttpDependencies

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def ready(request: Request, response: Response) -> dict[str, object]:
    deps: HttpDependencies = request.app.state.deps
    checks = await deps.health_check()
    all_ok = all(checks.values())
    if not all_ok:
        response.status_code = 503
    return {"status": "ready" if all_ok else "degraded", "checks": checks}
