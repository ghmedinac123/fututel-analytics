"""Endpoints de Machine Learning para predicción de churn."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from futuisp_analytics.infrastructure.database.connection import get_db_session
from futuisp_analytics.application.use_cases.entrenar_modelo_churn import EntrenarModeloChurn
from futuisp_analytics.application.use_cases.predecir_churn import PredecirChurn
from futuisp_analytics.infrastructure.ml.model_storage import ModelStorage
from futuisp_analytics.infrastructure.config.logging import logger
from futuisp_analytics.infrastructure.cache.redis_cache import redis_cache
from futuisp_analytics.interfaces.api.v1.schemas.ml import (
    ResultadoEntrenamiento,
    PrediccionUsuario,
    ResultadoBatch,
    InfoModelo,
    ListaModelos,
)


router = APIRouter(
    prefix="/ml",
    tags=["🤖 Machine Learning - Predicción de Churn"],
    responses={500: {"description": "Error interno del servidor"}},
)


@router.post("/train/churn", response_model=ResultadoEntrenamiento)
async def entrenar_modelo_churn(
    meses_historicos: int = Query(12, ge=6, le=24),
    min_facturas: int = Query(3, ge=1, le=12),
    test_size: float = Query(0.2, ge=0.1, le=0.4),
    session: AsyncSession = Depends(get_db_session)
):
    """Entrena nuevo modelo de predicción de churn."""
    try:
        use_case = EntrenarModeloChurn(session)
        resultado = await use_case.execute(
            meses_historicos=meses_historicos,
            min_facturas=min_facturas,
            test_size=test_size
        )
        
        # Limpiar cache después de entrenar
        await redis_cache.clear_pattern("churn:*")
        
        return resultado
    except Exception as e:
        logger.error(f"Error en entrenamiento: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al entrenar modelo: {str(e)}")


@router.get("/model/info", response_model=InfoModelo)
async def obtener_info_modelo():
    """Información del modelo actual."""
    try:
        storage = ModelStorage()
        _, feature_names, metrics = storage.load_model()
        modelos_disponibles = storage.list_models()
        
        return {
            "modelo_actual": {
                "fecha_entrenamiento": metrics.get("training_date"),
                "metricas": {
                    "test_accuracy": metrics.get("test_accuracy"),
                    "test_precision": metrics.get("test_precision"),
                    "test_recall": metrics.get("test_recall"),
                    "test_f1": metrics.get("test_f1"),
                    "test_roc_auc": metrics.get("test_roc_auc"),
                    "cv_roc_auc": metrics.get("cv_roc_auc_mean"),
                },
                "dataset": {
                    "samples_train": metrics.get("samples_train"),
                    "samples_test": metrics.get("samples_test"),
                    "churn_rate": metrics.get("churn_rate"),
                },
                "features_count": len(feature_names),
            },
            "modelos_disponibles": modelos_disponibles,
            "features": feature_names,
        }
    except Exception as e:
        logger.error(f"Error obteniendo info modelo: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al obtener información: {str(e)}")


@router.get("/model/list", response_model=ListaModelos)
async def listar_modelos():
    """Lista todos los modelos disponibles."""
    try:
        storage = ModelStorage()
        modelos = storage.list_models()
        return {"total_modelos": len(modelos), "modelos": modelos}
    except Exception as e:
        logger.error(f"Error listando modelos: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al listar modelos: {str(e)}")


@router.get("/predict/churn/batch", response_model=ResultadoBatch)
async def predecir_churn_batch(
    riesgo_minimo: float = Query(50.0, ge=0, le=100),
    limit: Optional[int] = Query(None, ge=1, le=1000),
    session: AsyncSession = Depends(get_db_session)
):
    """Predicción masiva de churn para usuarios ACTIVOS."""
    # ==========================================
    # CACHE LAYER
    # ==========================================
    cache_key = f"churn:batch:riesgo_{int(riesgo_minimo)}"
    if limit:
        cache_key += f":limit_{limit}"
    
    cached_result = await redis_cache.get(cache_key)
    if cached_result:
        logger.info(f"✅ Cache HIT - Batch (riesgo={riesgo_minimo})")
        return ResultadoBatch(**cached_result)
    
    logger.info(f"⚠️ Cache MISS - Batch (riesgo={riesgo_minimo})")
    
    # ==========================================
    # USE CASE EXECUTION
    # ==========================================
    try:
        use_case = PredecirChurn(session)
        resultados = await use_case.predecir_usuarios_activos(
            riesgo_minimo=riesgo_minimo,
            limit=limit
        )
        
        response_data = {
            "total_en_riesgo": len(resultados),
            "riesgo_minimo": riesgo_minimo,
            "usuarios": resultados
        }
        
        # Guardar en cache (30 minutos)
        await redis_cache.set(cache_key, response_data, ttl=1800)
        
        return ResultadoBatch(**response_data)
    except Exception as e:
        logger.error(f"Error en predicción batch: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error en predicción masiva: {str(e)}")


@router.get("/predict/churn/{usuario_id}", response_model=PrediccionUsuario)
async def predecir_churn_usuario(
    usuario_id: int = Path(..., gt=0),
    session: AsyncSession = Depends(get_db_session)
):
    """Predicción individual de churn."""
    # ==========================================
    # CACHE LAYER
    # ==========================================
    cache_key = f"churn:usuario:{usuario_id}"
    cached_result = await redis_cache.get(cache_key)
    
    if cached_result:
        logger.info(f"✅ Cache HIT - Usuario {usuario_id}")
        return PrediccionUsuario(**cached_result)
    
    logger.info(f"⚠️ Cache MISS - Usuario {usuario_id}")
    
    # ==========================================
    # USE CASE EXECUTION
    # ==========================================
    try:
        use_case = PredecirChurn(session)
        resultado = await use_case.predecir_usuario(usuario_id)
        
        if resultado is None:
            raise HTTPException(
                status_code=404,
                detail=f"Usuario {usuario_id} no encontrado o sin datos suficientes"
            )
        
        # Guardar en cache (1 hora)
        await redis_cache.set(cache_key, resultado, ttl=3600)
        
        return PrediccionUsuario(**resultado)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en predicción: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al predecir usuario {usuario_id}: {str(e)}")
