import pandas as pd
import numpy as np
from typing import Tuple, List, Optional
from datetime import datetime, timedelta
import requests
from config import (
    SYMBOLS, TIMEFRAMES, HF_DATASET_REPO, HF_DATASET_PATH,
    KLINE_COLUMNS, OPENTIME_COLUMN, CLOSETIME_COLUMN,
    BINANCE_US_BASE_URL
)

class DataHandler:
    def __init__(self, hf_token: str):
        self.hf_token = hf_token
        self.symbols = SYMBOLS
        self.timeframes = TIMEFRAMES
        self.binance_url = BINANCE_US_BASE_URL
        self.max_retries = 3
        self.retry_delay = 1

    def fetch_latest_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 1000
    ) -> Optional[pd.DataFrame]:
        """Fetch latest klines from Binance US API with retry logic"""
        url = f'{self.binance_url}/klines'
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        
        for attempt in range(self.max_retries):
            try:
                print(f"  Fetching from: {url} with params {params}")
                response = requests.get(url, params=params, timeout=15)
                response.raise_for_status()
                data = response.json()
                
                if not data:
                    print(f"  Warning: Empty response for {symbol} {interval}")
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
                
                print(f"  Successfully fetched {len(df)} klines for {symbol} {interval}")
                return df
            except requests.exceptions.RequestException as e:
                print(f"  Attempt {attempt + 1}/{self.max_retries} failed for {symbol} {interval}: {str(e)}")
                if attempt < self.max_retries - 1:
                    import time
                    time.sleep(self.retry_delay)
                continue
        
        print(f"  Error: Failed to fetch klines for {symbol} {interval} after {self.max_retries} attempts")
        return None

    def download_from_hf(
        self,
        symbol: str,
        timeframe: str
    ) -> Optional[pd.DataFrame]:
        """Download parquet file from HuggingFace"""
        try:
            from huggingface_hub import hf_hub_download
            
            file_name = f"{symbol.replace('USDT', '')}_{timeframe}.parquet"
            file_path_str = f"{HF_DATASET_PATH}/{symbol}/{file_name}"
            
            print(f"  Downloading from HF: {HF_DATASET_REPO}/{file_path_str}")
            
            try:
                file_path = hf_hub_download(
                    repo_id=HF_DATASET_REPO,
                    filename=file_path_str,
                    token=self.hf_token,
                    timeout=30
                )
                
                df = pd.read_parquet(file_path)
                print(f"  Successfully downloaded {symbol} {timeframe} with {len(df)} rows")
                return df
            except Exception as hf_error:
                if "404" in str(hf_error) or "Repository Not Found" in str(hf_error):
                    print(f"  Warning: File not found on HF: {file_path_str}")
                    print(f"  This will be created as new file after first update")
                    return None
                raise
        except Exception as e:
            print(f"  Error downloading {symbol} {timeframe} from HF: {str(e)}")
            return None

    def merge_and_deduplicate(
        self,
        existing_df: Optional[pd.DataFrame],
        new_df: Optional[pd.DataFrame]
    ) -> Optional[pd.DataFrame]:
        """Merge existing and new data, removing duplicates"""
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
        
        print(f"  Merged data: {len(existing_df)} existing + {len(new_df)} new = {len(merged_df)} total rows")
        return merged_df

    def validate_data(self, df: Optional[pd.DataFrame]) -> bool:
        """Validate data integrity"""
        if df is None or df.empty:
            return False
        
        required_columns = KLINE_COLUMNS
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            print(f"  Error: Missing columns: {missing}")
            return False
        
        if df[OPENTIME_COLUMN].dtype != 'datetime64[ns]':
            print(f"  Error: {OPENTIME_COLUMN} is not datetime format")
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
            import tempfile
            import os
            
            file_name = f"{symbol.replace('USDT', '')}_{timeframe}.parquet"
            folder_path = f"{HF_DATASET_PATH}/{symbol}"
            
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_file = os.path.join(tmp_dir, file_name)
                df.to_parquet(tmp_file, index=False, compression='snappy')
                
                from huggingface_hub import upload_file
                print(f"  Uploading to HF: {HF_DATASET_REPO}/{folder_path}/{file_name}")
                
                upload_file(
                    path_or_fileobj=tmp_file,
                    path_in_repo=f"{folder_path}/{file_name}",
                    repo_id=HF_DATASET_REPO,
                    token=self.hf_token,
                    private=private,
                    commit_message=f"Update {symbol} {timeframe} at {datetime.now().isoformat()}"
                )
            
            print(f"  Successfully uploaded {symbol} {timeframe}")
            return True
        except Exception as e:
            print(f"  Error uploading {symbol} {timeframe} to HF: {str(e)}")
            return False

    def process_symbol(
        self,
        symbol: str,
        timeframe: str
    ) -> bool:
        """Process single symbol update"""
        print(f"\nProcessing {symbol} {timeframe}...")
        
        existing_df = self.download_from_hf(symbol, timeframe)
        new_df = self.fetch_latest_klines(symbol, timeframe, limit=1000)
        
        if new_df is None:
            print(f"FAILED: Could not fetch latest klines for {symbol} {timeframe}")
            return False
        
        merged_df = self.merge_and_deduplicate(existing_df, new_df)
        
        if merged_df is None:
            print(f"FAILED: No data to merge for {symbol} {timeframe}")
            return False
        
        if not self.validate_data(merged_df):
            print(f"FAILED: Data validation failed for {symbol} {timeframe}")
            return False
        
        success = self.upload_to_hf(merged_df, symbol, timeframe, private=False)
        if success:
            print(f"SUCCESS: {symbol} {timeframe}")
        return success

    def process_all(
        self,
        symbols: Optional[List[str]] = None,
        timeframes: Optional[List[str]] = None
    ) -> dict:
        """Process all symbols and timeframes"""
        symbols = symbols or self.symbols
        timeframes = timeframes or self.timeframes
        
        results = {}
        total = len(symbols) * len(timeframes)
        current = 0
        
        for symbol in symbols:
            for timeframe in timeframes:
                current += 1
                key = f"{symbol}_{timeframe}"
                print(f"\n[{current}/{total}] {key}")
                success = self.process_symbol(symbol, timeframe)
                results[key] = "SUCCESS" if success else "FAILED"
        
        return results