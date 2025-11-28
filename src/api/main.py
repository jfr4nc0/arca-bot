"""
FastAPI application main module - simplified without unnecessary service factory.
"""

import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

import core.logging  # noqa: F401  Ensure logging is configured
from api.config.settings import settings
from api.controllers.health_controller import router as health_router
from api.controllers.system_controller import router as system_router
from api.controllers.workflow_controller import router as workflow_router
from api.controllers.workflow_controller import transaction_service
from api.middleware import (
    APITokenMiddleware,
    add_metrics_endpoint,
    add_observability_middleware,
)
from api.models.responses import ErrorResponse
from core.services.selenium_monitor import SeleniumMonitor
from core.services.selenium_scaler import SeleniumScaler

# Global selenium monitor task
_selenium_monitor_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management with Selenium auto-scaling."""
    global _selenium_monitor_task

    # Startup
    logger.info("Starting ArcaAutoVep API...")

    # Initialize Selenium auto-scaling if enabled
    selenium_scale_enabled = (
        os.getenv("SELENIUM_SCALE_ENABLED", "true").lower() == "true"
    )

    if selenium_scale_enabled:
        logger.info("Initializing Selenium auto-scaler...")

        # Get configuration from environment
        min_nodes = int(os.getenv("SELENIUM_MIN_NODES", "0"))
        max_nodes = int(os.getenv("SELENIUM_MAX_NODES", "3"))
        idle_timeout = int(os.getenv("SELENIUM_IDLE_TIMEOUT", "600"))

        # Create scaler and monitor
        selenium_scaler = SeleniumScaler(
            min_nodes=min_nodes,
            max_nodes=max_nodes,
            sessions_per_node=2,
        )

        selenium_monitor = SeleniumMonitor(
            scaler=selenium_scaler,
            idle_timeout=idle_timeout,
            check_interval=60,
        )

        # Start monitoring task
        _selenium_monitor_task = asyncio.create_task(
            selenium_monitor.start_monitoring()
        )
        logger.info(
            f"Selenium auto-scaler started (min={min_nodes}, max={max_nodes}, idle_timeout={idle_timeout}s)"
        )

        # Store scaler in app state for access by controllers
        app.state.selenium_scaler = selenium_scaler
        app.state.selenium_monitor = selenium_monitor
    else:
        logger.info("Selenium auto-scaling disabled")
        app.state.selenium_scaler = None
        app.state.selenium_monitor = None

    logger.info("ArcaAutoVep API started successfully")

    yield

    # Shutdown
    logger.info("Shutting down ArcaAutoVep API...")

    # Stop selenium monitor if running
    if _selenium_monitor_task and not _selenium_monitor_task.done():
        logger.info("Stopping Selenium auto-scaler...")
        _selenium_monitor_task.cancel()
        try:
            await _selenium_monitor_task
        except asyncio.CancelledError:
            logger.info("Selenium auto-scaler stopped")

    # Cleanup transaction service
    await transaction_service.cleanup()
    logger.info("ArcaAutoVep API shutdown complete")


def create_app() -> FastAPI:
    """Create FastAPI application with proper SOLID architecture."""
    app = FastAPI(
        title=settings.api_title,
        description=settings.api_description,
        version=settings.api_version,
        lifespan=lifespan,
        debug=settings.debug,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Add API token middleware first (before observability)
    app.add_middleware(APITokenMiddleware)
    logger.info("API token authentication middleware enabled")

    # Add observability middleware
    add_observability_middleware(app)
    add_metrics_endpoint(app)
    logger.info("Observability middleware and metrics endpoint enabled")

    # Add trusted host middleware in production (without HTTPS redirect)
    if settings.is_production():
        app.add_middleware(
            TrustedHostMiddleware, allowed_hosts=settings.get_allowed_hosts()
        )
        logger.info(
            f"Production security middleware enabled: trusted hosts {settings.get_allowed_hosts()}"
        )

    # Register routers
    app.include_router(workflow_router)
    app.include_router(health_router)
    app.include_router(system_router)

    # Simple exception handler (no need for middleware class)
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception in {request.url.path}: {exc}")
        error_response = ErrorResponse(
            error="InternalServerError", message="An unexpected error occurred"
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response.model_dump(mode="json"),
        )

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info",
    )
