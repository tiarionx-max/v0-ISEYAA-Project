"""ISEYAA API Gateway — Route proxy definitions."""
from fastapi import APIRouter

health_router = APIRouter()

@health_router.get("")
async def health():
    return {"service": "api-gateway", "status": "healthy", "version": "1.0.0"}

@health_router.get("/deep")
async def deep_health():
    import httpx
    from app.core.config import settings
    results = {}
    async with httpx.AsyncClient(timeout=5.0) as client:
        for name, url in settings.service_map.items():
            try:
                r = await client.get(f"{url}/health")
                results[name] = "healthy" if r.status_code == 200 else f"status_{r.status_code}"
            except Exception as e:
                results[name] = f"unreachable: {str(e)[:50]}"
    return {"gateway": "healthy", "services": results}

from app.routes.proxy import make_proxy_router

auth_router          = make_proxy_router("auth",         "/api/v1/auth")
wallet_router        = make_proxy_router("wallet",        "/api/v1/wallet")
events_router        = make_proxy_router("events",        "/api/v1/events")
lga_router           = make_proxy_router("lga",           "/api/v1/lga")
notifications_router = make_proxy_router("notifications", "/api/v1/notifications")
ai_router            = make_proxy_router("ai",            "/api/v1/ai")
