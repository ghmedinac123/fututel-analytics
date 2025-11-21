"""Router principal v1."""
from fastapi import APIRouter

from futuisp_analytics.interfaces.api.v1.endpoints import health, analytics, ml

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(analytics.router)
api_router.include_router(ml.router)  # ← AGREGAR ESTA LÍNEA