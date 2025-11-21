"""Endpoints de analytics."""
from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from futuisp_analytics.application.use_cases.obtener_metricas_mes import ObtenerMetricasMes
from futuisp_analytics.infrastructure.database.connection import get_db_session
from futuisp_analytics.infrastructure.database.repositories.factura_repository_impl import (
    FacturaRepositoryImpl,
)
from futuisp_analytics.application.use_cases.obtener_historial_usuario import ObtenerHistorialUsuario
from futuisp_analytics.application.use_cases.obtener_analisis_anual import ObtenerAnalisisAnual
from futuisp_analytics.domain.value_objects.score_cliente import ScoreCliente
from fastapi import Path


from futuisp_analytics.infrastructure.cache.redis_cache import redis_cache
from futuisp_analytics.interfaces.api.v1.schemas import MetricasMesResponse

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/payment-behavior", response_model=MetricasMesResponse)
async def obtener_comportamiento_pagos(
    fecha_inicio: date = Query(
        ...,
        description="Fecha inicio (YYYY-MM-DD)",
        example="2024-10-01"
    ),
    fecha_fin: date = Query(
        ...,
        description="Fecha fin (YYYY-MM-DD)",
        example="2024-11-01"
    ),
    zona_id: int | None = Query(
        None,
        description="ID de zona (opcional)"
    ),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Obtiene análisis de comportamiento de pagos.
    
    Clasifica los pagos en períodos:
    - OPTIMO: Pagos entre día 1-10
    - ACEPTABLE: Pagos entre día 11 y día de corte
    - CRITICO: Pagos después del día de corte
    - PENDIENTE: Facturas sin pagar
    """
    
    # Generar cache key
    cache_key = f"metricas:{fecha_inicio}:{fecha_fin}:{zona_id or 'all'}"
    
    # Intentar obtener de caché
    cached = await redis_cache.get(cache_key)
    if cached:
        return MetricasMesResponse(**cached)
    
    # Ejecutar caso de uso
    repo = FacturaRepositoryImpl(session)
    use_case = ObtenerMetricasMes(repo)
    
    resultado = await use_case.execute(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        zona_id=zona_id,
    )
    
    # Guardar en caché
    await redis_cache.set(cache_key, resultado, ttl=300)
    
    return MetricasMesResponse(**resultado)


@router.delete("/cache/clear")
async def limpiar_cache(
    pattern: str = Query(
        "metricas:*",
        description="Patrón de keys a eliminar"
    )
):
    """Limpia el caché de métricas."""
    
    deleted = await redis_cache.clear_pattern(pattern)
    
    return {
        "message": "Cache limpiado exitosamente",
        "keys_deleted": deleted,
    }



@router.get("/user/{usuario_id}/history")
async def obtener_historial_usuario_endpoint(
    usuario_id: int,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Obtiene historial COMPLETO de pagos de un usuario con score.
    
    ✅ El análisis se hace sobre TODAS las facturas históricas del usuario.
    
    Retorna:
    - Score general (0-100) basado en historial completo
    - Nivel de riesgo
    - Facturas agrupadas por mes
    - Distribución por período de pago
    """
    
    # Cache key sin fechas
    cache_key = f"user:{usuario_id}:history:complete"
    cached = await redis_cache.get(cache_key)
    if cached:
        return cached
    
    # Ejecutar caso de uso
    repo = FacturaRepositoryImpl(session)
    use_case = ObtenerHistorialUsuario(repo)
    
    # ✅ Solo pasar usuario_id
    resultado = await use_case.execute(usuario_id=usuario_id)
    
    # Guardar en caché (10 minutos)
    await redis_cache.set(cache_key, resultado, ttl=600)
    
    return resultado


@router.get("/annual-analysis/{año}")
async def obtener_analisis_anual_endpoint(
    año: int = Path(..., ge=2020, le=2030, description="Año a analizar"),
    zona_id: int | None = Query(None, description="Filtrar por zona"),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Análisis completo de un año mes a mes.
    
    Retorna:
    - Resumen anual
    - Métricas mensuales
    - Tendencias por período
    """
    
    # Cache key
    cache_key = f"annual:{año}:{zona_id or 'all'}"
    cached = await redis_cache.get(cache_key)
    if cached:
        return cached
    
    # Ejecutar caso de uso
    repo = FacturaRepositoryImpl(session)
    use_case = ObtenerAnalisisAnual(repo)
    
    resultado = await use_case.execute(año=año, zona_id=zona_id)
    
    # Guardar en caché (30 minutos - datos históricos)
    await redis_cache.set(cache_key, resultado, ttl=1800)
    
    return resultado


@router.get("/top-users")
async def obtener_top_usuarios_endpoint(
    fecha_inicio: date = Query(..., description="Fecha inicio"),
    fecha_fin: date = Query(..., description="Fecha fin"),
    limite: int = Query(100, ge=1, le=1000, description="Cantidad de usuarios"),
    orden: str = Query("mejor", regex="^(mejor|peor)$", description="Ordenar por mejor o peor"),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Ranking de usuarios por score de comportamiento de pago.
    
    Parámetros:
    - orden: "mejor" (score alto) o "peor" (score bajo)
    - limite: Cantidad de usuarios a retornar
    """
    
    # Cache key
    cache_key = f"top:{fecha_inicio}:{fecha_fin}:{limite}:{orden}"
    cached = await redis_cache.get(cache_key)
    if cached:
        return cached
    
    # Ejecutar
    repo = FacturaRepositoryImpl(session)
    resultado = await repo.obtener_top_usuarios(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        limite=limite,
        orden=orden,
    )
    
    # Caché 5 minutos
    await redis_cache.set(cache_key, resultado, ttl=300)
    
    return {
        "periodo": f"{fecha_inicio} a {fecha_fin}",
        "orden": orden,
        "total_usuarios": len(resultado),
        "usuarios": resultado,
    }


@router.get("/global-ranking")
async def obtener_ranking_global_endpoint(
    pagina: int = Query(1, ge=1, description="Número de página"),
    por_pagina: int = Query(50, ge=1, le=100, description="Registros por página"),
    orden: str = Query(
        "peor",
        regex="^(mejor|peor)$",
        description="Ordenar por mejor o peor score"
    ),
    buscar: str | None = Query(None, description="Buscar por nombre o cédula"),
    nivel_riesgo: str | None = Query(
        None,
        regex="^(CRITICO|ALTO|MEDIO|BAJO)$",
        description="Filtrar por nivel de riesgo"
    ),
    fecha_inicio: date | None = Query(None, description="Fecha inicio análisis"),
    fecha_fin: date | None = Query(None, description="Fecha fin análisis"),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Ranking global de usuarios con paginación y filtros.
    
    **Filtros disponibles**:
    - `buscar`: Busca por nombre o cédula del cliente
    - `nivel_riesgo`: CRITICO, ALTO, MEDIO, BAJO
    - `orden`: "peor" (críticos primero) o "mejor" (mejores primero)
    - `fecha_inicio` y `fecha_fin`: Rango de análisis
    
    **Paginación**:
    - `pagina`: Número de página (default: 1)
    - `por_pagina`: Registros por página (max: 100, default: 50)
    
    **Ejemplo**:
```
    GET /analytics/global-ranking?orden=peor&nivel_riesgo=CRITICO&pagina=1&por_pagina=20
```
    """
    
    # Import del caso de uso
    from futuisp_analytics.application.use_cases.obtener_ranking_global import (
        ObtenerRankingGlobal
    )
    
    # Cache key
    cache_key = (
        f"ranking:{pagina}:{por_pagina}:{orden}:"
        f"{buscar or 'all'}:{nivel_riesgo or 'all'}:"
        f"{fecha_inicio}:{fecha_fin}"
    )
    
    cached = await redis_cache.get(cache_key)
    if cached:
        return cached
    
    # Ejecutar caso de uso
    use_case = ObtenerRankingGlobal(session)
    
    resultado = await use_case.execute(
        pagina=pagina,
        por_pagina=por_pagina,
        orden=orden,
        buscar=buscar,
        nivel_riesgo=nivel_riesgo,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
    )
    
    # Guardar en caché (5 minutos)
    await redis_cache.set(cache_key, resultado, ttl=300)
    
    return resultado



@router.get("/global-stats")
async def obtener_estadisticas_globales(
    session: AsyncSession = Depends(get_db_session),
):
    """
    Obtiene estadísticas globales agregadas de TODOS los usuarios.
    
    ✅ OPTIMIZADO: 1 sola query en lugar de 4
    
    Retorna:
    {
        "total_usuarios": 5829,
        "por_nivel_riesgo": {
            "CRITICO": 1234,
            "ALTO": 2345,
            "MEDIO": 1678,
            "BAJO": 572
        },
        "score_promedio_general": 45.8,
        "facturas_totales": 235000,
        "facturas_puntuales": 89000,
        "facturas_morosas": 146000
    }
    """
    from futuisp_analytics.application.use_cases.obtener_ranking_global import ObtenerRankingGlobal
    
    # Cache key
    cache_key = "global:stats"
    cached = await redis_cache.get(cache_key)
    if cached:
        return cached
    
    # Obtener TODOS los usuarios (sin paginación)
    use_case = ObtenerRankingGlobal(session)
    resultado = await use_case.execute(
        pagina=1,
        por_pagina=999999,  # Número grande
        orden="peor",
        sin_limite=True  # ✅ CLAVE
    )
    
    usuarios = resultado['usuarios']
    
    # Calcular estadísticas agregadas
    stats = {
        "total_usuarios": len(usuarios),
        "por_nivel_riesgo": {
            "CRITICO": sum(1 for u in usuarios if u['nivel_riesgo'] == 'CRITICO'),
            "ALTO": sum(1 for u in usuarios if u['nivel_riesgo'] == 'ALTO'),
            "MEDIO": sum(1 for u in usuarios if u['nivel_riesgo'] == 'MEDIO'),
            "BAJO": sum(1 for u in usuarios if u['nivel_riesgo'] == 'BAJO'),
        },
        "score_promedio_general": round(sum(u['score'] for u in usuarios) / len(usuarios), 1) if usuarios else 0,
        "facturas_totales": sum(u['total_facturas'] for u in usuarios),
        "facturas_puntuales": sum(u['facturas_puntuales'] for u in usuarios),
        "facturas_morosas": sum(u['facturas_morosas'] for u in usuarios),
    }
    
    # Cache 10 minutos
    await redis_cache.set(cache_key, stats, ttl=600)
    
    return stats
