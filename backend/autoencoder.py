import os, json, logging, joblib
import numpy as np
from typing import List, Optional, Dict, Any
from .utils import MODEL_FEATURES

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
import tensorflow as tf
from tensorflow import keras
from keras import layers, Model

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TransactionAutoencoder:
    def __init__(self, input_dim: int, encoding_dim: int = 14,
                 hidden_layers: Optional[List[int]] = None):
        self.input_dim = input_dim
        self.encoding_dim = encoding_dim
        self.hidden_layers = hidden_layers or [64, 32]
        self.model = self._build()

    def _build(self) -> Model:
        inp = keras.Input(shape=(self.input_dim,))
        x = inp
        for u in self.hidden_layers:
            x = layers.Dense(u, activation='relu')(x)
            x = layers.BatchNormalization()(x)

        x = layers.Dense(self.encoding_dim, activation='relu', name='bottleneck')(x)

        for u in reversed(self.hidden_layers):
            x = layers.Dense(u, activation='relu')(x)
            x = layers.BatchNormalization()(x)

        out = layers.Dense(self.input_dim)(x)
        model = Model(inp, out, name='transaction_autoencoder')
        model.compile(optimizer='adam', loss='mean_squared_error')
        return model

    def fit(self, X: np.ndarray, epochs=100, batch_size=64,
            validation_split=0.1, verbose=1):
        return self.model.fit(
            X, X,
            epochs=epochs,
            batch_size=batch_size,
            validation_split=validation_split,
            callbacks=[keras.callbacks.EarlyStopping(
                monitor='val_loss', patience=5, restore_best_weights=True
            )],
            verbose=verbose
        )

    def compute_reconstruction_error(self, X: np.ndarray) -> np.ndarray:
        recon = self.model.predict(X, verbose=0)
        return np.mean((X - recon) ** 2, axis=1)

    def save(self, path: str):
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        self.model.save(path)

    @classmethod
    def load(cls, path: str) -> 'TransactionAutoencoder':
        model = keras.models.load_model(path)
        inst = cls.__new__(cls)
        inst.model = model
        inst.input_dim = model.input_shape[1]
        inst.encoding_dim = None
        inst.hidden_layers = None
        return inst

class AutoencoderInference:
    MODEL_PATH = 'backend/model/autoencoder.h5'
    SCALER_PATH = 'backend/model/autoencoder_scaler.pkl'
    THRESHOLD_PATH = 'backend/model/autoencoder_threshold.json'

    def __init__(self):
        self.model = None
        self.scaler = None
        self.threshold = None
        self.features = None

    def load(self) -> bool:
        try:
            self.model = TransactionAutoencoder.load(self.MODEL_PATH)
            self.scaler = joblib.load(self.SCALER_PATH)
            threshold_data = json.load(open(self.THRESHOLD_PATH))
            self.threshold = threshold_data['threshold']
            self.features = threshold_data.get('features', MODEL_FEATURES)
            logger.info(f"Loaded autoencoder with {len(self.features)} features")
            return True
        except Exception as e:
            logger.error(f"Autoencoder load failed: {e}")
            return False

    def score_transaction(self, features: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if self.model is None and not self.load():
            return None

        missing = [f for f in self.features if f not in features]
        if missing:
            logger.warning(f"Missing features: {missing[:5]}...")
            return None

        try:
            feature_values = []
            for f in self.features:
                val = features.get(f, 0.0)
                if val is None or (isinstance(val, float) and not np.isfinite(val)):
                    val = 0.0
                feature_values.append(float(val))
            
            x = np.array([feature_values], dtype=np.float32)
            
            if not np.all(np.isfinite(x)):
                logger.error(f"Invalid input features: {x}")
                return {
                    'reconstruction_error': 999.0,
                    'threshold': self.threshold,
                    'is_anomaly': True,
                    'reason': 'Invalid input features (NaN/Inf)'
                }
            
            x = self.scaler.transform(x)
            
            if not np.all(np.isfinite(x)):
                logger.error(f"Invalid scaled features: {x}")
                return {
                    'reconstruction_error': 999.0,
                    'threshold': self.threshold,
                    'is_anomaly': True,
                    'reason': 'Invalid scaled features (NaN/Inf)'
                }

            error = float(self.model.compute_reconstruction_error(x)[0])
            if not np.isfinite(error):
                logger.error(f"Invalid reconstruction error: {error}")
                return {
                    'reconstruction_error': 999.0,
                    'threshold': self.threshold,
                    'is_anomaly': True,
                    'reason': 'Invalid reconstruction error (NaN/Inf)'
                }

            is_anomaly = error > self.threshold
            return {
                'reconstruction_error': error,
                'threshold': self.threshold,
                'is_anomaly': is_anomaly,
                'reason': (
                    f"Autoencoder anomaly: {error:.4f} > {self.threshold:.4f}"
                    if is_anomaly else None
                )
            }

        except Exception as e:
            logger.error(f"Scoring failed: {e}")
            return None
