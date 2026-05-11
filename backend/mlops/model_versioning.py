import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import joblib
from backend.mlops.mlflow_config import get_mlflow_config, MODEL_ISOLATION_FOREST, MODEL_AUTOENCODER, MODEL_HYBRID

logger = logging.getLogger(__name__)

MODEL_BASE_DIR = "backend/model"
VERSIONS_DIR = os.path.join(MODEL_BASE_DIR, "versions")
CURRENT_VERSION_FILE = os.path.join(MODEL_BASE_DIR, "current_version.txt")


class ModelVersioning:
    def __init__(self):
        self._ensure_dirs()
        self.mlflow_config = get_mlflow_config()
    
    def _ensure_dirs(self):
        os.makedirs(VERSIONS_DIR, exist_ok=True)
        os.makedirs(MODEL_BASE_DIR, exist_ok=True)
    
    def get_next_version(self) -> str:
        try:
            current = self.get_current_version()
            parts = current.split('.')
            patch = int(parts[2]) + 1
            next_version = f"{parts[0]}.{parts[1]}.{patch}"
            logger.info(f"Next version: {next_version}")
            return next_version
        except Exception as e:
            logger.error(f"Error getting next version: {e}")
            return "1.0.1"
    
    def get_current_version(self) -> str:
        try:
            if os.path.exists(CURRENT_VERSION_FILE):
                with open(CURRENT_VERSION_FILE, 'r') as f:
                    version = f.read().strip()
                    return version if version else "1.0.0"
            return "1.0.0"
        except Exception as e:
            logger.error(f"Error reading current version: {e}")
            return "1.0.0"
    
    def save_model_version(self, model: Any, scaler: Any, version: str, model_type: str, metrics: Dict[str, Any]) -> bool:
        try:
            version_dir = os.path.join(VERSIONS_DIR, version, model_type)
            os.makedirs(version_dir, exist_ok=True)
            
            model_path = os.path.join(version_dir, "model.pkl")
            joblib.dump(model, model_path)
            logger.info(f"Saved model to {model_path}")
            
            if scaler is not None:
                scaler_path = os.path.join(version_dir, "scaler.pkl")
                joblib.dump(scaler, scaler_path)
                logger.info(f"Saved scaler to {scaler_path}")
            
            metadata = {
                'version': version,
                'model_type': model_type,
                'timestamp': datetime.now().isoformat(),
                'metrics': metrics
            }
            
            metadata_path = os.path.join(version_dir, "metadata.json")
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            logger.info(f"Saved metadata to {metadata_path}")
            
            return True
        except Exception as e:
            logger.error(f"Error saving model version: {e}")
            return False
    
    def set_current_version(self, version: str) -> bool:
        try:
            with open(CURRENT_VERSION_FILE, 'w') as f:
                f.write(version)
            logger.info(f"Set current version to {version}")
            return True
        except Exception as e:
            logger.error(f"Error setting current version: {e}")
            return False
    
    def load_model_version(self, version: str, model_type: str) -> tuple:
        try:
            version_dir = os.path.join(VERSIONS_DIR, version, model_type)
            model_path = os.path.join(version_dir, "model.pkl")
            model = joblib.load(model_path)
            logger.info(f"Loaded model from {model_path}")
            
            scaler = None
            scaler_path = os.path.join(version_dir, "scaler.pkl")
            if os.path.exists(scaler_path):
                scaler = joblib.load(scaler_path)
                logger.info(f"Loaded scaler from {scaler_path}")
            
            return model, scaler
        except Exception as e:
            logger.error(f"Error loading model version: {e}")
            return None, None
    
    def get_version_metadata(self, version: str, model_type: str) -> Optional[Dict]:
        try:
            metadata_path = os.path.join(VERSIONS_DIR, version, model_type, "metadata.json")
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    return json.load(f)
            return None
        except Exception as e:
            logger.error(f"Error reading version metadata: {e}")
            return None
    
    def list_versions(self) -> list:
        try:
            if not os.path.exists(VERSIONS_DIR):
                return []
            versions = sorted(os.listdir(VERSIONS_DIR))
            logger.info(f"Available versions: {versions}")
            return versions
        except Exception as e:
            logger.error(f"Error listing versions: {e}")
            return []
    
    def register_model_in_registry(self, version: str, model_type: str, metrics: Dict[str, Any]) -> bool:
        """Register model in MLflow Model Registry"""
        try:
            version_dir = os.path.join(VERSIONS_DIR, version, model_type)
            model_path = os.path.join(version_dir, "model.pkl")
            
            if not os.path.exists(model_path):
                logger.warning(f"Model file not found: {model_path}")
                return False
            
            # Determine model name based on type
            model_name = {
                'isolation_forest': MODEL_ISOLATION_FOREST,
                'autoencoder': MODEL_AUTOENCODER
            }.get(model_type, MODEL_HYBRID)
            
            # Register model in MLflow
            model_uri = f"file://{os.path.abspath(model_path)}"
            self.mlflow_config.register_model(model_uri, model_name)
            
            logger.info(f"Registered {model_type} model v{version} in MLflow Registry")
            return True
            
        except Exception as e:
            logger.error(f"Error registering model in MLflow: {e}")
            return False
    
    def get_model_registry_info(self, model_type: str) -> Optional[Dict]:
        """Get model info from MLflow Model Registry"""
        try:
            model_name = {
                'isolation_forest': MODEL_ISOLATION_FOREST,
                'autoencoder': MODEL_AUTOENCODER
            }.get(model_type, MODEL_HYBRID)
            
            model_version = self.mlflow_config.get_model_version(model_name, stage="Production")
            if model_version:
                return {
                    'name': model_name,
                    'version': model_version.version,
                    'stage': model_version.current_stage,
                    'created_timestamp': model_version.creation_timestamp,
                    'last_updated_timestamp': model_version.last_updated_timestamp
                }
            return None
        except Exception as e:
            logger.error(f"Error getting model registry info: {e}")
            return None


def get_versioning() -> ModelVersioning:
    return ModelVersioning()
