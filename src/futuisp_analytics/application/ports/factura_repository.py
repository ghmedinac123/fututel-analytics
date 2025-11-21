"""Puerto (interfaz) para repositorio de facturas."""
from abc import ABC, abstractmethod
from datetime import date

from futuisp_analytics.domain.entities.analisis_pago import AnalisisPago


class FacturaRepository(ABC):
    """Interfaz para repositorio de facturas."""
    
    @abstractmethod
    async def obtener_analisis_mes(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        zona_id: int | None = None,
    ) -> list[AnalisisPago]:
        """Obtiene análisis de pagos de un período."""
        pass
    
    @abstractmethod
    async def obtener_metricas_agregadas(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        zona_id: int | None = None,
    ) -> dict:
        """Obtiene métricas agregadas por período."""
        pass
    
    @abstractmethod
    async def obtener_analisis_usuario(
        self,
        usuario_id: int,
        fecha_inicio: date | None = None,
        fecha_fin: date | None = None,
    ) -> list[AnalisisPago]:
        """Obtiene historial de análisis de un usuario específico."""
        pass
    
    @abstractmethod
    async def obtener_top_usuarios(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        limite: int = 100,
        orden: str = "mejor",
    ) -> list[dict]:
        """Obtiene ranking de usuarios por score."""
        pass
