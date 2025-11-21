# application/use_cases/obtener_ranking_global.py
"""Caso de uso: Obtener ranking global de usuarios con paginación."""
from datetime import date
from typing import Dict, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import polars as pl
from futuisp_analytics.domain.services.score_calculator import ScoreCalculator
from futuisp_analytics.infrastructure.config.settings import get_settings  # ✅ NUEVO IMPORT

class ObtenerRankingGlobal:
    """Obtiene ranking global de usuarios con filtros y paginación."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.settings = get_settings()  # ✅ NUEVO: Cargar config
    
    # ✅ CORRECCIÓN: Estos métodos van al nivel de la CLASE, no dentro de __init__
    async def execute(
        self,
        pagina: int = 1,
        por_pagina: int = 50,
        orden: str = "peor",
        buscar: str | None = None,
        nivel_riesgo: str | None = None,
        fecha_inicio: date | None = None,
        fecha_fin: date | None = None,
        sin_limite: bool = False,  # ✅ NUEVO PARÁMETRO
    ) -> Dict[str, Any]:
        """Ejecuta el caso de uso."""
        
        # Validaciones
        pagina = max(1, pagina)
    
        # ✅ SI sin_limite=True, no aplicar el límite de 100
        if sin_limite:
            # Para estadísticas globales, sin restricción
            pass  
        else:
            # Para paginación normal, límite de 100
            por_pagina = min(100, max(1, por_pagina))
        
        # ✅ Obtener contadores de facturas por categoría
        df_usuarios = await self._obtener_contadores_facturas(
            buscar=buscar,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
        )
        
        if df_usuarios.height == 0:
            return {
                "pagina": pagina,
                "por_pagina": por_pagina,
                "total_usuarios": 0,
                "total_paginas": 0,
                "orden": orden,
                "filtros": {},
                "usuarios": [],
            }
        
        # ✅ CALCULAR SCORES CON DOMAIN SERVICE
        df_usuarios = self._calcular_scores_polars(df_usuarios)
        
        # Filtrar por nivel de riesgo
        if nivel_riesgo:
            df_usuarios = df_usuarios.filter(
                pl.col("nivel_riesgo") == nivel_riesgo.upper()
            )
        
        # Ordenar
        df_usuarios = df_usuarios.sort(
            "score",
            descending=(orden == "mejor")
        )
        
        # Paginar
        total = df_usuarios.height
        inicio = (pagina - 1) * por_pagina
        df_pagina = df_usuarios.slice(inicio, por_pagina)
        
        # Convertir a lista de dicts
        usuarios_list = df_pagina.to_dicts()
        
        return {
            "pagina": pagina,
            "por_pagina": por_pagina,
            "total_usuarios": total,
            "total_paginas": (total + por_pagina - 1) // por_pagina,
            "orden": orden,
            "filtros": {
                "buscar": buscar,
                "nivel_riesgo": nivel_riesgo,
                "fecha_inicio": str(fecha_inicio) if fecha_inicio else None,
                "fecha_fin": str(fecha_fin) if fecha_fin else None,
            },
            "usuarios": usuarios_list,
        }
    
    async def _obtener_contadores_facturas(
        self,
        buscar: str | None,
        fecha_inicio: date | None,  # ⚠️ MANTENER PARÁMETRO (no se usa, pero mantener firma)
        fecha_fin: date | None,      # ⚠️ MANTENER PARÁMETRO (no se usa, pero mantener firma)
    ) -> pl.DataFrame:
        """
        ✅ CORREGIDO: Cuenta TODAS las facturas históricas sin filtro de fecha.
        El score se calcula sobre el historial completo del usuario.
        """
        
        filtros_sql = [
            "u.estado = 'ACTIVO'",
            "f.total > 0",
            "f.estado != 'Anulado'"
        ]
        params = {}
        
        if buscar:
            filtros_sql.append("(u.nombre LIKE :buscar OR u.cedula LIKE :buscar)")
            params["buscar"] = f"%{buscar}%"
        
        # ✅ NO FILTRAR POR FECHA - Score histórico requiere todas las facturas
        
        where_clause = " AND ".join(filtros_sql)

        umbral = self.settings.score_umbral_minimo_facturas  # ✅ AGREGAR ESTA LÍNEA
        
        # Query cuenta TODAS las facturas históricas por categoría
        query = text(f"""
            SELECT 
                u.id as usuario_id,
                u.nombre,
                u.cedula,
                u.telefono,
                u.movil,
                u.correo,
                u.direccion_principal as direccion,
                u.estado,
                COUNT(f.id) as total_facturas,
                
                -- OPTIMO: días 0-10
                SUM(CASE 
                    WHEN op.fecha_pago IS NOT NULL 
                    AND DATEDIFF(op.fecha_pago, f.emitido) BETWEEN 0 AND 10
                    THEN 1 ELSE 0 
                END) as facturas_optimas,
                
                -- ACEPTABLE: días 11 hasta corte
                SUM(CASE 
                    WHEN op.fecha_pago IS NOT NULL 
                    AND DATEDIFF(op.fecha_pago, f.emitido) BETWEEN 11 AND av.corteautomatico
                    THEN 1 ELSE 0 
                END) as facturas_aceptables,
                
                -- CRITICO: día corte+1 hasta 30
                SUM(CASE 
                    WHEN op.fecha_pago IS NOT NULL 
                    AND DATEDIFF(op.fecha_pago, f.emitido) > av.corteautomatico
                    AND DATEDIFF(op.fecha_pago, f.emitido) <= 30
                    THEN 1 ELSE 0 
                END) as facturas_criticas,
                
                -- ✅ PENDIENTE: sin pago O después de día 30 (CORREGIDO)
                SUM(CASE 
                    WHEN op.fecha_pago IS NULL THEN 1
                    WHEN DATEDIFF(op.fecha_pago, f.emitido) > 30 THEN 1
                    ELSE 0 
                END) as facturas_pendientes,
                
                -- Días mora promedio
                AVG(CASE 
                    WHEN op.fecha_pago IS NOT NULL 
                    AND DATEDIFF(op.fecha_pago, f.emitido) > av.corteautomatico
                    THEN DATEDIFF(op.fecha_pago, f.emitido) - av.corteautomatico
                    ELSE 0
                END) as dias_mora_promedio
                
            FROM usuarios u
            LEFT JOIN facturas f ON f.idcliente = u.id
            LEFT JOIN tblavisouser av ON av.cliente = u.id
            LEFT JOIN (
                SELECT nfactura, MIN(fecha_pago) as fecha_pago
                FROM operaciones
                WHERE cobrado > 0
                GROUP BY nfactura
            ) op ON op.nfactura = f.id
            WHERE {where_clause}
            GROUP BY u.id
            HAVING total_facturas >= :umbral  
        """)

        params["umbral"] = umbral
        
        result = await self.session.execute(query, params)
        rows = result.fetchall()
        columns = result.keys()
        
        if not rows:
            return pl.DataFrame()
        
        # Polars procesa 300k+ registros eficientemente
        df = pl.DataFrame(
            {col: [row[i] for row in rows] for i, col in enumerate(columns)}
        )
        
        df = df.with_columns([
            pl.col("cedula").fill_null("Sin cédula"),
            pl.when(pl.col("movil").is_not_null() & (pl.col("movil") != ""))
            .then(pl.col("movil"))
            .when(pl.col("telefono").is_not_null() & (pl.col("telefono") != ""))
            .then(pl.col("telefono"))
            .otherwise(pl.lit("Sin teléfono"))
            .alias("telefono"),
            pl.col("correo").fill_null("Sin correo"),
            pl.col("direccion").fill_null("Sin dirección"),
            pl.col("dias_mora_promedio").fill_null(0).round(1),
        ])
        
        return df
    
    def _calcular_scores_polars(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        ✅ Aplica la fórmula de scoring usando Domain Service.
        """
        
        # Convertir a lista para procesar
        rows = df.to_dicts()
        
        # Calcular scores
        for row in rows:
            row["score"] = ScoreCalculator.calcular_score(
                total_facturas=row["total_facturas"],
                facturas_optimas=row["facturas_optimas"],
                facturas_aceptables=row["facturas_aceptables"],
                facturas_criticas=row["facturas_criticas"],
                facturas_pendientes=row["facturas_pendientes"],
            )
            row["nivel_riesgo"] = ScoreCalculator.calcular_nivel_riesgo(
                row["score"],
                row["total_facturas"],
                self.settings.score_umbral_minimo_facturas  # ✅ AGREGAR ESTOS DOS PARÁMETROS
            )
            
            # ✅ MANTENER COMPATIBILIDAD CON CAMPOS ORIGINALES
            row["facturas_puntuales"] = row["facturas_optimas"]  # Día 1-10
            row["facturas_morosas"] = (
                row["facturas_aceptables"] + 
                row["facturas_criticas"] + 
                row["facturas_pendientes"]
            )  # Todo lo que NO es puntual
        
        # Recrear DataFrame
        df_result = pl.DataFrame(rows)
        
        # ✅ SELECCIONAR COLUMNAS ORIGINALES (NO CAMBIAR SALIDA)
        df_result = df_result.select([
            "usuario_id",
            "nombre",
            "cedula",
            "telefono",
            "correo",
            "direccion",
            "estado",
            "score",
            "nivel_riesgo",
            "total_facturas",
            "facturas_puntuales",   # ✅ CAMPO ORIGINAL
            "facturas_morosas",      # ✅ CAMPO ORIGINAL
            "dias_mora_promedio",
        ])
        
        return df_result
        
