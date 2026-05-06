import os, json, logging, joblib
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from backend.utils import get_dynamic_model_features

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class IsolationForestTrainer:
    DATA_PATH = 'data/feature_datasetv2.csv'
    MODEL_PATH = 'backend/model/isolation_forest.pkl'
    SCALER_PATH = 'backend/model/isolation_forest_scaler.pkl'

    def __init__(self, contamination: float = 0.05, n_estimators: int = 100):
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.scaler: Optional[StandardScaler] = None
        self.model: Optional[IsolationForest] = None

    def _ensure_dir(self, path: str):
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)

    def load_data(self) -> pd.DataFrame:
        for p in [self.DATA_PATH, 'feature_datasetv2.csv']:
            if os.path.exists(p):
                logger.info(f"Loading data: {p}")
                return pd.read_csv(p)
        raise FileNotFoundError("feature_datasetv2.csv not found")

    def fit_scaler(self, X: np.ndarray):
        self.scaler = StandardScaler().fit(X)
        self._ensure_dir(self.SCALER_PATH)
        joblib.dump(self.scaler, self.SCALER_PATH)

    def train(self) -> Dict[str, Any]:
        logger.info("Starting Isolation Forest Training")

        df = self.load_data()
        
        dynamic_features = get_dynamic_model_features()
        
        available_features = [f for f in dynamic_features if f in df.columns]
        logger.info(f"Using {len(available_features)} features for training")
        
        X = df[available_features].fillna(0).values
        n_samples, n_features = X.shape

        self.fit_scaler(X)
        X_scaled = self.scaler.transform(X)

        self.model = IsolationForest(
            n_estimators=self.n_estimators,
            contamination=self.contamination,
            random_state=42,
            n_jobs=-1
        )
        self.model.fit(X_scaled)

        self._ensure_dir(self.MODEL_PATH)
        model_data = {
            'model': self.model,
            'features': available_features,
            'contamination': self.contamination,
            'n_estimators': self.n_estimators,
            'trained_at': datetime.now().isoformat()
        }
        joblib.dump(model_data, self.MODEL_PATH)

        predictions = self.model.predict(X_scaled)
        anomaly_count = np.sum(predictions == -1)
        anomaly_rate = anomaly_count / len(predictions)

        logger.info(f"Training done | Anomalies: {anomaly_count}/{len(predictions)} ({anomaly_rate:.2%})")
        return {
            'n_samples': n_samples,
            'n_features': n_features,
            'feature_list': available_features,
            'anomaly_count': int(anomaly_count),
            'anomaly_rate': float(anomaly_rate),
            'contamination': self.contamination
        }

    def validate(self, X_scaled: np.ndarray, expected_anomaly_rate: float, tolerance=0.10):
        if self.model is None:
            raise ValueError("Model not trained yet")
        
        predictions = self.model.predict(X_scaled)
        actual_rate = np.sum(predictions == -1) / len(predictions)
        diff = abs(actual_rate - expected_anomaly_rate)
        
        if diff > tolerance:
            raise ValueError(f"Validation failed: anomaly rate {actual_rate:.2%} vs expected {expected_anomaly_rate:.2%}")
        logger.info("Model validation PASSED")


def train_isolation_forest():
    trainer = IsolationForestTrainer()
    metrics = trainer.train()

    df = trainer.load_data()
    dynamic_features = get_dynamic_model_features()
    available_features = [f for f in dynamic_features if f in df.columns]
    
    X = trainer.scaler.transform(df[available_features].fillna(0).values)
    sample = X[:min(1000, len(X))]
    trainer.validate(sample, metrics['anomaly_rate'])
    return metrics


if __name__ == "__main__":
    train_isolation_forest()