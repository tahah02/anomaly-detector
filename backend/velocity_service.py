try:
    import redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False
    print("Redis not installed. Using in-memory storage as fallback.")

import json
from datetime import datetime
from typing import Dict, List
import os

class VelocityService:
    def __init__(self):
        self.redis_client = None
        self.memory_storage = {}
        
        if HAS_REDIS:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                self.redis_client.ping()
                print("Redis connected successfully")
            except Exception as e:
                print(f"Redis connection failed: {e}")
                print("Using in-memory storage")
                self.redis_client = None
        else:
            print("Redis not available. Using in-memory storage.")
        
    def record_transaction(self, customer_id: str, account_no: str, amount: float = 0):
        key = f"velocity:{customer_id}:{account_no}"
        now = datetime.now().timestamp()
        
        if self.redis_client:
            self.redis_client.zadd(key, {str(now): now})
            self.redis_client.expire(key, 3600)
            
            spending_key = f"spending:{customer_id}:{account_no}"
            self.redis_client.incrbyfloat(spending_key, amount)
            self.redis_client.expire(spending_key, 2592000)
        else:
            if key not in self.memory_storage:
                self.memory_storage[key] = []
            self.memory_storage[key].append(now)
            
            spending_key = f"spending:{customer_id}:{account_no}"
            if spending_key not in self.memory_storage:
                self.memory_storage[spending_key] = 0.0
            self.memory_storage[spending_key] += amount
    
    def get_velocity_metrics(self, customer_id: str, account_no: str) -> Dict:
        key = f"velocity:{customer_id}:{account_no}"
        now = datetime.now().timestamp()
        
        if self.redis_client:
            count_30s = self.redis_client.zcount(key, now - 30, now)
            count_10min = self.redis_client.zcount(key, now - 600, now)
            count_1hour = self.redis_client.zcount(key, now - 3600, now)
            
            recent_txns = self.redis_client.zrevrange(key, 0, 0, withscores=True)
            time_since_last = now - float(recent_txns[0][1]) if recent_txns else 3600
        else:
            history = self.memory_storage.get(key, [])
            history = [t for t in history if now - t < 3600]
            
            count_30s = sum(1 for t in history if now - t < 30)
            count_10min = sum(1 for t in history if now - t < 600)
            count_1hour = len(history)
            time_since_last = now - max(history) if history else 3600
        
        return {
            'txn_count_30s': count_30s,
            'txn_count_10min': count_10min,
            'txn_count_1hour': count_1hour,
            'time_since_last_txn': time_since_last
        }
    
    def get_session_spending(self, customer_id: str, account_no: str) -> float:
        spending_key = f"spending:{customer_id}:{account_no}"
        
        if self.redis_client:
            spending = self.redis_client.get(spending_key)
            return float(spending) if spending else 0.0
        else:
            return float(self.memory_storage.get(spending_key, 0.0))
    
    def cleanup_old_data(self):
        now = datetime.now().timestamp()
        cutoff_1hour = now - 3600
        
        if self.redis_client:
            velocity_keys = list(self.redis_client.scan_iter(match="velocity:*"))
            spending_keys = list(self.redis_client.scan_iter(match="spending:*"))
            
            cleaned_velocity = 0
            
            for key in velocity_keys:
                removed = self.redis_client.zremrangebyscore(key, 0, cutoff_1hour)
                cleaned_velocity += removed
                
                if self.redis_client.zcard(key) == 0:
                    self.redis_client.delete(key)
            
            for key in spending_keys:
                if not self.redis_client.exists(key):
                    continue
                    
                last_access = self.redis_client.ttl(key)
                if last_access == -1 or last_access > 2592000:
                    self.redis_client.expire(key, 2592000)
            
            return {
                'velocity_records_cleaned': cleaned_velocity,
                'velocity_keys_processed': len(velocity_keys),
                'spending_keys_processed': len(spending_keys)
            }
        else:
            cleaned = 0
            for key in list(self.memory_storage.keys()):
                if key.startswith("velocity:"):
                    history = self.memory_storage[key]
                    old_count = len(history)
                    self.memory_storage[key] = [t for t in history if now - t < 3600]
                    cleaned += old_count - len(self.memory_storage[key])
            
            return {
                'velocity_records_cleaned': cleaned,
                'velocity_keys_processed': len([k for k in self.memory_storage.keys() if k.startswith("velocity:")]),
                'spending_keys_processed': len([k for k in self.memory_storage.keys() if k.startswith("spending:")])
            }
    
    def get_memory_stats(self):
        if self.redis_client:
            velocity_keys = len(list(self.redis_client.scan_iter(match="velocity:*")))
            spending_keys = len(list(self.redis_client.scan_iter(match="spending:*")))
            
            total_records = 0
            for key in self.redis_client.scan_iter(match="velocity:*"):
                total_records += self.redis_client.zcard(key)
            
            return {
                'storage_type': 'redis',
                'velocity_keys': velocity_keys,
                'spending_keys': spending_keys,
                'total_velocity_records': total_records
            }
        else:
            velocity_keys = len([k for k in self.memory_storage.keys() if k.startswith("velocity:")])
            spending_keys = len([k for k in self.memory_storage.keys() if k.startswith("spending:")])
            
            total_records = sum(len(v) for k, v in self.memory_storage.items() if k.startswith("velocity:") and isinstance(v, list))
            
            return {
                'storage_type': 'memory',
                'velocity_keys': velocity_keys,
                'spending_keys': spending_keys,
                'total_velocity_records': total_records
            }

velocity_service = VelocityService()

def get_velocity_service() -> VelocityService:
    return velocity_service