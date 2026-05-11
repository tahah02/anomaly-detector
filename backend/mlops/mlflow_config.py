import os
import logging
from pathlib import Path
import mlflow
from mlflow.tracking import MlflowClient

logger = logging.getLogger(__name__)

# MLflow Configuration
MLFLOW_TRACKING_DIR = os.getenv("MLFLOW_TRACKING_DIR", "backend/mlops/mlruns")
MLFLOW_BACKEND_STORE_URI = f"file:{os.path.abspath(MLFLOW_TRACKING_DIR)}"
MLFLOW_ARTIFACT_ROOT = os.path.join(MLFLOW_TRACKING_DIR, "artifacts")

# Experiment Names
EXPERIMENT_ISOLATION_FOREST = "isolation_forest_training"
EXPERIMENT_AUTOENCODER = "autoencoder_training"
EXPERIMENT_HYBRID = "hybrid_model_training"
EXPERIMENT_DRIFT = "drift_monitoring"

# Model Registry Names
MODEL_ISOLATION_FOREST = "isolation_forest_model"
MODEL_AUTOENCODER = "autoencoder_model"
MODEL_HYBRID = "hybrid_anomaly_detector"


class MLflowConfig:
    """Centralized MLflow configuration and initialization"""
    
    def __init__(self):
        self.client = None
        self.tracking_uri = MLFLOW_BACKEND_STORE_URI
        self.artifact_root = MLFLOW_ARTIFACT_ROOT
        self._initialize()
    
    def _initialize(self):
        """Initialize MLflow tracking and create necessary directories"""
        try:
            # Create directories
            Path(MLFLOW_TRACKING_DIR).mkdir(parents=True, exist_ok=True)
            Path(MLFLOW_ARTIFACT_ROOT).mkdir(parents=True, exist_ok=True)
            
            # Set tracking URI
            mlflow.set_tracking_uri(self.tracking_uri)
            self.client = MlflowClient(tracking_uri=self.tracking_uri)
            
            logger.info(f"MLflow initialized with tracking URI: {self.tracking_uri}")
            logger.info(f"Artifact root: {self.artifact_root}")
            
            # Create experiments if they don't exist
            self._create_experiments()
            
        except Exception as e:
            logger.error(f"Error initializing MLflow: {e}")
            raise
    
    def _create_experiments(self):
        """Create default experiments if they don't exist"""
        experiments = [
            EXPERIMENT_ISOLATION_FOREST,
            EXPERIMENT_AUTOENCODER,
            EXPERIMENT_HYBRID,
            EXPERIMENT_DRIFT
        ]
        
        for exp_name in experiments:
            try:
                exp = self.client.get_experiment_by_name(exp_name)
                if exp is None:
                    self.client.create_experiment(exp_name)
                    logger.info(f"Created experiment: {exp_name}")
                else:
                    logger.info(f"Experiment already exists: {exp_name}")
            except Exception as e:
                logger.warning(f"Could not create experiment {exp_name}: {e}")
    
    def get_experiment_id(self, experiment_name: str) -> str:
        """Get experiment ID by name"""
        try:
            exp = self.client.get_experiment_by_name(experiment_name)
            if exp:
                return exp.experiment_id
            else:
                logger.warning(f"Experiment not found: {experiment_name}")
                return None
        except Exception as e:
            logger.error(f"Error getting experiment ID: {e}")
            return None
    
    def start_run(self, experiment_name: str, run_name: str = None, tags: dict = None):
        """Start a new MLflow run"""
        try:
            exp_id = self.get_experiment_id(experiment_name)
            if exp_id:
                mlflow.start_run(experiment_id=exp_id, run_name=run_name, tags=tags)
                logger.info(f"Started MLflow run: {run_name} in experiment: {experiment_name}")
            else:
                logger.warning(f"Could not start run - experiment not found: {experiment_name}")
        except Exception as e:
            logger.error(f"Error starting MLflow run: {e}")
    
    def end_run(self):
        """End the current MLflow run"""
        try:
            mlflow.end_run()
            logger.info("MLflow run ended")
        except Exception as e:
            logger.error(f"Error ending MLflow run: {e}")
    
    def log_params(self, params: dict):
        """Log parameters to MLflow"""
        try:
            for key, value in params.items():
                mlflow.log_param(key, value)
            logger.info(f"Logged {len(params)} parameters to MLflow")
        except Exception as e:
            logger.error(f"Error logging parameters: {e}")
    
    def log_metrics(self, metrics: dict, step: int = None):
        """Log metrics to MLflow"""
        try:
            for key, value in metrics.items():
                if isinstance(value, (int, float)):
                    mlflow.log_metric(key, value, step=step)
            logger.info(f"Logged {len(metrics)} metrics to MLflow")
        except Exception as e:
            logger.error(f"Error logging metrics: {e}")
    
    def log_artifact(self, local_path: str, artifact_path: str = None):
        """Log artifact to MLflow"""
        try:
            if os.path.isfile(local_path):
                mlflow.log_artifact(local_path, artifact_path)
            elif os.path.isdir(local_path):
                mlflow.log_artifacts(local_path, artifact_path)
            logger.info(f"Logged artifact: {local_path}")
        except Exception as e:
            logger.error(f"Error logging artifact: {e}")
    
    def register_model(self, model_uri: str, model_name: str):
        """Register model in MLflow Model Registry"""
        try:
            mlflow.register_model(model_uri, model_name)
            logger.info(f"Registered model: {model_name}")
        except Exception as e:
            logger.error(f"Error registering model: {e}")
    
    def get_model_version(self, model_name: str, stage: str = "Production"):
        """Get model version by stage"""
        try:
            versions = self.client.get_latest_versions(model_name, stages=[stage])
            if versions:
                return versions[0]
            return None
        except Exception as e:
            logger.error(f"Error getting model version: {e}")
            return None
    
    def transition_model_stage(self, model_name: str, version: int, stage: str):
        """Transition model to a new stage"""
        try:
            self.client.transition_model_version_stage(
                name=model_name,
                version=version,
                stage=stage
            )
            logger.info(f"Transitioned {model_name} v{version} to {stage}")
        except Exception as e:
            logger.error(f"Error transitioning model stage: {e}")
    
    def get_run_history(self, experiment_name: str, limit: int = 10):
        """Get recent runs from an experiment"""
        try:
            exp_id = self.get_experiment_id(experiment_name)
            if exp_id:
                runs = self.client.search_runs(
                    experiment_ids=[exp_id],
                    order_by=["start_time DESC"],
                    max_results=limit
                )
                return runs
            return []
        except Exception as e:
            logger.error(f"Error getting run history: {e}")
            return []


# Global MLflow config instance
_mlflow_config = None


def get_mlflow_config() -> MLflowConfig:
    """Get or create MLflow config instance"""
    global _mlflow_config
    if _mlflow_config is None:
        _mlflow_config = MLflowConfig()
    return _mlflow_config


def initialize_mlflow():
    """Initialize MLflow on application startup"""
    try:
        config = get_mlflow_config()
        logger.info("MLflow initialized successfully")
        return config
    except Exception as e:
        logger.error(f"Failed to initialize MLflow: {e}")
        raise
