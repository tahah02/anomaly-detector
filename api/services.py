import pandas as pd
import numpy as np
import logging
import os
from datetime import datetime, timedelta
from typing import Dict
from fastapi import HTTPException

logger = logging.getLogger(__name__)


def get_pending_transactions():
    from backend.db_service import get_db_service
    db = get_db_service()
    
    try:
        if not db.connect():
            raise HTTPException(status_code=503, detail="Database connection failed")
        
        query = """
            SELECT TransactionId, CustomerId, FromAccountNo, ToAccountNo,
                   Amount, TransferType, Decision, RiskScore, Reasons, CreatedAt
            FROM APITransactionLogs
            WHERE UserAction = 'PENDING'
            ORDER BY CreatedAt DESC
        """
        
        df = db.execute_query(query)
        
        transactions = []
        for _, row in df.iterrows():
            try:
                amount = float(row['Amount'])
                if pd.isna(amount) or np.isinf(amount):
                    amount = 0.0
            except:
                amount = 0.0
            
            try:
                risk_score = float(row['RiskScore'])
                if pd.isna(risk_score) or np.isinf(risk_score):
                    risk_score = 0.0
            except:
                risk_score = 0.0
            
            transactions.append({
                "transaction_id": str(row['TransactionId']),
                "customer_id": str(row['CustomerId']),
                "from_account": str(row['FromAccountNo']),
                "to_account": str(row['ToAccountNo']),
                "amount": amount,
                "transfer_type": str(row['TransferType']),
                "decision": str(row['Decision']),
                "risk_score": risk_score,
                "reasons": str(row['Reasons']),
                "timestamp": str(row['CreatedAt'])
            })
        
        return {"count": len(transactions), "transactions": transactions}
        
    except Exception as e:
        logger.error(f"Error fetching pending transactions: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        db.disconnect()
