import logging
import uuid
import json
import base64
import os
from api.models import TransactionRequest
from typing import List, Dict, Any
from fastapi import HTTPException, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from backend.db_service import get_db_service

logger = logging.getLogger(__name__)

def validate_transfer_request(request: TransactionRequest):
    return True

def save_transaction_to_file(request: TransactionRequest, decision: str, risk_score: float, reasons: List[str], transaction_id: str, result: Dict[str, Any] = None, idempotence_key: str = None):
    db = get_db_service()
    try:
        if not db.connect():
            raise Exception("Database connection failed")
        scores = result.get('individual_scores', {}) if result else {}
        re = scores.get('rule_engine', {})
        if_score = scores.get('isolation_forest', {})
        ae = scores.get('autoencoder', {})
        query = """INSERT INTO APITransactionLogs (
            TransactionId, CustomerId, FromAccountNo, FromAccountCurrency, ToAccountNo, Amount, TransferCurrency, TransferType, ChargesType,
            SwiftCode, CheckConstraint, BankCountry, Advice, RiskScore, RiskLevel, ConfidenceLevel, ModelAgreement, Reasons,
            RuleEngineViolated, RuleEngineThreshold, IsolationForestScore, IsolationForestAnomaly,
            AutoencoderError, AutoencoderThreshold, AutoencoderAnomaly, UserAction, ProcessingTimeMs
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        params = [
            transaction_id, request.customer_id, request.from_account_no, request.from_account_currency,
            request.to_account_no, float(request.transaction_amount), request.transfer_currency, request.transfer_type,
            request.charges_type or '', request.swift or '', 1 if request.check_constraint else 0, request.bank_country or 'UAE',
            decision, float(risk_score), result.get('risk_level', 'SAFE') if result else 'SAFE',
            float(result.get('confidence_level', 0.0)) if result else 0.0, float(result.get('model_agreement', 0.0)) if result else 0.0,
            ' | '.join(reasons) if reasons else '', 1 if re.get('violated', False) else 0, float(re.get('threshold', 0.0)),
            float(if_score.get('anomaly_score', 0.0)), 1 if if_score.get('is_anomaly', False) else 0,
            float(ae.get('reconstruction_error', 0.0)) if ae.get('reconstruction_error') is not None else None,
            float(ae.get('threshold', 0.0)) if ae.get('threshold') is not None else None, 1 if ae.get('is_anomaly', False) else 0,
            'PENDING' if decision in ['REQUIRES_USER_APPROVAL', 'BLOCK_AND_VERIFY'] else 'APPROVED',
            int(result.get('processing_time_ms', 0)) if result else 0
        ]
        db.execute_non_query(query, params)
        
        response_payload = {
            "advice": decision,
            "risk_score": float(risk_score),
            "risk_level": result.get('risk_level', 'SAFE') if result else 'SAFE',
            "confidence_level": float(result.get('confidence_level', 0.0)) if result else 0.0,
            "model_agreement": float(result.get('model_agreement', 0.0)) if result else 0.0,
            "reasons": reasons,
            "transaction_id": transaction_id,
            "processing_time_ms": int(result.get('processing_time_ms', 0)) if result else 0
        }
        request_dict = request.dict()
        request_dict['datetime'] = request_dict['datetime'].isoformat() if request_dict.get('datetime') else None
        if idempotence_key:
            db.insert_transaction_log(
                idempotence_key=idempotence_key,
                request_method="POST",
                request_endpoint="/api/analyze-transaction",
                request_payload=json.dumps(request_dict),
                response_status_code=200,
                is_successful=True,
                user_id=request.customer_id,
                response_payload=json.dumps(response_payload),
                risk_score=float(risk_score),
                decision=decision,
                execution_time_ms=int(result.get('processing_time_ms', 0)) if result else 0
            )
        logger.info(f"Transaction {transaction_id} saved")
    except Exception as e:
        logger.error(f"Save transaction failed: {e}", exc_info=True)
    finally:
        db.disconnect()

def update_transaction_status(transaction_id: str, action: str, actioned_by: str, comments: str = "") -> bool:
    db = get_db_service()
    try:
        if not db.connect():
            logger.error("Database connection failed")
            return False
        query = "UPDATE APITransactionLogs SET UserAction = %s, ActionedBy = %s, ActionTimestamp = GETDATE(), ActionComments = %s WHERE TransactionId = %s"
        db.execute_non_query(query, [action, actioned_by, comments, transaction_id])
        logger.info(f"Transaction {transaction_id} updated to {action}")
        return True
    except Exception as e:
        logger.error(f"Update transaction failed: {e}")
        return False
    finally:
        db.disconnect()

def verify_basic_auth(request: Request):
    return True

def verify_admin_key(admin_key: str) -> bool:
    return True

def generate_idempotence_key() -> str:
    return str(uuid.uuid4())

def check_idempotence(idempotence_key: str) -> dict:
    db = get_db_service()
    try:
        if not db.connect():
            return None
        cached_log = db.get_transaction_log_by_idempotence_key(idempotence_key)
        if cached_log:
            return {
                "is_duplicate": True,
                "decision": cached_log.get('Decision'),
                "risk_score": cached_log.get('RiskScore'),
                "response_payload": cached_log.get('ResponsePayload'),
                "log_id": cached_log.get('LogID')
            }
        return {"is_duplicate": False}
    except Exception as e:
        logger.error(f"Error checking idempotence: {e}")
        return None
    finally:
        db.disconnect()