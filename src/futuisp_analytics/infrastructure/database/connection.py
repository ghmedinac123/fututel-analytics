"""Gestión de conexiones a la base de datos."""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from futuisp_analytics.infrastructure.config.settings import get_settings


class DatabaseManager:
    """Gestor de conexiones a base de datos."""
    
    def __init__(self):
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None
    
    def initialize(self) -> None:
        """Inicializa el motor de base de datos."""
        settings = get_settings()
        
        self._engine = create_async_engine(
            settings.database_url,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_recycle=settings.db_pool_recycle,
            echo=settings.debug,
            pool_pre_ping=True,
        )
        
        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    
    async def close(self) -> None:
        """Cierra las conexiones."""
        if self._engine:
            await self._engine.dispose()
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Context manager para obtener sesión de BD."""
        if not self._session_factory:
            raise RuntimeError("Database no inicializada")
        
        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise


# Instancia global
db_manager = DatabaseManager()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency para FastAPI."""
    async with db_manager.get_session() as session:
        yield session