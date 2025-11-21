"""Schemas de response."""
from decimal import Decimal
from pydantic import BaseModel, Field


class MetricaPeriodoResponse(BaseModel):
    """Métrica de un período específico."""
    
    cantidad_usuarios: int = Field(..., description="Cantidad de usuarios")
    monto_total: float = Field(..., description="Monto total cobrado")
    porcentaje: float = Field(..., description="Porcentaje del total")
    dias_promedio_pago: float | None = Field(None, description="Días promedio hasta el pago")
    rendimiento: int = Field(..., description="Porcentaje de rendimiento (0-100)")


class MetricasMesResponse(BaseModel):
    """Response de métricas mensuales."""
    
    periodo: str = Field(..., description="Período analizado (YYYY-MM)", example="2024-10")
    total_facturas: int = Field(..., description="Total de facturas analizadas")
    metricas: dict[str, MetricaPeriodoResponse] = Field(
        ...,
        description="Métricas por cada período de pago"
    )


class HealthResponse(BaseModel):
    """Response del health check."""
    
    status: str = Field(..., example="healthy")
    service: str = Field(..., example="FUTUISP Analytics")
    version: str = Field(..., example="0.1.0")
    database: str = Field(..., example="connected")
    redis: str = Field(..., example="connected")