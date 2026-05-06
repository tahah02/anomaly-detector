import os
import joblib

def ensure_data_dir():
    os.makedirs('data', exist_ok=True)
    os.makedirs('models', exist_ok=True)

def get_clean_csv_path():
    return 'data/Clean.csv'

def get_feature_engineered_path():
    return 'data/feature_datasetv2.csv'

def get_model_path():
    return 'backend/model/isolation_forest.pkl'

TRANSFER_TYPE_MAPPING = {'S': 'Overseas', 'I': 'Ajman', 'L': 'UAE', 'Q': 'Quick', 'O': 'Own', 'M': 'MobilePay', 'F': 'Family Transfer'}
TRANSFER_TYPE_ENCODED = {'S': 4, 'I': 1, 'L': 2, 'Q': 3, 'O': 0, 'M': 5, 'F': 6}
TRANSFER_TYPE_RISK = {'S': 0.9, 'I': 0.1, 'L': 0.2, 'Q': 0.5, 'O': 0.0, 'M': 0.3, 'F': 0.15}

MODEL_FEATURES = [
    'transaction_amount','flag_amount','transfer_type_encoded','transfer_type_risk',
    'channel_encoded','deviation_from_avg','amount_to_max_ratio','rolling_std',
    'transaction_velocity','weekly_total','weekly_txn_count','weekly_avg_amount',
    'weekly_deviation','amount_vs_weekly_avg','current_month_spending','monthly_txn_count',
    'monthly_avg_amount','monthly_deviation','amount_vs_monthly_avg','hourly_total',
    'hourly_count','daily_total','daily_count','hour','day_of_week','is_weekend',
    'is_night','time_since_last','recent_burst','txn_count_30s','txn_count_10min',
    'txn_count_1hour','user_avg_amount','user_std_amount','user_max_amount',
    'user_txn_frequency','intl_ratio','user_high_risk_txn_ratio',
    'user_multiple_accounts_flag','cross_account_transfer_ratio',
    'geo_anomaly_flag','is_new_beneficiary','beneficiary_txn_count_30d'
]

def get_dynamic_model_features():
    from backend.db_service import get_db_service
    
    try:
        db = get_db_service()
        if not db.is_connected():
            db.connect()
        
        enabled_features = db.get_enabled_features()
        
        if not enabled_features:
            return MODEL_FEATURES
        
        base_features = ['transaction_amount']
        
        all_possible_features = [
            'flag_amount', 'transfer_type_encoded', 'transfer_type_risk',
            'channel_encoded', 'deviation_from_avg', 'amount_to_max_ratio',
            'rolling_std', 'transaction_velocity', 'weekly_total',
            'weekly_txn_count', 'weekly_avg_amount', 'weekly_deviation',
            'amount_vs_weekly_avg', 'current_month_spending', 'monthly_txn_count',
            'monthly_avg_amount', 'monthly_deviation', 'amount_vs_monthly_avg',
            'hourly_total', 'hourly_count', 'daily_total', 'daily_count',
            'hour', 'day_of_week', 'is_weekend', 'is_night',
            'time_since_last', 'recent_burst', 'txn_count_30s',
            'txn_count_10min', 'txn_count_1hour', 'user_avg_amount',
            'user_std_amount', 'user_max_amount', 'user_txn_frequency',
            'intl_ratio', 'user_high_risk_txn_ratio',
            'user_multiple_accounts_flag', 'cross_account_transfer_ratio',
            'geo_anomaly_flag', 'is_new_beneficiary', 'beneficiary_txn_count_30d'
        ]
        
        dynamic_features = base_features + [f for f in all_possible_features if f in enabled_features]
        
        return dynamic_features
        
    except Exception as e:
        print(f"Error fetching dynamic features: {e}")
        return MODEL_FEATURES

def load_model():
    try:
        model_path = get_model_path()
        scaler_path = 'backend/model/isolation_forest_scaler.pkl'
        model_data = joblib.load(model_path)
        if isinstance(model_data, dict):
            model = model_data.get('model', model_data)
        else:
            model = model_data
        scaler = None
        try:
            scaler = joblib.load(scaler_path)
        except FileNotFoundError:
            print("Scaler not found, using None")
        
        return model, MODEL_FEATURES, scaler
    
    except Exception as e:
        print(f"Error loading model: {e}")
        return None, None, None