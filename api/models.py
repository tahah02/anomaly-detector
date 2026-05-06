from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import List, Optional, Union


class TransactionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    customer_id: str = Field(alias="customerId")
    from_account_no: str = Field(alias="fromAccountNo")
    from_account_currency: str = Field(alias="fromAccountCurrency")
    to_account_no: str = Field(alias="toAccountNo")
    transaction_amount: float = Field(gt=0, alias="transactionAmount")
    transfer_currency: str = Field(alias="transferCurrency")
    transfer_type: str = Field(pattern="^[SILQOMF]$", alias="transferType")
    charges_type: Optional[str] = Field(default="", alias="chargesType")
    swift: Optional[str] = Field(default="", alias="swift")
    check_constraint: bool = Field(default=True, alias="checkConstraint")
    datetime: Optional[datetime] = None
    bank_country: Optional[str] = Field(default="UAE", alias="bankCountry")
    idempotence_key: Optional[str] = Field(default=None, alias="idempotenceKey")
    account_no: Optional[str] = Field(default=None, alias="accountNo")


class TransactionResponse(BaseModel):
    model_config = {"protected_namespaces": ()}
    
    advice: str
    risk_score: float
    risk_level: str
    confidence_level: float
    model_agreement: float
    reasons: List[str]
    individual_scores: dict
    transaction_id: str
    processing_time_ms: int
    idempotence_key: Optional[str] = None
    is_cached: Optional[bool] = False


class ApprovalRequest(BaseModel):
    transaction_id: str
    customer_id: str
    admin_key: str
    comments: Optional[str] = ""


class RejectionRequest(BaseModel):
    transaction_id: str
    customer_id: str
    admin_key: str
    reason: str


class ActionResponse(BaseModel):
    status: str
    transaction_id: str
    timestamp: str
    message: str
