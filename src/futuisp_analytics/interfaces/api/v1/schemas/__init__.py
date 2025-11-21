"""Schemas de la API v1."""
from futuisp_analytics.interfaces.api.v1.schemas.requests import MetricasMesRequest
from futuisp_analytics.interfaces.api.v1.schemas.responses import (
    MetricasMesResponse,
    MetricaPeriodoResponse,
    HealthResponse,
)

__all__ = [
    "MetricasMesRequest",
    "MetricasMesResponse",
    "MetricaPeriodoResponse",
    "HealthResponse",
]