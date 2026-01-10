# 完整歷史數據獲取指南

本指南說明如何從 Binance US 獲取從 2017-08-01 開始到現在的所有歷史 K 線數據，並上傳到 HuggingFace。

## 步驟 1：準備 Colab 環境

```python
# 建立資料夾
%mkdir -p crypto-data-updater
%cd crypto-data-updater
```

## 步驟 2：下載所有必要檔案

使用 `wget` 下載最新程式碼：

```python
# config 配置檔（40+ 幣種、歷史時間戳）
!wget -q https://raw.githubusercontent.com/caizongxun/crypto-data-updater/main/config.py -O config.py

# 刪除工具（清空 HF 上的舊數據）
!wget -q https://raw.githubusercontent.com/caizongxun/crypto-data-updater/main/delete_hf_files.py -O delete_hf_files.py

# 歷史數據抓取器（從 2017-08-01 開始循環抓取）
!wget -q https://raw.githubusercontent.com/caizongxun/crypto-data-updater/main/historical_fetcher.py -O historical_fetcher.py
```

## 步驟 3：安裝套件

```python
!pip install -q pandas pyarrow huggingface-hub requests numpy
```

## 步驟 4：刪除 HuggingFace 上的舊數據

**重要：這一步會刪除 klines 資料夾中的所有檔案，但保留資料夾結構。**

```python
from delete_hf_files import delete_all_files
delete_all_files()
```

執行後會：
1. 列出所有要刪除的檔案
2. 要求確認輸入 `yes`
3. 逐個刪除檔案
4. 保留 klines 資料夾結構（空的）

## 步驟 5：抓取完整歷史數據

**注意：這可能需要 2-4 小時，取決於網路和 Binance API 速率限制。**

```python
from historical_fetcher import HistoricalFetcher

fetcher = HistoricalFetcher(hf_token="your_hf_token_here")
results = fetcher.process_all()

# 印出結果摘要
print("\n" + "=" * 70)
print("Final Results")
print("=" * 70)
success_count = sum(1 for v in results.values() if v == "SUCCESS")
failed_count = sum(1 for v in results.values() if v == "FAILED")
print(f"Successful: {success_count}")
print(f"Failed: {failed_count}")
print(f"Total: {len(results)}")
```

## 程式邏輯說明

### 抓取策略

```
起始時間：2017-08-01（Binance 創立時間）
結束時間：現在

對每個幣種和時間框架：
  1. 初始化：current_time = 2017-08-01 (毫秒時間戳)
  2. 批次循環：
     - 每次從 Binance API 抓取 1000 根 K 線
     - 根據最後一根 K 線的時間更新 current_time
     - 繼續直到 current_time >= 現在時間
  3. 合併：將所有批次的數據合併成一個 DataFrame
  4. 去重：根據 open_time 列移除重複項
  5. 排序：按時間升序排列
  6. 上傳：保存為 parquet 並上傳到 HuggingFace
```

### 資料結構

上傳完成後，HuggingFace 上的結構如下：

```
zongowo111/v2-crypto-ohlcv-data/
  klines/
    BTCUSDT/
      BTC_15m.parquet
      BTC_1h.parquet
    ETHUSDT/
      ETH_15m.parquet
      ETH_1h.parquet
    ...
    (40+ 幣種)
```

每個檔案包含：
- `open_time`: 開盤時間（datetime）
- `close_time`: 收盤時間（datetime）
- `open`, `high`, `low`, `close`: 價格
- `volume`: 成交量
- `quote_asset_volume`: 報價資產成交量
- `number_of_trades`: 成交筆數
- 其他 Binance K 線欄位

## 支持的幣種（44 種）

```
AAVEUSDT, ADAUSDT, ALGOUSDT, ARBUSDT, ATOMUSDT,
AVAXUSDT, BCHUSDT, BNBUSDT, BTCUSDT, DOGEUSDT,
DOTUSDT, ETCUSDT, ETHUSDT, FILUSDT, LINKUSDT,
LTCUSDT, MATICUSDT, NEARUSDT, OPUSDT, SOLUSDT,
UNIUSDT, XRPUSDT, MANAUSDT, SANDUSDT, MKRUSDT,
ARUSDT, GRTUSDT, CROUSDT, GALAUSDT, SPELLUSDT,
FLRUSDT, ENSUSDT, IMXUSDT, YFIIUSDT, BATUSDT,
COMPUSDT, SNXUSDT, CRVUSDT, BALUSDT, DYDXUSDT,
KAVAUSDT, ZRXUSDT, ENJUSDT
```

## 故障排除

### 網路中斷

如果中途因網路中斷停止，可以：
1. 重新執行 `process_all()`
2. 程式會偵測已上傳的檔案，跳過已完成的幣種
3. 只重新處理失敗的幣種

### 某個幣種失敗

如果某個幣種始終失敗，可以只處理該幣種：

```python
fetcher.process_symbol('BTCUSDT', '15m')
fetcher.process_symbol('BTCUSDT', '1h')
```

### Binance API 速率限制

程式已內建：
- 每個請求之間 0.2 秒延遲
- 失敗重試最多 3 次
- 重試之間 2 秒延遲

如果仍遇到速率限制，可以增加延遲：

```python
fetcher.retry_delay = 5  # 改為 5 秒
```

## 預期結果

對於 44 種幣種 × 2 個時間框架 = 88 個檔案：

- **BTCUSDT 15m**：從 2017-08-01 到現在，約 ~12,000-15,000 根 K 線
- **BTCUSDT 1h**：約 ~3,000-4,000 根 K 線
- 其他新幣種：可能從上市時間開始（較少 K 線）

總耗時：預計 2-4 小時（取決於網路和 API 限制）
