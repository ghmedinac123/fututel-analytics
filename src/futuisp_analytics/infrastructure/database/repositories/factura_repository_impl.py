"""Implementación del repositorio de facturas."""
from datetime import date, datetime, timedelta
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from futuisp_analytics.application.ports.factura_repository import FacturaRepository
from futuisp_analytics.domain.entities.analisis_pago import AnalisisPago
from futuisp_analytics.domain.value_objects.periodo_pago import PeriodoPago
from futuisp_analytics.domain.value_objects.score_cliente import ScoreCliente
from futuisp_analytics.infrastructure.database.models import (
    Factura,
    Usuario,
    TblAvisoUser,
    Operacion,
)
from futuisp_analytics.domain.services.periodo_clasificador import PeriodoClasificador

class FacturaRepositoryImpl(FacturaRepository):
    """Implementación de repositorio de facturas."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def obtener_analisis_mes(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        zona_id: int | None = None,
    ) -> list[AnalisisPago]:
        """Obtiene análisis detallado de pagos."""
        
        subq_operaciones = (
            select(
                Operacion.nfactura,
                func.min(Operacion.fecha_pago).label("fecha_primer_pago"),
                func.sum(Operacion.cobrado).label("total_cobrado"),
                func.min(Operacion.operador).label("operador_id"),
            )
            .where(Operacion.cobrado > 0)
            .group_by(Operacion.nfactura)
            .subquery()
        )
        
        query = (
            select(
                Factura.id,
                Factura.idcliente,
                Usuario.nombre,
                Factura.emitido,
                TblAvisoUser.corteautomatico,
                subq_operaciones.c.fecha_primer_pago,
                Factura.estado,
                Factura.total,
                func.coalesce(subq_operaciones.c.total_cobrado, 0).label("total_pagado"),
                TblAvisoUser.zona,
                subq_operaciones.c.operador_id,
            )
            .join(Usuario, Factura.idcliente == Usuario.id)
            .join(TblAvisoUser, TblAvisoUser.cliente == Usuario.id)
            .outerjoin(subq_operaciones, subq_operaciones.c.nfactura == Factura.id)
            .where(
                and_(
                    Factura.emitido >= fecha_inicio,
                    Factura.emitido < fecha_fin,
                    Factura.estado != "Anulado",
                    Usuario.estado == "ACTIVO",
                    Factura.total > 0,  # ✅ EXCLUIR FACTURAS EN $0
                )
            )
        )
        
        if zona_id is not None:
            query = query.where(TblAvisoUser.zona == zona_id)
        
        result = await self.session.execute(query)
        rows = result.all()
        
        analisis_list = []
        for row in rows:
            fecha_corte_real = row.emitido + timedelta(days=row.corteautomatico)
            
            periodo = PeriodoClasificador.clasificar(
                row.estado,
                row.fecha_primer_pago,
                row.emitido,
                row.corteautomatico,
            )
            
            dias_hasta_pago = None
            fecha_pago_date = None
            if row.fecha_primer_pago:
                fecha_pago_date = row.fecha_primer_pago.date() if isinstance(row.fecha_primer_pago, datetime) else row.fecha_primer_pago
                dias_hasta_pago = (fecha_pago_date - row.emitido).days
            
            analisis = AnalisisPago(
                factura_id=row.id,
                cliente_id=row.idcliente,
                cliente_nombre=row.nombre,
                fecha_emision=row.emitido,
                dia_corte=row.corteautomatico,
                fecha_corte_real=fecha_corte_real,
                fecha_primer_pago=fecha_pago_date,
                estado_factura=row.estado,
                monto_total=row.total,
                monto_pagado=row.total_pagado,
                periodo_pago=periodo,
                dias_hasta_pago=dias_hasta_pago,
                zona=row.zona,
                operador_id=row.operador_id,
            )
            analisis_list.append(analisis)
        
        return analisis_list
    
    async def obtener_metricas_agregadas(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        zona_id: int | None = None,
    ) -> dict:
        """Obtiene métricas agregadas por período de pago."""
        
        analisis_list = await self.obtener_analisis_mes(fecha_inicio, fecha_fin, zona_id)
        
        metricas_por_periodo = {}
        total_facturas = len(analisis_list)
        
        for periodo in PeriodoPago:
            facturas_periodo = [a for a in analisis_list if a.periodo_pago == periodo]
            cantidad = len(facturas_periodo)
            monto_total = sum(a.monto_pagado for a in facturas_periodo)
            
            dias_pago = [a.dias_hasta_pago for a in facturas_periodo if a.dias_hasta_pago is not None]
            promedio_dias = sum(dias_pago) / len(dias_pago) if dias_pago else None
            
            metricas_por_periodo[periodo.value] = {
                "cantidad_usuarios": cantidad,
                "monto_total": float(monto_total),
                "porcentaje": round((cantidad / total_facturas * 100), 2) if total_facturas > 0 else 0,
                "dias_promedio_pago": round(promedio_dias, 1) if promedio_dias else None,
                "rendimiento": periodo.porcentaje_rendimiento,
            }
        
        return {
            "periodo": f"{fecha_inicio.strftime('%Y-%m')}",
            "total_facturas": total_facturas,
            "metricas": metricas_por_periodo,
        }
    
    async def obtener_analisis_usuario(
        self,
        usuario_id: int,
        fecha_inicio: date | None = None,  # Mantener firma pero no usar
        fecha_fin: date | None = None,      # Mantener firma pero no usar
    ) -> list[AnalisisPago]:
        """Obtiene historial completo de un usuario."""
        
        subq_operaciones = (
            select(
                Operacion.nfactura,
                func.min(Operacion.fecha_pago).label("fecha_primer_pago"),
                func.sum(Operacion.cobrado).label("total_cobrado"),
                func.min(Operacion.operador).label("operador_id"),
            )
            .where(Operacion.cobrado > 0)
            .group_by(Operacion.nfactura)
            .subquery()
        )
        
        query = (
            select(
                Factura.id,
                Factura.idcliente,
                Usuario.nombre,
                Factura.emitido,
                TblAvisoUser.corteautomatico,
                subq_operaciones.c.fecha_primer_pago,
                Factura.estado,
                Factura.total,
                func.coalesce(subq_operaciones.c.total_cobrado, 0).label("total_pagado"),
                TblAvisoUser.zona,
                subq_operaciones.c.operador_id,
            )
            .join(Usuario, Factura.idcliente == Usuario.id)
            .join(TblAvisoUser, TblAvisoUser.cliente == Usuario.id)
            .outerjoin(subq_operaciones, subq_operaciones.c.nfactura == Factura.id)
            .where(Factura.idcliente == usuario_id)
            .where(Factura.estado != "Anulado")
            .where(Factura.total > 0)
        )
        
        # ✅ SIN FILTROS DE FECHA - Todas las facturas históricas
        
        query = query.order_by(Factura.emitido.desc())
        
        result = await self.session.execute(query)
        rows = result.all()
        
        analisis_list = []
        for row in rows:
            fecha_corte_real = row.emitido + timedelta(days=row.corteautomatico)
            periodo = PeriodoClasificador.clasificar(
                row.estado, row.fecha_primer_pago, row.emitido, row.corteautomatico
            )
            
            dias_hasta_pago = None
            fecha_pago_date = None
            if row.fecha_primer_pago:
                fecha_pago_date = (
                    row.fecha_primer_pago.date()
                    if isinstance(row.fecha_primer_pago, datetime)
                    else row.fecha_primer_pago
                )
                dias_hasta_pago = (fecha_pago_date - row.emitido).days
            
            analisis = AnalisisPago(
                factura_id=row.id,
                cliente_id=row.idcliente,
                cliente_nombre=row.nombre,
                fecha_emision=row.emitido,
                dia_corte=row.corteautomatico,
                fecha_corte_real=fecha_corte_real,
                fecha_primer_pago=fecha_pago_date,
                estado_factura=row.estado,
                monto_total=row.total,
                monto_pagado=row.total_pagado,
                periodo_pago=periodo,
                dias_hasta_pago=dias_hasta_pago,
                zona=row.zona,
                operador_id=row.operador_id,
            )
            analisis_list.append(analisis)
        
        return analisis_list

    async def obtener_top_usuarios(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        limite: int = 100,
        orden: str = "mejor",
    ) -> list[dict]:
        """Obtiene ranking de usuarios por score."""
        
        analisis_list = await self.obtener_analisis_mes(fecha_inicio, fecha_fin)
        
        usuarios_scores = {}
        for analisis in analisis_list:
            uid = analisis.cliente_id
            if uid not in usuarios_scores:
                usuarios_scores[uid] = {
                    "usuario_id": uid,
                    "nombre": analisis.cliente_nombre,
                    "zona": analisis.zona,
                    "total_facturas": 0,
                    "optimas": 0,
                    "aceptables": 0,
                    "criticas": 0,
                    "pendientes": 0,
                }
            
            usuarios_scores[uid]["total_facturas"] += 1
            if analisis.periodo_pago == PeriodoPago.OPTIMO:
                usuarios_scores[uid]["optimas"] += 1
            elif analisis.periodo_pago == PeriodoPago.ACEPTABLE:
                usuarios_scores[uid]["aceptables"] += 1
            elif analisis.periodo_pago == PeriodoPago.CRITICO:
                usuarios_scores[uid]["criticas"] += 1
            else:
                usuarios_scores[uid]["pendientes"] += 1
        
        resultado = []
        for datos in usuarios_scores.values():
            score_obj = ScoreCliente(
                total_facturas=datos["total_facturas"],
                facturas_optimas=datos["optimas"],
                facturas_aceptables=datos["aceptables"],
                facturas_criticas=datos["criticas"],
                facturas_pendientes=datos["pendientes"],
            )
            
            resultado.append({
                **datos,
                "score": score_obj.score_total,
                "nivel_riesgo": score_obj.nivel_riesgo,
                "porcentaje_puntualidad": score_obj.porcentaje_puntualidad,
            })
        
        reverse = orden == "mejor"
        resultado_ordenado = sorted(resultado, key=lambda x: x["score"], reverse=reverse)
        
        return resultado_ordenado[:limite]
    
