import pandas as pd
import numpy as np
from typing import Optional, List
from datetime import datetime
import requests
import time
from huggingface_hub import login, hf_hub_download, upload_file
import tempfile
import os

from config import (
    SYMBOLS, TIMEFRAMES, HF_DATASET_REPO, HF_DATASET_PATH,
    KLINE_COLUMNS, OPENTIME_COLUMN, CLOSETIME_COLUMN,
    BINANCE_US_BASE_URL, get_file_name
)

class IncrementalUpdater:
    """
    Incremental updater: Fetch only latest 1000 klines and merge with existing data.
    Used for scheduled GitHub Actions to keep data up-to-date.
    """
    def __init__(self, hf_token: str):
        self.hf_token = hf_token
        self.binance_url = BINANCE_US_BASE_URL
        self.max_retries = 3
        self.retry_delay = 2
        
        print("Logging in to HuggingFace...")
        try:
            login(token=hf_token)
            print("HuggingFace login successful!\n")
        except Exception as e:
            print(f"Warning: HuggingFace login error: {e}\n")
    
    def fetch_latest_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 1000
    ) -> Optional[pd.DataFrame]:
        """
        Fetch latest 1000 klines from Binance US API.
        """
        url = f'{self.binance_url}/klines'
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        
        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            if not data:
                return None
            
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
            print(f"    Error fetching {symbol} {interval}: {str(e)[:80]}")
            return None
    
    def download_from_hf(
        self,
        symbol: str,
        timeframe: str
    ) -> Optional[pd.DataFrame]:
        """
        Download existing parquet file from HuggingFace.
        """
        try:
            file_name = get_file_name(symbol, timeframe)
            file_path_str = f"{HF_DATASET_PATH}/{symbol}/{file_name}"
            
            file_path = hf_hub_download(
                repo_id=HF_DATASET_REPO,
                filename=file_path_str,
                repo_type="dataset",
                token=self.hf_token
            )
            
            df = pd.read_parquet(file_path)
            return df
        except Exception as e:
            return None
    
    def merge_and_deduplicate(
        self,
        existing_df: Optional[pd.DataFrame],
        new_df: Optional[pd.DataFrame]
    ) -> Optional[pd.DataFrame]:
        """
        Merge existing and new data, removing duplicates.
        """
        if existing_df is None or existing_df.empty:
            if new_df is None or new_df.empty:
                return None
            return new_df.copy()
        
        if new_df is None or new_df.empty:
            return existing_df.copy()
        
        merged_df = pd.concat([existing_df, new_df], ignore_index=True)
        merged_df = merged_df.drop_duplicates(
            subset=[OPENTIME_COLUMN],
            keep='last'
        )
        merged_df = merged_df.sort_values(OPENTIME_COLUMN).reset_index(drop=True)
        
        return merged_df
    
    def validate_data(self, df: Optional[pd.DataFrame]) -> bool:
        """
        Validate data integrity.
        """
        if df is None or df.empty:
            return False
        
        if df[OPENTIME_COLUMN].dtype != 'datetime64[ns]':
            return False
        
        return True
    
    def upload_to_hf(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str
    ) -> bool:
        """
        Upload updated parquet file to HuggingFace.
        """
        try:
            import tempfile
            import os
            
            file_name = get_file_name(symbol, timeframe)
            folder_path = f"{HF_DATASET_PATH}/{symbol}"
            
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_file = os.path.join(tmp_dir, file_name)
                df.to_parquet(tmp_file, index=False, compression='snappy')
                
                upload_file(
                    path_or_fileobj=tmp_file,
                    path_in_repo=f"{folder_path}/{file_name}",
                    repo_id=HF_DATASET_REPO,
                    repo_type="dataset",
                    token=self.hf_token,
                    commit_message=f"Update {symbol} {timeframe} at {datetime.now().isoformat()}"
                )
            
            return True
        except Exception as e:
            print(f"    Upload error: {str(e)[:80]}")
            return False
    
    def process_symbol(
        self,
        symbol: str,
        timeframe: str
    ) -> bool:
        """
        Process single symbol: fetch latest, merge with existing, and upload.
        """
        print(f"  {symbol} {timeframe}...", end="", flush=True)
        
        # Download existing
        existing_df = self.download_from_hf(symbol, timeframe)
        
        # Fetch latest
        new_df = self.fetch_latest_klines(symbol, timeframe, limit=1000)
        
        if new_df is None:
            print(" FAILED (fetch error)")
            return False
        
        # Merge
        merged_df = self.merge_and_deduplicate(existing_df, new_df)
        
        if merged_df is None:
            print(" FAILED (no data)")
            return False
        
        if not self.validate_data(merged_df):
            print(" FAILED (validation error)")
            return False
        
        # Upload
        success = self.upload_to_hf(merged_df, symbol, timeframe)
        
        if success:
            new_rows = len(new_df) if existing_df is None else len(new_df)
            print(f" OK ({len(merged_df)} total)")
        else:
            print(" FAILED (upload error)")
        
        return success
    
    def process_all(
        self,
        symbols: Optional[List[str]] = None,
        timeframes: Optional[List[str]] = None
    ) -> dict:
        """
        Process all symbols and timeframes.
        """
        symbols = symbols or SYMBOLS
        timeframes = timeframes or TIMEFRAMES
        
        results = {}
        total = len(symbols) * len(timeframes)
        current = 0
        
        print(f"\n{'=' * 70}")
        print(f"Incremental Update: {len(symbols)} symbols × {len(timeframes)} timeframes")
        print(f"{'=' * 70}\n")
        
        for symbol in symbols:
            for timeframe in timeframes:
                current += 1
                key = f"{symbol}_{timeframe}"
                success = self.process_symbol(symbol, timeframe)
                results[key] = "SUCCESS" if success else "FAILED"
        
        # Summary
        print(f"\n{'=' * 70}")
        success_count = sum(1 for v in results.values() if v == "SUCCESS")
        failed_count = sum(1 for v in results.values() if v == "FAILED")
        print(f"Results: {success_count} successful, {failed_count} failed")
        print(f"{'=' * 70}\n")
        
        return results