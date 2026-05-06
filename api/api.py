from fastapi import FastAPI, HTTPException, Request, Depends
from datetime import datetime
import uuid
import logging
import json
from backend.hybrid_decision import make_decision
from backend.utils import load_model
from backend.autoencoder import AutoencoderInference
from backend.db_service import get_db_service
from backend.mlops.scheduler import start_scheduler, stop_scheduler
from backend.mlops.retraining_pipeline import run_retraining
from api.models import TransactionRequest, TransactionResponse, ApprovalRequest, RejectionRequest, ActionResponse
from api.services import get_pending_transactions
from api.helpers import save_transaction_to_file, update_transaction_status, validate_transfer_request, verify_basic_auth, generate_idempotence_key, check_idempotence, verify_admin_key

logger = logging.getLogger(__name__)
app = FastAPI(title="Banking Fraud Detection API", version="1.0.0")
db = get_db_service()

model, features, scaler = load_model()
autoencoder = AutoencoderInference()
autoencoder.load()


@app.on_event("startup")
async def startup_event():
    start_scheduler()
    logger.info("MLOps Scheduler started")


@app.get("/api/health")
def health_check():
    db_status = "disconnected"
    db_info = {}
    
    try:
        if db.connect():
            db_status = "connected"
            db.disconnect()
        else:
            db_status = "connection_failed"
    except Exception as e:
        db_status = "error"
        db_info = {"error": str(e)}
    
    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "timestamp": datetime.now().isoformat(),
        "models": {
            "isolation_forest": "loaded" if model else "unavailable",
            "autoencoder": "loaded" if autoencoder else "unavailable"
        },
        "database": {
            "status": db_status, **db_info
        }
    }


@app.post("/api/analyze-transaction", response_model=TransactionResponse)
async def analyze_transaction(request: TransactionRequest, req: Request):
    verify_basic_auth(req)
    start_time = datetime.now()
    
    if request.datetime is None:
        request.datetime = datetime.now()
    
    idempotence_key = request.idempotence_key or generate_idempotence_key()
    
    cached = check_idempotence(idempotence_key)
    if cached and cached.get("is_duplicate"):
        response_payload = cached.get("response_payload")
        if response_payload:
            response_data = json.loads(response_payload) if isinstance(response_payload, str) else response_payload
            response_data["idempotence_key"] = idempotence_key
            response_data["is_cached"] = True
            return TransactionResponse(**response_data)
    
    validate_transfer_request(request)
    
    try:
        db_stats = db.get_all_user_stats(request.customer_id, request.from_account_no, request.transfer_type)
        user_stats = {
            "user_avg_amount": db_stats.get("user_avg_amount", 5000.0),
            "user_std_amount": db_stats.get("user_std_amount", 2000.0),
            "user_max_amount": db_stats.get("user_max_amount", 15000.0),
            "user_txn_frequency": db_stats.get("user_txn_frequency", 0),
            "user_international_ratio": db_stats.get("user_international_ratio", 0.0),
            "current_month_spending": db_stats.get("current_month_spending", 0.0),
            "user_weekly_total": db_stats.get("user_weekly_total", 0.0),
            "user_weekly_txn_count": db_stats.get("user_weekly_txn_count", 0),
            "user_weekly_avg_amount": db_stats.get("user_weekly_avg_amount", 0.0),
            "user_weekly_deviation": db_stats.get("user_weekly_deviation", 0.0),
            "user_monthly_txn_count": db_stats.get("user_monthly_txn_count", 0),
            "user_monthly_avg_amount": db_stats.get("user_monthly_avg_amount", 0.0),
            "user_monthly_deviation": db_stats.get("user_monthly_deviation", 0.0),
            "txn_count_10min": db_stats.get("txn_count_10min", 0),
            "txn_count_1hour": db_stats.get("txn_count_1hour", 0),
            "time_since_last_txn": db_stats.get("time_since_last_txn", 3600.0)
        }
    except:
        user_stats = {
            "user_avg_amount": 5000.0, "user_std_amount": 2000.0, "user_max_amount": 15000.0,
            "user_txn_frequency": 0, "user_international_ratio": 0.0, "current_month_spending": 0.0,
            "user_weekly_total": 0.0, "user_weekly_txn_count": 0, "user_weekly_avg_amount": 0.0,
            "user_weekly_deviation": 0.0, "user_monthly_txn_count": 0, "user_monthly_avg_amount": 0.0,
            "user_monthly_deviation": 0.0, "txn_count_10min": 0, "txn_count_1hour": 0, "time_since_last_txn": 3600.0
        }
    
    try:
        is_new_ben = db.check_new_beneficiary(request.customer_id, request.to_account_no, request.transfer_type)
    except Exception as e:
        logger.error(f"Beneficiary check failed: {e}")
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    
    velocity_metrics = db.get_velocity_metrics(request.customer_id, request.from_account_no)
    
    txn = {
        "customer_id": request.customer_id,
        "account_no": request.from_account_no,
        "amount": request.transaction_amount,
        "transfer_type": request.transfer_type,
        "bank_country": request.bank_country,
        "txn_count_30s": velocity_metrics.get("txn_count_30s", 0),
        "txn_count_10min": velocity_metrics.get("txn_count_10min", 0),
        "txn_count_1hour": velocity_metrics.get("txn_count_1hour", 0),
        "time_since_last_txn": velocity_metrics.get("time_since_last_txn", 3600),
        "is_new_beneficiary": is_new_ben
    }
    
    result = make_decision(txn, user_stats, model, features, autoencoder)
    
    risk_level = result.get('risk_level', 'SAFE')
    if risk_level in ['HIGH', 'MEDIUM']:
        decision = "REQUIRES_USER_APPROVAL"
    elif risk_level == 'LOW':
        decision = "APPROVE_WITH_NOTIFICATION"
    else:
        decision = "APPROVED"
    
    processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
    transaction_id = f"txn_{uuid.uuid4().hex[:8]}"
    
    result['processing_time_ms'] = processing_time
    result['individual_scores'] = {
        "rule_engine": {"violated": result['is_fraud'], "threshold": result.get('threshold', 0)},
        "isolation_forest": {"anomaly_score": result.get('risk_score', 0), "is_anomaly": result.get('ml_flag', False)},
        "autoencoder": {"reconstruction_error": result.get('ae_reconstruction_error'), "is_anomaly": result.get('ae_flag', False)}
    }
    
    save_transaction_to_file(request=request, decision=decision, risk_score=result.get('risk_score', 0.0),
        reasons=result.get('reasons', []), transaction_id=transaction_id, result=result, idempotence_key=idempotence_key)
    
    return TransactionResponse(
        advice=decision,
        risk_score=result.get('risk_score', 0.0),
        risk_level=result.get('risk_level', 'SAFE'),
        confidence_level=result.get('confidence_level', 0.0),
        model_agreement=result.get('model_agreement', 0.0),
        reasons=result.get('reasons', []),
        individual_scores=result['individual_scores'],
        transaction_id=transaction_id,
        processing_time_ms=processing_time,
        idempotence_key=idempotence_key,
        is_cached=False
    )


@app.post("/api/transaction/approve", response_model=ActionResponse)
async def approve_transaction(request: ApprovalRequest, req: Request):
    verify_basic_auth(req)
    verify_admin_key(request.admin_key)
    
    try:
        success = update_transaction_status(
            transaction_id=request.transaction_id,
            action="APPROVED",
            actioned_by=request.customer_id,
            comments=request.comments
        )
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Transaction {request.transaction_id} not found or update failed"
            )
        
        db.insert_transaction_log(
            idempotence_key=f"approval_{request.transaction_id}",
            request_method="POST",
            request_endpoint="/api/transaction/approve",
            request_payload=json.dumps(request.dict()),
            response_status_code=200,
            is_successful=True,
            user_id=request.customer_id,
            decision="APPROVED",
            execution_time_ms=0
        )
        
        return ActionResponse(
            status="approved",
            transaction_id=request.transaction_id,
            timestamp=datetime.now().isoformat(),
            message="Transaction approved successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving transaction: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/transaction/reject", response_model=ActionResponse)
async def reject_transaction(request: RejectionRequest, req: Request):
    verify_basic_auth(req)
    verify_admin_key(request.admin_key)
    
    try:
        success = update_transaction_status(
            transaction_id=request.transaction_id,
            action="REJECTED",
            actioned_by=request.customer_id,
            comments=request.reason
        )
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Transaction {request.transaction_id} not found or update failed"
            )
        
        db.insert_transaction_log(
            idempotence_key=f"rejection_{request.transaction_id}",
            request_method="POST",
            request_endpoint="/api/transaction/reject",
            request_payload=json.dumps(request.dict()),
            response_status_code=200,
            is_successful=True,
            user_id=request.customer_id,
            decision="REJECTED",
            execution_time_ms=0
        )
        
        return ActionResponse(
            status="rejected",
            transaction_id=request.transaction_id,
            timestamp=datetime.now().isoformat(),
            message="Transaction rejected successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting transaction: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/transactions/pending")
def list_pending_transactions(req: Request):
    verify_basic_auth(req)
    return get_pending_transactions()


# Feature Configuration Endpoints
@app.get("/api/features")
def get_all_features(req: Request):
    verify_basic_auth(req)
    try:
        features = db.get_enabled_features()
        return {
            "status": "success",
            "features": features,
            "count": len(features)
        }
    except Exception as e:
        logger.error(f"Error fetching features: {e}")
        raise HTTPException(status_code=500, detail="Error fetching features")


@app.post("/api/features/{feature_name}/enable")
def enable_feature(feature_name: str, req: Request):
    verify_basic_auth(req)
    try:
        query = "UPDATE FeatureConfiguration SET IsEnabled = 1, UpdatedAt = GETDATE() WHERE FeatureName = ?"
        db.execute_non_query(query, [feature_name])
        return {
            "status": "success",
            "message": f"Feature '{feature_name}' enabled",
            "feature_name": feature_name
        }
    except Exception as e:
        logger.error(f"Error enabling feature: {e}")
        raise HTTPException(status_code=500, detail="Error enabling feature")


@app.post("/api/features/{feature_name}/disable")
def disable_feature(feature_name: str, req: Request):
    verify_basic_auth(req)
    try:
        query = "UPDATE FeatureConfiguration SET IsEnabled = 0, UpdatedAt = GETDATE() WHERE FeatureName = ?"
        db.execute_non_query(query, [feature_name])
        return {
            "status": "success",
            "message": f"Feature '{feature_name}' disabled",
            "feature_name": feature_name
        }
    except Exception as e:
        logger.error(f"Error disabling feature: {e}")
        raise HTTPException(status_code=500, detail="Error disabling feature")

@app.on_event("shutdown")
async def shutdown_event():
    stop_scheduler()
    logger.info("MLOps Scheduler stopped")


@app.post("/api/mlops/trigger-retraining")
async def trigger_retraining(req: Request):
    verify_basic_auth(req)
    result = run_retraining()
    return {"status": "success" if result else "failed"}