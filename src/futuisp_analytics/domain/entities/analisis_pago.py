"""Entidad de análisis de pago."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from futuisp_analytics.domain.value_objects.periodo_pago import PeriodoPago


@dataclass(frozen=True)
class AnalisisPago:
    """Entidad que representa el análisis de un pago."""
    
    factura_id: int
    cliente_id: int
    cliente_nombre: str
    fecha_emision: date
    dia_corte: int
    fecha_corte_real: date
    fecha_primer_pago: date | None
    estado_factura: str
    monto_total: Decimal
    monto_pagado: Decimal
    periodo_pago: PeriodoPago
    dias_hasta_pago: int | None
    zona: int
    operador_id: int | None
    
    @property
    def esta_pagado(self) -> bool:
        """Verifica si la factura está pagada."""
        return self.estado_factura == "Pagado"
    
    @property
    def esta_en_mora(self) -> bool:
        """Verifica si está en mora."""
        return self.periodo_pago in (PeriodoPago.CRITICO, PeriodoPago.PENDIENTE)
    
    @property
    def porcentaje_cobrado(self) -> float:
        """Porcentaje cobrado del total."""
        if self.monto_total == 0:
            return 0.0
        return float((self.monto_pagado / self.monto_total) * 100)