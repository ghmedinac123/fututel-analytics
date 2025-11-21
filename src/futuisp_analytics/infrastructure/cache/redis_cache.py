"""Servicio de caché con Redis."""
import json
from typing import Any
from contextlib import asynccontextmanager

import redis.asyncio as redis

from futuisp_analytics.infrastructure.config.settings import get_settings


class RedisCache:
    """Gestor de caché con Redis."""
    
    def __init__(self):
        self._client: redis.Redis | None = None
    
    async def initialize(self) -> None:
        """Inicializa conexión a Redis."""
        settings = get_settings()
        
        self._client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_keepalive=True,
        )
        
        # Verificar conexión
        await self._client.ping()
    
    async def close(self) -> None:
        """Cierra conexión."""
        if self._client:
            await self._client.aclose()
    
    async def get(self, key: str) -> Any | None:
        """Obtiene valor del caché."""
        if not self._client:
            return None
        
        try:
            value = await self._client.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            print(f"Error obteniendo de caché: {e}")
        
        return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> bool:
        """Guarda valor en caché."""
        if not self._client:
            return False
        
        try:
            settings = get_settings()
            ttl = ttl or settings.redis_ttl
            
            serialized = json.dumps(value, default=str)
            await self._client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            print(f"Error guardando en caché: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Elimina valor del caché."""
        if not self._client:
            return False
        
        try:
            await self._client.delete(key)
            return True
        except Exception as e:
            print(f"Error eliminando de caché: {e}")
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """Elimina todas las keys que coincidan con el patrón."""
        if not self._client:
            return 0
        
        try:
            keys = []
            async for key in self._client.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                return await self._client.delete(*keys)
            return 0
        except Exception as e:
            print(f"Error limpiando patrón: {e}")
            return 0


# Instancia global
redis_cache = RedisCache()