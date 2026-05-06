import pandas as pd
import numpy as np
from backend.utils import (ensure_data_dir, get_clean_csv_path,
                          TRANSFER_TYPE_ENCODED, TRANSFER_TYPE_RISK)
from backend.db_service import get_db_service

OUTPUT_PATH = 'data/feature_datasetv2.csv'

def engineer_features(df=None):
    ensure_data_dir()
    if df is None:
        df = pd.read_csv(get_clean_csv_path())
    
    try:
        db = get_db_service()
        if db.is_connected() or db.connect():
            enabled_features = db.get_enabled_features()
        else:
            enabled_features = []
        if not enabled_features:
            enabled_features = []
    except Exception as e:
        print(f"Warning: Could not fetch enabled features from DB: {e}")
        enabled_features = []
    
    df['CreateDate'] = pd.to_datetime(df.get('CreateDate'), errors='coerce')
    df['transaction_amount'] = pd.to_numeric(df.get('AmountInAed', 0), errors='coerce').fillna(0)
    
    if 'TransferType' in df:
        tt = df['TransferType'].astype(str).str.upper()
        if 'flag_amount' in enabled_features:
            df['flag_amount'] = (tt == 'S').astype(int)
        if 'transfer_type_encoded' in enabled_features:
            df['transfer_type_encoded'] = tt.map(TRANSFER_TYPE_ENCODED).fillna(0)
        if 'transfer_type_risk' in enabled_features:
            df['transfer_type_risk'] = tt.map(TRANSFER_TYPE_RISK).fillna(0.5)
    else:
        if 'flag_amount' in enabled_features:
            df['flag_amount'] = 0
        if 'transfer_type_encoded' in enabled_features:
            df['transfer_type_encoded'] = 0
        if 'transfer_type_risk' in enabled_features:
            df['transfer_type_risk'] = 0.5

    if 'channel_encoded' in enabled_features:
        df['channel_encoded'] = 0
        if 'ChannelId' in df:
            df['channel_encoded'] = (df['ChannelId'].map({v:i for i,v in enumerate(df['ChannelId'].dropna().unique())})
                                     .fillna(0).astype(int))

    if df['CreateDate'].notna().any():
        if 'hour' in enabled_features:
            df['hour'] = df['CreateDate'].dt.hour.fillna(12).astype(int)
        if 'day_of_week' in enabled_features:
            df['day_of_week'] = df['CreateDate'].dt.dayofweek.fillna(0).astype(int)
        if 'is_weekend' in enabled_features:
            df['is_weekend'] = (df['day_of_week'] >= 5).astype(int) if 'day_of_week' in enabled_features else 0
        if 'is_night' in enabled_features:
            df['is_night'] = ((df['hour'] < 6) | (df['hour'] >= 22)).astype(int) if 'hour' in enabled_features else 0
    else:
        if 'hour' in enabled_features:
            df['hour'] = 12
        if 'day_of_week' in enabled_features:
            df['day_of_week'] = 0
        if 'is_weekend' in enabled_features:
            df['is_weekend'] = 0
        if 'is_night' in enabled_features:
            df['is_night'] = 0

    if {'CustomerId','FromAccountNo'}.issubset(df.columns):
        key = ['CustomerId','FromAccountNo']
        df = df.sort_values(key + ['CreateDate'])
        
        stats = df.groupby(key)['transaction_amount'].agg(['mean','std','max','count'])
        stats.columns = ['user_avg_amount','user_std_amount','user_max_amount','user_txn_frequency']
        df = df.merge(stats.fillna(0).reset_index(), on=key, how='left')
        
        if 'deviation_from_avg' in enabled_features:
            df['deviation_from_avg'] = abs(df['transaction_amount'] - df['user_avg_amount'])
        if 'amount_to_max_ratio' in enabled_features:
            df['amount_to_max_ratio'] = df['transaction_amount'] / df['user_max_amount'].replace(0,1)
        if 'intl_ratio' in enabled_features:
            df['intl_ratio'] = df.groupby(key)['flag_amount'].transform('mean')
        if 'user_high_risk_txn_ratio' in enabled_features:
            df['user_high_risk_txn_ratio'] = df.groupby(key)['transfer_type_risk'].transform('mean')
        
        if 'num_accounts' in enabled_features or 'user_multiple_accounts_flag' in enabled_features:
            acc_cnt = df.groupby('CustomerId')['FromAccountNo'].nunique()
            df = df.merge(acc_cnt.rename('num_accounts'), on='CustomerId', how='left')
            if 'user_multiple_accounts_flag' in enabled_features:
                df['user_multiple_accounts_flag'] = (df['num_accounts'] > 1).astype(int)
        
        if 'cross_account_transfer_ratio' in enabled_features:
            cross = df.groupby('CustomerId').apply(lambda x: (x['FromAccountNo'] != x['FromAccountNo'].iloc[0]).mean())
            df = df.merge(cross.rename('cross_account_transfer_ratio'), on='CustomerId', how='left')

        if 'geo_anomaly_flag' in enabled_features:
            df['geo_anomaly_flag'] = 0
            if 'BankCountry' in df:
                cc = df.groupby(key)['BankCountry'].nunique()
                df = df.merge(cc.rename('country_count'), on=key, how='left')
                df['geo_anomaly_flag'] = (df['country_count'] > 2).astype(int)
                df.drop(columns='country_count', inplace=True)

        if 'is_new_beneficiary' in enabled_features or 'beneficiary_txn_count_30d' in enabled_features:
            if 'is_new_beneficiary' in enabled_features:
                df['is_new_beneficiary'] = 0
            if 'beneficiary_txn_count_30d' in enabled_features:
                df['beneficiary_txn_count_30d'] = 1
            if {'ReceipentAccount','CreateDate'}.issubset(df.columns) and 'is_new_beneficiary' in enabled_features:
                df['is_new_beneficiary'] = df.groupby(key)['ReceipentAccount'].transform(lambda x: (~x.duplicated()).astype(int))
      
        if 'time_since_last' in enabled_features or 'recent_burst' in enabled_features:
            df['time_since_last'] = df.groupby(key)['CreateDate'].diff().dt.total_seconds().fillna(3600)
            if 'recent_burst' in enabled_features:
                df['recent_burst'] = (df['time_since_last'] < 300).astype(int)
        
        def rolling_count(g, sec):
            t = g['CreateDate'].values
            return pd.Series([np.sum((t[:i] >= ts - np.timedelta64(sec,'s')) & (t[:i] <= ts)) + 1
                             if not pd.isna(ts) else 1
                             for i, ts in enumerate(t)], index=g.index)
        
        for s, col in [(30,'txn_count_30s'),(600,'txn_count_10min'),(3600,'txn_count_1hour')]:
            if col in enabled_features:
                df[col] = df.groupby(key, group_keys=False).apply(lambda g: rolling_count(g, s))
        for freq, cols in [('h', ('hourly_total','hourly_count')),
                          ('D', ('daily_total','daily_count'))]:
            if any(c in enabled_features for c in cols):
                k = df['CreateDate'].dt.floor(freq)
                k_name = f'{freq}_key'
                df[k_name] = k
                agg = df.groupby(key + [k_name])['transaction_amount'].agg(['sum','count'])
                agg.columns = cols
                df = df.merge(agg.reset_index(), on=key + [k_name], how='left')
                df.drop(columns=k_name, inplace=True)
        
        if any(f in enabled_features for f in ['weekly_total','weekly_txn_count','weekly_avg_amount','weekly_deviation','amount_vs_weekly_avg']):
            df['week_key'] = df['CreateDate'].dt.to_period('W')
            wk = df.groupby(key+['week_key'])['transaction_amount'].agg(['sum','count','mean'])
            wk.columns = ['weekly_total','weekly_txn_count','weekly_avg_amount']
            df = df.merge(wk.reset_index(), on=key+['week_key'], how='left').drop(columns='week_key')
            if 'weekly_deviation' in enabled_features:
                df['weekly_deviation'] = abs(df['transaction_amount'] - df['weekly_avg_amount'])
            if 'amount_vs_weekly_avg' in enabled_features:
                df['amount_vs_weekly_avg'] = df['transaction_amount'] / df['weekly_avg_amount'].replace(0,1)
        
        if any(f in enabled_features for f in ['current_month_spending','monthly_txn_count','monthly_avg_amount','monthly_deviation','amount_vs_monthly_avg']):
            df['month_key'] = df['CreateDate'].dt.to_period('M')
            mo = df.groupby(key+['month_key'])['transaction_amount'].agg(['sum','count','mean'])
            mo.columns = ['current_month_spending','monthly_txn_count','monthly_avg_amount']
            df = df.merge(mo.reset_index(), on=key+['month_key'], how='left').drop(columns='month_key')
            if 'monthly_deviation' in enabled_features:
                df['monthly_deviation'] = abs(df['transaction_amount'] - df['monthly_avg_amount'])
            if 'amount_vs_monthly_avg' in enabled_features:
                df['amount_vs_monthly_avg'] = df['transaction_amount'] / df['monthly_avg_amount'].replace(0,1)
        
        if 'rolling_std' in enabled_features:
            df['rolling_std'] = df.groupby(key)['transaction_amount'].transform(lambda x: x.rolling(min(5,len(x)),1).std()).fillna(0)
        if 'transaction_velocity' in enabled_features:
            df['transaction_velocity'] = (1 / (df['time_since_last'].replace(0,1) / 3600)).fillna(0)
    
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"Saved: {OUTPUT_PATH} | {df.shape}")
    return df

if __name__ == "__main__":
    engineer_features()
