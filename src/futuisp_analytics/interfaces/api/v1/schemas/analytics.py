"""Schemas Pydantic para endpoints de Analytics."""
from typing import List, Dict, Any, Optional
from datetime import date
from pydantic import BaseModel, Field


# ============================================================================
# SCHEMAS EXISTENTES (mantener compatibilidad)
# ============================================================================

class MetricasMesResponse(BaseModel):
    """Respuesta de métricas mensuales de comportamiento de pago."""
    periodo: str = Field(..., description="Período analizado", example="2024-10-01 a 2024-11-01")
    zona_id: Optional[int] = Field(None, description="ID de zona filtrada")
    total_facturas: int = Field(..., description="Total de facturas en el período")
    total_monto: float = Field(..., description="Monto total facturado")
    
    # Distribución por período de pago
    optimo: Dict[str, Any] = Field(..., description="Pagos óptimos (días 1-10)")
    aceptable: Dict[str, Any] = Field(..., description="Pagos aceptables (día 11-corte)")
    critico: Dict[str, Any] = Field(..., description="Pagos críticos (después de corte)")
    pendiente: Dict[str, Any] = Field(..., description="Facturas sin pagar")
    
    # Métricas generales
    score_promedio: float = Field(..., description="Score promedio de pago (0-100)", ge=0, le=100)
    dias_promedio_pago: float = Field(..., description="Días promedio para pagar")


# ============================================================================
# NUEVOS SCHEMAS PARA HISTORIAL DE USUARIO
# ============================================================================

class FacturaMes(BaseModel):
    """Factura individual dentro de un mes."""
    id: int = Field(..., description="ID de la factura")
    emitido: date = Field(..., description="Fecha de emisión")
    pago: Optional[date] = Field(None, description="Fecha de pago")
    total: float = Field(..., description="Monto total")
    estado: str = Field(..., description="Estado de la factura", example="Pagado")
    dias_pago: Optional[int] = Field(None, description="Días que tomó pagar")
    periodo: str = Field(..., description="Período de pago", example="OPTIMO")


class FacturasPorMes(BaseModel):
    """Facturas agrupadas por mes."""
    mes: str = Field(..., description="Mes (YYYY-MM)", example="2024-10")
    facturas: List[FacturaMes] = Field(..., description="Lista de facturas del mes")
    total_mes: float = Field(..., description="Total facturado en el mes")
    pagado_mes: float = Field(..., description="Total pagado en el mes")
    pendiente_mes: float = Field(..., description="Total pendiente en el mes")


class DistribucionPeriodo(BaseModel):
    """Distribución de facturas por período de pago."""
    optimo: int = Field(..., description="Cantidad en período óptimo")
    aceptable: int = Field(..., description="Cantidad en período aceptable")
    critico: int = Field(..., description="Cantidad en período crítico")
    pendiente: int = Field(..., description="Cantidad pendiente")


class HistorialUsuarioResponse(BaseModel):
    """Respuesta de historial completo de un usuario."""
    usuario_id: int = Field(..., description="ID del usuario")
    nombre_completo: str = Field(..., description="Nombre completo del usuario")
    
    # Score y nivel de riesgo
    score_general: float = Field(..., description="Score de comportamiento (0-100)", ge=0, le=100)
    nivel_riesgo: str = Field(..., description="Nivel de riesgo", example="BAJO")
    
    # Estadísticas generales
    total_facturas: int = Field(..., description="Total de facturas")
    total_facturado: float = Field(..., description="Total facturado")
    total_pagado: float = Field(..., description="Total pagado")
    total_pendiente: float = Field(..., description="Total pendiente")
    dias_promedio_pago: float = Field(..., description="Días promedio para pagar")
    
    # Distribución
    distribucion: DistribucionPeriodo = Field(..., description="Distribución por período")
    
    # Facturas por mes
    facturas_por_mes: List[FacturasPorMes] = Field(..., description="Facturas agrupadas por mes")


# ============================================================================
# SCHEMAS PARA ANÁLISIS ANUAL
# ============================================================================

class MetricasMensuales(BaseModel):
    """Métricas de un mes específico."""
    mes: str = Field(..., description="Mes (YYYY-MM)", example="2024-10")
    total_facturas: int = Field(..., description="Total de facturas")
    total_monto: float = Field(..., description="Monto total")
    score_promedio: float = Field(..., description="Score promedio", ge=0, le=100)
    dias_promedio_pago: float = Field(..., description="Días promedio de pago")
    
    # Distribución del mes
    optimo_count: int = Field(..., description="Facturas en período óptimo")
    aceptable_count: int = Field(..., description="Facturas en período aceptable")
    critico_count: int = Field(..., description="Facturas en período crítico")
    pendiente_count: int = Field(..., description="Facturas pendientes")


class ResumenAnual(BaseModel):
    """Resumen consolidado del año."""
    año: int = Field(..., description="Año analizado")
    zona_id: Optional[int] = Field(None, description="Zona filtrada")
    
    total_facturas_año: int = Field(..., description="Total facturas del año")
    total_monto_año: float = Field(..., description="Total facturado en el año")
    score_promedio_año: float = Field(..., description="Score promedio anual", ge=0, le=100)
    dias_promedio_pago_año: float = Field(..., description="Días promedio de pago anual")
    
    # Mejor y peor mes
    mejor_mes: str = Field(..., description="Mes con mejor score")
    mejor_mes_score: float = Field(..., description="Score del mejor mes")
    peor_mes: str = Field(..., description="Mes con peor score")
    peor_mes_score: float = Field(..., description="Score del peor mes")


class TendenciaPeriodo(BaseModel):
    """Tendencia de un período específico a lo largo del año."""
    periodo: str = Field(..., description="Nombre del período", example="OPTIMO")
    porcentaje_promedio: float = Field(..., description="Porcentaje promedio", ge=0, le=100)
    tendencia: str = Field(..., description="Dirección de la tendencia", example="CRECIENTE")


class AnalisisAnualResponse(BaseModel):
    """Respuesta de análisis anual completo."""
    resumen: ResumenAnual = Field(..., description="Resumen del año")
    metricas_mensuales: List[MetricasMensuales] = Field(..., description="Métricas mes a mes")
    tendencias: List[TendenciaPeriodo] = Field(..., description="Tendencias por período")


# ============================================================================
# SCHEMAS PARA TOP USUARIOS
# ============================================================================

class UsuarioScore(BaseModel):
    """Usuario con su score de comportamiento."""
    usuario_id: int = Field(..., description="ID del usuario")
    nombre_completo: str = Field(..., description="Nombre completo")
    telefono: Optional[str] = Field(None, description="Teléfono de contacto")
    email: Optional[str] = Field(None, description="Email")
    
    # Métricas de comportamiento
    score: float = Field(..., description="Score de comportamiento (0-100)", ge=0, le=100)
    nivel_riesgo: str = Field(..., description="Nivel de riesgo", example="BAJO")
    total_facturas: int = Field(..., description="Total de facturas")
    total_pagado: float = Field(..., description="Total pagado")
    dias_promedio_pago: float = Field(..., description="Días promedio para pagar")
    
    # Distribución
    pagos_optimos: int = Field(..., description="Cantidad de pagos óptimos")
    pagos_aceptables: int = Field(..., description="Cantidad de pagos aceptables")
    pagos_criticos: int = Field(..., description="Cantidad de pagos críticos")
    facturas_pendientes: int = Field(..., description="Facturas sin pagar")


class TopUsuariosResponse(BaseModel):
    """Respuesta de ranking de usuarios."""
    periodo: str = Field(..., description="Período analizado", example="2024-10-01 a 2024-11-01")
    orden: str = Field(..., description="Tipo de ordenamiento", example="mejor")
    total_usuarios: int = Field(..., description="Total de usuarios en el ranking")
    usuarios: List[UsuarioScore] = Field(..., description="Lista de usuarios ordenados")


# ============================================================================
# SCHEMAS PARA LIMPIEZA DE CACHE
# ============================================================================

class CacheClearResponse(BaseModel):
    """Respuesta de limpieza de cache."""
    message: str = Field(..., description="Mensaje de confirmación")
    keys_deleted: int = Field(..., description="Cantidad de keys eliminadas", ge=0)