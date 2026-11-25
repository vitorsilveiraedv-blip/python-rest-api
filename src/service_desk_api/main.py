"""FastAPI application entry point."""

from fastapi import FastAPI

from service_desk_api.api.v1.router import api_router
from service_desk_api.config import get_settings


def create_app() -> FastAPI:
    """Build the application; keeping a factory makes tests isolated and predictable."""
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "A service desk backend for managing support requests, ownership, "
            "workflows and operational history."
        ),
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url="/redoc" if settings.environment != "production" else None,
        openapi_url="/openapi.json" if settings.environment != "production" else None,
    )
    application.include_router(api_router, prefix=settings.api_v1_prefix)
    return application


app = create_app()
