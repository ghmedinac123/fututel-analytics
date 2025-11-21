"""
Caso de uso: Predecir riesgo de churn para usuarios.
Carga modelo entrenado y realiza predicciones individuales o masivas.
"""
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import polars as pl

from futuisp_analytics.infrastructure.ml.feature_extractor import ChurnFeatureExtractor
from futuisp_analytics.infrastructure.ml.model_storage import ModelStorage
from futuisp_analytics.infrastructure.config.logging import logger


class PredecirChurn:
    """Caso de uso para predecir churn de usuarios."""
    
    def __init__(
        self,
        session: AsyncSession,
        models_dir: str = "models"
    ):
        self.session = session
        self.feature_extractor = ChurnFeatureExtractor(session)
        self.storage = ModelStorage(models_dir)
        
        # Cargar modelo al inicializar
        self.model, self.feature_names, self.metrics = self.storage.load_model()
        
        logger.info(f"Modelo cargado - Test Accuracy: {self.metrics.get('test_accuracy', 0):.4f}")
    
    async def predecir_usuario(self, usuario_id: int) -> Optional[Dict]:
        """
        Predice riesgo de churn para un usuario específico.
        
        Args:
            usuario_id: ID del usuario
            
        Returns:
            Diccionario con predicción o None si usuario no existe
        """
        logger.info(f"Prediciendo churn para usuario {usuario_id}")
        
        # Extraer features del usuario
        df_user = await self.feature_extractor.extract_user_features(usuario_id)
        
        if df_user is None or df_user.height == 0:
            logger.warning(f"Usuario {usuario_id} no encontrado o sin datos")
            return None
        
        # Obtener datos básicos del usuario
        info_usuario = await self._obtener_info_usuario(usuario_id)
        
        # Predecir probabilidad
        probas = self.model.predict_proba(
            df_user.select(self.feature_names).to_numpy()
        )
        
        probabilidad_churn = float(probas[0][1] * 100)  # Probabilidad de clase 1 (RIESGO)
        
        # Clasificar nivel de riesgo
        nivel_riesgo = self._clasificar_riesgo(probabilidad_churn)
        
        # Obtener features principales que contribuyen al riesgo
        factores_riesgo = self._analizar_factores_riesgo(df_user)
        
        # Recomendaciones
        recomendacion = self._generar_recomendacion(
            nivel_riesgo, 
            probabilidad_churn,
            factores_riesgo
        )
        
        resultado = {
            "usuario_id": usuario_id,
            "nombre_completo": f"{info_usuario['nombre']} {info_usuario['apellido']}",
            "telefono": info_usuario['telefono'],
            "email": info_usuario['email'],
            "direccion": info_usuario['direccion'],
            "probabilidad_retiro": round(probabilidad_churn, 2),
            "nivel_riesgo": nivel_riesgo,
            "factores_principales": factores_riesgo[:5],  # Top 5
            "recomendacion": recomendacion,
            "metricas_usuario": {
                "facturas_pendientes": int(df_user["facturas_pendientes"][0]),
                "deuda_total": float(df_user["deuda_total"][0]),
                "promedio_dias_pago": float(df_user["promedio_dias_pago"][0]),
                "pagos_puntuales": float(df_user["porcentaje_pagos_puntuales"][0]),
            }
        }
        
        logger.info(
            f"Usuario {usuario_id} ({info_usuario['nombre']}): "
            f"{probabilidad_churn:.2f}% riesgo ({nivel_riesgo})"
        )
        
        return resultado
    
    async def predecir_usuarios_activos(
        self,
        riesgo_minimo: float = 50.0,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Predice churn para TODOS los usuarios ACTIVOS.
        
        Args:
            riesgo_minimo: % mínimo de riesgo para incluir en resultado
            limit: Máximo de usuarios a retornar (None = todos)
            
        Returns:
            Lista de usuarios en riesgo ordenados por probabilidad
        """
        logger.info(f"Prediciendo churn para usuarios ACTIVOS (riesgo >= {riesgo_minimo}%)")
        
        # Extraer features de usuarios activos
        df_activos = await self.feature_extractor.extract_active_users_features()
        
        if df_activos.height == 0:
            logger.warning("No se encontraron usuarios ACTIVOS")
            return []
        
        logger.info(f"Analizando {df_activos.height} usuarios ACTIVOS")
        
        # Predecir para todos
        X = df_activos.select(self.feature_names).to_numpy()
        probas = self.model.predict_proba(X)
        
        # Agregar probabilidades al DataFrame
        df_activos = df_activos.with_columns(
            pl.Series("probabilidad_churn", probas[:, 1] * 100)
        )
        
        # Filtrar por riesgo mínimo
        df_riesgo = df_activos.filter(
            pl.col("probabilidad_churn") >= riesgo_minimo
        ).sort("probabilidad_churn", descending=True)
        
        logger.info(f"Usuarios en riesgo (>={riesgo_minimo}%): {df_riesgo.height}")
        
        # Obtener IDs para consultar datos básicos
        usuario_ids = [row["usuario_id"] for row in df_riesgo.iter_rows(named=True)]
        
        # Obtener datos básicos de todos los usuarios en una sola consulta
        usuarios_info = await self._obtener_info_usuarios_batch(usuario_ids)
        
        # Convertir a lista de diccionarios
        resultados = []
        
        for row in df_riesgo.iter_rows(named=True):
            probabilidad = row["probabilidad_churn"]
            nivel_riesgo = self._clasificar_riesgo(probabilidad)
            usuario_id = row["usuario_id"]
            
            # Obtener info del usuario
            info = usuarios_info.get(usuario_id, {})
            
            resultado = {
                "usuario_id": usuario_id,
                "nombre_completo": f"{info.get('nombre', 'N/A')} {info.get('apellido', '')}".strip(),
                "telefono": info.get('telefono', 'N/A'),
                "email": info.get('email', 'N/A'),
                "direccion": info.get('direccion', 'N/A'),
                "probabilidad_retiro": round(probabilidad, 2),
                "nivel_riesgo": nivel_riesgo,
                "facturas_pendientes": row["facturas_pendientes"],
                "deuda_total": round(row["deuda_total"], 2),
                "promedio_dias_pago": round(row["promedio_dias_pago"], 2),
            }
            
            resultados.append(resultado)
            
            # Aplicar límite si existe
            if limit and len(resultados) >= limit:
                break
        
        return resultados
    
    async def _obtener_info_usuario(self, usuario_id: int) -> Dict:
        """Obtiene información básica de un usuario."""
        query = text("""
            SELECT 
                nombre,
                COALESCE(movil, telefono) as telefono,
                correo,
                direccion_principal
            FROM usuarios
            WHERE id = :usuario_id
        """)
        
        result = await self.session.execute(query, {"usuario_id": usuario_id})
        row = result.fetchone()
        
        if row:
            return {
                "nombre": row[0] or "N/A",
                "apellido": "",  # No existe en tu BD
                "telefono": row[1] or "N/A",
                "email": row[2] or "N/A",
                "direccion": row[3] or "N/A"
            }
        
        return {
            "nombre": "N/A",
            "apellido": "",
            "telefono": "N/A",
            "email": "N/A",
            "direccion": "N/A"
        }
    
    async def _obtener_info_usuarios_batch(self, usuario_ids: List[int]) -> Dict[int, Dict]:
        """Obtiene información básica de múltiples usuarios."""
        if not usuario_ids:
            return {}
        
        placeholders = ','.join([str(uid) for uid in usuario_ids])
        
        query = text(f"""
            SELECT 
                id,
                nombre,
                COALESCE(movil, telefono) as telefono,
                correo,
                direccion_principal
            FROM usuarios
            WHERE id IN ({placeholders})
        """)
        
        result = await self.session.execute(query)
        rows = result.fetchall()
        
        usuarios = {}
        for row in rows:
            usuarios[row[0]] = {
                "nombre": row[1] or "N/A",
                "apellido": "",
                "telefono": row[2] or "N/A",
                "email": row[3] or "N/A",
                "direccion": row[4] or "N/A"
            }
        
        return usuarios
    
    def _clasificar_riesgo(self, probabilidad: float) -> str:
        """Clasifica nivel de riesgo según probabilidad."""
        if probabilidad >= 80:
            return "CRÍTICO"
        elif probabilidad >= 60:
            return "ALTO"
        elif probabilidad >= 40:
            return "MEDIO"
        elif probabilidad >= 20:
            return "BAJO"
        else:
            return "MUY BAJO"
    
    def _analizar_factores_riesgo(self, df_user: pl.DataFrame) -> List[str]:
        """Identifica factores que contribuyen al riesgo."""
        factores = []
        
        row = df_user.row(0, named=True)
        
        # Facturas pendientes
        if row["facturas_pendientes"] >= 3:
            factores.append(f"{row['facturas_pendientes']} facturas pendientes")
        elif row["facturas_pendientes"] >= 1:
            factores.append(f"{row['facturas_pendientes']} factura pendiente")
        
        # Deuda alta
        if row["deuda_total"] > 100000:
            factores.append(f"Deuda alta: ${row['deuda_total']:,.0f}")
        
        # Días de pago
        if row["promedio_dias_pago"] > 20:
            factores.append(f"Paga con retraso ({row['promedio_dias_pago']:.0f} días promedio)")
        
        # Tendencia empeorando
        if row["tendencia_pago"] > 5:
            factores.append("Tendencia de pago empeorando")
        
        # Actividad baja
        if row["ratio_actividad_reciente"] < 0.3:
            factores.append("Actividad reciente muy baja")
        
        # Pagos puntuales bajos
        if row["porcentaje_pagos_puntuales"] < 30:
            factores.append(f"Pocos pagos puntuales ({row['porcentaje_pagos_puntuales']:.0f}%)")
        
        return factores if factores else ["Sin factores críticos identificados"]
    
    def _generar_recomendacion(
        self, 
        nivel_riesgo: str, 
        probabilidad: float,
        factores: List[str]
    ) -> str:
        """Genera recomendación basada en el riesgo."""
        
        if nivel_riesgo == "CRÍTICO":
            return "🔴 CONTACTAR INMEDIATAMENTE - Riesgo extremo de pérdida"
        
        elif nivel_riesgo == "ALTO":
            return "🟠 Contactar en 24-48 horas - Ofrecer plan de pagos"
        
        elif nivel_riesgo == "MEDIO":
            return "🟡 Monitorear de cerca - Enviar recordatorio de pago"
        
        elif nivel_riesgo == "BAJO":
            return "🟢 Seguimiento rutinario"
        
        else:
            return "✅ Cliente estable - No requiere acción"