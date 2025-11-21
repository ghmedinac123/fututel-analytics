"""Value Object para períodos de pago."""
from enum import Enum


class PeriodoPago(str, Enum):
    """Clasificación de períodos de pago."""
    
    OPTIMO = "OPTIMO"  # Pago días 1-10
    ACEPTABLE = "ACEPTABLE"  # Pago días 11 hasta corte
    CRITICO = "CRITICO"  # Pago después del corte
    PENDIENTE = "PENDIENTE"  # Sin pago aún
    SIN_PAGO = "SIN_PAGO"  # Sin registro de pago
    
    @property
    def descripcion(self) -> str:
        """Descripción del período."""
        descripciones = {
            self.OPTIMO: "Pago puntual (días 1-10)",
            self.ACEPTABLE: "Pago antes del corte",
            self.CRITICO: "Pago tardío o suspendido",
            self.PENDIENTE: "Factura no pagada",
            self.SIN_PAGO: "Sin registro de pago",
        }
        return descripciones[self]
    
    @property
    def porcentaje_rendimiento(self) -> int:
        """Porcentaje de rendimiento asociado."""
        porcentajes = {
            self.OPTIMO: 100,
            self.ACEPTABLE: 75,
            self.CRITICO: 40,
            self.PENDIENTE: 0,
            self.SIN_PAGO: 0,
        }
        return porcentajes[self]