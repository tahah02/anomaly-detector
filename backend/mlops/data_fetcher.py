import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import Optional
from backend.db_service import get_db_service

logger = logging.getLogger(__name__)


class DataFetcher:
    def __init__(self):
        self.db = get_db_service()
    
    def fetch_training_data(self, since_date: Optional[datetime] = None) -> pd.DataFrame:
        try:
            if since_date is None:
                since_date = datetime.now() - timedelta(days=90)
            
            logger.info(f"Fetching training data from TransactionHistoryLogs since {since_date}...")
            
            query = """
                SELECT 
                    CustomerId, 
                    FromAccountNo, 
                    ReceipentAccount, 
                    AmountInAed, 
                    TransferType, 
                    CreateDate, 
                    ChannelId, 
                    BankCountry
                FROM TransactionHistoryLogs 
                WHERE CreateDate >= %s 
                AND CreateDate IS NOT NULL 
                ORDER BY CreateDate DESC
            """
            
            df = self.db.execute_query(query, [since_date])
            
            if df is None or df.empty:
                logger.warning(f"No training data fetched from TransactionHistoryLogs since {since_date}")
                return pd.DataFrame()
            
            logger.info(f"Fetched {len(df)} records from TransactionHistoryLogs")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching training data: {e}")
            return pd.DataFrame()


def get_data_fetcher() -> DataFetcher:
    return DataFetcher()
