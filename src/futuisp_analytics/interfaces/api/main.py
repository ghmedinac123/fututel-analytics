"""Aplicación principal FastAPI."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from futuisp_analytics.infrastructure.config.settings import get_settings
from futuisp_analytics.infrastructure.config.logging import setup_logging, logger
from futuisp_analytics.infrastructure.database.connection import db_manager
from futuisp_analytics.infrastructure.cache.redis_cache import redis_cache
from futuisp_analytics.interfaces.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestiona el ciclo de vida de la aplicación."""
    settings = get_settings()
    
    # Setup logging
    setup_logging(level="DEBUG" if settings.debug else "WARNING")
    
    # Startup
    logger.info(f"🚀 Iniciando {settings.app_name} v{settings.app_version}")
    
    # Inicializar base de datos
    logger.info("📊 Conectando a base de datos...")
    try:
        db_manager.initialize()
        logger.info("✅ Base de datos conectada")
    except Exception as e:
        logger.error(f"❌ Error conectando a base de datos: {e}")
        raise
    
    # Inicializar Redis
    logger.info("�� Conectando a Redis...")
    try:
        await redis_cache.initialize()
        logger.info("✅ Redis conectado")
    except Exception as e:
        logger.warning(f"⚠️ Redis no disponible: {e}")
    
    logger.info("🎉 Servicios iniciados correctamente")
    
    yield
    
    # Shutdown
    logger.info("🛑 Cerrando conexiones...")
    await db_manager.close()
    await redis_cache.close()
    logger.info("👋 Servicios detenidos")


def create_app() -> FastAPI:
    """Factory de la aplicación."""
    settings = get_settings()
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Microservicio de análisis estadístico de pagos para FUTUISP",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # En producción: especificar dominios
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Incluir routers
    app.include_router(api_router, prefix="/api/v1")
    
    return app


app = create_app()
