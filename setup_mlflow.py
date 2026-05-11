#!/usr/bin/env python
"""
MLflow Setup Script
Initializes MLflow configuration and creates necessary directories
"""

import os
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_mlflow():
    """Initialize MLflow configuration"""
    try:
        logger.info("=" * 60)
        logger.info("MLflow Setup Started")
        logger.info("=" * 60)
        
        # Import MLflow config
        from backend.mlops.mlflow_config import initialize_mlflow
        
        # Initialize
        config = initialize_mlflow()
        
        logger.info("\n✅ MLflow initialized successfully!")
        logger.info(f"   Tracking URI: {config.tracking_uri}")
        logger.info(f"   Artifact Root: {config.artifact_root}")
        
        # Create directories
        Path("backend/mlops/mlruns").mkdir(parents=True, exist_ok=True)
        Path("backend/mlops/mlruns/artifacts").mkdir(parents=True, exist_ok=True)
        
        logger.info("\n✅ Directories created successfully!")
        
        # List experiments
        experiments = config.client.list_experiments()
        logger.info(f"\n✅ {len(experiments)} experiments initialized:")
        for exp in experiments:
            logger.info(f"   - {exp.name} (ID: {exp.experiment_id})")
        
        logger.info("\n" + "=" * 60)
        logger.info("MLflow Setup Completed Successfully!")
        logger.info("=" * 60)
        logger.info("\nNext Steps:")
        logger.info("1. Run your training pipeline")
        logger.info("2. Access MLflow Dashboard:")
        logger.info("   - From ConfigManagementUI: Config → MLflow Dashboard")
        logger.info("   - Or command line: mlflow ui --backend-store-uri file:backend/mlops/mlruns")
        logger.info("3. View experiments at http://localhost:5000")
        
        return True
        
    except Exception as e:
        logger.error(f"\n❌ MLflow Setup Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_dependencies():
    """Verify required dependencies are installed"""
    logger.info("\nVerifying dependencies...")
    
    dependencies = {
        'mlflow': 'MLflow',
        'polars': 'Polars',
        'pandas': 'Pandas',
        'sklearn': 'Scikit-learn'
    }
    
    missing = []
    for module, name in dependencies.items():
        try:
            __import__(module)
            logger.info(f"   ✅ {name}")
        except ImportError:
            logger.warning(f"   ❌ {name} - NOT INSTALLED")
            missing.append(name)
    
    if missing:
        logger.error(f"\n❌ Missing dependencies: {', '.join(missing)}")
        logger.error("   Run: pip install -r requirements.txt")
        return False
    
    logger.info("\n✅ All dependencies installed!")
    return True


if __name__ == "__main__":
    logger.info("MLflow Setup Script")
    logger.info("=" * 60)
    
    # Verify dependencies
    if not verify_dependencies():
        sys.exit(1)
    
    # Setup MLflow
    if not setup_mlflow():
        sys.exit(1)
    
    sys.exit(0)
