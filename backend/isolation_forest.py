import os, json, logging, joblib
import numpy as np
from typing import Dict, Any, Optional
from sklearn.ensemble import IsolationForest
from .utils import MODEL_FEATURES

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IsolationForestInference:
    MODEL_PATH = 'backend/model/isolation_forest.pkl'
    SCALER_PATH = 'backend/model/isolation_forest_scaler.pkl'

    def __init__(self):
        self.model = None
        self.scaler = None
        self.features = None

    def load(self) -> bool:
        try:
            model_data = joblib.load(self.MODEL_PATH)
            self.model = model_data['model'] if isinstance(model_data, dict) else model_data
            self.features = model_data.get('features', MODEL_FEATURES) if isinstance(model_data, dict) else MODEL_FEATURES
            self.scaler = joblib.load(self.SCALER_PATH)
            logger.info(f"Loaded model with {len(self.features)} features")
            return True
        except Exception as e:
            logger.error(f"Isolation Forest load failed: {e}")
            return False

    def score_transaction(self, features: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if self.model is None and not self.load():
            return None

        missing = [f for f in self.features if f not in features]
        if missing:
            logger.warning(f"Missing features: {missing[:5]}...")
            return None

        try:
            x = np.array([[features.get(f, 0) for f in self.features]], dtype=np.float32)
            x_scaled = self.scaler.transform(x)
            prediction = self.model.predict(x_scaled)[0]
            anomaly_score = self.model.decision_function(x_scaled)[0]
            
            is_anomaly = prediction == -1
            return {
                'anomaly_score': float(anomaly_score),
                'prediction': int(prediction),
                'is_anomaly': is_anomaly,
                'reason': (
                    f"Isolation Forest anomaly: score={anomaly_score:.4f}"
                    if is_anomaly else None
                )
            }

        except Exception as e:
            logger.error(f"Scoring failed: {e}")
            return None