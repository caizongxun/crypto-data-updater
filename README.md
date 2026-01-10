# Crypto Data Updater

自動從 Binance US API 抓取加密貨幣 K 線數據，存放在 HuggingFace 數據集。

## 數據信息

- **數據集**: [zongowo111/v2-crypto-ohlcv-data](https://huggingface.co/datasets/zongowo111/v2-crypto-ohlcv-data)
- **幣種**: 38 種（AAVEUSDT, ADAUSDT, ALGOUSDT 等）
- **時框**: 15分鐘、1小時
- **數據範圍**: 2017-08-01 至現在（歷史數據）
- **更新頻率**: 每天 UTC 00:00 自動更新（GitHub Actions）

## 資料結構

```
zongowo111/v2-crypto-ohlcv-data/
  klines/
    BTCUSDT/
      BTC_15m.parquet    (15分鐘K線)
      BTC_1h.parquet     (1小時K線)
    ETHUSDT/
      ETH_15m.parquet
      ETH_1h.parquet
    ... (36 種其他幣種)
```

## 支援的幣種 (38 種)

```
AAVEUSDT, ADAUSDT, ALGOUSDT, ARBUSDT, ATOMUSDT,
AVAXUSDT, BCHUSDT, BNBUSDT, BTCUSDT, DOGEUSDT,
DOTUSDT, ETCUSDT, ETHUSDT, FILUSDT, LINKUSDT,
LTCUSDT, MATICUSDT, NEARUSDT, OPUSDT, SOLUSDT,
UNIUSDT, XRPUSDT, MANAUSDT, SANDUSDT, MKRUSDT,
GRTUSDT, GALAUSDT, SPELLUSDT, ENSUSDT, IMXUSDT,
BATUSDT, COMPUSDT, SNXUSDT, CRVUSDT, BALUSDT,
KAVAUSDT, ZRXUSDT, ENJUSDT
```

## 功能

### 1. 歷史數據抓取 (historical_fetcher.py)

從 2017-08-01 開始抓取所有歷史數據，分批存放在本地再上傳到 HuggingFace。

**用途**: 初始化數據集

**特性**:
- 批量快取（所有數據先存本地）
- 批量上傳（每 20 個檔案一次性上傳）
- 避免 API 速率限制

### 2. 增量更新 (incremental_updater.py)

每次只抓取最新 1000 根 K 線，與現有數據合併後上傳。

**用途**: 定期更新（GitHub Actions）

**特性**:
- 輕量級，只抓最新數據
- 自動去重
- 快速上傳

### 3. 文件刪除 (delete_hf_files.py)

刪除 HuggingFace 上的所有舊數據，但保留文件夾結構。

**用途**: 清空數據集準備重新初始化

## 使用方法

### 在 Colab 初始化數據

新建 Colab Notebook，執行以下 Cell：

```python
# Step 1: 建立資料夾並下載檔案
print("\n" + "=" * 70)
print("STEP 1: Setting up environment")
print("=" * 70)

%mkdir -p crypto-data-updater
%cd crypto-data-updater

print("Downloading files from GitHub...")
!curl -L https://raw.githubusercontent.com/caizongxun/crypto-data-updater/main/config.py -o config.py
!curl -L https://raw.githubusercontent.com/caizongxun/crypto-data-updater/main/delete_hf_files.py -o delete_hf_files.py
!curl -L https://raw.githubusercontent.com/caizongxun/crypto-data-updater/main/historical_fetcher.py -o historical_fetcher.py
print("✓ Files downloaded successfully.\n")

# Step 2: 安裝套件
print("=" * 70)
print("STEP 2: Installing packages")
print("=" * 70)
!pip install -q pandas pyarrow huggingface-hub requests numpy
print("✓ Packages installed successfully.\n")

# Step 3: 清除 Python module cache
print("=" * 70)
print("STEP 3: Clearing module cache")
print("=" * 70)
import sys
for mod in list(sys.modules.keys()):
    if any(x in mod for x in ['config', 'delete', 'historical']):
        del sys.modules[mod]
print("✓ Cache cleared.\n")

# Step 4: 刪除 HuggingFace 上的舊數據
print("=" * 70)
print("STEP 4: Deleting old data from HuggingFace")
print("=" * 70)
print("備註：這一步會刪除 klines 資料夾中的所有檔案，但保留資料夾結構\n")

from delete_hf_files import delete_all_files
delete_all_files()

# Step 5: 抓取歷史數據並分批上傳
print("\n" + "=" * 70)
print("STEP 5: Fetching historical data and batch uploading")
print("=" * 70)
print("機制：")
print("  • Phase 1: 抓取所有歷史數據 (2017-08-01 到現在)")
print("  • Phase 2: 批量上傳 (每 20 個檔案一批)\n")

from historical_fetcher import HistoricalFetcher

hf_token = input("Enter your HuggingFace token: ")

fetcher = HistoricalFetcher(hf_token=hf_token)
results = fetcher.process_all()

# 最終統計
print("\n" + "=" * 70)
print("✓ COMPLETE WORKFLOW FINISHED")
print("=" * 70)
success_count = sum(1 for v in results.values() if v == "SUCCESS")
failed_count = sum(1 for v in results.values() if v == "FAILED")
print(f"\n總結:")
print(f"  • 總共處理: {len(results)} 個幣種/時框")
print(f"  • 成功: {success_count}")
print(f"  • 失敗: {failed_count}")
print(f"\n數據現已上線:")
print(f"  → https://huggingface.co/datasets/zongowo111/v2-crypto-ohlcv-data")
print("=" * 70 + "\n")
```

### GitHub Actions 自動更新

1. **設置 HF Token Secret**
   - 進入 GitHub 倉庫 → Settings → Secrets and variables → Actions
   - 點擊 "New repository secret"
   - 名稱: `HF_TOKEN`
   - 值: 你的 HuggingFace token

2. **啟用 Actions**
   - 工作流會在每天 UTC 00:00 自動運行
   - 或手動觸發：Actions → Daily Crypto Data Update → Run workflow

## 配置文件

### config.py

包含所有配置常數：
- `SYMBOLS`: 支援的幣種列表
- `TIMEFRAMES`: 時框列表（15m, 1h）
- `HF_DATASET_REPO`: HuggingFace 數據集 ID
- `START_TIMESTAMP`: 歷史數據開始時間（2017-08-01）

## 技術細節

### 數據來源
- **API**: Binance US Public API
- **端點**: `https://api.binance.us/api/v3/klines`

### 數據欄位

每個 parquet 檔案包含：
```
open_time                        - 開盤時間 (datetime)
open                             - 開盤價
high                             - 最高價
low                              - 最低價
close                            - 收盤價
volume                           - 成交量
close_time                       - 收盤時間
quote_asset_volume               - 報價資產成交量
number_of_trades                 - 成交筆數
taker_buy_base_asset_volume      - 取方買入基礎資產成交量
taker_buy_quote_asset_volume     - 取方買入報價資產成交量
```

### 更新機制

**增量更新流程**:
1. 從 Binance US 抓取最新 1000 根 K 線
2. 從 HuggingFace 下載現有數據
3. 合併新舊數據，按 open_time 去重（保留最新版本）
4. 上傳回 HuggingFace

## 注意事項

- 初次初始化數據需要 2-4 小時
- 每日增量更新通常在 5-10 分鐘內完成
- HuggingFace token 需要有寫入權限
- 某些新上線的幣種可能沒有完整歷史數據

## 故障排除

### GitHub Action 失敗
- 檢查 `HF_TOKEN` secret 是否正確設置
- 查看 Actions 日誌了解具體錯誤
- 確保 token 未過期

### 部分幣種無數據
- 某些幣種在 Binance US 上市時間較晚
- 更新程序會自動跳過無數據的幣種

## 授權

MIT License
