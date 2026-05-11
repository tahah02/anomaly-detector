import pandas as pd
import polars as pl
import logging
from datetime import datetime, timedelta
from typing import Optional, Union
from backend.db_service import get_db_service, get_param_placeholder

logger = logging.getLogger(__name__)


class DataFetcher:
    def __init__(self, use_polars: bool = True):
        self.db = get_db_service()
        self.param_placeholder = get_param_placeholder()
        self.use_polars = use_polars
    
    def fetch_training_data(self, since_date: Optional[datetime] = None, use_polars: bool = None) -> Union[pd.DataFrame, pl.DataFrame]:
        """
        Fetch training data from database.
        
        Args:
            since_date: Start date for data fetching (default: 90 days ago)
            use_polars: Use Polars instead of Pandas (default: self.use_polars)
        
        Returns:
            DataFrame (Pandas or Polars depending on use_polars flag)
        """
        try:
            if since_date is None:
                since_date = datetime.now() - timedelta(days=90)
            
            use_polars_flag = use_polars if use_polars is not None else self.use_polars
            
            logger.info(f"Fetching training data from TransactionHistoryLogs since {since_date}...")
            logger.info(f"Using {'Polars' if use_polars_flag else 'Pandas'} for data processing")
            
            query = f"""
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
                WHERE CreateDate >= {self.param_placeholder} 
                AND CreateDate IS NOT NULL 
                ORDER BY CreateDate DESC
            """
            
            df_pandas = self.db.execute_query(query, [since_date])
            
            if df_pandas is None or df_pandas.empty:
                logger.warning(f"No training data fetched from TransactionHistoryLogs since {since_date}")
                return pl.DataFrame() if use_polars_flag else pd.DataFrame()
            
            logger.info(f"Fetched {len(df_pandas)} records from TransactionHistoryLogs")
            
            # Convert to Polars if requested
            if use_polars_flag:
                df_polars = pl.from_pandas(df_pandas)
                logger.info(f"Converted to Polars DataFrame - Shape: {df_polars.shape}")
                return df_polars
            else:
                return df_pandas
            
        except Exception as e:
            logger.error(f"Error fetching training data: {e}")
            use_polars_flag = use_polars if use_polars is not None else self.use_polars
            return pl.DataFrame() if use_polars_flag else pd.DataFrame()
    
    def fetch_training_data_pandas(self, since_date: Optional[datetime] = None) -> pd.DataFrame:
        """Fetch training data as Pandas DataFrame (backward compatible)"""
        return self.fetch_training_data(since_date, use_polars=False)
    
    def fetch_training_data_polars(self, since_date: Optional[datetime] = None) -> pl.DataFrame:
        """Fetch training data as Polars DataFrame (10x faster)"""
        return self.fetch_training_data(since_date, use_polars=True)


def get_data_fetcher(use_polars: bool = True) -> DataFetcher:
    """Get DataFetcher instance with optional Polars support"""
    return DataFetcher(use_polars=use_polars)
