import os, json, logging, joblib
import numpy as np
from typing import Dict, Any, Optional
from pyod.models.lof import LOF
from .utils import MODEL_FEATURES

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PyODInference:
    MODEL_PATH = 'backend/model/pyod_model.pkl'
    SCALER_PATH = 'backend/model/pyod_scaler.pkl'
    CONFIG_PATH = 'backend/model/pyod_config.json'

    def __init__(self):
        self.model = None
        self.scaler = None
        self.threshold = None
        self.features = None

    def load(self) -> bool:
        try:
            model_data = joblib.load(self.MODEL_PATH)
            self.model = model_data['model']
            self.features = model_data.get('features', MODEL_FEATURES)
            self.threshold = model_data.get('threshold', 0.5)
            
            if os.path.exists(self.SCALER_PATH):
                self.scaler = joblib.load(self.SCALER_PATH)
            
            try:
                from backend.db_service import get_db_service
                db = get_db_service()
                if db.connect():
                    query = """
                        SELECT ThresholdValue 
                        FROM ThresholdConfig 
                        WHERE ThresholdName = 'pyod_threshold' 
                        AND IsActive = 1
                    """
                    result = db.execute_query(query)
                    if not result.empty:
                        self.threshold = float(result['ThresholdValue'].iloc[0])
                        logger.info(f"Loaded PyOD threshold from DATABASE: {self.threshold}")
                    db.disconnect()
            except Exception as db_error:
                logger.warning(f"Database error: {db_error}, using model threshold")
            
            logger.info(f"Loaded PyOD model with {len(self.features)} features")
            return True
        except Exception as e:
            logger.error(f"PyOD load failed: {e}")
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
            
            if self.scaler is not None:
                x = self.scaler.transform(x)
            
            anomaly_score = float(self.model.decision_function(x)[0])
            prediction = int(self.model.predict(x)[0])
            
            normalized_score = min(max(anomaly_score / (self.threshold * 2), 0), 1)
            is_anomaly = anomaly_score > self.threshold
            
            return {
                'anomaly_score': anomaly_score,
                'normalized_score': normalized_score,
                'prediction': prediction,
                'is_anomaly': is_anomaly,
                'threshold': float(self.threshold),
                'reason': (
                    f"PyOD anomaly: score={anomaly_score:.4f} > threshold={self.threshold:.4f}"
                    if is_anomaly else None
                )
            }

        except Exception as e:
            logger.error(f"PyOD scoring failed: {e}")
            return None
