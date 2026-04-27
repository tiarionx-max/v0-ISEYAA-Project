"""
ISEYAA API Gateway — HTTP Reverse Proxy helper.
Forwards requests to downstream microservices, preserving headers,
query params, and body. Injects X-User-ID from JWT middleware state.
"""
import httpx
from fastapi import APIRouter, Request
from fastapi.responses import Response
from app.core.config import settings


def make_proxy_router(service_name: str, path_prefix: str) -> APIRouter:
    router = APIRouter()

    @router.api_route(
        "/{path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    )
    async def proxy(path: str, request: Request):
        base_url = settings.service_map[service_name]
        url = f"{base_url}{path_prefix}/{path}"

        # Forward headers; inject user context from JWT middleware
        headers = dict(request.headers)
        headers.pop("host", None)
        if hasattr(request.state, "user_id") and request.state.user_id:
            headers["X-User-ID"]   = str(request.state.user_id)
            headers["X-User-Role"] = str(getattr(request.state, "user_role", ""))
            headers["X-User-LGA"]  = str(getattr(request.state, "user_lga", "") or "")

        body = await request.body()

        async with httpx.AsyncClient(timeout=30.0) as client:
            upstream = await client.request(
                method=request.method,
                url=url,
                headers=headers,
                params=request.query_params,
                content=body,
            )

        return Response(
            content=upstream.content,
            status_code=upstream.status_code,
            headers=dict(upstream.headers),
            media_type=upstream.headers.get("content-type"),
        )

    return router
