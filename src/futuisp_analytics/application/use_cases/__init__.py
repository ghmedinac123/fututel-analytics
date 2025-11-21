"""Casos de uso de la aplicación."""
from futuisp_analytics.application.use_cases.obtener_metricas_mes import ObtenerMetricasMes
from futuisp_analytics.application.use_cases.obtener_historial_usuario import ObtenerHistorialUsuario
from futuisp_analytics.application.use_cases.obtener_analisis_anual import ObtenerAnalisisAnual

__all__ = ["ObtenerMetricasMes", "ObtenerHistorialUsuario", "ObtenerAnalisisAnual"]
