import pandas as pd
import numpy as np
from typing import Optional, List, Tuple
from datetime import datetime, timedelta
import requests
import time
from huggingface_hub import login, upload_file
import tempfile
import os
import shutil

from config import (
    SYMBOLS, TIMEFRAMES, HF_DATASET_REPO, HF_DATASET_PATH,
    KLINE_COLUMNS, OPENTIME_COLUMN, CLOSETIME_COLUMN,
    BINANCE_US_BASE_URL, START_TIMESTAMP, get_file_name
)

class HistoricalFetcher:
    def __init__(self, hf_token: str, cache_dir: str = '/tmp/crypto_cache'):
        self.hf_token = hf_token
        self.binance_url = BINANCE_US_BASE_URL
        self.max_retries = 3
        self.retry_delay = 2
        self.batch_size = 20
        
        self.cache_dir = os.path.join(cache_dir, HF_DATASET_PATH)
        os.makedirs(self.cache_dir, exist_ok=True)
        
        print("Logging in to HuggingFace...")
        try:
            login(token=hf_token)
            print("HuggingFace login successful!\n")
        except Exception as e:
            print(f"Warning: HuggingFace login error: {e}\n")
    
    def get_interval_ms(self, timeframe: str) -> int:
        if timeframe == '15m':
            return 15 * 60 * 1000
        elif timeframe == '1h':
            return 60 * 60 * 1000
        else:
            raise ValueError(f"Unknown timeframe: {timeframe}")
    
    def fetch_batch(
        self,
        symbol: str,
        interval: str,
        start_time: int,
        limit: int = 1000
    ) -> Optional[pd.DataFrame]:
        url = f'{self.binance_url}/klines'
        params = {
            'symbol': symbol,
            'interval': interval,
            'startTime': start_time,
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
            return None
    
    def fetch_all_history(
        self,
        symbol: str,
        interval: str
    ) -> Optional[pd.DataFrame]:
        print(f"  Fetching {symbol} {interval} from 2017-08-01 to now...")
        
        all_data = []
        current_time = START_TIMESTAMP
        now_ms = int(datetime.now().timestamp() * 1000)
        interval_ms = self.get_interval_ms(interval)
        batch_count = 0
        empty_batches = 0
        max_empty_batches = 5
        
        while current_time < now_ms:
            batch_count += 1
            
            for attempt in range(self.max_retries):
                try:
                    df = self.fetch_batch(symbol, interval, current_time, limit=1000)
                    
                    if df is None or df.empty:
                        empty_batches += 1
                        
                        if empty_batches >= max_empty_batches:
                            break
                        
                        current_time += interval_ms * 1000
                        break
                    
                    empty_batches = 0
                    all_data.append(df)
                    current_time = int(df[CLOSETIME_COLUMN].iloc[-1].timestamp() * 1000) + 1
                    
                    time.sleep(0.2)
                    break
                    
                except Exception as e:
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                    continue
            
            if empty_batches >= max_empty_batches:
                break
        
        if not all_data:
            print(f"  ERROR: Failed to fetch any data for {symbol} {interval}")
            return None
        
        combined_df = pd.concat(all_data, ignore_index=True)
        combined_df = combined_df.drop_duplicates(subset=[OPENTIME_COLUMN], keep='last')
        combined_df = combined_df.sort_values(OPENTIME_COLUMN).reset_index(drop=True)
        
        print(f"  Total: {len(combined_df)} klines from {combined_df[OPENTIME_COLUMN].iloc[0]} to {combined_df[OPENTIME_COLUMN].iloc[-1]}")
        
        return combined_df
    
    def validate_data(self, df: Optional[pd.DataFrame]) -> bool:
        if df is None or df.empty:
            return False
        
        required_columns = KLINE_COLUMNS
        if not all(col in df.columns for col in required_columns):
            return False
        
        if df[OPENTIME_COLUMN].dtype != 'datetime64[ns]':
            return False
        
        return True
    
    def save_to_cache(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str
    ) -> str:
        file_name = get_file_name(symbol, timeframe)
        symbol_dir = os.path.join(self.cache_dir, symbol)
        os.makedirs(symbol_dir, exist_ok=True)
        
        file_path = os.path.join(symbol_dir, file_name)
        df.to_parquet(file_path, index=False, compression='snappy')
        
        return file_path
    
    def upload_batch_to_hf(self, batch_num: int, cached_files: List[Tuple]) -> int:
        """
        Upload a batch of cached files to HuggingFace.
        cached_files: list of (symbol, timeframe, file_path) tuples
        """
        print(f"\n{'=' * 70}")
        print(f"Batch {batch_num} Upload: {len(cached_files)} files to HuggingFace")
        print(f"{'=' * 70}")
        
        successful = 0
        
        for i, (symbol, timeframe, file_path) in enumerate(cached_files, 1):
            try:
                file_name = get_file_name(symbol, timeframe)
                folder_path = f"{HF_DATASET_PATH}/{symbol}"
                repo_path = f"{folder_path}/{file_name}"
                
                print(f"  [{i}/{len(cached_files)}] Uploading {file_name}...", end="", flush=True)
                
                upload_file(
                    path_or_fileobj=file_path,
                    path_in_repo=repo_path,
                    repo_id=HF_DATASET_REPO,
                    repo_type="dataset",
                    token=self.hf_token,
                    commit_message=f"Upload {symbol} {timeframe} historical data (batch {batch_num})"
                )
                
                print(" Done")
                successful += 1
                time.sleep(0.5)
                
            except Exception as e:
                print(f" Failed: {str(e)[:60]}")
        
        print(f"Batch {batch_num}: {successful}/{len(cached_files)} successful\n")
        return successful
    
    def process_symbol(
        self,
        symbol: str,
        timeframe: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Process single symbol: fetch all history and save to cache.
        Returns: (success, file_path)
        """
        df = self.fetch_all_history(symbol, timeframe)
        
        if df is None:
            return False, None
        
        if not self.validate_data(df):
            return False, None
        
        file_path = self.save_to_cache(df, symbol, timeframe)
        print(f"  Cached to {symbol} {timeframe}")
        return True, file_path
    
    def process_all(
        self,
        symbols: Optional[List[str]] = None,
        timeframes: Optional[List[str]] = None
    ) -> dict:
        """
        Phase 1: Fetch all data and cache locally.
        Phase 2: Upload in batches of 20 files.
        """
        symbols = symbols or SYMBOLS
        timeframes = timeframes or TIMEFRAMES
        
        results = {}
        total = len(symbols) * len(timeframes)
        current = 0
        
        if os.path.exists(self.cache_dir):
            shutil.rmtree(self.cache_dir)
        os.makedirs(self.cache_dir, exist_ok=True)
        
        print(f"\n{'=' * 70}")
        print(f"PHASE 1: Fetching historical data ({total} files)")
        print(f"{'=' * 70}\n")
        
        cached_files_list = []  # 用來記錄所有快取的檔案
        
        for symbol in symbols:
            for timeframe in timeframes:
                current += 1
                key = f"{symbol}_{timeframe}"
                print(f"[{current}/{total}] {key}")
                
                success, file_path = self.process_symbol(symbol, timeframe)
                results[key] = "SUCCESS" if success else "FAILED"
                
                if success and file_path:
                    cached_files_list.append((symbol, timeframe, file_path))
        
        # Phase 2: 批量上傳
        print(f"\n{'=' * 70}")
        print(f"PHASE 2: Batch uploading to HuggingFace")
        print(f"{'=' * 70}")
        print(f"Total cached files: {len(cached_files_list)}")
        print(f"Batch size: {self.batch_size} files per batch\n")
        
        batch_num = 1
        total_uploaded = 0
        
        for i in range(0, len(cached_files_list), self.batch_size):
            batch = cached_files_list[i:i + self.batch_size]
            uploaded = self.upload_batch_to_hf(batch_num, batch)
            total_uploaded += uploaded
            batch_num += 1
        
        # Final summary
        print(f"\n{'=' * 70}")
        print(f"FINAL SUMMARY")
        print(f"{'=' * 70}")
        success_count = sum(1 for v in results.values() if v == "SUCCESS")
        failed_count = sum(1 for v in results.values() if v == "FAILED")
        print(f"Fetched: {success_count} successful, {failed_count} failed")
        print(f"Uploaded: {total_uploaded}/{len(cached_files_list)} files")
        print(f"Data location: https://huggingface.co/datasets/zongowo111/v2-crypto-ohlcv-data")
        print(f"{'=' * 70}\n")
        
        return results