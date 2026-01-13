# AI Dataset Prompt Guide

本文件提供給 AI 系統的完整提示說明，幫助 AI 正確理解和使用你的加密貨幣 K 線資料集。

---

## 資料集基本資訊

### 位置和存取

- **HuggingFace Dataset**: `zongowo111/v2-crypto-ohlcv-data`
- **資料集類型**: 公開資料集
- **更新頻率**: 每天四個時段更新（UTC 00:00, 01:00, 02:00, 03:00）
- **數據來源**: Binance US API
- **歷史範圍**: 2017-08-01 至今

### 支援的交易對（38 個）

```text
AAVEUSDT, ADAUSDT, ALGOUSDT, ARBUSDT, ATOMUSDT,
AVAXUSDT, BALUSDT, BATUSDT, BCHUSDT, BNBUSDT,
BTCUSDT, COMPUSDT, CRVUSDT, DOGEUSDT, DOTUSDT,
ENJUSDT, ENSUSDT, ETCUSDT, ETHUSDT, FILUSDT,
GALAUSDT, GRTUSDT, IMXUSDT, KAVAUSDT, LINKUSDT,
LTCUSDT, MANAUSDT, MATICUSDT, MKRUSDT, NEARUSDT,
OPUSDT, SANDUSDT, SNXUSDT, SOLUSDT, SPELLUSDT,
UNIUSDT, XRPUSDT, ZRXUSDT
```

---

## 資料夾結構規範

### 目錄層級

```
klines/
├── BTCUSDT/
│   ├── BTC_15m.parquet      (15 分鐘 K 線)
│   ├── BTC_1h.parquet       (1 小時 K 線)
│   └── BTC_1d.parquet       (日線 K 線)
├── ETHUSDT/
│   ├── ETH_15m.parquet
│   ├── ETH_1h.parquet
│   └── ETH_1d.parquet
└── ... (38 個交易對)
```

### 檔案命名規則

**通用格式**:
```
{BASE_SYMBOL}_{TIMEFRAME}.parquet
```

**範例**:
- `BTCUSDT` + `15m` → `BTC_15m.parquet`
- `ETHUSDT` + `1h` → `ETH_1h.parquet`
- `ADAUSDT` + `1d` → `ADA_1d.parquet`

### 時間框架定義

| 時框代碼 | 說明 | 檔案範例 |
|---------|------|----------|
| `15m` | 15 分鐘 K 線 | `BTC_15m.parquet` |
| `1h` | 1 小時 K 線 | `BTC_1h.parquet` |
| `1d` | 日線 K 線 | `BTC_1d.parquet` |

---

## Parquet 檔案內容結構

### 欄位定義

每個 parquet 檔案都包含以下欄位（按順序）：

| 欄位名稱 | 資料型別 | 說明 |
|--------|---------|------|
| `open_time` | datetime | K 線開盤時間（UTC） |
| `open` | float | 開盤價 |
| `high` | float | 最高價 |
| `low` | float | 最低價 |
| `close` | float | 收盤價 |
| `volume` | float | 成交量（基礎資產） |
| `close_time` | datetime | K 線收盤時間（UTC） |
| `quote_asset_volume` | float | 成交量（計價資產，通常是 USDT） |
| `number_of_trades` | int | 該時段交易筆數 |
| `taker_buy_base_asset_volume` | float | 買方成交量（基礎資產） |
| `taker_buy_quote_asset_volume` | float | 買方成交量（計價資產） |
| `ignore` | (可忽略) | Binance API 返回的冗餘欄位 |

### 數據特性

- **時間索引**: 按 `open_time` 升序排列
- **去重**: 相同 `open_time` 的重複行已移除
- **缺失值**: 不存在（Binance API 連續供應）
- **數據精度**: Float 為浮點精度，無特殊舍入
- **時區**: 所有時間為 UTC（無本地時區轉換）

---

## 讀取資料的方法

### 方法 1：使用 Python（推薦）

```python
from huggingface_hub import hf_hub_download
import pandas as pd

# 設定參數
REPO_ID = "zongowo111/v2-crypto-ohlcv-data"
SYMBOL = "BTCUSDT"
TIMEFRAME = "1h"

# 組合路徑和檔名
BASE = SYMBOL.replace("USDT", "")
FILENAME = f"BTC_{TIMEFRAME}.parquet"
PATH_IN_REPO = f"klines/{SYMBOL}/{FILENAME}"

# 下載並讀取
local_path = hf_hub_download(
    repo_id=REPO_ID,
    filename=PATH_IN_REPO,
    repo_type="dataset"
)
df = pd.read_parquet(local_path)

print(df.head())
print(f"形狀: {df.shape}")
print(f"時間範圍: {df['open_time'].min()} 到 {df['open_time'].max()}")
```

### 方法 2：通用函式

```python
from huggingface_hub import hf_hub_download
import pandas as pd

def load_klines(symbol: str, timeframe: str, repo_id="zongowo111/v2-crypto-ohlcv-data") -> pd.DataFrame:
    """
    從 HuggingFace 讀取加密貨幣 K 線資料
    
    參數:
        symbol (str): 交易對，例如 'BTCUSDT', 'ETHUSDT'
        timeframe (str): 時間框架 '15m', '1h', '1d'
        repo_id (str): HuggingFace 資料集 ID
    
    返回:
        pd.DataFrame: K 線資料
    """
    base = symbol.replace("USDT", "")
    filename = f"{base}_{timeframe}.parquet"
    path_in_repo = f"klines/{symbol}/{filename}"
    
    local_path = hf_hub_download(
        repo_id=repo_id,
        filename=path_in_repo,
        repo_type="dataset"
    )
    
    return pd.read_parquet(local_path)

# 使用範例
btc_1h = load_klines("BTCUSDT", "1h")
eth_1d = load_klines("ETHUSDT", "1d")

print(f"BTC 1h 資料: {len(btc_1h)} 行")
print(f"ETH 1d 資料: {len(eth_1d)} 行")
```

### 方法 3：批量讀取多個幣種

```python
from huggingface_hub import hf_hub_download
import pandas as pd

SYMBOLS = [
    'BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOGEUSDT', 'SOLUSDT'
]
TIMEFRAME = '1h'

data = {}
for symbol in SYMBOLS:
    try:
        base = symbol.replace("USDT", "")
        filename = f"{base}_{TIMEFRAME}.parquet"
        path_in_repo = f"klines/{symbol}/{filename}"
        
        local_path = hf_hub_download(
            repo_id="zongowo111/v2-crypto-ohlcv-data",
            filename=path_in_repo,
            repo_type="dataset"
        )
        data[symbol] = pd.read_parquet(local_path)
    except Exception as e:
        print(f"Failed to load {symbol}: {e}")

print(f"成功加載 {len(data)} 個幣種")
```

---

## 常見使用場景

### 場景 1：計算技術指標

```python
# 讀取 BTC 1h 資料
df = load_klines("BTCUSDT", "1h")

# 計算簡單移動平均線 (SMA)
df['SMA_20'] = df['close'].rolling(window=20).mean()
df['SMA_50'] = df['close'].rolling(window=50).mean()

print(df[['open_time', 'close', 'SMA_20', 'SMA_50']].tail(10))
```

### 場景 2：比較多個幣種的漲跌

```python
btc_1d = load_klines("BTCUSDT", "1d")
eth_1d = load_klines("ETHUSDT", "1d")

# 最近 7 天漲幅
btc_return = ((btc_1d['close'].iloc[-1] - btc_1d['close'].iloc[-7]) / btc_1d['close'].iloc[-7]) * 100
eth_return = ((eth_1d['close'].iloc[-1] - eth_1d['close'].iloc[-7]) / eth_1d['close'].iloc[-7]) * 100

print(f"BTC 7 天漲幅: {btc_return:.2f}%")
print(f"ETH 7 天漲幅: {eth_return:.2f}%")
```

### 場景 3：查詢特定時期的數據

```python
df = load_klines("BTCUSDT", "1d")

# 篩選 2024 年 1 月的資料
jan_2024 = df[
    (df['open_time'].dt.year == 2024) & 
    (df['open_time'].dt.month == 1)
]

print(f"2024 年 1 月 BTC 日線資料: {len(jan_2024)} 天")
print(f"  最高: ${jan_2024['high'].max():.2f}")
print(f"  最低: ${jan_2024['low'].min():.2f}")
print(f"  平均: ${jan_2024['close'].mean():.2f}")
```

---

## 更新排程

### 自動更新時間表

| 時間 (UTC) | 處理的幣種組別 | 更新範圍 |
|-----------|---------------|----------|
| 00:00 | Group 0（AAVEUSDT - DOGEUSDT） | 15m, 1h, 1d |
| 01:00 | Group 1（DOTUSDT - SOLUSDT） | 15m, 1h, 1d |
| 02:00 | Group 2（UNIUSDT - IMXUSDT） | 15m, 1h, 1d |
| 03:00 | Group 3（BATUSDT - ENJUSDT） | 15m, 1h, 1d |

每日迴圈，每次更新都會合併最新 K 線並去重。

---

## 數據品質保證

### 檢查清單

- [x] 所有 38 個幣種都有完整的 15m, 1h, 1d 資料
- [x] 時間戳記以 UTC 儲存（無時區混淆）
- [x] 已移除所有重複行
- [x] 按 `open_time` 升序排列
- [x] 無缺失值（Binance API 連續供應）
- [x] 每日自動更新，無人工介入
- [x] 壓縮格式（Snappy）以節省存儲空間

### 已知限制

- 資料從 2017-08-01 開始（Binance US 開始交易日期）
- 某些新幣種可能沒有 7 年的完整歷史
- 15m 資料保留約 6 個月（舊資料自動清理）
- 1h 資料保留約 2 年
- 1d 資料保留完整歷史

---

## 給 AI 的使用指引

### 當 AI 需要讀取數據時

當你要求 AI 分析或處理你的加密貨幣資料時，可以直接告訴 AI：

> "我的資料在 HuggingFace 的 `zongowo111/v2-crypto-ohlcv-data` 資料集中。
> 資料結構是 `klines/{SYMBOL}/{BASE_SYMBOL}_{TIMEFRAME}.parquet`。
> 例如 BTC 1 小時資料是 `klines/BTCUSDT/BTC_1h.parquet`。
> 我要分析的幣種是 [列出幣種]，時間框架是 [15m/1h/1d]。
> 請用提供的函式讀取資料並進行分析。"

### 常見 AI 指令

#### 1. 要求技術分析

```
我的數據在 zongowo111/v2-crypto-ohlcv-data，結構是 klines/{SYMBOL}/{BASE}_{TIMEFRAME}.parquet。
請分析 BTCUSDT 1h 資料的 RSI、MACD 和布林通道，並找出買賣信號。
```

#### 2. 要求統計分析

```
使用 klines/ETHUSDT/ETH_1d.parquet 計算最近 30 天的波動率、最大回撤和夏普比率。
```

#### 3. 要求回測

```
基於 klines/BTCUSDT/BTC_15m.parquet 的資料，回測一個簡單的均線交叉策略。
計算勝率、平均回報和最大回撤。
```

#### 4. 要求多幣種對比

```
比較 klines/BTCUSDT、klines/ETHUSDT 和 klines/SOLUSDT 的 1d 資料，
找出相關性最高和最低的幣種對。
```

---

## 疑難排解

### 問題 1：找不到檔案

**症狀**：`FileNotFoundError` 或 `404 Not Found`

**解決方案**：
1. 檢查 SYMBOL 是否正確（必須加 USDT 後綴）
2. 檢查 TIMEFRAME 是否為 '15m', '1h', 或 '1d'
3. 檢查路徑格式是否為 `klines/{SYMBOL}/{BASE}_{TIMEFRAME}.parquet`

### 問題 2：下載很慢

**症狀**：檔案下載耗時很長

**解決方案**：
- 這是正常的（首次下載會快取到本地）
- 後續訪問會從快取讀取，速度會很快
- 單個檔案通常 10-100 MB

### 問題 3：資料不是最新的

**症狀**：資料停留在幾小時前

**解決方案**：
- 檢查更新排程（上面的時間表）
- 如果超過排程時間 30 分鐘還沒更新，可能是自動更新失敗
- 在 GitHub Actions 中檢查工作流執行狀態

---

## 聯絡和反饋

- **GitHub Repository**: [caizongxun/crypto-data-updater](https://github.com/caizongxun/crypto-data-updater)
- **HuggingFace Dataset**: [zongowo111/v2-crypto-ohlcv-data](https://huggingface.co/datasets/zongowo111/v2-crypto-ohlcv-data)
- **建議和問題**: 請在 GitHub 上提出 Issue

---

**最後更新**: 2026-01-13
