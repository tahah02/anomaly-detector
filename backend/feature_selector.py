import pandas as pd
import numpy as np
from mrmr import mrmr_classif
from typing import List, Dict, Tuple
import logging
from backend.db_service import get_db_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MrMRFeatureSelector:
    def __init__(self, n_features: int = 15):
        self.n_features = n_features
        self.selected_features = []
        self.feature_scores = {}
        
    def select_features(self, X: pd.DataFrame, y: pd.Series) -> List[str]:
        try:
            logger.info(f"Starting MrMR feature selection with {X.shape[1]} features")
            
            numeric_cols = X.select_dtypes(include=[np.number]).columns.tolist()
            X_numeric = X[numeric_cols].copy()
            
            for col in X_numeric.columns:
                if X_numeric[col].isnull().any():
                    X_numeric[col].fillna(X_numeric[col].median(), inplace=True)
            
            if len(numeric_cols) <= self.n_features:
                logger.warning(f"Number of features ({len(numeric_cols)}) <= n_features ({self.n_features}), returning all")
                self.selected_features = numeric_cols
                self.feature_scores = {f: 1.0 for f in numeric_cols}
                return self.selected_features
            
            selected = mrmr_classif(X=X_numeric, y=y, K=min(self.n_features, len(numeric_cols)))
            
            self.selected_features = selected
            self.feature_scores = {f: float(len(selected) - i) / len(selected) for i, f in enumerate(selected)}
            
            logger.info(f"Selected {len(self.selected_features)} features using MrMR")
            logger.info(f"Top 5 features: {self.selected_features[:5]}")
            
            return self.selected_features
            
        except Exception as e:
            logger.error(f"Error in MrMR feature selection: {e}")
            return X.columns.tolist()
    
    def get_feature_importance(self) -> Dict[str, float]:
        return self.feature_scores
    
    def save_to_db(self, model_version: str):
        try:
            db = get_db_service()
            if not db.is_connected():
                if not db.connect():
                    logger.error("Cannot connect to database")
                    return False
            
            ph = db.param_placeholder
            
            for rank, feature_name in enumerate(self.selected_features, 1):
                score = self.feature_scores.get(feature_name, 0.0)
                
                check_query = f"SELECT FeatureID FROM FeaturesConfig WHERE FeatureName = {ph}"
                existing = db.execute_query(check_query, [feature_name])
                
                if not existing.empty:
                    update_query = f"""
                    UPDATE FeaturesConfig 
                    SET MrMRScore = {ph}, FeatureRank = {ph}, Version = {ph}, 
                        IsEnabled = 1, IsActive = 1, UpdatedAt = GETDATE()
                    WHERE FeatureName = {ph}
                    """
                    params = [score, rank, model_version, feature_name]
                    db.execute_non_query(update_query, params)
                else:
                    insert_query = f"""
                    INSERT INTO FeaturesConfig 
                    (FeatureName, MrMRScore, FeatureRank, IsEnabled, IsActive, Version, 
                     FeatureType, CreatedAt, UpdatedAt)
                    VALUES ({ph}, {ph}, {ph}, 1, 1, {ph}, 'mrmr_selected', GETDATE(), GETDATE())
                    """
                    params = [feature_name, score, rank, model_version]
                    db.execute_non_query(insert_query, params)
            
            logger.info(f"Saved {len(self.selected_features)} features to FeaturesConfig for version {model_version}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving features to database: {e}")
            return False
        finally:
            db.disconnect()

def load_selected_features(model_version: str = None) -> List[str]:
    try:
        db = get_db_service()
        if not db.is_connected():
            if not db.connect():
                logger.error("Cannot connect to database")
                return []
        
        ph = db.param_placeholder
        
        if model_version:
            query = f"""
            SELECT FeatureName FROM FeaturesConfig 
            WHERE Version = {ph} AND IsEnabled = 1 AND MrMRScore IS NOT NULL
            ORDER BY FeatureRank
            """
            params = [model_version]
        else:
            query = """
            SELECT FeatureName FROM FeaturesConfig 
            WHERE IsEnabled = 1 AND MrMRScore IS NOT NULL
            ORDER BY FeatureRank
            """
            params = None
        
        result = db.execute_query(query, params)
        
        if result is not None and not result.empty:
            features = result['FeatureName'].tolist()
            logger.info(f"Loaded {len(features)} selected features from FeaturesConfig")
            return features
        
        logger.warning("No selected features found in FeaturesConfig")
        return []
        
    except Exception as e:
        logger.error(f"Error loading selected features: {e}")
        return []
    finally:
        db.disconnect()

def get_feature_selection_history() -> pd.DataFrame:
    try:
        db = get_db_service()
        if not db.is_connected():
            if not db.connect():
                return pd.DataFrame()
        
        query = """
        SELECT Version, FeatureName, MrMRScore, FeatureRank, UpdatedAt
        FROM FeaturesConfig
        WHERE MrMRScore IS NOT NULL
        ORDER BY Version DESC, FeatureRank
        """
        
        result = db.execute_query(query)
        return result
        
    except Exception as e:
        logger.error(f"Error getting feature selection history: {e}")
        return pd.DataFrame()
    finally:
        db.disconnect()

def compare_feature_sets(version1: str, version2: str) -> Dict[str, List[str]]:
    try:
        features_v1 = set(load_selected_features(version1))
        features_v2 = set(load_selected_features(version2))
        
        added = list(features_v2 - features_v1)
        removed = list(features_v1 - features_v2)
        common = list(features_v1 & features_v2)
        
        return {
            'added': added,
            'removed': removed,
            'common': common
        }
        
    except Exception as e:
        logger.error(f"Error comparing feature sets: {e}")
        return {'added': [], 'removed': [], 'common': []}

def get_db_service():
    from backend.db_service import DatabaseService
    return DatabaseService()
