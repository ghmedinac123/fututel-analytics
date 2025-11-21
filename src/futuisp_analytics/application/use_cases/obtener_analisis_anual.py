"""Caso de uso: Análisis histórico por año."""
from datetime import date
from collections import defaultdict

from futuisp_analytics.application.ports.factura_repository import FacturaRepository
from futuisp_analytics.domain.value_objects.periodo_pago import PeriodoPago


class ObtenerAnalisisAnual:
    """Caso de uso para análisis año completo mes a mes."""
    
    def __init__(self, factura_repo: FacturaRepository):
        self.factura_repo = factura_repo
    
    async def execute(self, año: int, zona_id: int | None = None) -> dict:
        """
        Ejecuta análisis mensual de todo el año.
        
        Args:
            año: Año a analizar (ej: 2024)
            zona_id: Filtrar por zona (opcional)
        """
        
        fecha_inicio = date(año, 1, 1)
        fecha_fin = date(año + 1, 1, 1)
        
        # Obtener todas las facturas del año
        analisis_list = await self.factura_repo.obtener_analisis_mes(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            zona_id=zona_id,
        )
        
        # Agrupar por mes
        metricas_mensuales = defaultdict(lambda: {
            "total_facturas": 0,
            "por_periodo": {periodo.value: 0 for periodo in PeriodoPago},
            "monto_total": 0.0,
        })
        
        for analisis in analisis_list:
            mes_key = analisis.fecha_emision.strftime("%Y-%m")
            metricas_mensuales[mes_key]["total_facturas"] += 1
            metricas_mensuales[mes_key]["por_periodo"][analisis.periodo_pago.value] += 1
            metricas_mensuales[mes_key]["monto_total"] += float(analisis.monto_pagado)
        
        # Calcular porcentajes por mes
        resultado_mensual = {}
        for mes, datos in sorted(metricas_mensuales.items()):
            total = datos["total_facturas"]
            resultado_mensual[mes] = {
                "total_facturas": total,
                "metricas": {},
                "monto_total": round(datos["monto_total"], 2),
            }
            
            for periodo in PeriodoPago:
                cantidad = datos["por_periodo"][periodo.value]
                resultado_mensual[mes]["metricas"][periodo.value] = {
                    "cantidad": cantidad,
                    "porcentaje": round((cantidad / total * 100), 2) if total > 0 else 0,
                }
        
        # Resumen anual
        total_año = sum(d["total_facturas"] for d in metricas_mensuales.values())
        resumen_anual = {periodo.value: 0 for periodo in PeriodoPago}
        for datos in metricas_mensuales.values():
            for periodo, cantidad in datos["por_periodo"].items():
                resumen_anual[periodo] += cantidad
        
        return {
            "año": año,
            "zona_id": zona_id,
            "resumen_anual": {
                "total_facturas": total_año,
                "por_periodo": {
                    k: {
                        "cantidad": v,
                        "porcentaje": round((v / total_año * 100), 2) if total_año > 0 else 0,
                    }
                    for k, v in resumen_anual.items()
                },
            },
            "metricas_mensuales": resultado_mensual,
        }
