"""Servicio de dominio para clasificación de períodos de pago."""
from datetime import date, datetime

from futuisp_analytics.domain.value_objects.periodo_pago import PeriodoPago


class PeriodoClasificador:
    """
    Servicio de dominio que encapsula la lógica de clasificación de períodos.
    
    Reglas de negocio:
    - OPTIMO: Pago días 1-10 desde emisión
    - ACEPTABLE: Pago días 11 hasta día de corte
    - CRITICO: Pago después de corte hasta día 30
    - PENDIENTE: Sin pago o después de día 30
    """
    
    @staticmethod
    def clasificar(
        estado_factura: str,
        fecha_pago: date | datetime | None,
        fecha_emision: date,
        dia_corte: int,
    ) -> PeriodoPago:
        """
        Clasifica el período de pago según reglas de negocio.
        
        Args:
            estado_factura: Estado de la factura ("Pagado", "No pagado", etc.)
            fecha_pago: Fecha en que se realizó el pago (puede ser None)
            fecha_emision: Fecha de emisión de la factura
            dia_corte: Día límite de corte para el cliente
            
        Returns:
            PeriodoPago correspondiente según la clasificación
        """
        
        # Sin registro de pago
        if fecha_pago is None:
            if estado_factura == "No pagado":
                return PeriodoPago.PENDIENTE
            return PeriodoPago.SIN_PAGO
        
        # Normalizar fecha_pago a date si es datetime
        if isinstance(fecha_pago, datetime):
            fecha_pago = fecha_pago.date()
        
        # Calcular días transcurridos desde emisión
        dias_transcurridos = (fecha_pago - fecha_emision).days
        
        # Aplicar reglas de clasificación
        if 0 <= dias_transcurridos <= 10:
            return PeriodoPago.OPTIMO
        elif 11 <= dias_transcurridos <= dia_corte:
            return PeriodoPago.ACEPTABLE
        elif dia_corte < dias_transcurridos <= 30:
            return PeriodoPago.CRITICO
        else:
            # Después del día 30 = mora crítica = PENDIENTE
            return PeriodoPago.PENDIENTE