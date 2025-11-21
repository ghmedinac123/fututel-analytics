"""
Caso de uso: Entrenar modelo de predicción de churn.
Coordina extracción de features, entrenamiento y guardado del modelo.
"""
from typing import Dict
from sqlalchemy.ext.asyncio import AsyncSession

from futuisp_analytics.infrastructure.ml.feature_extractor import ChurnFeatureExtractor
from futuisp_analytics.infrastructure.ml.model_trainer import ChurnModelTrainer
from futuisp_analytics.infrastructure.ml.model_storage import ModelStorage
from futuisp_analytics.infrastructure.config.logging import logger


class EntrenarModeloChurn:
    """Caso de uso para entrenar modelo de churn."""
    
    def __init__(
        self,
        session: AsyncSession,
        models_dir: str = "models"
    ):
        self.session = session
        self.feature_extractor = ChurnFeatureExtractor(session)
        self.trainer = ChurnModelTrainer()
        self.storage = ModelStorage(models_dir)
    
    async def execute(
        self,
        meses_historicos: int = 24,  # ✅ 2 años en lugar de 12
        min_facturas: int = 6,       # ✅ 6 facturas en lugar de 3
        test_size: float = 0.2
    ) -> Dict:
        """
        Ejecuta entrenamiento completo del modelo.
        
        Args:
            meses_historicos: Meses de historial para entrenamiento
            min_facturas: Mínimo de facturas por usuario
            test_size: Proporción de datos para validación
            
        Returns:
            Diccionario con métricas y path del modelo guardado
        """
        logger.info("=" * 80)
        logger.info("INICIO DE ENTRENAMIENTO DE MODELO DE PREDICCIÓN DE CHURN")
        logger.info("=" * 80)
        
        try:
            # PASO 1: Extraer features
            logger.info("\n[1/4] EXTRACCIÓN DE FEATURES")
            logger.info("-" * 80)
            
            df_training = await self.feature_extractor.extract_training_data(
                meses_historicos=meses_historicos,
                min_facturas=min_facturas
            )
            
            if df_training.height == 0:
                raise ValueError("No se encontraron datos para entrenamiento")
            
            logger.info(f"✅ Features extraídas: {df_training.height} usuarios")
            
            # PASO 2: Entrenar modelo
            logger.info("\n[2/4] ENTRENAMIENTO DEL MODELO")
            logger.info("-" * 80)
            
            feature_names = self.feature_extractor.get_feature_names()
            
            metrics = self.trainer.train(
                df=df_training,
                feature_names=feature_names,
                test_size=test_size
            )
            
            logger.info(f"✅ Modelo entrenado - Test Accuracy: {metrics['test_accuracy']:.4f}")
            
            # PASO 3: Guardar modelo
            logger.info("\n[3/4] GUARDANDO MODELO")
            logger.info("-" * 80)
            
            model_path = self.storage.save_model(
                model=self.trainer.model,
                feature_names=feature_names,
                metrics=metrics
            )
            
            logger.info(f"✅ Modelo guardado en: {model_path}")
            
            # PASO 4: Feature importance
            logger.info("\n[4/4] ANÁLISIS DE FEATURES")
            logger.info("-" * 80)
            
            feature_importance = self.trainer.get_feature_importance()
            top_features = feature_importance.head(5)
            
            logger.info("Top 5 features más importantes:")
            for row in top_features.iter_rows(named=True):
                logger.info(f"  - {row['feature']}: {row['importance']:.4f}")
            
            logger.info("\n" + "=" * 80)
            logger.info("✅ ENTRENAMIENTO COMPLETADO EXITOSAMENTE")
            logger.info("=" * 80)
            
            # Resultado final
            return {
                "success": True,
                "model_path": model_path,
                "metrics": {
                    "training_date": metrics["training_date"],
                    "samples_total": metrics["samples_total"],
                    "samples_train": metrics["samples_train"],
                    "samples_test": metrics["samples_test"],
                    "churn_rate": metrics["churn_rate"],
                    "train_accuracy": metrics["train_accuracy"],
                    "train_precision": metrics["train_precision"],
                    "train_recall": metrics["train_recall"],
                    "train_f1": metrics["train_f1"],
                    "test_accuracy": metrics["test_accuracy"],
                    "test_precision": metrics["test_precision"],
                    "test_recall": metrics["test_recall"],
                    "test_f1": metrics["test_f1"],
                    "test_roc_auc": metrics["test_roc_auc"],
                    "confusion_matrix": metrics["confusion_matrix"],
                    "cv_roc_auc": metrics["cv_roc_auc_mean"],
                },
                "dataset": {
                    "total_usuarios": df_training.height,  # ← CORREGIDO: usar .height
                    "meses_historicos": meses_historicos,
                    "min_facturas": min_facturas,
                    "samples_train": metrics["samples_train"],
                    "samples_test": metrics["samples_test"],
                    "churn_rate": metrics["churn_rate"],
                },
                "top_features": [
                    {
                        "feature": row['feature'],
                        "importance": float(row['importance'])
                    }
                    for row in feature_importance.head(5).iter_rows(named=True)  # ← CORREGIDO
                ]
            }
            
        except Exception as e:
            logger.error(f"❌ Error durante entrenamiento: {str(e)}", exc_info=True)
            raise