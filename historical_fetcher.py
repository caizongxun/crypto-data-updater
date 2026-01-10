import pandas as pd
import numpy as np
from typing import Optional, List
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
        self.cache_dir = cache_dir
        self.batch_size = 20  # 每 20 個檔案上傳一次
        
        # 建立快取目錄
        self.cache_dir = os.path.join(cache_dir, HF_DATASET_PATH)
        os.makedirs(self.cache_dir, exist_ok=True)
        
        print("Logging in to HuggingFace...")
        try:
            login(token=hf_token)
            print("HuggingFace login successful!\n")
        except Exception as e:
            print(f"Warning: HuggingFace login error: {e}\n")
    
    def get_interval_ms(self, timeframe: str) -> int:
        """
        Get interval in milliseconds for timeframe.
        """
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
        """
        Fetch a batch of klines from Binance US API.
        start_time: milliseconds timestamp
        """
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
            
            # Convert numeric columns
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
        """
        Fetch all historical data from START_TIMESTAMP to now.
        Loop through batches of 1000 klines.
        """
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
            print(f"    Batch {batch_count}: ", end="", flush=True)
            
            for attempt in range(self.max_retries):
                try:
                    df = self.fetch_batch(symbol, interval, current_time, limit=1000)
                    
                    if df is None or df.empty:
                        empty_batches += 1
                        print(f"Empty response")
                        
                        if empty_batches >= max_empty_batches:
                            print(f"    Reached end of data (consecutive empty batches)")
                            break
                        
                        current_time += interval_ms * 1000
                        break
                    
                    empty_batches = 0
                    
                    all_data.append(df)
                    last_time = df[OPENTIME_COLUMN].iloc[-1]
                    current_time = int(df[CLOSETIME_COLUMN].iloc[-1].timestamp() * 1000) + 1
                    
                    rows = len(df)
                    date_str = df[OPENTIME_COLUMN].iloc[-1].strftime('%Y-%m-%d %H:%M')
                    print(f"{rows} rows up to {date_str}")
                    
                    time.sleep(0.2)
                    break
                    
                except Exception as e:
                    print(f"Attempt {attempt + 1} failed: {str(e)[:50]}", flush=True)
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
        """
        Validate data integrity.
        """
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
    
    def save_to_cache(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str
    ) -> str:
        """
        Save parquet file to local cache.
        Returns: file path
        """
        file_name = get_file_name(symbol, timeframe)
        symbol_dir = os.path.join(self.cache_dir, symbol)
        os.makedirs(symbol_dir, exist_ok=True)
        
        file_path = os.path.join(symbol_dir, file_name)
        df.to_parquet(file_path, index=False, compression='snappy')
        
        print(f"  Cached to {file_path}")
        return file_path
    
    def upload_batch_to_hf(self, batch_num: int, cached_files: List[tuple]) -> int:
        """
        Upload a batch of cached files to HuggingFace.
        cached_files: list of (symbol, timeframe, file_path) tuples
        Returns: number of successful uploads
        """
        print(f"\n{'=' * 70}")
        print(f"Uploading Batch {batch_num} ({len(cached_files)} files) to HuggingFace...")
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
                time.sleep(0.5)  # 延遲以避免速率限制
                
            except Exception as e:
                print(f" Failed: {str(e)[:60]}")
        
        print(f"\nBatch {batch_num} Upload Summary: {successful}/{len(cached_files)} successful")
        return successful
    
    def process_symbol(
        self,
        symbol: str,
        timeframe: str
    ) -> bool:
        """
        Process single symbol: fetch all history and save to cache.
        """
        print(f"\nProcessing {symbol} {timeframe}...")
        
        df = self.fetch_all_history(symbol, timeframe)
        
        if df is None:
            print(f"FAILED: Could not fetch historical data")
            return False
        
        if not self.validate_data(df):
            print(f"FAILED: Data validation failed")
            return False
        
        self.save_to_cache(df, symbol, timeframe)
        print(f"SUCCESS: {symbol} {timeframe} ({len(df)} klines)")
        return True
    
    def process_all(
        self,
        symbols: Optional[List[str]] = None,
        timeframes: Optional[List[str]] = None
    ) -> dict:
        """
        Process all symbols and timeframes.
        Fetch and cache all data, then upload in batches.
        """
        symbols = symbols or SYMBOLS
        timeframes = timeframes or TIMEFRAMES
        
        results = {}
        total = len(symbols) * len(timeframes)
        current = 0
        
        # 清空快取目錄
        if os.path.exists(self.cache_dir):
            shutil.rmtree(self.cache_dir)
        os.makedirs(self.cache_dir, exist_ok=True)
        
        print(f"\n{'=' * 70}")
        print(f"Phase 1: Fetching historical data for {len(symbols)} symbols")
        print(f"Total operations: {total}")
        print(f"Batch upload size: {self.batch_size} files")
        print(f"{'=' * 70}\n")
        
        # Phase 1: 抓取所有數據並快取
        for symbol in symbols:
            for timeframe in timeframes:
                current += 1
                key = f"{symbol}_{timeframe}"
                print(f"\n[{current}/{total}] {key}")
                success = self.process_symbol(symbol, timeframe)
                results[key] = "SUCCESS" if success else "FAILED"
        
        # Phase 2: 批量上傳
        print(f"\n\n{'=' * 70}")
        print(f"Phase 2: Batch uploading to HuggingFace")
        print(f"{'=' * 70}\n")
        
        cached_files = []
        batch_num = 1
        upload_count = 0
        
        # 掃描快取目錄並構建檔案列表
        for symbol in symbols:
            symbol_dir = os.path.join(self.cache_dir, symbol)
            if os.path.exists(symbol_dir):
                for timeframe in timeframes:
                    file_name = get_file_name(symbol, timeframe)
                    file_path = os.path.join(symbol_dir, file_name)
                    if os.path.exists(file_path):
                        cached_files.append((symbol, timeframe, file_path))
                        
                        # 每 20 個檔案上傳一次
                        if len(cached_files) == self.batch_size:
                            upload_count += self.upload_batch_to_hf(batch_num, cached_files)
                            batch_num += 1
                            cached_files = []
        
        # 上傳剩餘檔案
        if cached_files:
            upload_count += self.upload_batch_to_hf(batch_num, cached_files)
        
        print(f"\n\n{'=' * 70}")
        print(f"FINAL SUMMARY")
        print(f"{'=' * 70}")
        success_count = sum(1 for v in results.values() if v == "SUCCESS")
        failed_count = sum(1 for v in results.values() if v == "FAILED")
        print(f"Fetch Results: {success_count} successful, {failed_count} failed")
        print(f"Upload Results: {upload_count} files uploaded")
        print(f"{'=' * 70}\n")
        
        return results