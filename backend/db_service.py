import pandas as pd
import logging
import os
from dotenv import load_dotenv
from typing import Optional, List, Dict, Any
from queue import Queue, Empty
import threading
from datetime import datetime


try:
    import pyodbc
    DRIVER_TYPE = 'pyodbc'
    logger = logging.getLogger(__name__)
    logger.info("Using pyodbc driver")
except ImportError:
    try:
        import pymssql
        DRIVER_TYPE = 'pymssql'
        logger = logging.getLogger(__name__)
        logger.info("Using pymssql driver")
    except ImportError:
        raise ImportError("Neither pymssql nor pyodbc is installed. Please install one of them.")

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_param_placeholder():
    return '?' if DRIVER_TYPE == 'pyodbc' else '%s'

class DatabaseService:
    _pool = None
    _pool_lock = threading.Lock()
    _pool_size = int(os.getenv("DB_POOL_SIZE", "3000"))
    _pool_initialized = False
    
    def __init__(self):
        self.server = os.getenv("DB_SERVER", "10.112.32.4")
        self.port = int(os.getenv("DB_PORT", "1433"))
        self.database = os.getenv("DB_DATABASE", "retailchannelLogs")
        self.username = os.getenv("DB_USERNAME", "dbuser")
        self.password = os.getenv("DB_PASSWORD", "")
        self.connection = None
        self.param_placeholder = get_param_placeholder()
        
        if not DatabaseService._pool_initialized:
            with DatabaseService._pool_lock:
                if not DatabaseService._pool_initialized:
                    DatabaseService._pool = Queue(maxsize=DatabaseService._pool_size)
                    DatabaseService._pool_initialized = True
                    logger.info(f"Connection pool initialized with size {DatabaseService._pool_size}")
        
        self.REQUIRED_COLUMNS = [
            'CustomerId', 'TransferType', 'FromAccountCurrency', 'FromAccountNo',
            'SwiftCode', 'ReceipentAccount', 'ReceipentName', 'Amount', 'Currency',
            'PurposeCode', 'Charges', 'Status', 'CreateDate', 'FlagAmount',
            'FlagCurrency', 'AmountInAed', 'BankStatus', 'BankName', 'PurposeDetails',
            'ChargesAmount', 'BenId', 'AccountType', 'BankCountry', 'ChannelId'
        ]
    
    def _create_connection(self):
        try:
            if DRIVER_TYPE == 'pyodbc':
                conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={self.server},{self.port};DATABASE={self.database};UID={self.username};PWD={self.password}"
                conn = pyodbc.connect(conn_str, timeout=15)
                logger.info("New connection created using pyodbc")
            else:
                conn = pymssql.connect(
                    server=self.server,
                    port=self.port,
                    database=self.database,
                    user=self.username,
                    password=self.password,
                    timeout=15,
                    login_timeout=15
                )
                logger.info("New connection created using pymssql")
            return conn
        except Exception as e:
            logger.error(f"Failed to create connection: {e}")
            return None
    
    def _get_connection_from_pool(self):
        try:
            conn = DatabaseService._pool.get_nowait()
            
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                cursor.close()
                logger.debug("Reusing connection from pool")
                return conn
            except:
                logger.warning("Connection from pool is dead, creating new one")
                try:
                    conn.close()
                except:
                    pass
                return self._create_connection()
                
        except Empty:
            logger.debug("Pool empty, creating new connection")
            return self._create_connection()
    
    def _return_connection_to_pool(self, conn):
        if conn is None:
            return
        
        try:
            if DatabaseService._pool.full():
                logger.debug("Pool is full, closing connection")
                conn.close()
            else:
                DatabaseService._pool.put_nowait(conn)
                logger.debug("Connection returned to pool")
        except Exception as e:
            logger.error(f"Error returning connection to pool: {e}")
            try:
                conn.close()
            except:
                pass
    
    def connect(self) -> bool:
        try:
            if self.connection:
                return True
            
            self.connection = self._get_connection_from_pool()
            return self.connection is not None
            
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self.connection = None
            return False
    
    def disconnect(self):
        try:
            if self.connection:
                self._return_connection_to_pool(self.connection)
                self.connection = None
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")
    
    def is_connected(self) -> bool:
        try:
            if not self.connection:
                return False
            cursor = self.connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            return True
        except:
            return False
    
    def execute_query(self, query: str, params: Optional[List] = None) -> pd.DataFrame:
        try:
            if not self.is_connected():
                if not self.connect():
                    raise Exception("Cannot connect to database")
            
            cursor = self.connection.cursor()
            
            if params:
                cursor.execute(query, tuple(params))
            else:
                cursor.execute(query)
            
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            cursor.close()
            
            df = pd.DataFrame.from_records(rows, columns=columns)
            
            for col in df.columns:
                if df[col].dtype == 'object':
                    try:
                        df[col] = pd.to_numeric(df[col], errors='ignore')
                    except:
                        pass
            
            return df
        except Exception as e:
            logger.error(f"Query error: {e}")
            raise
    
    def execute_non_query(self, query: str, params: Optional[List] = None) -> int:
        try:
            if not self.is_connected():
                if not self.connect():
                    raise Exception("Cannot connect to database")
            
            cursor = self.connection.cursor()
            
            if params:
                cursor.execute(query, tuple(params))
            else:
                cursor.execute(query)
            
            self.connection.commit()
            rows_affected = cursor.rowcount
            cursor.close()
            
            return rows_affected
        except Exception as e:
            logger.error(f"Non-query error: {e}")
            if self.connection:
                self.connection.rollback()
            raise
    
    def get_all_customers(self) -> List[str]:
        query = "SELECT DISTINCT CustomerId FROM TransactionHistoryLogs WHERE CustomerId IS NOT NULL ORDER BY CustomerId"
        df = self.execute_query(query)
        return df['CustomerId'].astype(str).tolist()
    
    def get_customer_accounts(self, customer_id: str) -> List[str]:
        if DRIVER_TYPE == 'pymssql':
            query = "SELECT DISTINCT FromAccountNo FROM TransactionHistoryLogs WHERE CustomerId = %s AND FromAccountNo IS NOT NULL ORDER BY FromAccountNo"
        else:
            query = "SELECT DISTINCT FromAccountNo FROM TransactionHistoryLogs WHERE CustomerId = ? AND FromAccountNo IS NOT NULL ORDER BY FromAccountNo"
        df = self.execute_query(query, [customer_id])
        return df['FromAccountNo'].astype(str).tolist()
    
    def get_account_transactions(self, customer_id: str, account_no: str) -> pd.DataFrame:
        columns_str = ", ".join([f"[{col}]" for col in self.REQUIRED_COLUMNS])
        
        padded_account = account_no.zfill(14)
        stripped_account = account_no.lstrip('0') or '0'
        
        if DRIVER_TYPE == 'pymssql':
            query = f"""SELECT {columns_str} FROM TransactionHistoryLogs 
                        WHERE CustomerId = %s 
                        AND (FromAccountNo = %s OR FromAccountNo = %s OR FromAccountNo = %s)
                        ORDER BY CreateDate DESC"""
        else:
            query = f"""SELECT {columns_str} FROM TransactionHistoryLogs 
                        WHERE CustomerId = ? 
                        AND (FromAccountNo = ? OR FromAccountNo = ? OR FromAccountNo = ?)
                        ORDER BY CreateDate DESC"""
        
        return self.execute_query(query, [customer_id, account_no, padded_account, stripped_account])
    
    def get_customer_all_transactions(self, customer_id: str) -> pd.DataFrame:
        columns_str = ", ".join([f"[{col}]" for col in self.REQUIRED_COLUMNS])
        if DRIVER_TYPE == 'pymssql':
            query = f"SELECT {columns_str} FROM TransactionHistoryLogs WHERE CustomerId = %s ORDER BY FromAccountNo, CreateDate DESC"
        else:
            query = f"SELECT {columns_str} FROM TransactionHistoryLogs WHERE CustomerId = ? ORDER BY FromAccountNo, CreateDate DESC"
        return self.execute_query(query, [customer_id])
    
    def get_user_statistics(self, customer_id: str, account_no: str, transfer_type: str) -> Dict[str, Any]:
        try:
            df = self.get_account_transactions(customer_id, account_no)
            
            if len(df) == 0:
                return {
                    "user_avg_amount": 5000.0,
                    "user_std_amount": 2000.0,
                    "user_max_amount": 15000.0,
                    "user_txn_frequency": 0,
                    "user_international_ratio": 0.0,
                    "current_month_spending": 0.0
                }
            
            if 'CreateDate' in df.columns:
                df['CreateDate'] = pd.to_datetime(df['CreateDate'])
                current_month_start = pd.Timestamp(datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0))
                historical_df = df[df['CreateDate'] < current_month_start].copy()
                
                if len(historical_df) > 0:
                    historical_df['AmountInAed'] = historical_df['AmountInAed'].astype(float)
                    avg_amount = float(historical_df['AmountInAed'].mean())
                    std_amount = float(historical_df['AmountInAed'].std()) if len(historical_df) > 1 else 2000.0
                    max_amount = float(historical_df['AmountInAed'].max())
                    txn_count = len(historical_df)
                    logger.info(f"Using {len(historical_df)} historical transactions for threshold calculation")
                else:
                    logger.warning(f"No historical data found for customer {customer_id}, using defaults")
                    avg_amount = 5000.0
                    std_amount = 2000.0
                    max_amount = 15000.0
                    txn_count = 0
            else:
                df['AmountInAed'] = df['AmountInAed'].astype(float)
                avg_amount = float(df['AmountInAed'].mean())
                std_amount = float(df['AmountInAed'].std()) if len(df) > 1 else 2000.0
                max_amount = float(df['AmountInAed'].max())
                txn_count = len(df)
            
            intl_ratio = 0.0
            if 'TransferType' in df.columns:
                intl_count = len(df[df['TransferType'] == 'S'])
                intl_ratio = intl_count / len(df) if len(df) > 0 else 0.0
            
            current_month_spending = self.get_monthly_spending(customer_id, account_no, transfer_type)
            
            return {
                "user_avg_amount": float(avg_amount),
                "user_std_amount": float(std_amount),
                "user_max_amount": float(max_amount),
                "user_txn_frequency": int(txn_count),
                "user_international_ratio": float(intl_ratio),
                "current_month_spending": float(current_month_spending)
            }
        except Exception as e:
            logger.error(f"Error getting user statistics: {e}", exc_info=True)
            return {
                "user_avg_amount": 5000.0,
                "user_std_amount": 2000.0,
                "user_max_amount": 15000.0,
                "user_txn_frequency": 0,
                "user_international_ratio": 0.0,
                "current_month_spending": 0.0
            }
    
    def get_monthly_spending(self, customer_id: str, account_no: str, transfer_type: str) -> float:
        try:
            padded_account = account_no.zfill(14)
            if DRIVER_TYPE == 'pymssql':
                query = """
                    SELECT COALESCE(SUM(AmountInAed), 0) as monthly_total
                    FROM TransactionHistoryLogs 
                    WHERE CustomerId = %s AND (FromAccountNo = %s OR FromAccountNo = %s)
                    AND TransferType = %s
                    AND CreateDate >= DATEADD(MONTH, DATEDIFF(MONTH, 0, GETDATE()), 0)
                    AND CreateDate < DATEADD(MONTH, DATEDIFF(MONTH, 0, GETDATE()) + 1, 0)
                """
                params = [customer_id, account_no, padded_account, transfer_type]
            else:
                query = """
                    SELECT COALESCE(SUM(AmountInAed), 0) as monthly_total
                    FROM TransactionHistoryLogs 
                    WHERE CustomerId = ? AND (FromAccountNo = ? OR FromAccountNo = ?)
                    AND TransferType = ?
                    AND CreateDate >= DATEADD(MONTH, DATEDIFF(MONTH, 0, GETDATE()), 0)
                    AND CreateDate < DATEADD(MONTH, DATEDIFF(MONTH, 0, GETDATE()) + 1, 0)
                """
                params = [customer_id, account_no, padded_account, transfer_type]
            df = self.execute_query(query, params)
            return float(df['monthly_total'].iloc[0] or 0.0)
        except Exception as e:
            logger.error(f"Error getting monthly spending: {e}")
            return 0.0
    
    def check_new_beneficiary(self, customer_id: str, recipient_account: str, transfer_type: str = None) -> int:
        try:
            placeholder = '%s' if DRIVER_TYPE == 'pymssql' else '?'
            
            if transfer_type:
                query = f"""SELECT COUNT(*) as count FROM TransactionHistoryLogs 
                            WHERE CustomerId = {placeholder} 
                            AND (ReceipentAccount = {placeholder} OR ReceipentAccount LIKE {placeholder})
                            AND TransferType = {placeholder}"""
                params = [customer_id, recipient_account, f'%{recipient_account}%', transfer_type]
            else:
                query = f"""SELECT COUNT(*) as count FROM TransactionHistoryLogs 
                            WHERE CustomerId = {placeholder} 
                            AND (ReceipentAccount = {placeholder} OR ReceipentAccount LIKE {placeholder})"""
                params = [customer_id, recipient_account, f'%{recipient_account}%']
            
            df = self.execute_query(query, params)
            count = df['count'].iloc[0]
            
            if count > 0:
                logger.info(f"Customer {customer_id} has {count} previous transactions to {recipient_account}")
                return 0
            else:
                logger.info(f"Customer {customer_id} has no previous transactions to {recipient_account}")
                return 1
                
        except Exception as e:
            logger.error(f"Error checking beneficiary: {e}")
            return 1
    
    def get_weekly_stats(self, customer_id: str, account_no: str) -> Dict[str, Any]:
        try:
            padded_account = account_no.zfill(14)
            if DRIVER_TYPE == 'pymssql':
                query = """
                    SELECT 
                        SUM(AmountInAed) as weekly_total,
                        COUNT(*) as weekly_txn_count,
                        AVG(AmountInAed) as weekly_avg_amount,
                        STDEV(AmountInAed) as weekly_std
                    FROM TransactionHistoryLogs 
                    WHERE CustomerId = %s AND (FromAccountNo = %s OR FromAccountNo = %s)
                    AND CreateDate >= DATEADD(DAY, -7, CAST(GETDATE() AS DATE))
                """
            else:
                query = """
                    SELECT 
                        SUM(AmountInAed) as weekly_total,
                        COUNT(*) as weekly_txn_count,
                        AVG(AmountInAed) as weekly_avg_amount,
                        STDEV(AmountInAed) as weekly_std
                    FROM TransactionHistoryLogs 
                    WHERE CustomerId = ? AND (FromAccountNo = ? OR FromAccountNo = ?)
                    AND CreateDate >= DATEADD(DAY, -7, CAST(GETDATE() AS DATE))
                """
            df = self.execute_query(query, [customer_id, account_no, padded_account])
            
            weekly_total = float(df['weekly_total'].iloc[0] or 0.0)
            weekly_txn_count = int(df['weekly_txn_count'].iloc[0] or 0)
            weekly_avg = float(df['weekly_avg_amount'].iloc[0] or 0.0)
            weekly_std = float(df['weekly_std'].iloc[0] or 0.0) if df['weekly_std'].iloc[0] is not None else 0.0
            
            weekly_deviation = 0.0
            if weekly_avg > 0:
                if DRIVER_TYPE == 'pymssql':
                    query_deviation = """
                        SELECT AVG(ABS(AmountInAed - %s)) as avg_deviation
                        FROM TransactionHistoryLogs 
                        WHERE CustomerId = %s AND (FromAccountNo = %s OR FromAccountNo = %s)
                        AND CreateDate >= DATEADD(DAY, -7, CAST(GETDATE() AS DATE))
                    """
                else:
                    query_deviation = """
                        SELECT AVG(ABS(AmountInAed - ?)) as avg_deviation
                        FROM TransactionHistoryLogs 
                        WHERE CustomerId = ? AND (FromAccountNo = ? OR FromAccountNo = ?)
                        AND CreateDate >= DATEADD(DAY, -7, CAST(GETDATE() AS DATE))
                    """
                df_dev = self.execute_query(query_deviation, [weekly_avg, customer_id, account_no, padded_account])
                weekly_deviation = float(df_dev['avg_deviation'].iloc[0] or 0.0) if df_dev['avg_deviation'].iloc[0] is not None else 0.0
            
            return {
                "user_weekly_total": weekly_total,
                "user_weekly_txn_count": weekly_txn_count,
                "user_weekly_avg_amount": weekly_avg,
                "user_weekly_deviation": weekly_deviation
            }
        except Exception as e:
            logger.error(f"Error getting weekly stats: {e}")
            return {
                "user_weekly_total": 0.0,
                "user_weekly_txn_count": 0,
                "user_weekly_avg_amount": 0.0,
                "user_weekly_deviation": 0.0
            }
    
    def get_monthly_stats(self, customer_id: str, account_no: str) -> Dict[str, Any]:
        try:
            padded_account = account_no.zfill(14)
            if DRIVER_TYPE == 'pymssql':
                query = """
                    SELECT 
                        SUM(AmountInAed) as monthly_total,
                        COUNT(*) as monthly_txn_count,
                        AVG(AmountInAed) as monthly_avg_amount
                    FROM TransactionHistoryLogs 
                    WHERE CustomerId = %s AND (FromAccountNo = %s OR FromAccountNo = %s)
                    AND MONTH(CreateDate) = MONTH(GETDATE()) 
                    AND YEAR(CreateDate) = YEAR(GETDATE())
                """
            else:
                query = """
                    SELECT 
                        SUM(AmountInAed) as monthly_total,
                        COUNT(*) as monthly_txn_count,
                        AVG(AmountInAed) as monthly_avg_amount
                    FROM TransactionHistoryLogs 
                    WHERE CustomerId = ? AND (FromAccountNo = ? OR FromAccountNo = ?)
                    AND MONTH(CreateDate) = MONTH(GETDATE()) 
                    AND YEAR(CreateDate) = YEAR(GETDATE())
                """
            df = self.execute_query(query, [customer_id, account_no, padded_account])
            
            monthly_total = float(df['monthly_total'].iloc[0] or 0.0)
            monthly_txn_count = int(df['monthly_txn_count'].iloc[0] or 0)
            monthly_avg = float(df['monthly_avg_amount'].iloc[0] or 0.0)
            
            monthly_deviation = 0.0
            if monthly_avg > 0:
                if DRIVER_TYPE == 'pymssql':
                    query_deviation = """
                        SELECT AVG(ABS(AmountInAed - %s)) as avg_deviation
                        FROM TransactionHistoryLogs 
                        WHERE CustomerId = %s AND (FromAccountNo = %s OR FromAccountNo = %s) 
                        AND MONTH(CreateDate) = MONTH(GETDATE()) 
                        AND YEAR(CreateDate) = YEAR(GETDATE())
                    """
                else:
                    query_deviation = """
                        SELECT AVG(ABS(AmountInAed - ?)) as avg_deviation
                        FROM TransactionHistoryLogs 
                        WHERE CustomerId = ? AND (FromAccountNo = ? OR FromAccountNo = ?) 
                        AND MONTH(CreateDate) = MONTH(GETDATE()) 
                        AND YEAR(CreateDate) = YEAR(GETDATE())
                    """
                df_dev = self.execute_query(query_deviation, [monthly_avg, customer_id, account_no, padded_account])
                monthly_deviation = float(df_dev['avg_deviation'].iloc[0] or 0.0) if df_dev['avg_deviation'].iloc[0] is not None else 0.0
            
            return {
                "current_month_spending": monthly_total,
                "user_monthly_txn_count": monthly_txn_count,
                "user_monthly_avg_amount": monthly_avg,
                "user_monthly_deviation": monthly_deviation
            }
        except Exception as e:
            logger.error(f"Error getting monthly stats: {e}")
            return {
                "current_month_spending": 0.0,
                "user_monthly_txn_count": 0,
                "user_monthly_avg_amount": 0.0,
                "user_monthly_deviation": 0.0
            }
    
    def get_velocity_metrics(self, customer_id: str, account_no: str) -> Dict[str, Any]:
        try:
            padded_account = account_no.zfill(14)
            if DRIVER_TYPE == 'pymssql':
                query = """
                    SELECT 
                        COUNT(CASE WHEN CreateDate >= DATEADD(MINUTE, -10, GETDATE()) THEN 1 END) as txn_count_10min,
                        COUNT(CASE WHEN CreateDate >= DATEADD(HOUR, -1, GETDATE()) THEN 1 END) as txn_count_1hour,
                        MAX(CreateDate) as last_txn_time
                    FROM TransactionHistoryLogs 
                    WHERE CustomerId = %s AND (FromAccountNo = %s OR FromAccountNo = %s)
                """
            else:
                query = """
                    SELECT 
                        COUNT(CASE WHEN CreateDate >= DATEADD(MINUTE, -10, GETDATE()) THEN 1 END) as txn_count_10min,
                        COUNT(CASE WHEN CreateDate >= DATEADD(HOUR, -1, GETDATE()) THEN 1 END) as txn_count_1hour,
                        MAX(CreateDate) as last_txn_time
                    FROM TransactionHistoryLogs 
                    WHERE CustomerId = ? AND (FromAccountNo = ? OR FromAccountNo = ?)
                """
            df = self.execute_query(query, [customer_id, account_no, padded_account])
            
            txn_count_10min = int(df['txn_count_10min'].iloc[0] or 0)
            txn_count_1hour = int(df['txn_count_1hour'].iloc[0] or 0)
            last_txn_time = df['last_txn_time'].iloc[0]
            
            time_since_last_txn = 3600.0
            if last_txn_time:
                from datetime import datetime
                time_diff = datetime.now() - last_txn_time
                time_since_last_txn = time_diff.total_seconds()
            
            return {
                "txn_count_10min": txn_count_10min,
                "txn_count_1hour": txn_count_1hour,
                "time_since_last_txn": time_since_last_txn
            }
        except Exception as e:
            logger.error(f"Error getting velocity metrics: {e}")
            return {
                "txn_count_10min": 0,
                "txn_count_1hour": 0,
                "time_since_last_txn": 3600.0
            }
    
    def get_all_user_stats(self, customer_id: str, account_no: str, transfer_type: str) -> Dict[str, Any]:
        try:
            base_stats = self.get_user_statistics(customer_id, account_no, transfer_type)
            weekly_stats = self.get_weekly_stats(customer_id, account_no)
            monthly_stats = self.get_monthly_stats(customer_id, account_no)
            velocity_stats = self.get_velocity_metrics(customer_id, account_no)
            
            combined_stats = {
                **base_stats,
                **weekly_stats,
                **monthly_stats,
                **velocity_stats
            }
            
            return combined_stats
        except Exception as e:
            logger.error(f"Error getting all user stats: {e}")
            return {
                "user_avg_amount": 5000.0,
                "user_std_amount": 2000.0,
                "user_max_amount": 15000.0,
                "user_txn_frequency": 0,
                "user_international_ratio": 0.0,
                "current_month_spending": 0.0,
                "user_weekly_total": 0.0,
                "user_weekly_txn_count": 0,
                "user_weekly_avg_amount": 0.0,
                "user_weekly_deviation": 0.0,
                "user_monthly_txn_count": 0,
                "user_monthly_avg_amount": 0.0,
                "user_monthly_deviation": 0.0,
                "txn_count_10min": 0,
                "txn_count_1hour": 0,
                "time_since_last_txn": 3600.0
            }
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def get_enabled_features(self) -> List[str]:
        try:
            if not self.is_connected():
                if not self.connect():
                    return []
            
            query = "SELECT FeatureName FROM FeaturesConfig WHERE IsEnabled = 1"
            result = self.execute_query(query)
            if result is not None and not result.empty:
                return result['FeatureName'].tolist()
            return []
        except Exception as e:
            logger.error(f"Error fetching enabled features: {e}")
            return []

    def insert_transaction_log(self, idempotence_key: str, request_method: str, 
                               request_endpoint: str, request_payload: str,
                               response_status_code: int, is_successful: bool,
                               user_id: str = None, client_ip: str = None,
                               response_payload: str = None, risk_score: float = None,
                               decision: str = None, error_code: str = None,
                               error_message: str = None, execution_time_ms: int = None) -> int:
        try:
            if not self.is_connected():
                if not self.connect():
                    return -1
            
            query = """
            INSERT INTO TransactionLogs (
                IdempotenceKey, RequestMethod, RequestEndpoint, RequestPayload,
                ResponseStatusCode, IsSuccessful, UserID, ClientIP, ResponsePayload,
                RiskScore, Decision, ErrorCode, ErrorMessage, ExecutionTimeMs
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            params = [
                idempotence_key, request_method, request_endpoint, request_payload,
                response_status_code, is_successful, user_id, client_ip, response_payload,
                risk_score, decision, error_code, error_message, execution_time_ms
            ]
            
            return self.execute_non_query(query, params)
        except Exception as e:
            logger.error(f"Error inserting transaction log: {e}")
            return -1

    def get_transaction_log_by_idempotence_key(self, idempotence_key: str) -> dict:
        try:
            if not self.is_connected():
                if not self.connect():
                    return None
            
            query = """
            SELECT * FROM TransactionLogs 
            WHERE IdempotenceKey = %s AND IsSuccessful = %s
            ORDER BY CreatedAt DESC
            """
            
            result = self.execute_query(query, [idempotence_key, 1])
            
            if result is not None and not result.empty:
                return result.iloc[0].to_dict()
            return None
        except Exception as e:
            logger.error(f"Error fetching transaction log: {e}")
            return None

    def get_customer_checks_config(self, customer_id: str, account_no: str, transfer_type: str) -> Dict[str, int]:
        try:
            if not self.is_connected():
                if not self.connect():
                    return self._default_checks_config()

            query = """
            SELECT ParameterName, IsEnabled
            FROM CustomerAccountTransferTypeConfig
            WHERE CustomerID = %s AND AccountNo = %s AND TransferType = %s
            AND ParameterName IN ('velocity_check_10min', 'velocity_check_1hour', 'monthly_spending_check', 'new_beneficiary_check')
            AND IsEnabled IN (0, 1)
            """

            result = self.execute_query(query, [customer_id, account_no, transfer_type])

            config = self._default_checks_config()

            if result is not None and len(result) > 0:
                for _, row in result.iterrows():
                    param_name = row['ParameterName']
                    if param_name in config:
                        config[param_name] = row['IsEnabled']

            return config

        except Exception as e:
            logger.error(f"Error fetching customer checks config: {e}")
            return self._default_checks_config()

    def _default_checks_config(self) -> Dict[str, int]:
        return {
            'velocity_check_10min': 1,
            'velocity_check_1hour': 1,
            'monthly_spending_check': 1,
            'new_beneficiary_check': 1
        }

    def get_all_thresholds(self) -> Dict[str, float]:
        try:
            if not self.is_connected():
                if not self.connect():
                    return self._default_thresholds()

            query = "SELECT ThresholdName, ThresholdValue FROM ThresholdConfig WHERE IsActive = 1"
            result = self.execute_query(query)

            thresholds = self._default_thresholds()

            if result is not None and not result.empty:
                for _, row in result.iterrows():
                    threshold_name = row['ThresholdName']
                    threshold_value = float(row['ThresholdValue'])
                    thresholds[threshold_name] = threshold_value

            return thresholds

        except Exception as e:
            logger.error(f"Error fetching thresholds: {e}")
            return self._default_thresholds()

    def _default_thresholds(self) -> Dict[str, float]:
        return {
            'MAX_VELOCITY_10MIN': 5.0,
            'MAX_VELOCITY_1HOUR': 15.0,
            'TRANSFER_MULTIPLIER_S': 2.0,
            'TRANSFER_MULTIPLIER_Q': 2.5,
            'TRANSFER_MULTIPLIER_L': 3.0,
            'TRANSFER_MULTIPLIER_I': 3.5,
            'TRANSFER_MULTIPLIER_O': 4.0,
            'TRANSFER_MULTIPLIER_M': 3.2,
            'TRANSFER_MULTIPLIER_F': 3.8,
            'TRANSFER_MIN_FLOOR_S': 5000.0,
            'TRANSFER_MIN_FLOOR_Q': 3000.0,
            'TRANSFER_MIN_FLOOR_L': 2000.0,
            'TRANSFER_MIN_FLOOR_I': 1500.0,
            'TRANSFER_MIN_FLOOR_O': 1000.0,
            'TRANSFER_MIN_FLOOR_M': 1800.0,
            'TRANSFER_MIN_FLOOR_F': 1200.0,
            'TRANSFER_TYPE_RISK_S': 0.9,
            'TRANSFER_TYPE_RISK_I': 0.1,
            'TRANSFER_TYPE_RISK_L': 0.2,
            'TRANSFER_TYPE_RISK_Q': 0.5,
            'TRANSFER_TYPE_RISK_O': 0.0,
            'TRANSFER_TYPE_RISK_M': 0.3,
            'TRANSFER_TYPE_RISK_F': 0.15,
            'RISK_SCORE_VELOCITY': 0.85,
            'RISK_SCORE_MONTHLY_SPENDING': 0.70,
            'RISK_SCORE_NEW_BENEFICIARY': 0.60,
            'RISK_SCORE_DEFAULT': 0.75,
            'ML_SCORE_BOOST': 0.15,
            'AE_SCORE_BOOST': 0.10,
            'RECENT_BURST_THRESHOLD': 300.0,
            'DEFAULT_USER_AVG': 5000.0,
            'DEFAULT_TIME_SINCE_LAST': 3600.0,
        }
    
    def get_cached_monthly_limit(self, customer_id: str, account_no: str, transfer_type: str) -> float:
        from datetime import datetime
        
        current_month = datetime.now().month
        current_year = datetime.now().year
        cache_key = f"limit:{customer_id}:{account_no}:{transfer_type}:{current_month}:{current_year}"
        
        try:
            from backend.velocity_service import get_velocity_service
            velocity_service = get_velocity_service()
            
            if velocity_service.redis_client:
                cached_limit = velocity_service.redis_client.get(cache_key)
                if cached_limit:
                    return float(cached_limit)
            else:
                if not hasattr(self, '_limit_cache'):
                    self._limit_cache = {}
                if cache_key in self._limit_cache:
                    return self._limit_cache[cache_key]
        except Exception as e:
            logger.warning(f"Cache check failed: {e}")
            if not hasattr(self, '_limit_cache'):
                self._limit_cache = {}
            if cache_key in self._limit_cache:
                return self._limit_cache[cache_key]
        
        try:
            padded_account = account_no.zfill(14)
            
            if DRIVER_TYPE == 'pymssql':
                query = """
                    SELECT 
                        AVG(AmountInAed) as avg_amount,
                        STDEV(AmountInAed) as std_amount
                    FROM TransactionHistoryLogs
                    WHERE CustomerId = %s 
                    AND (FromAccountNo = %s OR FromAccountNo = %s)
                    AND TransferType = %s
                    AND MONTH(CreateDate) = %s
                    AND YEAR(CreateDate) = %s
                """
            else:
                query = """
                    SELECT 
                        AVG(AmountInAed) as avg_amount,
                        STDEV(AmountInAed) as std_amount
                    FROM TransactionHistoryLogs
                    WHERE CustomerId = ? 
                    AND (FromAccountNo = ? OR FromAccountNo = ?)
                    AND TransferType = ?
                    AND MONTH(CreateDate) = ?
                    AND YEAR(CreateDate) = ?
                """
            
            prev_month = current_month - 1 if current_month > 1 else 12
            prev_year = current_year if current_month > 1 else current_year - 1
            
            result = self.execute_query(query, [customer_id, account_no, padded_account, transfer_type, prev_month, prev_year])
            
            if result is not None and len(result) > 0 and result['avg_amount'].iloc[0] is not None:
                user_avg = float(result['avg_amount'].iloc[0])
                user_std = float(result['std_amount'].iloc[0] or 0)
                
                import math
                if math.isnan(user_avg) or math.isnan(user_std):
                    user_avg = 5000.0
                    user_std = 2000.0
            else:
                user_avg = 5000.0
                user_std = 2000.0
            
            # Lazy import to avoid circular dependency
            from backend import rule_engine
            limit = rule_engine.calculate_threshold(user_avg, user_std, transfer_type)
            
            try:
                from backend.velocity_service import get_velocity_service
                velocity_service = get_velocity_service()
                
                if velocity_service.redis_client:
                    velocity_service.redis_client.setex(cache_key, 2592000, limit)
                    logger.info(f"Cached limit in Redis for {customer_id}/{account_no}/{transfer_type}: {limit}")
                else:
                    if not hasattr(self, '_limit_cache'):
                        self._limit_cache = {}
                    self._limit_cache[cache_key] = limit
                    logger.info(f"Cached limit in memory for {customer_id}/{account_no}/{transfer_type}: {limit}")
            except Exception as e:
                logger.warning(f"Cache store failed: {e}")
                if not hasattr(self, '_limit_cache'):
                    self._limit_cache = {}
                self._limit_cache[cache_key] = limit
            
            return limit
            
        except Exception as e:
            logger.error(f"Error calculating monthly limit: {e}")
            return 9000.0
    
    def save_drift_results(self, check_date: datetime, drift_type: str, drift_detected: bool, 
                          drift_score: Optional[float], features_affected: Optional[str],
                          overall_status: Optional[str], recommendation: Optional[str],
                          results_json: Optional[str]) -> bool:
        try:
            query = f"""
                INSERT INTO DriftMonitoringResults 
                (CheckDate, DriftType, DriftDetected, DriftScore, FeaturesAffected, 
                 OverallStatus, Recommendation, ResultsJson)
                VALUES ({self.param_placeholder}, {self.param_placeholder}, {self.param_placeholder}, 
                        {self.param_placeholder}, {self.param_placeholder}, {self.param_placeholder}, 
                        {self.param_placeholder}, {self.param_placeholder})
            """
            
            self.execute_non_query(query, [
                check_date, drift_type, drift_detected, drift_score,
                features_affected, overall_status, recommendation, results_json
            ])
            
            logger.info(f"Drift results saved: {drift_type} - {overall_status}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving drift results: {e}")
            return False
    
    def get_latest_drift_status(self) -> Optional[Dict[str, Any]]:
        try:
            query = """
                SELECT TOP 1 
                    Id, CheckDate, DriftType, DriftDetected, DriftScore,
                    FeaturesAffected, OverallStatus, Recommendation, ResultsJson
                FROM DriftMonitoringResults
                WHERE DriftType = 'full_monitoring'
                ORDER BY CheckDate DESC
            """
            
            result = self.execute_query(query)
            
            if result is not None and len(result) > 0:
                row = result.iloc[0]
                return {
                    'id': int(row['Id']),
                    'check_date': row['CheckDate'],
                    'drift_type': row['DriftType'],
                    'drift_detected': bool(row['DriftDetected']),
                    'drift_score': float(row['DriftScore']) if row['DriftScore'] is not None else None,
                    'features_affected': row['FeaturesAffected'],
                    'overall_status': row['OverallStatus'],
                    'recommendation': row['Recommendation'],
                    'results_json': row['ResultsJson']
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting latest drift status: {e}")
            return None
    
    def get_drift_history(self, limit: int = 30) -> List[Dict[str, Any]]:
        try:
            query = f"""
                SELECT TOP {limit}
                    Id, CheckDate, DriftType, DriftDetected, DriftScore,
                    FeaturesAffected, OverallStatus, Recommendation
                FROM DriftMonitoringResults
                WHERE DriftType = 'full_monitoring'
                ORDER BY CheckDate DESC
            """
            
            result = self.execute_query(query)
            
            if result is not None and len(result) > 0:
                return [
                    {
                        'id': int(row['Id']),
                        'check_date': row['CheckDate'],
                        'drift_type': row['DriftType'],
                        'drift_detected': bool(row['DriftDetected']),
                        'drift_score': float(row['DriftScore']) if row['DriftScore'] is not None else None,
                        'features_affected': row['FeaturesAffected'],
                        'overall_status': row['OverallStatus'],
                        'recommendation': row['Recommendation']
                    }
                    for _, row in result.iterrows()
                ]
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting drift history: {e}")
            return []
    
    def get_drift_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        try:
            query = f"""
                SELECT 
                    Id, CheckDate, DriftType, DriftDetected, DriftScore,
                    FeaturesAffected, OverallStatus, Recommendation
                FROM DriftMonitoringResults
                WHERE CheckDate >= {self.param_placeholder} AND CheckDate <= {self.param_placeholder}
                ORDER BY CheckDate DESC
            """
            
            result = self.execute_query(query, [start_date, end_date])
            
            if result is not None and len(result) > 0:
                return [
                    {
                        'id': int(row['Id']),
                        'check_date': row['CheckDate'],
                        'drift_type': row['DriftType'],
                        'drift_detected': bool(row['DriftDetected']),
                        'drift_score': float(row['DriftScore']) if row['DriftScore'] is not None else None,
                        'features_affected': row['FeaturesAffected'],
                        'overall_status': row['OverallStatus'],
                        'recommendation': row['Recommendation']
                    }
                    for _, row in result.iterrows()
                ]
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting drift by date range: {e}")
            return []

db_service = DatabaseService()

def get_db_service() -> DatabaseService:
    return db_service

if __name__ == "__main__":
    print("Testing Database Connection...")
    
    with DatabaseService() as db:
        if db.connect():
            print("Connection successful!")
            
            customers = db.get_all_customers()[:5]
            print(f"Sample customers: {customers}")
            
            if customers:
                accounts = db.get_customer_accounts(customers[0])
                print(f"Customer {customers[0]} accounts: {accounts}")
                
                if accounts:
                    stats = db.get_user_statistics(customers[0], accounts[0])
                    print(f"Account stats: {stats}")
        else:
            print("Connection failed!")
