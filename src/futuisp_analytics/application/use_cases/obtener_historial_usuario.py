"""Caso de uso: Obtener historial completo de usuario."""
from futuisp_analytics.application.ports.factura_repository import FacturaRepository
from futuisp_analytics.domain.value_objects.score_cliente import ScoreCliente
from futuisp_analytics.domain.value_objects.periodo_pago import PeriodoPago
from futuisp_analytics.infrastructure.config.settings import get_settings  # ✅ NUEVO IMPORT

class ObtenerHistorialUsuario:
    """Caso de uso para análisis individual de usuario."""
    
    def __init__(self, factura_repo: FacturaRepository):
        self.factura_repo = factura_repo
        self.settings = get_settings()  # ✅ NUEVO
    
    async def execute(self, usuario_id: int) -> dict:
        """
        ✅ CORREGIDO: Analiza TODAS las facturas históricas del usuario.
        El score refleja el comportamiento histórico completo.
        """
        
        # ✅ SIN FILTROS DE FECHA - Traer TODO el historial
        analisis_list = await self.factura_repo.obtener_analisis_usuario(
            usuario_id=usuario_id,
            fecha_inicio=None,  # ✅ Siempre None
            fecha_fin=None,     # ✅ Siempre None
        )
        
        if not analisis_list:
            return {
                "usuario_id": usuario_id,
                "mensaje": "No se encontraron facturas para este usuario",
                "score": None,
            }
        
        # Contar por período
        contadores = {periodo: 0 for periodo in PeriodoPago}
        for analisis in analisis_list:
            contadores[analisis.periodo_pago] += 1
        
        # Calcular score sobre TODAS las facturas
        score = ScoreCliente(
            total_facturas=len(analisis_list),
            facturas_optimas=contadores[PeriodoPago.OPTIMO],
            facturas_aceptables=contadores[PeriodoPago.ACEPTABLE],
            facturas_criticas=contadores[PeriodoPago.CRITICO],
            facturas_pendientes=contadores[PeriodoPago.PENDIENTE],
            umbral_minimo=self.settings.score_umbral_minimo_facturas  # ✅ NUEVO PARÁMETRO
        )
        
        # Agrupar por mes para visualización
        facturas_por_mes = {}
        for analisis in analisis_list:
            mes_key = analisis.fecha_emision.strftime("%Y-%m")
            if mes_key not in facturas_por_mes:
                facturas_por_mes[mes_key] = []
            facturas_por_mes[mes_key].append({
                "factura_id": analisis.factura_id,
                "fecha_emision": str(analisis.fecha_emision),
                "monto_total": float(analisis.monto_total),
                "monto_pagado": float(analisis.monto_pagado),
                "periodo_pago": analisis.periodo_pago.value,
                "dias_hasta_pago": analisis.dias_hasta_pago,
            })
        
        return {
            "usuario_id": usuario_id,
            "cliente_nombre": analisis_list[0].cliente_nombre,
            "periodo_analizado": "Historial completo",  # ✅ Sin fechas
            "score": {
                "total": score.score_total,
                "nivel_riesgo": score.nivel_riesgo,
                "porcentaje_puntualidad": score.porcentaje_puntualidad,
            },
            "resumen": {
                "total_facturas": score.total_facturas,
                "por_periodo": {
                    "OPTIMO": contadores[PeriodoPago.OPTIMO],
                    "ACEPTABLE": contadores[PeriodoPago.ACEPTABLE],
                    "CRITICO": contadores[PeriodoPago.CRITICO],
                    "PENDIENTE": contadores[PeriodoPago.PENDIENTE],
                },
            },
            "facturas_por_mes": facturas_por_mes,
        }