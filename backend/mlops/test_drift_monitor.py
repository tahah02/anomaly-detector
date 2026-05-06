import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.mlops.drift_monitor import get_drift_monitor
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_drift_monitor():
    print("\n" + "="*60)
    print("TESTING DRIFT MONITOR")
    print("="*60 + "\n")
    
    try:
        monitor = get_drift_monitor()
        print("✓ Drift monitor initialized successfully")
        
        print("\nTesting data preparation...")
        ref_data = monitor.prepare_reference_data(days_back=30)
        if not ref_data.empty:
            print(f"✓ Reference data prepared: {len(ref_data)} records")
            print(f"  Columns: {list(ref_data.columns)}")
        else:
            print("✗ No reference data available")
            return False
        
        analysis_data = monitor.prepare_analysis_data(days_back=7)
        if not analysis_data.empty:
            print(f"✓ Analysis data prepared: {len(analysis_data)} records")
        else:
            print("✗ No analysis data available")
            return False
        
        print("\nChecking required features...")
        missing_features = [f for f in monitor.feature_columns if f not in ref_data.columns]
        if missing_features:
            print(f"✗ Missing features: {missing_features}")
            return False
        else:
            print(f"✓ All required features present")
        
        print("\nRunning full drift monitoring...")
        results = monitor.run_full_monitoring(reference_days=30, analysis_days=7)
        
        if 'error' in results:
            print(f"✗ Drift monitoring failed: {results['error']}")
            return False
        
        print("\n" + "="*60)
        print("DRIFT MONITORING TEST RESULTS")
        print("="*60)
        print(f"Overall Status: {results['overall_assessment']['status']}")
        print(f"Drift Indicators: {results['overall_assessment']['drift_count']}")
        print(f"Recommendation: {results['overall_assessment']['recommendation']}")
        
        if results.get('univariate_drift'):
            features_with_drift = results['univariate_drift'].get('features_with_drift', [])
            print(f"\nUnivariate Drift: {len(features_with_drift)} features affected")
            if features_with_drift:
                print(f"  Affected features: {', '.join(features_with_drift)}")
        
        if results.get('multivariate_drift'):
            print(f"\nMultivariate Drift: {results['multivariate_drift'].get('drift_detected', False)}")
        
        if results.get('concept_drift'):
            print(f"\nConcept Drift: {results['concept_drift'].get('drift_detected', False)}")
        
        print("\n✓ All tests passed successfully!")
        print("="*60 + "\n")
        return True
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_drift_monitor()
    sys.exit(0 if success else 1)
