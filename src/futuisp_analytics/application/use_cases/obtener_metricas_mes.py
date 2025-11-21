"""Caso de uso: Obtener métricas del mes."""
from datetime import date

from futuisp_analytics.application.ports.factura_repository import FacturaRepository


class ObtenerMetricasMes:
    """Caso de uso para obtener métricas mensuales."""
    
    def __init__(self, factura_repo: FacturaRepository):
        self.factura_repo = factura_repo
    
    async def execute(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        zona_id: int | None = None,
    ) -> dict:
        """Ejecuta el caso de uso."""
        
        metricas = await self.factura_repo.obtener_metricas_agregadas(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            zona_id=zona_id,
        )
        
        return metricas