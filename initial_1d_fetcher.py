import os
import time
import requests
import pandas as pd
from huggingface_hub import HfApi
from config import (
    SYMBOLS,
    TIMEFRAMES,
    HF_DATASET_REPO,
    HF_DATASET_PATH,
    BINANCE_US_BASE_URL,
    KLINE_COLUMNS,
    START_TIMESTAMP,
    get_file_name,
    TIMEFRAME_MAPPING
)

class Initial1dFetcher:
    def __init__(self, hf_token: str):
        self.hf_token = hf_token
        self.hf_api = HfApi(token=hf_token)
        self.repo_id = HF_DATASET_REPO
        self.repo_type = "dataset"
        self.base_url = BINANCE_US_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({'Accept-Encoding': 'gzip, deflate'})
        self.results = {}

    def fetch_klines(self, symbol: str, timeframe: str, limit: int = 1000) -> pd.DataFrame:
        """
        從 Binance 抓取 K 線數據
        timeframe: '15m', '1h', '1d'
        """
        endpoint = f"{self.base_url}/klines"
        params = {
            'symbol': symbol,
            'interval': timeframe,
            'startTime': START_TIMESTAMP,
            'limit': limit
        }
        
        all_data = []
        
        while True:
            try:
                resp = self.session.get(endpoint, params=params, timeout=10)
                if resp.status_code != 200:
                    print(f"  ❌ Error fetching {symbol} {timeframe}: HTTP {resp.status_code}")
                    return None
                
                data = resp.json()
                if not data:
                    break
                
                all_data.extend(data)
                
                # 更新 startTime 以繼續抓取下一批
                last_timestamp = data[-1][0]
                params['startTime'] = last_timestamp + 1
                
                print(f"    Fetched {len(all_data)} rows for {symbol} {timeframe}")
                
                # 避免超過 API 速率限制
                time.sleep(0.1)
                
            except Exception as e:
                print(f"  ❌ Exception fetching {symbol} {timeframe}: {str(e)}")
                return None
        
        if not all_data:
            print(f"  ❌ No data found for {symbol} {timeframe}")
            return None
        
        # 轉換為 DataFrame
        df = pd.DataFrame(all_data, columns=KLINE_COLUMNS)
        
        # 時間戳轉換
        df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
        df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
        
        # 數值轉換
        for col in ['open', 'high', 'low', 'close', 'volume', 'quote_asset_volume',
                    'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        df['number_of_trades'] = pd.to_numeric(df['number_of_trades'], errors='coerce').astype('Int64')
        
        # 按時間排序，移除重複
        df = df.sort_values('open_time').drop_duplicates(subset=['open_time'])
        
        return df

    def upload_to_hf(self, symbol: str, timeframe: str, df: pd.DataFrame) -> bool:
        """
        上傳 parquet 檔案到 HuggingFace
        """
        try:
            # 建立臨時檔案
            filename = get_file_name(symbol, timeframe)
            temp_path = f"/tmp/{filename}"
            df.to_parquet(temp_path, index=False, compression='snappy')
            
            # 上傳到 HF
            path_in_repo = f"{HF_DATASET_PATH}/{symbol}/{filename}"
            self.hf_api.upload_file(
                path_or_fileobj=temp_path,
                path_in_repo=path_in_repo,
                repo_id=self.repo_id,
                repo_type=self.repo_type,
                commit_message=f"Upload {symbol} {timeframe} historical data"
            )
            
            # 清理臨時檔案
            os.remove(temp_path)
            
            print(f"  ✓ Uploaded {symbol} {timeframe} ({len(df)} rows)")
            return True
            
        except Exception as e:
            print(f"  ❌ Failed to upload {symbol} {timeframe}: {str(e)}")
            return False

    def process_all_1d(self):
        """
        抓取所有幣種的日線 (1d) 歷史數據並上傳
        """
        print("\n" + "=" * 70)
        print("INITIAL 1D KLINES FETCHER")
        print("=" * 70)
        print(f"\nFetching 1d klines for all {len(SYMBOLS)} symbols...\n")
        
        success_count = 0
        failed_count = 0
        
        for idx, symbol in enumerate(SYMBOLS, 1):
            print(f"[{idx}/{len(SYMBOLS)}] Processing {symbol}...")
            
            # 只抓 1d
            timeframe = '1d'
            
            # 抓取數據
            df = self.fetch_klines(symbol, timeframe)
            if df is None:
                self.results[symbol] = "FAILED"
                failed_count += 1
                continue
            
            # 上傳到 HF
            if self.upload_to_hf(symbol, timeframe, df):
                self.results[symbol] = "SUCCESS"
                success_count += 1
            else:
                self.results[symbol] = "FAILED"
                failed_count += 1
            
            # 避免 API 限制
            time.sleep(0.5)
        
        return success_count, failed_count

    def print_summary(self, success_count, failed_count):
        """
        列印執行摘要
        """
        print("\n" + "=" * 70)
        print("INITIAL 1D FETCH COMPLETED")
        print("=" * 70)
        print(f"\nSummary:")
        print(f"  Total symbols: {len(SYMBOLS)}")
        print(f"  Successful: {success_count}")
        print(f"  Failed: {failed_count}")
        print(f"\nYour data is now available at:")
        print(f"  https://huggingface.co/datasets/zongowo111/v2-crypto-ohlcv-data")
        print("=" * 70 + "\n")

if __name__ == "__main__":
    hf_token = input("Enter your HuggingFace token: ")
    fetcher = Initial1dFetcher(hf_token=hf_token)
    success_count, failed_count = fetcher.process_all_1d()
    fetcher.print_summary(success_count, failed_count)
