import os, json, logging, joblib
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional
from sklearn.preprocessing import StandardScaler
from backend.autoencoder import TransactionAutoencoder
from backend.utils import get_dynamic_model_features

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AutoencoderTrainer:
    DATA_PATH = 'data/feature_datasetv2.csv'
    MODEL_PATH = 'backend/model/autoencoder.h5'
    SCALER_PATH = 'backend/model/autoencoder_scaler.pkl'
    THRESHOLD_PATH = 'backend/model/autoencoder_threshold.json'



    def __init__(self, k: float = 3.0):
        self.k = k
        self.scaler: Optional[StandardScaler] = None
        self.autoencoder: Optional[TransactionAutoencoder] = None

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

    def compute_threshold(self, errors: np.ndarray) -> Dict[str, float]:
        mean, std = float(errors.mean()), float(errors.std())
        return {'threshold': mean + self.k * std, 'mean': mean, 'std': std, 'k': self.k}

    def save_threshold(self, cfg: Dict[str, Any], n_samples: int, n_features: int, feature_list: list):
        self._ensure_dir(self.THRESHOLD_PATH)
        cfg.update({
            'computed_at': datetime.now().isoformat(),
            'n_samples': n_samples,
            'n_features': n_features,
            'features': feature_list
        })
        json.dump(cfg, open(self.THRESHOLD_PATH, 'w'), indent=2)

    def train(self, epochs=100, batch_size=64) -> Dict[str, Any]:
        logger.info("Starting Autoencoder Training")

        df = self.load_data()
        
        dynamic_features = get_dynamic_model_features()
        
        available_features = [f for f in dynamic_features if f in df.columns]
        logger.info(f"Using {len(available_features)} features for training")
        
        X = df[available_features].fillna(0).values
        n_samples, n_features = X.shape

        self.fit_scaler(X)
        Xs = self.scaler.transform(X)

        self.autoencoder = TransactionAutoencoder(
            input_dim=n_features,
            encoding_dim=max(7, n_features // 2),
            hidden_layers=[64, 32]
        )
        self.autoencoder.fit(Xs, epochs=epochs, batch_size=batch_size, verbose=1)
        self._ensure_dir(self.MODEL_PATH)
        self.autoencoder.save(self.MODEL_PATH)

        errors = self.autoencoder.compute_reconstruction_error(Xs)
        cfg = self.compute_threshold(errors)
        self.save_threshold(cfg, n_samples, n_features, available_features)

        logger.info(f"Training done | Threshold={cfg['threshold']:.6f}")
        return {**cfg, 'n_samples': n_samples, 'n_features': n_features, 'feature_list': available_features}

    def validate(self, X_scaled: np.ndarray, expected_errors: np.ndarray, tol=0.01):
        ae = TransactionAutoencoder.load(self.MODEL_PATH)
        errs = ae.compute_reconstruction_error(X_scaled)
        diff = abs(errs.mean() - expected_errors.mean()) / (expected_errors.mean() + 1e-10)
        if diff > tol:
            raise ValueError(f"Validation failed ({diff*100:.2f}%)")
        logger.info("Model validation PASSED")


def train_autoencoder():
    trainer = AutoencoderTrainer()
    metrics = trainer.train()

    df = trainer.load_data()
    dynamic_features = get_dynamic_model_features()
    available_features = [f for f in dynamic_features if f in df.columns]
    
    X = trainer.scaler.transform(df[available_features].fillna(0).values)
    sample = X[:min(1000, len(X))]
    trainer.validate(sample, trainer.autoencoder.compute_reconstruction_error(sample))
    return metrics


if __name__ == "__main__":
    train_autoencoder()
