import pandas as pd
import numpy as np
from typing import Optional, List, Dict
from datetime import datetime
import requests
import time
from huggingface_hub import login, hf_hub_download, upload_file
import tempfile
import os
import logging
from pathlib import Path
import shutil

from config import (
    SYMBOLS, TIMEFRAMES, HF_DATASET_REPO, HF_DATASET_PATH,
    KLINE_COLUMNS, OPENTIME_COLUMN, CLOSETIME_COLUMN,
    BINANCE_US_BASE_URL, get_file_name, get_symbols_for_hour,
    SYMBOL_GROUPS, TOTAL_GROUPS, GROUP_SIZE
)

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GroupedUpdater:
    """
    按組別更新加密貨幣數據的更新器
    每小時更新一組 (10 個幣種 × 2 時間框架 = 20 個檔案)
    臨時檔案存放在 GitHub data/temp/ (用完即刪)
    """
    
    def __init__(self, hf_token: str, temp_dir: str = "data/temp"):
        self.hf_token = hf_token
        self.binance_url = BINANCE_US_BASE_URL
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.max_retries = 3
        self.retry_delay = 2
        
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
            logger.debug(f"Could not download {symbol} {timeframe}: {str(e)[:60]}")
            return None
    
    def save_to_temp(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str
    ) -> bool:
        """
        將檔案暫存到 GitHub temp 資料夾
        """
        try:
            symbol_dir = self.temp_dir / symbol
            symbol_dir.mkdir(exist_ok=True)
            
            filename = get_file_name(symbol, timeframe)
            filepath = symbol_dir / filename
            
            df.to_parquet(filepath, index=False, compression='snappy')
            logger.debug(f"Saved to temp: {symbol} {timeframe}")
            return True
        except Exception as e:
            logger.error(f"Failed to save to temp: {e}")
            return False
    
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
                
                logger.info(f"Uploaded {symbol} {timeframe}")
                return True
            
            except Exception as e:
                error_msg = str(e)[:80]
                if attempt < max_retries - 1:
                    if "429" in error_msg or "Too Many" in error_msg:
                        wait_time = 10 * (attempt + 1)
                        logger.warning(f"Rate limited. Waiting {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        time.sleep(self.retry_delay)
                else:
                    logger.error(f"Upload failed: {error_msg}")
                    return False
        
        return False
    
    def process_symbol(
        self,
        symbol: str,
        timeframe: str
    ) -> bool:
        """
        處理單個幣種：
        1. 下載 HF 現有檔案
        2. 抓取 Binance 最新 K 線
        3. 合併更新
        4. 暫存到 temp
        5. 上傳到 HF
        """
        logger.info(f"Processing {symbol} {timeframe}...")
        
        # 下載現有
        existing_df = self.download_from_hf(symbol, timeframe)
        
        # 抓取最新
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
            logger.warning(f"{symbol} {timeframe}: Validation failed")
            return False
        
        # 暫存
        temp_saved = self.save_to_temp(merged_df, symbol, timeframe)
        if not temp_saved:
            logger.error(f"{symbol} {timeframe}: Failed to save to temp")
            return False
        
        # 上傳
        success = self.upload_to_hf_with_retry(merged_df, symbol, timeframe)
        return success
    
    def process_group(
        self,
        group_idx: int
    ) -> Dict[str, str]:
        """
        處理一個完整的組別 (10 個幣種 × 2 時間框架)
        """
        if group_idx >= TOTAL_GROUPS:
            logger.error(f"Invalid group index: {group_idx} (max: {TOTAL_GROUPS})")
            return {}
        
        symbols = SYMBOL_GROUPS[group_idx]
        results = {}
        
        logger.info(f"\n{'=' * 70}")
        logger.info(f"Processing Group {group_idx + 1}/{TOTAL_GROUPS}")
        logger.info(f"Symbols: {symbols}")
        logger.info(f"{'=' * 70}\n")
        
        for symbol in symbols:
            for timeframe in TIMEFRAMES:
                key = f"{symbol}_{timeframe}"
                success = self.process_symbol(symbol, timeframe)
                results[key] = "SUCCESS" if success else "FAILED"
        
        # 統計
        success_count = sum(1 for v in results.values() if v == "SUCCESS")
        failed_count = sum(1 for v in results.values() if v == "FAILED")
        
        logger.info(f"\n{'=' * 70}")
        logger.info(f"Group {group_idx + 1} Results: {success_count} successful, {failed_count} failed")
        logger.info(f"{'=' * 70}\n")
        
        return results
    
    def cleanup_temp(self):
        """
        刪除臨時資料夾中的所有檔案
        """
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                self.temp_dir.mkdir(parents=True, exist_ok=True)
                logger.info("Cleaned up temp directory")
                return True
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
            return False
    
    def process_hourly(self, hour: int) -> Dict[str, str]:
        """
        根據小時數處理對應的組別
        hour 0-4 對應 Group 0-3 (然後迴圈)
        """
        group_idx = hour % TOTAL_GROUPS
        results = self.process_group(group_idx)
        
        # 清理臨時檔案
        self.cleanup_temp()
        
        return results
