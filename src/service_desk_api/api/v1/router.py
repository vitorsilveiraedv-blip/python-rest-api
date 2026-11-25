"""Aggregate versioned API routers."""

from fastapi import APIRouter

from service_desk_api.api.v1.auth import router as auth_router
from service_desk_api.api.v1.health import router as health_router
from service_desk_api.api.v1.tickets import router as tickets_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(tickets_router)
