import logging
from datetime import datetime
from typing import Dict, Any, Optional
import pandas as pd
import json

from backend.mlops.data_fetcher import get_data_fetcher
from backend.mlops.model_versioning import get_versioning
from backend.feature_engineering import engineer_features
from backend.train_isolation_forest import IsolationForestTrainer
from backend.train_autoencoder import AutoencoderTrainer
from backend.db_service import get_db_service

logger = logging.getLogger(__name__)


class RetrainingPipeline:
    def __init__(self):
        self.data_fetcher = get_data_fetcher()
        self.versioning = get_versioning()
        self.db = get_db_service()
    
    def fetch_data(self, since_date: Optional[datetime] = None) -> pd.DataFrame:
        logger.info("STEP 1: Fetching training data...")
        df = self.data_fetcher.fetch_training_data(since_date)
        if df.empty:
            logger.error("No training data fetched!")
            return pd.DataFrame()
        logger.info(f"Fetched {len(df)} records")
        return df
    
    def engineer_features_step(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("STEP 2: Engineering features...")
        try:
            enabled_features = self.db.get_enabled_features()
            logger.info(f"Enabled features: {len(enabled_features)}")
            df_engineered = engineer_features(df)
            logger.info(f"Engineered features, shape: {df_engineered.shape}")
            return df_engineered
        except Exception as e:
            logger.error(f"Error engineering features: {e}")
            return pd.DataFrame()
    
    def train_isolation_forest(self, df: pd.DataFrame) -> Dict[str, Any]:
        logger.info("STEP 3: Training Isolation Forest...")
        try:
            trainer = IsolationForestTrainer()
            metrics = trainer.train()
            logger.info(f"Isolation Forest trained - Samples: {metrics.get('n_samples')}, Anomalies: {metrics.get('anomaly_count')}")
            return metrics
        except Exception as e:
            logger.error(f"Error training Isolation Forest: {e}")
            return {}
    
    def train_autoencoder(self, df: pd.DataFrame) -> Dict[str, Any]:
        logger.info("STEP 4: Training Autoencoder...")
        try:
            trainer = AutoencoderTrainer()
            metrics = trainer.train()
            logger.info(f"Autoencoder trained - Samples: {metrics.get('n_samples')}, Threshold: {metrics.get('threshold'):.6f}")
            return metrics
        except Exception as e:
            logger.error(f"Error training Autoencoder: {e}")
            return {}
    
    def validate_models(self, if_metrics: Dict, ae_metrics: Dict) -> bool:
        logger.info("STEP 5: Validating models...")
        try:
            if not if_metrics or not ae_metrics:
                logger.error("Missing metrics for validation")
                return False
            logger.info("Models validated successfully")
            return True
        except Exception as e:
            logger.error(f"Error validating models: {e}")
            return False
    
    def save_models(self, version: str, if_metrics: Dict, ae_metrics: Dict) -> bool:
        logger.info("STEP 6: Saving versioned models...")
        try:
            if_trainer = IsolationForestTrainer()
            ae_trainer = AutoencoderTrainer()
            
            self.versioning.save_model_version(
                if_trainer.model, 
                if_trainer.scaler, 
                version, 
                'isolation_forest', 
                if_metrics
            )
            
            self.versioning.save_model_version(
                ae_trainer.autoencoder, 
                ae_trainer.scaler, 
                version, 
                'autoencoder', 
                ae_metrics
            )
            
            logger.info(f"Models saved for version {version}")
            return True
        except Exception as e:
            logger.error(f"Error saving models: {e}")
            return False
    
    def update_version(self, version: str) -> bool:
        logger.info("STEP 7: Updating current version...")
        try:
            self.versioning.set_current_version(version)
            logger.info(f"Current version updated to {version}")
            return True
        except Exception as e:
            logger.error(f"Error updating version: {e}")
            return False
    
    def log_training_run(self, version: str, status: str, if_metrics: Dict, ae_metrics: Dict):
        try:
            query = "INSERT INTO ModelTrainingRuns (RunDate, ModelVersion, Status, DataSize, Metrics) VALUES (%s, %s, %s, %s, %s)"
            metrics_json = {'isolation_forest': if_metrics, 'autoencoder': ae_metrics}
            self.db.execute_non_query(query, [datetime.now(), version, status, 0, json.dumps(metrics_json)])
            logger.info(f"Training run logged for version {version}")
        except Exception as e:
            logger.warning(f"Could not log training run: {e}")
    
    def run(self, since_date: Optional[datetime] = None, auto_update: bool = False) -> bool:
        logger.info("\n" + "="*60)
        logger.info("STARTING MODEL RETRAINING PIPELINE")
        logger.info(f"Start Time: {datetime.now()}")
        logger.info(f"Auto Update Version: {auto_update}")
        logger.info("="*60 + "\n")
        
        try:
            df = self.fetch_data(since_date)
            if df.empty:
                raise Exception("No training data available")
            
            df_engineered = self.engineer_features_step(df)
            if df_engineered.empty:
                raise Exception("Feature engineering failed")
            
            if_metrics = self.train_isolation_forest(df_engineered)
            if not if_metrics:
                raise Exception("Isolation Forest training failed")
            
            ae_metrics = self.train_autoencoder(df_engineered)
            if not ae_metrics:
                raise Exception("Autoencoder training failed")
            
            if not self.validate_models(if_metrics, ae_metrics):
                raise Exception("Model validation failed")
            
            version = self.versioning.get_next_version()
            
            if not self.save_models(version, if_metrics, ae_metrics):
                raise Exception("Model saving failed")
            if auto_update:
                if not self.update_version(version):
                    raise Exception("Version update failed")
                logger.info(f"Version automatically updated to {version}")
            else:
                logger.info(f"Version {version} saved. Manual selection required via config screen.")
            
            self.log_training_run(version, "SUCCESS", if_metrics, ae_metrics)
            
            logger.info("\n" + "="*60)
            logger.info("RETRAINING PIPELINE COMPLETED SUCCESSFULLY")
            logger.info(f"New Version: {version}")
            logger.info(f"End Time: {datetime.now()}")
            logger.info("="*60 + "\n")
            
            return True
            
        except Exception as e:
            logger.error(f"\nRETRAINING PIPELINE FAILED: {e}\n")
            version = self.versioning.get_next_version()
            self.log_training_run(version, "FAILED", {}, {})
            return False


def get_pipeline() -> RetrainingPipeline:
    return RetrainingPipeline()


def run_retraining():
    pipeline = get_pipeline()
    return pipeline.run()
