import json
import numpy as np
from backend.rule_engine import check_rule_violation, get_thresholds
from backend.db_service import get_db_service


def load_risk_config():
    db = get_db_service()
    thresholds = get_thresholds()
    
    config = {
        'isolation_forest': {
            'high_risk_threshold': thresholds.get('IF_Anomaly_High', 0.85),
            'medium_risk_threshold': thresholds.get('IF_Anomaly_Medium', 0.65),
            'low_risk_threshold': thresholds.get('IF_Anomaly_Low', 0.45)
        },
        'confidence_calculation': {
            'all_models_agree': thresholds.get('Confidence_AllAgree', 0.95),
            'two_models_agree': thresholds.get('Confidence_TwoAgree', 0.75),
            'one_model_agrees': thresholds.get('Confidence_OneAgrees', 0.50),
            'high_risk_boost': thresholds.get('Confidence_HighRiskBoost', 0.15)
        },
        'risk_levels': {
            'safe': 'SAFE',
            'low': 'LOW',
            'medium': 'MEDIUM',
            'high': 'HIGH'
        },
        'risk_scores': {
            'velocity': thresholds.get('RISK_SCORE_VELOCITY', 0.85),
            'monthly_spending': thresholds.get('RISK_SCORE_MONTHLY_SPENDING', 0.70),
            'new_beneficiary': thresholds.get('RISK_SCORE_NEW_BENEFICIARY', 0.60),
            'default': thresholds.get('RISK_SCORE_DEFAULT', 0.75),
            'ml_boost': thresholds.get('ML_SCORE_BOOST', 0.15),
            'ae_boost': thresholds.get('AE_SCORE_BOOST', 0.10)
        }
    }
    
    return config


def calculate_risk_level(risk_score, config):
    thresholds = config['isolation_forest']
    if risk_score >= thresholds['high_risk_threshold']:
        return config['risk_levels']['high']
    elif risk_score >= thresholds['medium_risk_threshold']:
        return config['risk_levels']['medium']
    elif risk_score >= thresholds['low_risk_threshold']:
        return config['risk_levels']['low']
    else:
        return config['risk_levels']['safe']


def calculate_confidence(rule_violated, ml_flag, ae_flag, risk_score, config):
    flags = [rule_violated, ml_flag, ae_flag]
    fraud_count = sum(flags)
    conf_config = config['confidence_calculation']
    
    if fraud_count == 3:
        confidence = conf_config['all_models_agree']
    elif fraud_count == 2:
        confidence = conf_config['two_models_agree']
    elif fraud_count == 1:
        confidence = conf_config['one_model_agrees']
    else:
        confidence = conf_config['all_models_agree']
    
    if ml_flag and risk_score > 0.8:
        confidence += conf_config['high_risk_boost']
    
    return round(min(confidence, 1.0), 2)


def make_decision(txn, user_stats, model, features, autoencoder=None):
    config = load_risk_config()
    db = get_db_service()
    thresholds = get_thresholds()
    
    customer_id = txn.get("customer_id", "")
    account_no = txn.get("account_no", "")
    transfer_type = txn.get("transfer_type", "O")
    
    checks_config = db.get_customer_checks_config(customer_id, account_no, transfer_type)
    
    result = {
        "is_fraud": False,
        "reasons": [],
        "risk_score": 0.0,
        "risk_level": "SAFE",
        "confidence_level": 0.0,
        "model_agreement": 0.0,
        "threshold": 0.0,
        "ml_flag": False,
        "ae_flag": False,
        "ae_reconstruction_error": None,
        "ae_threshold": None,
    }
    violated, rule_reasons, threshold = check_rule_violation(
        amount=txn["amount"],
        user_avg=user_stats["user_avg_amount"],
        user_std=user_stats["user_std_amount"],
        transfer_type=txn["transfer_type"],
        txn_count_10min=txn["txn_count_10min"],
        txn_count_1hour=txn["txn_count_1hour"],
        monthly_spending=user_stats["current_month_spending"],
        is_new_beneficiary=txn.get("is_new_beneficiary", 0),
        checks_config=checks_config,
        thresholds=thresholds
    )

    result["threshold"] = threshold
    risk_score = 0.0
    
    if violated:
        result["is_fraud"] = True
        result["reasons"].extend(rule_reasons)
        
        if any("Velocity" in reason for reason in rule_reasons):
            risk_score = config['risk_scores']['velocity']
        elif any("Monthly spending" in reason for reason in rule_reasons):
            risk_score = config['risk_scores']['monthly_spending']
        elif any("New beneficiary" in reason for reason in rule_reasons):
            risk_score = config['risk_scores']['new_beneficiary']
        else:
            risk_score = config['risk_scores']['default']

    if model is not None:
        vec = np.array([[txn.get(f, 0) for f in features]])
        pred = model.predict(vec)[0]
        raw_score = model.decision_function(vec)[0]
        ml_score = max(0, min(1, (raw_score + 1) / 2))

        if violated:
            risk_score = risk_score + (ml_score * config['risk_scores']['ml_boost'])
        else:
            risk_score = ml_score

        if ml_score >= config['isolation_forest']['medium_risk_threshold']:
            result["ml_flag"] = True
            result["is_fraud"] = True
            result["reasons"].append(f"ML anomaly detected: risk score {ml_score:.4f} exceeds threshold {config['isolation_forest']['medium_risk_threshold']}")
        elif pred == -1:
            result["ml_flag"] = True
            result["is_fraud"] = True
            result["reasons"].append(f"ML anomaly detected: abnormal behavior pattern (risk score {ml_score:.4f})")
    if autoencoder is not None:
        amount = txn.get('amount', 0)
        user_avg = user_stats.get('user_avg_amount', thresholds.get('DEFAULT_USER_AVG', 5000))
        user_max = max(user_stats.get('user_max_amount', 1), 1)
        weekly_avg = user_stats.get('user_weekly_avg_amount', 0)
        monthly_avg = user_stats.get('monthly_avg_amount', user_avg)
        time_since_last = txn.get('time_since_last_txn', thresholds.get('DEFAULT_TIME_SINCE_LAST', 3600))
        recent_burst_threshold = thresholds.get('RECENT_BURST_THRESHOLD', 300)
        
        transfer_type_risk = {
            'S': thresholds.get('TRANSFER_TYPE_RISK_S', 0.9),
            'I': thresholds.get('TRANSFER_TYPE_RISK_I', 0.1),
            'L': thresholds.get('TRANSFER_TYPE_RISK_L', 0.2),
            'Q': thresholds.get('TRANSFER_TYPE_RISK_Q', 0.5),
            'O': thresholds.get('TRANSFER_TYPE_RISK_O', 0.0),
            'M': thresholds.get('TRANSFER_TYPE_RISK_M', 0.3),
            'F': thresholds.get('TRANSFER_TYPE_RISK_F', 0.15),
        }
        
        ae_features = { 
            'transaction_amount': amount,
            'flag_amount': 1 if txn.get('transfer_type') == 'S' else 0,
            'transfer_type_encoded': {'S': 4, 'I': 1, 'L': 2, 'Q': 3, 'O': 0}.get(txn.get('transfer_type', 'O'), 0),
            'transfer_type_risk': transfer_type_risk.get(txn.get('transfer_type', 'O'), 0.5),
            'channel_encoded': 0,
            'deviation_from_avg': abs(amount - user_avg),
            'amount_to_max_ratio': amount / user_max,
            'rolling_std': user_stats.get('user_std_amount', 0),
            'transaction_velocity': 3600 / max(time_since_last, 1),
            'weekly_total': user_stats.get('user_weekly_total', 0),           
            'weekly_txn_count': user_stats.get('user_weekly_txn_count', 0),       
            'weekly_avg_amount': weekly_avg,      
            'weekly_deviation': abs(amount - weekly_avg) if weekly_avg > 0 else 0,
            'amount_vs_weekly_avg': amount / max(weekly_avg, 1) if weekly_avg > 0 else 1,
            'current_month_spending': user_stats.get('current_month_spending', 0),
            'monthly_txn_count': user_stats.get('monthly_txn_count', user_stats.get('user_txn_frequency', 0)),
            'monthly_avg_amount': monthly_avg,
            'monthly_deviation': abs(amount - monthly_avg),
            'amount_vs_monthly_avg': amount / max(monthly_avg, 1),
            'hourly_total': amount,
            'hourly_count': 1,
            'daily_total': amount,
            'daily_count': 1,
            'hour': 12,  
            'day_of_week': 0,
            'is_weekend': 0,
            'is_night': 0,
            'time_since_last': time_since_last,
            'recent_burst': 1 if time_since_last < recent_burst_threshold else 0,
            'txn_count_30s': txn.get('txn_count_30s', 1),
            'txn_count_10min': txn.get('txn_count_10min', 1),
            'txn_count_1hour': txn.get('txn_count_1hour', 1),
            'user_avg_amount': user_avg,
            'user_std_amount': user_stats.get('user_std_amount', 0),
            'user_max_amount': user_stats.get('user_max_amount', 0),
            'user_txn_frequency': user_stats.get('user_txn_frequency', 0),
            'intl_ratio': user_stats.get('user_international_ratio', 0),
            'user_high_risk_txn_ratio': user_stats.get('user_high_risk_txn_ratio', 0.5),
            'user_multiple_accounts_flag': 1 if user_stats.get('num_accounts', 1) > 1 else 0,
            'cross_account_transfer_ratio': user_stats.get('cross_account_transfer_ratio', 0),
            'geo_anomaly_flag': 1 if txn.get('bank_country', 'UAE') not in ['UAE', 'United Arab Emirates'] else 0,
            'is_new_beneficiary': txn.get('is_new_beneficiary', 0),
            'beneficiary_txn_count_30d': user_stats.get('beneficiary_txn_count_30d', 1),
        }
        
        ae_result = autoencoder.score_transaction(ae_features)
        
        if ae_result is not None:
            result["ae_reconstruction_error"] = ae_result['reconstruction_error']
            result["ae_threshold"] = ae_result['threshold']
            ae_score = ae_result.get('reconstruction_error', 0)
            
            if ae_result['is_anomaly']:
                result["ae_flag"] = True
                result["is_fraud"] = True
                result["reasons"].append(ae_result['reason'])
                risk_score = risk_score + (ae_score * config['risk_scores']['ae_boost'])

    result["risk_score"] = min(risk_score, 1.0)
    result["risk_level"] = calculate_risk_level(result["risk_score"], config)
    
    if result["is_fraud"] and result["risk_level"] == "SAFE":
        result["risk_level"] = "LOW"
    
    result["confidence_level"] = calculate_confidence(violated, result["ml_flag"], result["ae_flag"], result["risk_score"], config)
    result["model_agreement"] = round(sum([violated, result["ml_flag"], result["ae_flag"]]) / 3, 2)

    return result
