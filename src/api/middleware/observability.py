"""
FastAPI middleware for automatic observability.
Captures HTTP metrics and structured logging.
"""

import time
import uuid
from typing import Callable

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from core.logging import clear_exchange_id, set_exchange_id
from core.observability import record_http_request


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Middleware to automatically capture HTTP metrics and logs."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate or extract exchange_id for tracing
        exchange_id = request.headers.get("X-Exchange-ID", str(uuid.uuid4()))
        request.state.exchange_id = exchange_id

        # Start timing
        start_time = time.time()

        # Get request info
        method = request.method
        url_path = request.url.path

        # Process request
        set_exchange_id(exchange_id)
        try:
            response = await call_next(request)
        finally:
            clear_exchange_id()

        # Calculate duration
        duration = time.time() - start_time

        # Record metrics
        record_http_request(
            method=method,
            endpoint=url_path,
            status_code=response.status_code,
            duration=duration,
        )

        # Add exchange_id to response headers for traceability
        response.headers["X-Exchange-ID"] = exchange_id

        return response


def add_observability_middleware(app: FastAPI) -> None:
    """Add observability middleware to FastAPI app."""
    app.add_middleware(ObservabilityMiddleware)


def add_metrics_endpoint(app: FastAPI) -> None:
    """Add metrics endpoint for Prometheus scraping."""
    from core.observability import get_metrics_endpoint

    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint."""
        content, content_type = get_metrics_endpoint()
        return Response(content=content, media_type=content_type)
