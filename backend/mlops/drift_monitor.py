import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import json
import os

try:
    import nannyml as nml
    HAS_NANNYML = True
except ImportError:
    HAS_NANNYML = False

from backend.db_service import get_db_service
from backend.mlops.data_fetcher import get_data_fetcher

logger = logging.getLogger(__name__)

DRIFT_RESULTS_DIR = "backend/model/drift_results"


class DriftMonitor:
    
    def __init__(self):
        if not HAS_NANNYML:
            raise ImportError("NannyML is required. Install with: pip install nannyml")
        
        self.db = get_db_service()
        self.data_fetcher = get_data_fetcher()
        self._ensure_dirs()
        
        self.feature_columns = [
            'AmountInAed',
            'hour_of_day',
            'day_of_week',
            'is_weekend',
            'is_night',
            'txn_count_30s',
            'txn_count_10min',
            'txn_count_1hour',
            'time_since_last_txn',
            'amount_vs_avg',
            'amount_vs_median',
            'is_new_beneficiary'
        ]
        
        self.prediction_column = 'fraud_probability'
        self.timestamp_column = 'CreateDate'
    
    def _ensure_dirs(self):
        os.makedirs(DRIFT_RESULTS_DIR, exist_ok=True)
    
    def prepare_reference_data(self, days_back: int = 90) -> pd.DataFrame:
        try:
            since_date = datetime.now() - timedelta(days=days_back)
            logger.info(f"Fetching reference data from last {days_back} days...")
            
            df = self.data_fetcher.fetch_training_data(since_date)
            
            if df.empty:
                logger.error("No reference data available")
                return pd.DataFrame()
            
            from backend.feature_engineering import engineer_features
            df = engineer_features(df)
            
            logger.info(f"Reference data prepared: {len(df)} records")
            return df
            
        except Exception as e:
            logger.error(f"Error preparing reference data: {e}")
            return pd.DataFrame()
    
    def prepare_analysis_data(self, days_back: int = 7) -> pd.DataFrame:
        try:
            since_date = datetime.now() - timedelta(days=days_back)
            logger.info(f"Fetching analysis data from last {days_back} days...")
            
            df = self.data_fetcher.fetch_training_data(since_date)
            
            if df.empty:
                logger.error("No analysis data available")
                return pd.DataFrame()
            
            from backend.feature_engineering import engineer_features
            df = engineer_features(df)
            
            logger.info(f"Analysis data prepared: {len(df)} records")
            return df
            
        except Exception as e:
            logger.error(f"Error preparing analysis data: {e}")
            return pd.DataFrame()
    
    def detect_univariate_drift(self, reference_data: pd.DataFrame, 
                                analysis_data: pd.DataFrame) -> Dict[str, Any]:
        try:
            logger.info("Running univariate drift detection...")
            
            calc = nml.UnivariateDriftCalculator(
                column_names=self.feature_columns,
                timestamp_column_name=self.timestamp_column,
                continuous_methods=['kolmogorov_smirnov', 'jensen_shannon'],
                categorical_methods=['chi2', 'jensen_shannon']
            )
            
            calc.fit(reference_data)
            
            results = calc.calculate(analysis_data)
            
            drift_summary = {
                'timestamp': datetime.now().isoformat(),
                'features_with_drift': [],
                'drift_scores': {}
            }
            
            for feature in self.feature_columns:
                try:
                    drift_detected = results.filter(column_names=[feature]).to_df()
                    
                    if not drift_detected.empty:
                        has_drift = drift_detected['alert'].any()
                        
                        if has_drift:
                            drift_summary['features_with_drift'].append(feature)
                        
                        drift_summary['drift_scores'][feature] = {
                            'drift_detected': bool(has_drift),
                            'method': 'kolmogorov_smirnov'
                        }
                except Exception as e:
                    logger.warning(f"Could not process drift for feature {feature}: {e}")
            
            logger.info(f"Univariate drift detection complete. Features with drift: {len(drift_summary['features_with_drift'])}")
            
            self._save_drift_results('univariate_drift', drift_summary)
            
            return drift_summary
            
        except Exception as e:
            logger.error(f"Error in univariate drift detection: {e}")
            return {}
    
    def detect_multivariate_drift(self, reference_data: pd.DataFrame,
                                  analysis_data: pd.DataFrame) -> Dict[str, Any]:
        try:
            logger.info("Running multivariate drift detection...")
            
            calc = nml.DataReconstructionDriftCalculator(
                column_names=self.feature_columns,
                timestamp_column_name=self.timestamp_column
            )
            
            calc.fit(reference_data)
            
            results = calc.calculate(analysis_data)
            
            results_df = results.to_df()
            
            drift_summary = {
                'timestamp': datetime.now().isoformat(),
                'drift_detected': bool(results_df['alert'].any()),
                'reconstruction_error_mean': float(results_df['reconstruction_error'].mean()),
                'reconstruction_error_std': float(results_df['reconstruction_error'].std())
            }
            
            logger.info(f"Multivariate drift detection complete. Drift detected: {drift_summary['drift_detected']}")
            
            self._save_drift_results('multivariate_drift', drift_summary)
            
            return drift_summary
            
        except Exception as e:
            logger.error(f"Error in multivariate drift detection: {e}")
            return {}
    
    def estimate_performance(self, reference_data: pd.DataFrame,
                            analysis_data: pd.DataFrame) -> Dict[str, Any]:
        try:
            logger.info("Running performance estimation...")
            
            if self.prediction_column not in reference_data.columns:
                logger.warning(f"Prediction column '{self.prediction_column}' not found. Skipping performance estimation.")
                return {}
            
            estimator = nml.CBPE(
                y_pred_proba=self.prediction_column,
                y_pred='predicted_fraud',
                y_true='is_fraud',
                timestamp_column_name=self.timestamp_column,
                metrics=['roc_auc', 'f1', 'precision', 'recall'],
                problem_type='classification_binary'
            )
            
            estimator.fit(reference_data)
            
            results = estimator.estimate(analysis_data)
            
            results_df = results.to_df()
            
            performance_summary = {
                'timestamp': datetime.now().isoformat(),
                'estimated_metrics': {
                    'roc_auc': float(results_df['roc_auc'].mean()) if 'roc_auc' in results_df else None,
                    'f1': float(results_df['f1'].mean()) if 'f1' in results_df else None,
                    'precision': float(results_df['precision'].mean()) if 'precision' in results_df else None,
                    'recall': float(results_df['recall'].mean()) if 'recall' in results_df else None
                },
                'performance_degradation_detected': bool(results_df['alert'].any()) if 'alert' in results_df else False
            }
            
            logger.info(f"Performance estimation complete. Estimated ROC-AUC: {performance_summary['estimated_metrics']['roc_auc']}")
            
            self._save_drift_results('performance_estimation', performance_summary)
            
            return performance_summary
            
        except Exception as e:
            logger.error(f"Error in performance estimation: {e}")
            return {}
    
    def monitor_concept_drift(self, reference_data: pd.DataFrame,
                             analysis_data: pd.DataFrame) -> Dict[str, Any]:
        try:
            logger.info("Running concept drift monitoring...")
            
            if self.prediction_column not in reference_data.columns:
                logger.warning("Prediction column not found. Cannot monitor concept drift.")
                return {}
            
            ref_predictions = reference_data[self.prediction_column]
            analysis_predictions = analysis_data[self.prediction_column]
            
            from scipy import stats
            
            ks_statistic, ks_pvalue = stats.ks_2samp(ref_predictions, analysis_predictions)
            
            concept_drift_summary = {
                'timestamp': datetime.now().isoformat(),
                'ks_statistic': float(ks_statistic),
                'ks_pvalue': float(ks_pvalue),
                'drift_detected': ks_pvalue < 0.05,
                'reference_mean_prediction': float(ref_predictions.mean()),
                'analysis_mean_prediction': float(analysis_predictions.mean()),
                'prediction_shift': float(analysis_predictions.mean() - ref_predictions.mean())
            }
            
            logger.info(f"Concept drift monitoring complete. Drift detected: {concept_drift_summary['drift_detected']}")
            
            self._save_drift_results('concept_drift', concept_drift_summary)
            
            return concept_drift_summary
            
        except Exception as e:
            logger.error(f"Error in concept drift monitoring: {e}")
            return {}
    
    def run_full_monitoring(self, reference_days: int = 90, 
                           analysis_days: int = 7) -> Dict[str, Any]:
        logger.info("\n" + "="*60)
        logger.info("STARTING DRIFT MONITORING WITH NANNYML")
        logger.info(f"Start Time: {datetime.now()}")
        logger.info("="*60 + "\n")
        
        try:
            reference_data = self.prepare_reference_data(reference_days)
            if reference_data.empty:
                raise Exception("No reference data available")
            
            analysis_data = self.prepare_analysis_data(analysis_days)
            if analysis_data.empty:
                raise Exception("No analysis data available")
            
            results = {
                'timestamp': datetime.now().isoformat(),
                'reference_period_days': reference_days,
                'analysis_period_days': analysis_days,
                'reference_data_size': len(reference_data),
                'analysis_data_size': len(analysis_data)
            }
            
            results['univariate_drift'] = self.detect_univariate_drift(
                reference_data, analysis_data
            )
            
            results['multivariate_drift'] = self.detect_multivariate_drift(
                reference_data, analysis_data
            )
            
            results['concept_drift'] = self.monitor_concept_drift(
                reference_data, analysis_data
            )
            
            results['performance_estimation'] = self.estimate_performance(
                reference_data, analysis_data
            )
            
            results['overall_assessment'] = self._assess_overall_drift(results)
            
            self._save_drift_results('full_monitoring', results)
            
            logger.info("\n" + "="*60)
            logger.info("DRIFT MONITORING COMPLETED")
            logger.info(f"Overall Status: {results['overall_assessment']['status']}")
            logger.info(f"End Time: {datetime.now()}")
            logger.info("="*60 + "\n")
            
            return results
            
        except Exception as e:
            logger.error(f"Drift monitoring failed: {e}")
            return {'error': str(e)}
    
    def _assess_overall_drift(self, results: Dict[str, Any]) -> Dict[str, Any]:
        drift_indicators = []
        
        if results.get('univariate_drift', {}).get('features_with_drift'):
            drift_indicators.append('univariate_drift')
        
        if results.get('multivariate_drift', {}).get('drift_detected'):
            drift_indicators.append('multivariate_drift')
        
        if results.get('concept_drift', {}).get('drift_detected'):
            drift_indicators.append('concept_drift')
        
        if results.get('performance_estimation', {}).get('performance_degradation_detected'):
            drift_indicators.append('performance_degradation')
        
        if len(drift_indicators) >= 3:
            status = 'CRITICAL'
            recommendation = 'Immediate model retraining recommended'
        elif len(drift_indicators) >= 2:
            status = 'WARNING'
            recommendation = 'Model retraining should be scheduled soon'
        elif len(drift_indicators) == 1:
            status = 'CAUTION'
            recommendation = 'Monitor closely, retraining may be needed'
        else:
            status = 'HEALTHY'
            recommendation = 'Model performing well, continue monitoring'
        
        return {
            'status': status,
            'drift_indicators': drift_indicators,
            'drift_count': len(drift_indicators),
            'recommendation': recommendation
        }
    
    def _save_drift_results(self, result_type: str, results: Dict[str, Any]):
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{result_type}_{timestamp}.json"
            filepath = os.path.join(DRIFT_RESULTS_DIR, filename)
            
            with open(filepath, 'w') as f:
                json.dump(results, f, indent=2)
            
            logger.info(f"Drift results saved to {filepath}")
            
        except Exception as e:
            logger.warning(f"Could not save drift results: {e}")
    
    def get_latest_drift_status(self) -> Dict[str, Any]:
        try:
            files = [f for f in os.listdir(DRIFT_RESULTS_DIR) if f.startswith('full_monitoring_')]
            if not files:
                return {'status': 'NO_DATA', 'message': 'No drift monitoring results available'}
            
            latest_file = sorted(files)[-1]
            filepath = os.path.join(DRIFT_RESULTS_DIR, latest_file)
            
            with open(filepath, 'r') as f:
                results = json.load(f)
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting latest drift status: {e}")
            return {'status': 'ERROR', 'message': str(e)}


def get_drift_monitor() -> DriftMonitor:
    return DriftMonitor()


def run_drift_monitoring():
    monitor = get_drift_monitor()
    return monitor.run_full_monitoring()
