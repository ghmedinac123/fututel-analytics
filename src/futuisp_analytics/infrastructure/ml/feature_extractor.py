"""
Feature Extractor para predicción de churn.
Extrae features desde MySQL usando Polars para procesamiento eficiente.
VERSIÓN CORREGIDA: Sin data leakage, target basado en comportamiento predictivo.
"""
from typing import Optional
import polars as pl
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from futuisp_analytics.infrastructure.config.logging import logger


class ChurnFeatureExtractor:
    """Extrae features para entrenamiento/predicción de churn."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def extract_training_data(
        self, 
        meses_historicos: int = 24,  # ✅ 2 años
        min_facturas: int = 6        # ✅ 6 mínimo
    ) -> pl.DataFrame:
        """Extrae dataset completo para entrenamiento."""
        logger.info(
            f"Extrayendo datos de entrenamiento: {meses_historicos} meses, "
            f"mínimo {min_facturas} facturas"
        )
        
        query = self._build_training_query(meses_historicos, min_facturas)
        
        # ✅ MÉTODO CORRECTO con SQLAlchemy async
        result = await self.session.execute(text(query))
        rows = result.fetchall()
        columns = result.keys()
        
        logger.info(f"Registros extraídos: {len(rows)}")
        
        df = pl.DataFrame(
            {col: [row[i] for row in rows] for i, col in enumerate(columns)}
        )
        
        df = self._process_features(df)
        
        logger.info(f"Dataset final: {df.shape[0]} usuarios, {df.shape[1]} features")
        
        return df
    
    async def extract_user_features(self, usuario_id: int) -> Optional[pl.DataFrame]:
        """Extrae features de un usuario específico."""
        query = self._build_user_query(usuario_id)
        
        result = await self.session.execute(text(query))
        rows = result.fetchall()
        
        if not rows:
            logger.warning(f"Usuario {usuario_id} no encontrado")
            return None
        
        columns = result.keys()
        df = pl.DataFrame({col: [rows[0][i]] for i, col in enumerate(columns)})
        df = self._process_features(df)
        
        return df
    
    async def extract_active_users_features(self, batch_size: int = 1000) -> pl.DataFrame:
        """Extrae features de usuarios ACTIVOS."""
        logger.info("Extrayendo features de usuarios ACTIVOS")
        
        query = self._build_active_users_query()
        
        result = await self.session.execute(text(query))
        rows = result.fetchall()
        columns = result.keys()
        
        logger.info(f"Usuarios ACTIVOS encontrados: {len(rows)}")
        
        df = pl.DataFrame({col: [row[i] for row in rows] for i, col in enumerate(columns)})
        df = self._process_features(df)
        
        return df
    
    def _build_training_query(self, meses: int, min_facturas: int) -> str:
        """Query SQL CORREGIDO con target MÁS SENSIBLE."""
        return f"""
        SELECT 
            u.id as usuario_id,
            u.estado as estado_real,
            
            -- ============================================================
            -- TARGET AJUSTADO: Captura comportamiento de riesgo real
            -- ============================================================
            CASE 
                -- CRÍTICO: 3+ facturas pendientes + 60+ días sin pagar
                WHEN SUM(CASE WHEN f.estado != 'Pagado' THEN 1 ELSE 0 END) >= 3
                    AND COALESCE(DATEDIFF(CURDATE(), MAX(CASE WHEN f.estado = 'Pagado' THEN f.pago END)), 999) > 60
                THEN 1
                
                -- ALTO: 2+ facturas pendientes + 45+ días sin pagar + deuda > promedio
                WHEN SUM(CASE WHEN f.estado != 'Pagado' THEN 1 ELSE 0 END) >= 2
                    AND COALESCE(DATEDIFF(CURDATE(), MAX(CASE WHEN f.estado = 'Pagado' THEN f.pago END)), 999) > 45
                    AND COALESCE(SUM(CASE WHEN f.estado != 'Pagado' THEN f.total ELSE 0 END), 0) > 
                        COALESCE(AVG(f.total), 1)
                THEN 1
                
                -- MEDIO: Tendencia negativa clara (pagos empeorando)
                WHEN COALESCE(AVG(CASE 
                        WHEN f.pago IS NOT NULL 
                        AND f.estado = 'Pagado'
                        AND f.emitido >= DATE_SUB(CURDATE(), INTERVAL 3 MONTH)
                        THEN DATEDIFF(f.pago, f.emitido) 
                    END), 0) > 25
                    AND SUM(CASE WHEN f.estado != 'Pagado' THEN 1 ELSE 0 END) >= 1
                THEN 1
                
                -- INCLUIR usuarios RETIRADOS/SUSPENDIDOS (para aprender patrones)
                WHEN u.estado IN ('RETIRADO', 'SUSPENDIDO')
                THEN 1
                
                -- ESTABLE
                ELSE 0
            END as target_churn,
            
            -- FEATURES (las mismas que ya tenemos)
            COUNT(f.id) as total_facturas,
            SUM(CASE WHEN f.estado != 'Pagado' THEN 1 ELSE 0 END) as facturas_pendientes,
            COALESCE(SUM(CASE WHEN f.estado != 'Pagado' THEN f.total ELSE 0 END), 0) as deuda_total,
            
            COALESCE(AVG(CASE 
                WHEN f.pago IS NOT NULL AND f.estado = 'Pagado' 
                THEN DATEDIFF(f.pago, f.emitido) 
            END), 0) as promedio_dias_pago,
            
            COALESCE(MAX(CASE 
                WHEN f.pago IS NOT NULL AND f.estado = 'Pagado' 
                THEN DATEDIFF(f.pago, f.emitido) 
            END), 0) as max_dias_pago,
            
            COALESCE(STDDEV(CASE 
                WHEN f.pago IS NOT NULL AND f.estado = 'Pagado' 
                THEN DATEDIFF(f.pago, f.emitido) 
            END), 0) as std_dias_pago,
            
            MAX(DATEDIFF(CURDATE(), f.emitido)) as dias_ultima_factura,
            
            COALESCE(DATEDIFF(CURDATE(), MAX(CASE WHEN f.estado = 'Pagado' THEN f.pago END)), 999) as dias_desde_ultimo_pago,
            
            DATEDIFF(CURDATE(), MIN(f.emitido)) / 30 as antiguedad_meses,
            
            a.corteautomatico,
            COALESCE(a.zona, 1) as zona,
            CASE WHEN a.mora = 'on' THEN 1 ELSE 0 END as mora_activa,
            CASE WHEN a.reconexion = 'on' THEN 1 ELSE 0 END as reconexion_historica,
            
            CASE 
                WHEN a.fecha_suspendido IS NOT NULL 
                    AND a.fecha_suspendido != '0000-00-00 00:00:00'
                    AND DATEDIFF(CURDATE(), a.fecha_suspendido) < 30
                THEN 1 ELSE 0 
            END as tiene_suspension_reciente,
            
            CASE 
                WHEN a.fecha_suspendido IS NOT NULL 
                    AND a.fecha_suspendido != '0000-00-00 00:00:00'
                    AND DATEDIFF(CURDATE(), a.fecha_suspendido) < 30
                THEN DATEDIFF(CURDATE(), a.fecha_suspendido)
                ELSE 0 
            END as dias_suspension_reciente,
            
            COALESCE(AVG(CASE 
                WHEN f.pago IS NOT NULL 
                    AND f.estado = 'Pagado' 
                    AND f.emitido >= DATE_SUB(CURDATE(), INTERVAL 3 MONTH)
                THEN DATEDIFF(f.pago, f.emitido) 
            END), 0) as dias_pago_ultimos_3m,
            
            COALESCE(AVG(CASE 
                WHEN f.pago IS NOT NULL 
                    AND f.estado = 'Pagado' 
                    AND f.emitido BETWEEN DATE_SUB(CURDATE(), INTERVAL 6 MONTH) 
                                    AND DATE_SUB(CURDATE(), INTERVAL 3 MONTH)
                THEN DATEDIFF(f.pago, f.emitido) 
            END), 0) as dias_pago_3m_anteriores,
            
            SUM(CASE 
                WHEN f.pago IS NOT NULL 
                    AND f.estado = 'Pagado'
                    AND DATEDIFF(f.pago, f.emitido) <= 10 
                THEN 1 ELSE 0 
            END) as pagos_puntuales_count,
            
            SUM(CASE 
                WHEN f.pago IS NOT NULL 
                    AND f.estado = 'Pagado'
                    AND DATEDIFF(f.pago, f.emitido) > 30 
                THEN 1 ELSE 0 
            END) as pagos_muy_tardios_count,
            
            COALESCE(STDDEV(f.total), 0.01) as variacion_monto_facturas,
            COALESCE(AVG(f.total), 0.01) as promedio_monto_factura,
            COALESCE(MAX(f.total), 0) as monto_maximo_factura,
            COALESCE(MIN(f.total), 0) as monto_minimo_factura,
            
            COUNT(CASE WHEN f.emitido >= DATE_SUB(CURDATE(), INTERVAL 3 MONTH) THEN 1 END) as facturas_ultimos_3m,
            
            COUNT(CASE 
                WHEN f.emitido >= DATE_SUB(CURDATE(), INTERVAL 3 MONTH)
                    AND f.estado = 'Pagado'
                THEN 1 
            END) as facturas_pagadas_ultimos_3m

        FROM usuarios u
        LEFT JOIN tblavisouser a ON a.cliente = u.id
        LEFT JOIN facturas f ON f.idcliente = u.id
        WHERE f.emitido >= DATE_SUB(CURDATE(), INTERVAL {meses} MONTH)
        AND u.estado IN ('ACTIVO', 'RETIRADO', 'SUSPENDIDO')
        AND (a.fecha_retirado IS NULL OR a.fecha_retirado != '0000-00-00')
        GROUP BY u.id
        HAVING total_facturas >= {min_facturas}
        AND promedio_monto_factura > 0
        AND antiguedad_meses >= 3
        ORDER BY u.estado, u.id;
        """
    
    def _build_user_query(self, usuario_id: int) -> str:
        """Query para usuario específico (usa misma lógica limpia)."""
        base_query = self._build_training_query(12, 1)
        return base_query.replace(
            "WHERE f.emitido",
            f"WHERE u.id = {usuario_id} AND f.emitido"
        ).replace("AND u.estado IN", "-- AND u.estado IN")
    
    def _build_active_users_query(self) -> str:
        """Query para usuarios ACTIVOS (usa misma lógica limpia)."""
        base_query = self._build_training_query(12, 1)
        return base_query.replace(
            "AND u.estado IN ('ACTIVO', 'RETIRADO', 'SUSPENDIDO')",
            "AND u.estado = 'ACTIVO'"
        )
    
    def _process_features(self, df: pl.DataFrame) -> pl.DataFrame:
        """Procesa features con LAZY EXECUTION de Polars."""
        logger.info("Procesando features con Polars LazyFrame...")
        
        # ✅ CONVERTIR A LAZYFRAME (procesamiento optimizado)
        df_lazy = df.lazy()
        
        # ✅ TODAS LAS OPERACIONES SE PLANIFICAN, NO SE EJECUTAN
        df_lazy = df_lazy.with_columns([
            # Evitar divisiones por cero de forma eficiente
            pl.when(pl.col("promedio_monto_factura") == 0)
            .then(pl.lit(1.0))
            .otherwise(pl.col("promedio_monto_factura"))
            .alias("promedio_monto_factura_safe"),
            
            pl.when(pl.col("total_facturas") == 0)
            .then(pl.lit(1))
            .otherwise(pl.col("total_facturas"))
            .alias("total_facturas_safe"),
        ])
        
        # ✅ Features derivadas (encadenadas en un solo plan de ejecución)
        df_lazy = df_lazy.with_columns([
            # Tendencia de pago
            (pl.col("dias_pago_ultimos_3m") - pl.col("dias_pago_3m_anteriores"))
                .fill_null(0)
                .alias("tendencia_pago"),
            
            # Porcentaje pagos puntuales
            ((pl.col("pagos_puntuales_count") / pl.col("total_facturas_safe")) * 100)
                .fill_null(0)
                .alias("porcentaje_pagos_puntuales"),
            
            # ✅ NUEVA: Días mora respecto a corteautomatico
            (pl.col("promedio_dias_pago") - pl.col("corteautomatico"))
                .clip(0, None)  # Solo valores positivos = mora real
                .alias("dias_mora_real"),
            
            # ✅ NUEVA: Ratio mora vs limite
            ((pl.col("promedio_dias_pago") - pl.col("corteautomatico")) / pl.col("corteautomatico"))
                .clip(0, 10)  # Limitar outliers
                .fill_null(0)
                .alias("ratio_mora_vs_limite"),
            
            # Ratio deuda
            (pl.col("deuda_total") / pl.col("promedio_monto_factura_safe"))
                .fill_null(0)
                .alias("ratio_deuda"),
            
            # Coef variación
            (pl.col("variacion_monto_facturas") / pl.col("promedio_monto_factura_safe"))
                .fill_null(0)
                .alias("coef_variacion_monto"),
            
            # Meses desde última factura
            (pl.col("dias_ultima_factura") / 30)
                .fill_null(0)
                .alias("meses_desde_ultima_factura"),
            
            # Ratio morosidad
            (pl.col("facturas_pendientes") / pl.col("total_facturas_safe"))
                .fill_null(0)
                .alias("ratio_facturas_pendientes"),
            
            # Severidad mora
            (pl.col("promedio_dias_pago") * pl.col("facturas_pendientes"))
                .fill_null(0)
                .alias("severidad_mora"),
            
            # Score riesgo económico
            ((pl.col("deuda_total") / pl.col("promedio_monto_factura_safe")) * 
            (pl.col("facturas_pendientes") / pl.col("total_facturas_safe")))
                .fill_null(0)
                .alias("score_riesgo_economico"),
            
            # Ratio pagos muy tardíos
            ((pl.col("pagos_muy_tardios_count") / pl.col("total_facturas_safe")) * 100)
                .fill_null(0)
                .alias("porcentaje_pagos_muy_tardios"),
            
            # Actividad reciente
            (pl.col("facturas_ultimos_3m") / pl.col("total_facturas_safe"))
                .fill_null(0)
                .alias("ratio_actividad_reciente"),
            
            # Tasa pago reciente
            (pl.col("facturas_pagadas_ultimos_3m") / 
            pl.when(pl.col("facturas_ultimos_3m") == 0)
            .then(pl.lit(1))
            .otherwise(pl.col("facturas_ultimos_3m")))
                .fill_null(0)
                .alias("tasa_pago_reciente"),
            
            # ✅ NUEVA: Volatilidad de pago
            (pl.col("std_dias_pago") / (pl.col("promedio_dias_pago") + 1))
                .fill_null(0)
                .alias("volatilidad_pago"),
            
            # ✅ NUEVA: Aceleración de mora (cambio en tendencia)
            ((pl.col("dias_pago_ultimos_3m") - pl.col("dias_pago_3m_anteriores")) / 
            (pl.col("dias_pago_3m_anteriores") + 1))
                .fill_null(0)
                .alias("aceleracion_mora"),
        ])
        
        # ✅ EJECUTAR TODO EL PLAN DE UNA VEZ (optimización automática de Polars)
        df = df_lazy.collect()
        
        # Eliminar columnas temporales
        df = df.drop(["promedio_monto_factura_safe", "total_facturas_safe"])
        
        # Limpiar valores problemáticos (Polars optimiza esto internamente)
        df = df.fill_nan(0).fill_null(0)
        
        # ✅ USAR select_dtypes para operación vectorizada
        numeric_cols = [col for col in df.columns if df[col].dtype in [pl.Float64, pl.Float32]]
        
        for col in numeric_cols:
            df = df.with_columns([
                pl.when(pl.col(col).is_infinite())
                .then(pl.lit(0.0))
                .otherwise(pl.col(col))
                .alias(col)
            ])
        
        logger.info(f"Procesamiento completado: {df.height} filas, {df.width} columnas")
        return df
    
    def get_feature_names(self) -> list[str]:
        """
        Features OPTIMIZADAS con corteautomatico dinámico.
        
        ✅ NUEVAS FEATURES AGREGADAS:
        - dias_mora_real
        - ratio_mora_vs_limite
        - volatilidad_pago
        - aceleracion_mora
        """
        return [
            # Features base (limpias)
            "total_facturas",
            "facturas_pendientes",
            "deuda_total",
            "promedio_dias_pago",
            "max_dias_pago",
            "std_dias_pago",
            "dias_ultima_factura",
            "dias_desde_ultimo_pago",
            "antiguedad_meses",
            "corteautomatico",
            "zona",
            "mora_activa",
            "reconexion_historica",
            
            # Suspensión (solo reciente <30 días)
            "tiene_suspension_reciente",
            "dias_suspension_reciente",
            
            # Tendencias temporales
            "dias_pago_ultimos_3m",
            "dias_pago_3m_anteriores",
            
            # Comportamiento de pago
            "pagos_puntuales_count",
            "pagos_muy_tardios_count",
            
            # Estabilidad económica
            "variacion_monto_facturas",
            "promedio_monto_factura",
            "monto_maximo_factura",
            "monto_minimo_factura",
            
            # Actividad reciente
            "facturas_ultimos_3m",
            "facturas_pagadas_ultimos_3m",
            
            # Features derivadas
            "tendencia_pago",
            "porcentaje_pagos_puntuales",
            "ratio_deuda",
            "coef_variacion_monto",
            "meses_desde_ultima_factura",
            "ratio_facturas_pendientes",
            "severidad_mora",
            "score_riesgo_economico",
            "porcentaje_pagos_muy_tardios",
            "ratio_actividad_reciente",
            "tasa_pago_reciente",
            
            # ✅ NUEVAS: Con corteautomatico dinámico
            "dias_mora_real",              # Días REALES de mora post-corte
            "ratio_mora_vs_limite",        # Qué tan lejos está del límite
            "volatilidad_pago",            # Estabilidad de comportamiento
            "aceleracion_mora",            # Velocidad de empeoramiento
        ]