import os, json, logging, joblib
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from backend.utils import get_dynamic_model_features
from backend.feature_selector import MrMRFeatureSelector

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class IsolationForestTrainer:
    DATA_PATH = 'data/feature_datasetv2.csv'
    MODEL_PATH = 'backend/model/isolation_forest.pkl'
    SCALER_PATH = 'backend/model/isolation_forest_scaler.pkl'

    def __init__(self, contamination: float = 0.05, n_estimators: int = 100, use_mrmr: bool = True, n_features: int = 15):
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.use_mrmr = use_mrmr
        self.n_features = n_features
        self.scaler: Optional[StandardScaler] = None
        self.model: Optional[IsolationForest] = None
        self.feature_selector: Optional[MrMRFeatureSelector] = None

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
        
        selected_features = available_features
        
        if self.use_mrmr and len(available_features) > self.n_features:
            logger.info(f"Running MrMR feature selection to select top {self.n_features} features")
            
            try:
                y = (df[available_features].fillna(0).std(axis=1) > df[available_features].fillna(0).std(axis=1).median()).astype(int)
                
                self.feature_selector = MrMRFeatureSelector(n_features=self.n_features)
                selected_features = self.feature_selector.select_features(
                    X=df[available_features].fillna(0),
                    y=y
                )
                
                model_version = datetime.now().strftime("%Y%m%d_%H%M%S")
                self.feature_selector.save_to_db(model_version)
                
                logger.info(f"MrMR selected {len(selected_features)} features")
                logger.info(f"Selected features: {selected_features[:10]}...")
                
            except Exception as e:
                logger.error(f"MrMR feature selection failed: {e}")
                logger.info("Falling back to all available features")
                selected_features = available_features
        
        X = df[selected_features].fillna(0).values
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
            'features': selected_features,
            'contamination': self.contamination,
            'n_estimators': self.n_estimators,
            'trained_at': datetime.now().isoformat(),
            'mrmr_used': self.use_mrmr and self.feature_selector is not None
        }
        joblib.dump(model_data, self.MODEL_PATH)

        predictions = self.model.predict(X_scaled)
        anomaly_count = np.sum(predictions == -1)
        anomaly_rate = anomaly_count / len(predictions)

        logger.info(f"Training done | Anomalies: {anomaly_count}/{len(predictions)} ({anomaly_rate:.2%})")
        
        result = {
            'n_samples': n_samples,
            'n_features': n_features,
            'feature_list': selected_features,
            'anomaly_count': int(anomaly_count),
            'anomaly_rate': float(anomaly_rate),
            'contamination': self.contamination,
            'mrmr_used': self.use_mrmr and self.feature_selector is not None
        }
        
        if self.feature_selector:
            result['feature_importance'] = self.feature_selector.get_feature_importance()
        
        return result

    def validate(self, X_scaled: np.ndarray, expected_anomaly_rate: float, tolerance=0.10):
        if self.model is None:
            raise ValueError("Model not trained yet")
        
        predictions = self.model.predict(X_scaled)
        actual_rate = np.sum(predictions == -1) / len(predictions)
        diff = abs(actual_rate - expected_anomaly_rate)
        
        if diff > tolerance:
            raise ValueError(f"Validation failed: anomaly rate {actual_rate:.2%} vs expected {expected_anomaly_rate:.2%}")
        logger.info("Model validation PASSED")


def train_isolation_forest(use_mrmr: bool = True, n_features: int = 15):
    trainer = IsolationForestTrainer(use_mrmr=use_mrmr, n_features=n_features)
    metrics = trainer.train()

    df = trainer.load_data()
    feature_list = metrics['feature_list']
    
    X = trainer.scaler.transform(df[feature_list].fillna(0).values)
    sample = X[:min(1000, len(X))]
    trainer.validate(sample, metrics['anomaly_rate'])
    return metrics


if __name__ == "__main__":
    train_isolation_forest()