"""Schemas de request."""
from datetime import date
from pydantic import BaseModel, Field


class MetricasMesRequest(BaseModel):
    """Request para obtener métricas del mes."""
    
    fecha_inicio: date = Field(
        ...,
        description="Fecha de inicio del período (YYYY-MM-DD)",
        example="2024-10-01"
    )
    fecha_fin: date = Field(
        ...,
        description="Fecha fin del período (YYYY-MM-DD)",
        example="2024-11-01"
    )
    zona_id: int | None = Field(
        None,
        description="ID de zona para filtrar (opcional)",
        example=1
    )