import os, json, logging, joblib
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional
from sklearn.preprocessing import StandardScaler
from backend.autoencoder import TransactionAutoencoder
from backend.utils import get_dynamic_model_features
from backend.feature_selector import MrMRFeatureSelector

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AutoencoderTrainer:
    DATA_PATH = 'data/feature_datasetv2.csv'
    MODEL_PATH = 'backend/model/autoencoder.h5'
    SCALER_PATH = 'backend/model/autoencoder_scaler.pkl'
    THRESHOLD_PATH = 'backend/model/autoencoder_threshold.json'



    def __init__(self, k: float = 3.0, use_mrmr: bool = True, n_features: int = 15):
        self.k = k
        self.use_mrmr = use_mrmr
        self.n_features = n_features
        self.scaler: Optional[StandardScaler] = None
        self.autoencoder: Optional[TransactionAutoencoder] = None
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
        self.save_threshold(cfg, n_samples, n_features, selected_features)

        logger.info(f"Training done | Threshold={cfg['threshold']:.6f}")
        
        result = {
            **cfg, 
            'n_samples': n_samples, 
            'n_features': n_features, 
            'feature_list': selected_features,
            'mrmr_used': self.use_mrmr and self.feature_selector is not None
        }
        
        if self.feature_selector:
            result['feature_importance'] = self.feature_selector.get_feature_importance()
        
        return result

    def validate(self, X_scaled: np.ndarray, expected_errors: np.ndarray, tol=0.01):
        ae = TransactionAutoencoder.load(self.MODEL_PATH)
        errs = ae.compute_reconstruction_error(X_scaled)
        diff = abs(errs.mean() - expected_errors.mean()) / (expected_errors.mean() + 1e-10)
        if diff > tol:
            raise ValueError(f"Validation failed ({diff*100:.2f}%)")
        logger.info("Model validation PASSED")


def train_autoencoder(use_mrmr: bool = True, n_features: int = 15):
    trainer = AutoencoderTrainer(use_mrmr=use_mrmr, n_features=n_features)
    metrics = trainer.train()

    df = trainer.load_data()
    feature_list = metrics['feature_list']
    
    X = trainer.scaler.transform(df[feature_list].fillna(0).values)
    sample = X[:min(1000, len(X))]
    trainer.validate(sample, trainer.autoencoder.compute_reconstruction_error(sample))
    return metrics


if __name__ == "__main__":
    train_autoencoder()
