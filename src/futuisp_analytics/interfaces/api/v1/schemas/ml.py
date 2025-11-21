"""Schemas Pydantic para endpoints de Machine Learning."""
from typing import List
from pydantic import BaseModel, Field


class MetricasModelo(BaseModel):
    """Métricas de evaluación del modelo ML."""
    test_accuracy: float = Field(..., description="Precisión en test set (0-1)", example=0.9817)
    test_precision: float = Field(..., description="Precisión de clase positiva", example=0.9292)
    test_recall: float = Field(..., description="Recall de clase positiva", example=0.9654)
    test_f1: float = Field(..., description="F1-Score", example=0.9469)
    test_roc_auc: float = Field(..., description="Área bajo curva ROC", example=0.9971)
    cv_roc_auc: float = Field(..., description="ROC-AUC en cross-validation", example=0.9961)


class DatasetInfo(BaseModel):
    """Información del dataset de entrenamiento."""
    samples_train: int = Field(..., description="Usuarios en set de entrenamiento", example=5452)
    samples_test: int = Field(..., description="Usuarios en set de prueba", example=1363)
    churn_rate: float = Field(..., description="Tasa de churn (%)", example=16.96)


class TopFeature(BaseModel):
    """Feature importante del modelo."""
    feature: str = Field(..., description="Nombre de la feature", example="dias_pago_ultimos_3m")
    importance: float = Field(..., description="Importancia relativa (0-1)", example=0.3581)


class ResultadoEntrenamiento(BaseModel):
    """Resultado del entrenamiento del modelo."""
    success: bool = Field(..., description="Indica si el entrenamiento fue exitoso", example=True)
    model_path: str = Field(..., description="Ruta donde se guardó el modelo")
    metrics: MetricasModelo = Field(..., description="Métricas de evaluación")
    dataset: DatasetInfo = Field(..., description="Información del dataset")
    top_features: List[TopFeature] = Field(..., description="Top 5 features más importantes")


class MetricasUsuario(BaseModel):
    """Métricas específicas de un usuario."""
    facturas_pendientes: int = Field(..., description="Cantidad de facturas sin pagar", example=4)
    deuda_total: float = Field(..., description="Deuda acumulada total", example=180000.0)
    promedio_dias_pago: float = Field(..., description="Promedio de días para pagar", example=25.3)
    pagos_puntuales: float = Field(..., description="% de pagos puntuales (<10 días)", example=15.0)


class PrediccionUsuario(BaseModel):
    """Predicción de churn para un usuario específico."""
    usuario_id: int = Field(..., description="ID del usuario", example=7790)
    nombre_completo: str = Field(..., description="Nombre completo", example="María López")
    telefono: str = Field(..., description="Teléfono", example="3109876543")
    email: str = Field(..., description="Email", example="maria@example.com")
    direccion: str = Field(..., description="Dirección", example="Avenida 45 #12-34")
    probabilidad_retiro: float = Field(..., description="Probabilidad de retiro (0-100%)", example=78.5)
    nivel_riesgo: str = Field(..., description="Nivel de riesgo", example="ALTO")
    factores_principales: List[str] = Field(..., description="Factores que contribuyen al riesgo")
    recomendacion: str = Field(..., description="Acción recomendada")
    metricas_usuario: MetricasUsuario = Field(..., description="Métricas del usuario")


class UsuarioEnRiesgo(BaseModel):
    """Usuario en riesgo de churn (versión resumida para batch)."""
    usuario_id: int = Field(..., description="ID del usuario", example=1234)
    nombre_completo: str = Field(..., description="Nombre completo del usuario", example="Juan Pérez")
    telefono: str = Field(..., description="Teléfono de contacto", example="3001234567")
    email: str = Field(..., description="Email del usuario", example="juan@example.com")
    direccion: str = Field(..., description="Dirección del usuario", example="Calle 123 #45-67")
    probabilidad_retiro: float = Field(..., description="Probabilidad de retiro (%)", example=92.3)
    nivel_riesgo: str = Field(..., description="Nivel de riesgo", example="CRÍTICO")
    facturas_pendientes: int = Field(..., description="Facturas sin pagar", example=5)
    deuda_total: float = Field(..., description="Deuda total", example=250000.0)
    promedio_dias_pago: float = Field(..., description="Días promedio de pago", example=45.2)


class ResultadoBatch(BaseModel):
    """Resultado de predicción masiva."""
    total_en_riesgo: int = Field(..., description="Total de usuarios en riesgo encontrados", example=145)
    riesgo_minimo: float = Field(..., description="Umbral de riesgo aplicado (%)", example=70.0)
    usuarios: List[UsuarioEnRiesgo] = Field(..., description="Lista de usuarios en riesgo")


class ModeloActual(BaseModel):
    """Información del modelo actual en producción."""
    fecha_entrenamiento: str = Field(..., description="Fecha de entrenamiento")
    metricas: MetricasModelo = Field(..., description="Métricas del modelo")
    dataset: DatasetInfo = Field(..., description="Dataset usado")
    features_count: int = Field(..., description="Cantidad de features", example=34)


class ModeloDisponible(BaseModel):
    """Modelo disponible en el sistema."""
    model_name: str = Field(..., description="Nombre del modelo")
    saved_at: str = Field(..., description="Fecha de guardado")
    test_accuracy: float = Field(..., description="Precisión en test", example=0.9817)
    test_roc_auc: float = Field(..., description="ROC-AUC", example=0.9971)


class InfoModelo(BaseModel):
    """Información completa del modelo."""
    modelo_actual: ModeloActual = Field(..., description="Modelo en uso")
    modelos_disponibles: List[ModeloDisponible] = Field(..., description="Modelos guardados")
    features: List[str] = Field(..., description="Lista de features usadas")


class ListaModelos(BaseModel):
    """Lista de todos los modelos."""
    total_modelos: int = Field(..., description="Total de modelos guardados", example=3)
    modelos: List[ModeloDisponible] = Field(..., description="Lista de modelos")