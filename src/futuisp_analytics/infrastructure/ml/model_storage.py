"""
Model Storage para persistencia de modelos entrenados.
Guarda y carga modelos XGBoost con metadata.
"""
from typing import Dict, Optional
from pathlib import Path
from datetime import datetime
import joblib
import json

from futuisp_analytics.infrastructure.config.logging import logger


class ModelStorage:
    """Gestiona persistencia de modelos ML."""
    
    def __init__(self, models_dir: str = "models"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self.metadata_file = self.models_dir / "metadata.json"
    
    def save_model(
        self,
        model,
        feature_names: list[str],
        metrics: Dict,
        model_name: Optional[str] = None
    ) -> str:
        """
        Guarda modelo con metadata.
        
        Args:
            model: Modelo XGBoost entrenado
            feature_names: Lista de features
            metrics: Diccionario con métricas
            model_name: Nombre custom (default: churn_model_YYYY-MM)
            
        Returns:
            Path del modelo guardado
        """
        if model_name is None:
            timestamp = datetime.now().strftime("%Y-%m")
            model_name = f"churn_model_{timestamp}"
        
        model_path = self.models_dir / f"{model_name}.pkl"
        
        logger.info(f"Guardando modelo en: {model_path}")
        
        # Guardar modelo con joblib (más eficiente que pickle)
        joblib.dump(model, model_path)
        
        # Guardar metadata
        metadata = {
            "model_name": model_name,
            "model_path": str(model_path),
            "feature_names": feature_names,
            "metrics": metrics,
            "saved_at": datetime.now().isoformat(),
        }
        
        self._save_metadata(model_name, metadata)
        
        # Calcular tamaño del archivo
        size_mb = model_path.stat().st_size / (1024 * 1024)
        logger.info(f"Modelo guardado exitosamente ({size_mb:.2f} MB)")
        
        return str(model_path)
    
    def load_model(
        self, 
        model_name: Optional[str] = None
    ) -> tuple:
        """
        Carga modelo más reciente o específico.
        
        Args:
            model_name: Nombre del modelo (default: más reciente)
            
        Returns:
            (model, feature_names, metrics)
        """
        if model_name is None:
            model_name = self._get_latest_model_name()
            if model_name is None:
                raise FileNotFoundError("No hay modelos guardados")
        
        model_path = self.models_dir / f"{model_name}.pkl"
        
        if not model_path.exists():
            raise FileNotFoundError(f"Modelo no encontrado: {model_path}")
        
        logger.info(f"Cargando modelo: {model_path}")
        
        # Cargar modelo
        model = joblib.load(model_path)
        
        # Cargar metadata
        metadata = self._load_metadata(model_name)
        
        feature_names = metadata.get("feature_names", [])
        metrics = metadata.get("metrics", {})
        
        logger.info(f"Modelo cargado exitosamente (entrenado: {metadata.get('saved_at', 'unknown')})")
        
        return model, feature_names, metrics
    
    def list_models(self) -> list[Dict]:
        """
        Lista todos los modelos disponibles.
        
        Returns:
            Lista de diccionarios con info de modelos
        """
        all_metadata = self._load_all_metadata()
        
        models = []
        for model_name, metadata in all_metadata.items():
            models.append({
                "model_name": model_name,
                "saved_at": metadata.get("saved_at"),
                "test_accuracy": metadata.get("metrics", {}).get("test_accuracy"),
                "test_roc_auc": metadata.get("metrics", {}).get("test_roc_auc"),
            })
        
        # Ordenar por fecha (más reciente primero)
        models.sort(key=lambda x: x["saved_at"], reverse=True)
        
        return models
    
    def _save_metadata(self, model_name: str, metadata: Dict):
        """Guarda metadata de un modelo."""
        all_metadata = self._load_all_metadata()
        all_metadata[model_name] = metadata
        
        with open(self.metadata_file, 'w') as f:
            json.dump(all_metadata, f, indent=2)
    
    def _load_metadata(self, model_name: str) -> Dict:
        """Carga metadata de un modelo específico."""
        all_metadata = self._load_all_metadata()
        
        if model_name not in all_metadata:
            raise ValueError(f"Metadata no encontrada para: {model_name}")
        
        return all_metadata[model_name]
    
    def _load_all_metadata(self) -> Dict:
        """Carga toda la metadata."""
        if not self.metadata_file.exists():
            return {}
        
        with open(self.metadata_file, 'r') as f:
            return json.load(f)
    
    def _get_latest_model_name(self) -> Optional[str]:
        """Obtiene nombre del modelo más reciente."""
        all_metadata = self._load_all_metadata()
        
        if not all_metadata:
            return None
        
        # Ordenar por fecha de guardado
        sorted_models = sorted(
            all_metadata.items(),
            key=lambda x: x[1].get("saved_at", ""),
            reverse=True
        )
        
        return sorted_models[0][0] if sorted_models else None
