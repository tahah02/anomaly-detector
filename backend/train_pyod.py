import os, json, logging, joblib
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.preprocessing import StandardScaler
from pyod.models.lof import LOF
from backend.utils import get_dynamic_model_features
import mlflow
import mlflow.sklearn

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PyODTrainer:
    DATA_PATH = 'data/feature_datasetv2.csv'
    MODEL_PATH = 'backend/model/pyod_model.pkl'
    SCALER_PATH = 'backend/model/pyod_scaler.pkl'
    CONFIG_PATH = 'backend/model/pyod_config.json'

    def __init__(self, n_neighbors: int = 20, contamination: float = 0.1):
        self.n_neighbors = n_neighbors
        self.contamination = contamination
        self.scaler = None
        self.model = None

    def _ensure_dir(self, path: str):
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)

    def load_data(self) -> pd.DataFrame:
        for p in [self.DATA_PATH, 'feature_datasetv2.csv']:
            if os.path.exists(p):
                logger.info(f"Loading data: {p}")
                return pd.read_csv(p)
        raise FileNotFoundError("feature_datasetv2.csv not found")

    def train(self):
        logger.info("Starting PyOD LOF Training")
        
        mlflow.set_experiment("anomaly_detector")
        
        with mlflow.start_run(run_name="pyod_lof_training"):
            df = self.load_data()
            
            dynamic_features = get_dynamic_model_features()
            available_features = [f for f in dynamic_features if f in df.columns]
            logger.info(f"Using {len(available_features)} features")
            
            X = df[available_features].fillna(0).values
            n_samples, n_features = X.shape
            
            mlflow.log_params({
                "model_type": "LOF",
                "n_neighbors": self.n_neighbors,
                "contamination": self.contamination,
                "n_features": n_features
            })
            
            self.scaler = StandardScaler().fit(X)
            X_scaled = self.scaler.transform(X)
            
            self.model = LOF(
                n_neighbors=self.n_neighbors,
                contamination=self.contamination,
                n_jobs=-1
            )
            self.model.fit(X_scaled)
            
            scores = self.model.decision_function(X_scaled)
            threshold = np.percentile(scores, 90)
            
            self._ensure_dir(self.MODEL_PATH)
            
            model_data = {
                'model': self.model,
                'features': available_features,
                'threshold': float(threshold),
                'trained_at': datetime.now().isoformat()
            }
            joblib.dump(model_data, self.MODEL_PATH)
            joblib.dump(self.scaler, self.SCALER_PATH)
            
            config = {
                'model_type': 'LOF',
                'n_neighbors': self.n_neighbors,
                'contamination': self.contamination,
                'threshold': float(threshold),
                'features': available_features,
                'trained_at': datetime.now().isoformat()
            }
            with open(self.CONFIG_PATH, 'w') as f:
                json.dump(config, f, indent=2)
            
            predictions = self.model.predict(X_scaled)
            anomaly_count = np.sum(predictions == 1)
            anomaly_rate = anomaly_count / len(predictions)
            
            mlflow.log_metrics({
                "anomaly_rate": float(anomaly_rate),
                "anomaly_count": int(anomaly_count),
                "threshold": float(threshold),
                "n_samples": n_samples
            })
            
            mlflow.log_artifact(self.MODEL_PATH)
            mlflow.log_artifact(self.SCALER_PATH)
            mlflow.log_artifact(self.CONFIG_PATH)
            
            logger.info(f"Training done | Anomalies: {anomaly_count}/{n_samples} ({anomaly_rate:.2%})")
            logger.info(f"Threshold: {threshold:.4f}")
            
            return {
                'n_samples': n_samples,
                'n_features': n_features,
                'anomaly_count': int(anomaly_count),
                'anomaly_rate': float(anomaly_rate),
                'threshold': float(threshold)
            }

def train_pyod():
    trainer = PyODTrainer()
    return trainer.train()

if __name__ == "__main__":
    train_pyod()
