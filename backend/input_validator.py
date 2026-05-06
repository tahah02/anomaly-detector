import re
from typing import Dict, List, Optional, Any
from datetime import datetime

class InputValidator:
    
    VALID_TRANSFER_TYPES = {'O', 'I', 'L', 'Q', 'S'}
    VALID_COUNTRIES = {
        'UAE', 'USA', 'UK', 'India', 'Pakistan', 'Philippines', 
        'Egypt', 'Saudi Arabia', 'Kuwait', 'Qatar', 'Bahrain', 'Oman'
    }
    
    MIN_AMOUNT = 1.0
    MAX_AMOUNT = 1000000.0
    
    @staticmethod
    def validate_customer_id(customer_id: str) -> Dict[str, Any]:
        if not customer_id:
            return {"valid": False, "error": "Customer ID is required"}
        
        if not isinstance(customer_id, str):
            return {"valid": False, "error": "Customer ID must be a string"}
        
        if not customer_id.isdigit():
            return {"valid": False, "error": "Customer ID must contain only digits"}
        
        if len(customer_id) < 6 or len(customer_id) > 10:
            return {"valid": False, "error": "Customer ID must be 6-10 digits"}
        
        return {"valid": True, "cleaned": customer_id}
    
    @staticmethod
    def validate_account_number(account_no: str) -> Dict[str, Any]:
        if not account_no:
            return {"valid": False, "error": "Account number is required"}
        
        if not isinstance(account_no, str):
            return {"valid": False, "error": "Account number must be a string"}
        
        cleaned = re.sub(r'[^a-zA-Z0-9]', '', account_no)
        
        if len(cleaned) < 5 or len(cleaned) > 20:
            return {"valid": False, "error": "Account number must be 5-20 characters"}
        
        return {"valid": True, "cleaned": cleaned}
    
    @staticmethod
    def validate_amount(amount: float) -> Dict[str, Any]:
        if amount is None:
            return {"valid": False, "error": "Amount is required"}
        
        try:
            amount = float(amount)
        except (ValueError, TypeError):
            return {"valid": False, "error": "Amount must be a valid number"}
        
        if amount <= 0:
            return {"valid": False, "error": "Amount must be positive"}
        
        if amount < InputValidator.MIN_AMOUNT:
            return {"valid": False, "error": f"Minimum amount is AED {InputValidator.MIN_AMOUNT}"}
        
        if amount > InputValidator.MAX_AMOUNT:
            return {"valid": False, "error": f"Maximum amount is AED {InputValidator.MAX_AMOUNT:,.0f}"}
        
        return {"valid": True, "cleaned": round(amount, 2)}
    
    @staticmethod
    def validate_transfer_type(transfer_type: str) -> Dict[str, Any]:
        if not transfer_type:
            return {"valid": False, "error": "Transfer type is required"}
        
        if not isinstance(transfer_type, str):
            return {"valid": False, "error": "Transfer type must be a string"}
        
        transfer_type = transfer_type.upper().strip()
        
        if transfer_type not in InputValidator.VALID_TRANSFER_TYPES:
            valid_types = ", ".join(InputValidator.VALID_TRANSFER_TYPES)
            return {"valid": False, "error": f"Transfer type must be one of: {valid_types}"}
        
        return {"valid": True, "cleaned": transfer_type}
    
    @staticmethod
    def validate_country(country: str) -> Dict[str, Any]:
        if not country:
            return {"valid": True, "cleaned": "UAE"}
        
        if not isinstance(country, str):
            return {"valid": False, "error": "Country must be a string"}
        
        country = country.strip().title()
        
        if country not in InputValidator.VALID_COUNTRIES:
            return {"valid": True, "cleaned": "Other"}
        
        return {"valid": True, "cleaned": country}
    
    @staticmethod
    def validate_datetime(dt) -> Dict[str, Any]:
        if dt is None:
            return {"valid": True, "cleaned": datetime.now()}
        
        if isinstance(dt, str):
            try:
                dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
            except ValueError:
                return {"valid": False, "error": "Invalid datetime format"}
        
        if not isinstance(dt, datetime):
            return {"valid": False, "error": "Datetime must be a valid datetime object"}
        
        now = datetime.now()
        if dt > now:
            return {"valid": False, "error": "Transaction datetime cannot be in the future"}
        
        if (now - dt).days > 1:
            return {"valid": False, "error": "Transaction datetime cannot be more than 1 day old"}
        
        return {"valid": True, "cleaned": dt}
    
    @staticmethod
    def sanitize_string(text: str, max_length: int = 100) -> str:
        if not text:
            return ""
        
        text = str(text).strip()
        text = re.sub(r'[<>"\';\\]', '', text)
        text = text[:max_length]
        
        return text
    
    @staticmethod
    def validate_transaction_request(data: Dict[str, Any]) -> Dict[str, Any]:
        errors = []
        cleaned_data = {}
        
        customer_id_result = InputValidator.validate_customer_id(data.get('customer_id', ''))
        if not customer_id_result['valid']:
            errors.append(customer_id_result['error'])
        else:
            cleaned_data['customer_id'] = customer_id_result['cleaned']
        
        from_account_result = InputValidator.validate_account_number(data.get('from_account_no', ''))
        if not from_account_result['valid']:
            errors.append(from_account_result['error'])
        else:
            cleaned_data['from_account_no'] = from_account_result['cleaned']
        
        to_account_result = InputValidator.validate_account_number(data.get('to_account_no', ''))
        if not to_account_result['valid']:
            errors.append(to_account_result['error'])
        else:
            cleaned_data['to_account_no'] = to_account_result['cleaned']
        
        amount_result = InputValidator.validate_amount(data.get('transaction_amount'))
        if not amount_result['valid']:
            errors.append(amount_result['error'])
        else:
            cleaned_data['transaction_amount'] = amount_result['cleaned']
        
        transfer_type_result = InputValidator.validate_transfer_type(data.get('transfer_type', ''))
        if not transfer_type_result['valid']:
            errors.append(transfer_type_result['error'])
        else:
            cleaned_data['transfer_type'] = transfer_type_result['cleaned']
        
        country_result = InputValidator.validate_country(data.get('bank_country', 'UAE'))
        if not country_result['valid']:
            errors.append(country_result['error'])
        else:
            cleaned_data['bank_country'] = country_result['cleaned']
        
        datetime_result = InputValidator.validate_datetime(data.get('datetime'))
        if not datetime_result['valid']:
            errors.append(datetime_result['error'])
        else:
            cleaned_data['datetime'] = datetime_result['cleaned']
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'cleaned_data': cleaned_data if len(errors) == 0 else {}
        }

validator = InputValidator()

def get_validator() -> InputValidator:
    return validator