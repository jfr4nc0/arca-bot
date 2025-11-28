"""
API Token authentication middleware.
"""

from fastapi import HTTPException, Request, status
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from api.config.settings import settings

api_token_header = APIKeyHeader(name="X-API-Token", auto_error=False)


class APITokenMiddleware(BaseHTTPMiddleware):
    """Middleware to validate API token for all requests except health check and docs."""

    EXCLUDED_PATHS = {"/health", "/docs", "/redoc", "/openapi.json", "/metrics"}

    async def dispatch(self, request: Request, call_next):
        """Validate API token for protected endpoints."""
        # Skip authentication for excluded paths
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)

        # Check if API token is configured
        if not settings.api_token:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "error": "ServiceUnavailable",
                    "message": "API token is not configured",
                },
            )

        # Get token from header
        token = request.headers.get("X-API-Token")

        # Validate token
        if not token or token != settings.api_token:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "Unauthorized",
                    "message": "Invalid or missing API token",
                },
            )

        return await call_next(request)
