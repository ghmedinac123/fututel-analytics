"""
Model Trainer para predicción de churn usando XGBoost.
Entrena, valida y evalúa modelos de Machine Learning.
"""
from typing import Dict, Tuple, Optional
from datetime import datetime
import polars as pl
import xgboost as xgb
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (
    accuracy_score, 
    precision_score, 
    recall_score, 
    f1_score,
    roc_auc_score,
    classification_report,
    confusion_matrix
)
import numpy as np

from futuisp_analytics.infrastructure.config.logging import logger


class ChurnModelTrainer:
    """Entrena y evalúa modelos de predicción de churn."""
    
    def __init__(self):
        self.model: Optional[xgb.XGBClassifier] = None
        self.feature_names: Optional[list[str]] = None
        self.training_date: Optional[datetime] = None
        self.metrics: Optional[Dict] = None
    
    def train(
        self, 
        df: pl.DataFrame,
        feature_names: list[str],
        test_size: float = 0.2,
        random_state: int = 42
    ) -> Dict:
        """
        Entrena modelo XGBoost con validación.
        
        Args:
            df: DataFrame de Polars con features y target
            feature_names: Lista de nombres de features
            test_size: Proporción de datos para test
            random_state: Semilla aleatoria
            
        Returns:
            Diccionario con métricas de evaluación
        """
        logger.info("=" * 60)
        logger.info("INICIANDO ENTRENAMIENTO DE MODELO DE CHURN")
        logger.info("=" * 60)
        
        self.feature_names = feature_names
        self.training_date = datetime.now()
        
        # Preparar datos
        logger.info("Preparando dataset...")
        X, y = self._prepare_data(df, feature_names)
        
        # Información del dataset
        total_samples = len(y)
        churn_count = int(y.sum())
        active_count = total_samples - churn_count
        churn_rate = (churn_count / total_samples) * 100
        
        logger.info(f"Dataset preparado:")
        logger.info(f"  - Total usuarios: {total_samples}")
        logger.info(f"  - RIESGO (1): {churn_count} ({churn_rate:.2f}%)")
        logger.info(f"  - ESTABLE (0): {active_count} ({100-churn_rate:.2f}%)")
        logger.info(f"  - Features: {len(feature_names)}")
        
        # Split train/test
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, 
            test_size=test_size, 
            random_state=random_state,
            stratify=y  # Mantiene proporción de clases
        )
        
        logger.info(f"Split: {len(X_train)} train, {len(X_test)} test")
        
        # Entrenar modelo
        logger.info("Entrenando XGBoost...")
        self.model = self._train_xgboost(X_train, y_train)
        
        # Evaluar modelo
        logger.info("Evaluando modelo...")
        self.metrics = self._evaluate_model(
            X_train, X_test, 
            y_train, y_test
        )
        
        # Feature importance
        self._log_feature_importance()
        
        logger.info("=" * 60)
        logger.info("ENTRENAMIENTO COMPLETADO")
        logger.info("=" * 60)
        
        return self.metrics
    
    def predict_proba(self, df: pl.DataFrame) -> np.ndarray:
        """
        Predice probabilidad de churn para usuarios.
        
        Args:
            df: DataFrame de Polars con features
            
        Returns:
            Array numpy con probabilidades [prob_estable, prob_churn]
        """
        if self.model is None:
            raise ValueError("Modelo no entrenado. Ejecuta train() primero.")
        
        X = self._prepare_features(df, self.feature_names)
        
        # XGBoost retorna probabilidades para cada clase
        probas = self.model.predict_proba(X)
        
        return probas
    
    def predict(self, df: pl.DataFrame) -> np.ndarray:
        """
        Predice clase (0=ESTABLE, 1=RIESGO).
        
        Args:
            df: DataFrame de Polars con features
            
        Returns:
            Array numpy con predicciones binarias
        """
        if self.model is None:
            raise ValueError("Modelo no entrenado. Ejecuta train() primero.")
        
        X = self._prepare_features(df, self.feature_names)
        
        return self.model.predict(X)
    
    def _prepare_data(
        self, 
        df: pl.DataFrame, 
        feature_names: list[str]
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Prepara X (features) e y (target) desde DataFrame."""
        
        # Extraer target
        y = df.select("target_churn").to_numpy().flatten()
        
        # Extraer features
        X = self._prepare_features(df, feature_names)
        
        return X, y
    
    def _prepare_features(
        self, 
        df: pl.DataFrame, 
        feature_names: list[str]
    ) -> np.ndarray:
        """Extrae solo las features necesarias en el orden correcto."""
        
        # Polars es mucho más rápido que pandas para selección de columnas
        X = df.select(feature_names).to_numpy()
        
        # Reemplazar inf y -inf con valores seguros
        X = np.nan_to_num(X, nan=0.0, posinf=999999, neginf=-999999)
        
        return X
    
    def _train_xgboost(
        self, 
        X_train: np.ndarray, 
        y_train: np.ndarray
    ) -> xgb.XGBClassifier:
        """
        Entrena modelo XGBoost con hiperparámetros optimizados.
        """
        
        # Calcular scale_pos_weight para datos desbalanceados
        n_negative = (y_train == 0).sum()
        n_positive = (y_train == 1).sum()
        scale_pos_weight = n_negative / n_positive if n_positive > 0 else 1
        
        logger.info(f"Scale pos weight: {scale_pos_weight:.2f} (para balancear clases)")
        
        model = xgb.XGBClassifier(
            # Hiperparámetros optimizados para churn prediction
            n_estimators=200,           # Número de árboles
            max_depth=6,                # Profundidad máxima
            learning_rate=0.1,          # Tasa de aprendizaje
            subsample=0.8,              # % de muestras por árbol
            colsample_bytree=0.8,       # % de features por árbol
            scale_pos_weight=scale_pos_weight,  # Balance de clases
            
            # Regularización
            gamma=0.1,                  # Mínima reducción de loss para split
            reg_alpha=0.1,              # L1 regularization
            reg_lambda=1.0,             # L2 regularization
            
            # Performance
            n_jobs=-1,                  # Usa todos los cores CPU
            random_state=42,
            
            # Optimización
            objective='binary:logistic',
            eval_metric='logloss',
            
            # Producción
            verbosity=0                 # Sin logs verbose
        )
        
        # Entrenar
        start_time = datetime.now()
        model.fit(X_train, y_train)
        training_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"Entrenamiento completado en {training_time:.2f} segundos")
        
        return model
    
    def _evaluate_model(
        self,
        X_train: np.ndarray,
        X_test: np.ndarray,
        y_train: np.ndarray,
        y_test: np.ndarray
    ) -> Dict:
        """Evalúa modelo con múltiples métricas."""
        
        # Predicciones
        y_train_pred = self.model.predict(X_train)
        y_test_pred = self.model.predict(X_test)
        
        # Probabilidades para ROC-AUC
        y_test_proba = self.model.predict_proba(X_test)[:, 1]
        
        # Métricas
        metrics = {
            "training_date": self.training_date.isoformat(),
            "samples_total": len(y_train) + len(y_test),
            "samples_train": len(y_train),
            "samples_test": len(y_test),
            "churn_rate": float((y_train.sum() + y_test.sum()) / (len(y_train) + len(y_test)) * 100),
            
            # Métricas en TRAIN (overfitting check)
            "train_accuracy": float(accuracy_score(y_train, y_train_pred)),
            "train_precision": float(precision_score(y_train, y_train_pred, zero_division=0)),
            "train_recall": float(recall_score(y_train, y_train_pred, zero_division=0)),
            "train_f1": float(f1_score(y_train, y_train_pred, zero_division=0)),
            
            # Métricas en TEST (performance real)
            "test_accuracy": float(accuracy_score(y_test, y_test_pred)),
            "test_precision": float(precision_score(y_test, y_test_pred, zero_division=0)),
            "test_recall": float(recall_score(y_test, y_test_pred, zero_division=0)),
            "test_f1": float(f1_score(y_test, y_test_pred, zero_division=0)),
            "test_roc_auc": float(roc_auc_score(y_test, y_test_proba)),
            
            # Matriz de confusión
            "confusion_matrix": confusion_matrix(y_test, y_test_pred).tolist(),
        }
        
        # Cross-validation (validación cruzada 5-fold)
        logger.info("Ejecutando validación cruzada...")
        cv_scores = cross_val_score(
            self.model, 
            X_train, 
            y_train, 
            cv=5, 
            scoring='roc_auc',
            n_jobs=-1
        )
        
        metrics["cv_roc_auc_mean"] = float(cv_scores.mean())
        metrics["cv_roc_auc_std"] = float(cv_scores.std())
        
        # Log de resultados
        logger.info("\n" + "=" * 60)
        logger.info("MÉTRICAS DEL MODELO")
        logger.info("=" * 60)
        logger.info(f"Dataset: {metrics['samples_train']} train / {metrics['samples_test']} test")
        logger.info(f"Tasa de Churn: {metrics['churn_rate']:.2f}%")
        logger.info("")
        logger.info("TRAIN SET:")
        logger.info(f"  Accuracy:  {metrics['train_accuracy']:.4f}")
        logger.info(f"  Precision: {metrics['train_precision']:.4f}")
        logger.info(f"  Recall:    {metrics['train_recall']:.4f}")
        logger.info(f"  F1-Score:  {metrics['train_f1']:.4f}")
        logger.info("")
        logger.info("TEST SET:")
        logger.info(f"  Accuracy:  {metrics['test_accuracy']:.4f}")
        logger.info(f"  Precision: {metrics['test_precision']:.4f}")
        logger.info(f"  Recall:    {metrics['test_recall']:.4f}")
        logger.info(f"  F1-Score:  {metrics['test_f1']:.4f}")
        logger.info(f"  ROC-AUC:   {metrics['test_roc_auc']:.4f}")
        logger.info("")
        logger.info("CROSS-VALIDATION (5-fold):")
        logger.info(f"  ROC-AUC: {metrics['cv_roc_auc_mean']:.4f} (±{metrics['cv_roc_auc_std']:.4f})")
        logger.info("")
        
        # Matriz de confusión
        cm = metrics["confusion_matrix"]
        logger.info("MATRIZ DE CONFUSIÓN:")
        logger.info(f"  TN: {cm[0][0]:4d}  |  FP: {cm[0][1]:4d}")
        logger.info(f"  FN: {cm[1][0]:4d}  |  TP: {cm[1][1]:4d}")
        logger.info("=" * 60 + "\n")
        
        # Classification report detallado
        logger.info("REPORTE DE CLASIFICACIÓN:")
        logger.info("\n" + classification_report(
            y_test, 
            y_test_pred,
            target_names=['ESTABLE', 'RIESGO'],
            digits=4
        ))
        
        return metrics
    
    def _log_feature_importance(self):
        """Log de las features más importantes."""
        
        importance = self.model.feature_importances_
        
        # Crear DataFrame con Polars para ordenar
        df_importance = pl.DataFrame({
            "feature": self.feature_names,
            "importance": importance
        }).sort("importance", descending=True)
        
        logger.info("\n" + "=" * 60)
        logger.info("TOP 10 FEATURES MÁS IMPORTANTES")
        logger.info("=" * 60)
        
        for row in df_importance.head(10).iter_rows(named=True):
            logger.info(f"  {row['feature']:30s} {row['importance']:.4f}")
        
        logger.info("=" * 60 + "\n")
    
    def get_feature_importance(self) -> pl.DataFrame:
        """
        Retorna DataFrame de Polars con feature importance.
        
        Returns:
            DataFrame con columnas: feature, importance
        """
        if self.model is None:
            raise ValueError("Modelo no entrenado")
        
        return pl.DataFrame({
            "feature": self.feature_names,
            "importance": self.model.feature_importances_
        }).sort("importance", descending=True)