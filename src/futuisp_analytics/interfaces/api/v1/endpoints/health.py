"""Endpoint de health check."""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from futuisp_analytics.infrastructure.database.connection import get_db_session
from futuisp_analytics.infrastructure.cache.redis_cache import redis_cache
from futuisp_analytics.infrastructure.config.settings import get_settings
from futuisp_analytics.interfaces.api.v1.schemas import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(session: AsyncSession = Depends(get_db_session)):
    """Health check del servicio."""
    settings = get_settings()
    
    # Verificar base de datos
    db_status = "connected"
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        db_status = "disconnected"
    
    # Verificar Redis
    redis_status = "connected"
    try:
        await redis_cache._client.ping()
    except Exception:
        redis_status = "disconnected"
    
    status = "healthy" if db_status == "connected" and redis_status == "connected" else "degraded"
    
    return HealthResponse(
        status=status,
        service=settings.app_name,
        version=settings.app_version,
        database=db_status,
        redis=redis_status,
    )
