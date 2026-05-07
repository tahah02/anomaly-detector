def get_thresholds():
    # Import inside function to avoid circular dependency
    from backend.db_service import get_db_service
    db = get_db_service()
    return db.get_all_thresholds()

def get_transfer_multipliers(thresholds=None):
    if thresholds is None:
        thresholds = get_thresholds()
    return {
        'S': thresholds.get('TRANSFER_MULTIPLIER_S', 2.0),
        'Q': thresholds.get('TRANSFER_MULTIPLIER_Q', 2.5),
        'L': thresholds.get('TRANSFER_MULTIPLIER_L', 3.0),
        'I': thresholds.get('TRANSFER_MULTIPLIER_I', 3.5),
        'O': thresholds.get('TRANSFER_MULTIPLIER_O', 4.0),
        'M': thresholds.get('TRANSFER_MULTIPLIER_M', 3.2),
        'F': thresholds.get('TRANSFER_MULTIPLIER_F', 3.8),
    }

def get_transfer_min_floors(thresholds=None):
    if thresholds is None:
        thresholds = get_thresholds()
    return {
        'S': thresholds.get('TRANSFER_MIN_FLOOR_S', 5000),
        'Q': thresholds.get('TRANSFER_MIN_FLOOR_Q', 3000),
        'L': thresholds.get('TRANSFER_MIN_FLOOR_L', 2000),
        'I': thresholds.get('TRANSFER_MIN_FLOOR_I', 1500),
        'O': thresholds.get('TRANSFER_MIN_FLOOR_O', 1000),
        'M': thresholds.get('TRANSFER_MIN_FLOOR_M', 1800),
        'F': thresholds.get('TRANSFER_MIN_FLOOR_F', 1200),
    }

def calculate_threshold(user_avg, user_std, transfer_type='O', thresholds=None):
    if thresholds is None:
        thresholds = get_thresholds()
    multipliers = get_transfer_multipliers(thresholds)
    floors = get_transfer_min_floors(thresholds)
    multiplier = multipliers.get(transfer_type, 3.0)
    floor = floors.get(transfer_type, 2000)
    return max(user_avg + multiplier * user_std, floor)

def calculate_all_limits(user_avg, user_std, thresholds=None):
    if thresholds is None:
        thresholds = get_thresholds()
    return {t: calculate_threshold(user_avg, user_std, t, thresholds) for t in ['S', 'I', 'L', 'Q', 'O', 'M', 'F']}

def check_rule_violation(amount, user_avg, user_std, transfer_type, txn_count_10min, txn_count_1hour, monthly_spending, is_new_beneficiary=0, checks_config=None, thresholds=None):
    if checks_config is None:
        checks_config = {
            'velocity_check_10min': 1,
            'velocity_check_1hour': 1,
            'monthly_spending_check': 1,
            'new_beneficiary_check': 1
        }
    
    if thresholds is None:
        thresholds = get_thresholds()
    
    monthly_check_global = thresholds.get('monthly_spending_check', 1)
    if monthly_check_global == 0:
        checks_config['monthly_spending_check'] = 0
    
    max_velocity_10min = thresholds.get('MAX_VELOCITY_10MIN', 5)
    max_velocity_1hour = thresholds.get('MAX_VELOCITY_1HOUR', 15)
    
    reasons = []
    violated = False
    threshold = calculate_threshold(user_avg, user_std, transfer_type, thresholds)

    if checks_config['velocity_check_10min'] == 1:
        # Include current transaction in the count
        current_txn_count_10min = txn_count_10min + 1
        if current_txn_count_10min > max_velocity_10min:
            violated = True
            reasons.append(f"Velocity limit exceeded: {current_txn_count_10min} transactions in last 10 minutes (max allowed {max_velocity_10min})")

    if checks_config['velocity_check_1hour'] == 1:
        # Include current transaction in the count
        current_txn_count_1hour = txn_count_1hour + 1
        if current_txn_count_1hour > max_velocity_1hour:
            violated = True
            reasons.append(f"Hourly velocity limit exceeded: {current_txn_count_1hour} transactions in last 1 hour (max allowed {max_velocity_1hour})")

    if checks_config['monthly_spending_check'] == 1:
        if monthly_spending > threshold:
            violated = True
            reasons.append(f"Monthly spending AED {monthly_spending:,.2f} exceeds limit AED {threshold:,.2f}")

    if checks_config['new_beneficiary_check'] == 1:
        if is_new_beneficiary == 1:
            violated = True
            reasons.append("New beneficiary detected - first time transaction to this recipient requires approval")

    return violated, reasons, threshold
