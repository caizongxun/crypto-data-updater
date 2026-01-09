import pandas as pd
import numpy as np
from typing import Tuple, List
from datetime import datetime, timedelta
import requests
from config import (
    SYMBOLS, TIMEFRAMES, HF_DATASET_REPO, HF_DATASET_PATH,
    KLINE_COLUMNS, OPENTIME_COLUMN, CLOSETIME_COLUMN
)

class DataHandler:
    def __init__(self, hf_token: str):
        self.hf_token = hf_token
        self.symbols = SYMBOLS
        self.timeframes = TIMEFRAMES

    def fetch_latest_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 1000
    ) -> pd.DataFrame:
        """Fetch latest klines from Binance API"""
        url = f'https://api.binance.com/api/v3/klines'
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            df = pd.DataFrame(data, columns=KLINE_COLUMNS)
            df[OPENTIME_COLUMN] = pd.to_datetime(df[OPENTIME_COLUMN], unit='ms')
            df[CLOSETIME_COLUMN] = pd.to_datetime(df[CLOSETIME_COLUMN], unit='ms')
            
            numeric_columns = ['open', 'high', 'low', 'close', 'volume',
                             'quote_asset_volume', 'taker_buy_base_asset_volume',
                             'taker_buy_quote_asset_volume']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            df['number_of_trades'] = pd.to_numeric(df['number_of_trades'], errors='coerce')
            
            return df
        except Exception as e:
            print(f"Error fetching klines for {symbol} {interval}: {str(e)}")
            return None

    def download_from_hf(
        self,
        symbol: str,
        timeframe: str
    ) -> pd.DataFrame:
        """Download parquet file from HuggingFace"""
        try:
            from huggingface_hub import hf_hub_download
            
            file_name = f"{symbol.replace('USDT', '')}_{timeframe}.parquet"
            file_path = hf_hub_download(
                repo_id=HF_DATASET_REPO,
                filename=f"{HF_DATASET_PATH}/{symbol}/{file_name}",
                token=self.hf_token
            )
            
            df = pd.read_parquet(file_path)
            return df
        except Exception as e:
            print(f"Error downloading {symbol} {timeframe} from HF: {str(e)}")
            return None

    def merge_and_deduplicate(
        self,
        existing_df: pd.DataFrame,
        new_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Merge existing and new data, removing duplicates"""
        if existing_df is None or existing_df.empty:
            return new_df
        
        if new_df is None or new_df.empty:
            return existing_df
        
        merged_df = pd.concat([existing_df, new_df], ignore_index=True)
        merged_df = merged_df.drop_duplicates(
            subset=[OPENTIME_COLUMN],
            keep='last'
        )
        merged_df = merged_df.sort_values(OPENTIME_COLUMN).reset_index(drop=True)
        
        return merged_df

    def validate_data(self, df: pd.DataFrame) -> bool:
        """Validate data integrity"""
        if df is None or df.empty:
            return False
        
        required_columns = KLINE_COLUMNS
        if not all(col in df.columns for col in required_columns):
            return False
        
        if df[OPENTIME_COLUMN].dtype != 'datetime64[ns]':
            return False
        
        return True

    def upload_to_hf(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str,
        private: bool = False
    ) -> bool:
        """Upload updated parquet file to HuggingFace"""
        try:
            from huggingface_hub import CommitScheduler
            import tempfile
            import os
            
            file_name = f"{symbol.replace('USDT', '')}_{timeframe}.parquet"
            folder_path = f"{HF_DATASET_PATH}/{symbol}"
            
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_file = os.path.join(tmp_dir, file_name)
                df.to_parquet(tmp_file, index=False)
                
                from huggingface_hub import upload_file
                upload_file(
                    path_or_fileobj=tmp_file,
                    path_in_repo=f"{folder_path}/{file_name}",
                    repo_id=HF_DATASET_REPO,
                    token=self.hf_token,
                    private=private
                )
            
            print(f"Successfully uploaded {symbol} {timeframe}")
            return True
        except Exception as e:
            print(f"Error uploading {symbol} {timeframe} to HF: {str(e)}")
            return False

    def process_symbol(
        self,
        symbol: str,
        timeframe: str
    ) -> bool:
        """Process single symbol update"""
        print(f"Processing {symbol} {timeframe}...")
        
        existing_df = self.download_from_hf(symbol, timeframe)
        new_df = self.fetch_latest_klines(symbol, timeframe, limit=1000)
        
        if new_df is None:
            print(f"Failed to fetch latest klines for {symbol} {timeframe}")
            return False
        
        merged_df = self.merge_and_deduplicate(existing_df, new_df)
        
        if not self.validate_data(merged_df):
            print(f"Data validation failed for {symbol} {timeframe}")
            return False
        
        success = self.upload_to_hf(merged_df, symbol, timeframe, private=False)
        return success

    def process_all(
        self,
        symbols: List[str] = None,
        timeframes: List[str] = None
    ) -> dict:
        """Process all symbols and timeframes"""
        symbols = symbols or self.symbols
        timeframes = timeframes or self.timeframes
        
        results = {}
        for symbol in symbols:
            for timeframe in timeframes:
                key = f"{symbol}_{timeframe}"
                success = self.process_symbol(symbol, timeframe)
                results[key] = "SUCCESS" if success else "FAILED"
                print(f"{key}: {results[key]}")
        
        return results