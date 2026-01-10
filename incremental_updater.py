import pandas as pd
import numpy as np
from typing import Optional, List
from datetime import datetime
import requests
import time
from huggingface_hub import login, hf_hub_download, upload_file
import tempfile
import os
import logging

from config import (
    SYMBOLS, TIMEFRAMES, HF_DATASET_REPO, HF_DATASET_PATH,
    KLINE_COLUMNS, OPENTIME_COLUMN, CLOSETIME_COLUMN,
    BINANCE_US_BASE_URL, get_file_name
)
from cache_manager import GitHubCacheManager

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class IncrementalUpdater:
    """
    Incremental updater with GitHub cache support.
    流程：抓取最新 K 線 → 合併 → 存到 GitHub 快取 → 定期批量上傳到 HuggingFace
    """
    def __init__(self, hf_token: str):
        self.hf_token = hf_token
        self.binance_url = BINANCE_US_BASE_URL
        self.max_retries = 3
        self.retry_delay = 2
        
        # 初始化快取管理器
        self.cache_manager = GitHubCacheManager(
            repo_owner="caizongxun",
            repo_name="crypto-data-updater"
        )
        
        logger.info("Logging in to HuggingFace...")
        try:
            login(token=hf_token)
            logger.info("HuggingFace login successful!")
        except Exception as e:
            logger.warning(f"HuggingFace login warning: {e}")
    
    def fetch_latest_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 1000
    ) -> Optional[pd.DataFrame]:
        """
        從 Binance US API 抓取最新 1000 根 K 線
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
            logger.error(f"Error fetching {symbol} {interval}: {str(e)[:80]}")
            return None
    
    def download_from_hf(
        self,
        symbol: str,
        timeframe: str
    ) -> Optional[pd.DataFrame]:
        """
        從 HuggingFace 下載現有 parquet 檔案
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
            logger.debug(f"Could not download {symbol} {timeframe} from HF: {str(e)[:60]}")
            return None
    
    def merge_and_deduplicate(
        self,
        existing_df: Optional[pd.DataFrame],
        new_df: Optional[pd.DataFrame]
    ) -> Optional[pd.DataFrame]:
        """
        合併現有和新數據，移除重複
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
        驗證數據完整性
        """
        if df is None or df.empty:
            return False
        
        if df[OPENTIME_COLUMN].dtype != 'datetime64[ns]':
            return False
        
        return True
    
    def upload_to_hf_with_retry(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str,
        max_retries: int = 3
    ) -> bool:
        """
        上傳到 HuggingFace（含重試邏輯）
        """
        for attempt in range(max_retries):
            try:
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
                
                logger.info(f"Uploaded {symbol} {timeframe} (attempt {attempt + 1})")
                return True
            
            except Exception as e:
                error_msg = str(e)[:80]
                if attempt < max_retries - 1:
                    # 如果是速率限制，等待更長時間
                    if "429" in error_msg or "Too Many" in error_msg:
                        wait_time = 10 * (attempt + 1)
                        logger.warning(f"Rate limited. Waiting {wait_time}s before retry...")
                        time.sleep(wait_time)
                    else:
                        time.sleep(self.retry_delay)
                else:
                    logger.error(f"Upload failed after {max_retries} attempts: {error_msg}")
                    return False
        
        return False
    
    def process_symbol(
        self,
        symbol: str,
        timeframe: str,
        upload_to_hf: bool = False
    ) -> bool:
        """
        處理單個符號：抓取最新 → 合併 → 存到快取（可選上傳到 HF）
        """
        logger.info(f"Processing {symbol} {timeframe}...")
        
        # 從 HF 下載現有
        existing_df = self.download_from_hf(symbol, timeframe)
        
        # 從 Binance 抓取最新
        new_df = self.fetch_latest_klines(symbol, timeframe, limit=1000)
        
        if new_df is None:
            logger.warning(f"{symbol} {timeframe}: Failed to fetch from Binance")
            return False
        
        # 合併
        merged_df = self.merge_and_deduplicate(existing_df, new_df)
        
        if merged_df is None:
            logger.warning(f"{symbol} {timeframe}: No data to merge")
            return False
        
        if not self.validate_data(merged_df):
            logger.warning(f"{symbol} {timeframe}: Data validation failed")
            return False
        
        # 存到快取
        cache_saved = self.cache_manager.save_to_cache(merged_df, symbol, timeframe)
        if not cache_saved:
            logger.error(f"{symbol} {timeframe}: Failed to save to cache")
            return False
        
        # 可選：直接上傳到 HF
        if upload_to_hf:
            success = self.upload_to_hf_with_retry(merged_df, symbol, timeframe)
            if success:
                self.cache_manager.mark_as_uploaded(symbol, timeframe)
            return success
        
        return True
    
    def process_all(
        self,
        symbols: Optional[List[str]] = None,
        timeframes: Optional[List[str]] = None,
        upload_to_hf: bool = False
    ) -> dict:
        """
        處理所有符號和時間框架
        """
        symbols = symbols or SYMBOLS
        timeframes = timeframes or TIMEFRAMES
        
        results = {}
        
        logger.info(f"\n{'=' * 70}")
        logger.info(f"Incremental Update: {len(symbols)} symbols × {len(timeframes)} timeframes")
        logger.info(f"Upload to HuggingFace: {upload_to_hf}")
        logger.info(f"{'=' * 70}\n")
        
        for symbol in symbols:
            for timeframe in timeframes:
                key = f"{symbol}_{timeframe}"
                success = self.process_symbol(symbol, timeframe, upload_to_hf=upload_to_hf)
                results[key] = "SUCCESS" if success else "FAILED"
        
        # 統計
        success_count = sum(1 for v in results.values() if v == "SUCCESS")
        failed_count = sum(1 for v in results.values() if v == "FAILED")
        
        logger.info(f"\n{'=' * 70}")
        logger.info(f"Results: {success_count} successful, {failed_count} failed")
        
        # 快取統計
        cache_stats = self.cache_manager.get_cache_stats()
        logger.info(f"\nCache Statistics:")
        logger.info(f"  Cached files: {cache_stats['cached_count']}")
        logger.info(f"  Uploaded files: {cache_stats['uploaded_count']}")
        logger.info(f"  Total rows: {cache_stats['total_rows_cached']}")
        logger.info(f"  Total size: {cache_stats['total_size_mb']} MB")
        logger.info(f"{'=' * 70}\n")
        
        return results
    
    def batch_upload_from_cache(self, batch_size: int = 20, delay_between_files: float = 1.0) -> dict:
        """
        從快取批量上傳到 HuggingFace（用於排程更新）
        """
        logger.info(f"\n{'=' * 70}")
        logger.info(f"Batch Upload from Cache")
        logger.info(f"{'=' * 70}\n")
        
        cached_files = self.cache_manager.get_cached_files(status="cached")
        results = {}
        uploaded_count = 0
        
        for i, file_info in enumerate(cached_files[:batch_size]):
            symbol = file_info["symbol"]
            timeframe = file_info["timeframe"]
            
            logger.info(f"[{i+1}/{min(batch_size, len(cached_files))}] Uploading {symbol} {timeframe}...")
            
            try:
                df = pd.read_parquet(file_info["filepath"])
                success = self.upload_to_hf_with_retry(df, symbol, timeframe, max_retries=3)
                
                if success:
                    self.cache_manager.mark_as_uploaded(symbol, timeframe)
                    uploaded_count += 1
                    results[f"{symbol}_{timeframe}"] = "UPLOADED"
                else:
                    results[f"{symbol}_{timeframe}"] = "FAILED"
            
            except Exception as e:
                logger.error(f"Error uploading {symbol} {timeframe}: {str(e)[:80]}")
                results[f"{symbol}_{timeframe}"] = "ERROR"
            
            # 批次間延遲
            if i < len(cached_files) - 1:
                time.sleep(delay_between_files)
        
        # 清理已上傳的文件
        self.cache_manager.cleanup_uploaded()
        
        logger.info(f"\nUploaded {uploaded_count}/{min(batch_size, len(cached_files))} files")
        logger.info(f"{'=' * 70}\n")
        
        return results
