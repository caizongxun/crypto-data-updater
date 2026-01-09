# 故障排除指南

## 問題 1: HuggingFace 檔案未找到

### 症狀
```
Repository Not Found for url: [.../OP_1h.parquet]
Error fetching klines for OPUSDT 1h: 451 Client Error
```

### 原因
某些檔案在HuggingFace上不存在。這可能是因為：
1. 檔案尚未被初始化
2. 檔案名稱不匹配
3. 符號或時間框架配置錯誤

### 解決方案

#### 步驟 1: 檢查現有檔案

在Colab中執行：
```python
!git clone https://github.com/caizongxun/crypto-data-updater.git
%cd crypto-data-updater
!pip install -q huggingface-hub

from check_hf_files import check_hf_files
check_hf_files()
```

這會顯示：
- 哪些檔案已存在
- 哪些檔案缺失
- 需要初始化的檔案列表

#### 步驟 2: 創建缺失檔案

對於缺失的檔案，系統會自動在第一次運行時創建它們。只需在 `colab_updater.py` 中確認進行。

## 問題 2: Binance API 錯誤

### 症狀
```
Error fetching klines for BTCUSDT 15m: 451 Client Error
```

### 原因
1. 使用了國際 Binance API (已修復)
2. API 請求速率限制
3. Binance US 服務不可用

### 解決方案

確保配置正確：
```python
# config.py 應包含
BINANCE_US_BASE_URL = 'https://api.binance.us/api/v3'
USE_BINANCE_US = True
```

驗證 API 連接：
```python
import requests
url = 'https://api.binance.us/api/v3/klines'
params = {'symbol': 'BTCUSDT', 'interval': '15m', 'limit': 1}
response = requests.get(url, params=params)
print(response.status_code)  # 應該是 200
print(response.json())  # 應該返回數據
```

## 問題 3: HuggingFace 認證失敗

### 症狀
```
Repository Not Found
If you are trying to access a private or gated repo, make sure you are authenticated
```

### 原因
1. HF_TOKEN 無效
2. Token 沒有寫入權限
3. 數據集是私有的

### 解決方案

#### 驗證 Token
```python
from huggingface_hub import HfApi

api = HfApi()
user_info = api.whoami(token="your_token_here")
print(f"Logged in as: {user_info['name']}")
```

#### 重新生成 Token
1. 訪問 https://huggingface.co/settings/tokens
2. 刪除舊 token
3. 創建新 token，確保選擇 "Write" 權限
4. 複製新 token
5. 在 GitHub Secrets 中更新 `HF_TOKEN`

#### 驗證數據集權限
```python
from huggingface_hub import get_repo_info

info = get_repo_info(
    repo_id="zongowo111/v2-crypto-ohlcv-data",
    token="your_token_here"
)
print(f"Private: {info.private}")
print(f"Gated: {info.gated}")
```

## 問題 4: 網路連接問題

### 症狀
```
Timeout connecting to https://api.binance.us/api/v3/klines
Connection error to huggingface.co
```

### 原因
1. 網路不穩定
2. ISP 限制
3. VPN 問題 (Colab 環境)

### 解決方案

#### Colab 中測試連接
```python
import requests

# 測試 Binance US
try:
    r = requests.get('https://api.binance.us/api/v3/ping', timeout=10)
    print(f"Binance US: {r.status_code}")
except Exception as e:
    print(f"Binance US error: {e}")

# 測試 HuggingFace
try:
    r = requests.get('https://huggingface.co', timeout=10)
    print(f"HuggingFace: {r.status_code}")
except Exception as e:
    print(f"HuggingFace error: {e}")
```

#### 增加超時時間
在 Colab 或 GitHub Actions 中，可能需要更長的超時。代碼已設置為 15-30 秒。

## 問題 5: 數據驗證失敗

### 症狀
```
FAILED: Data validation failed for BTCUSDT 15m
```

### 原因
1. 數據列缺失
2. 時間戳格式錯誤
3. 數據為空

### 解決方案

驗證數據格式：
```python
import pandas as pd
from config import KLINE_COLUMNS

# 讀取本地parquet檔案
df = pd.read_parquet('BTCUSDT_15m.parquet')

# 檢查列
print(f"Columns: {df.columns.tolist()}")
print(f"Expected: {KLINE_COLUMNS}")

# 檢查時間戳
print(f"open_time dtype: {df['open_time'].dtype}")
print(f"First rows:\n{df.head()}")
```

## 問題 6: 儲存空間不足

### 症狀
```
Error uploading BTCUSDT 15m to HF: Quota exceeded
```

### 解決方案

1. 檢查 HuggingFace 存儲配額
   - 訪問 https://huggingface.co/settings/storage
   - 升級帳戶或刪除舊檔案

2. 壓縮 Parquet 檔案
   ```python
   df.to_parquet('file.parquet', compression='snappy')
   ```

## 常見問題

### Q: Colab 執行時中斷怎麼辦？
A: Colab 連接超時後會自動重新連接。執行的代碼狀態會保留，但需要重新導入模塊。

### Q: 可以只更新特定幣種嗎？
A: 可以，修改 `colab_updater.py` 或使用代碼：
```python
from data_handler import DataHandler

handler = DataHandler(hf_token="your_token")
results = handler.process_all(
    symbols=['BTCUSDT', 'ETHUSDT'],
    timeframes=['1h']
)
```

### Q: 更新頻率可以改變嗎？
A: 可以，編輯 `.github/workflows/hourly-update.yml`：
```yaml
on:
  schedule:
    - cron: '0 */6 * * *'  # 每6小時
    # 或
    - cron: '0 0 * * *'    # 每天午夜
```

### Q: 如何查看歷史日誌？
A: 
- GitHub Actions: 進入倉庫 > Actions > 點擊工作流
- Colab: 滾動查看輸出

### Q: 數據是否會重複？
A: 不會。系統會自動去重，基於 `open_time` 時間戳。相同時間戳的新數據會覆蓋舊數據。

## 聯繫支持

如果遇到以上都無法解決的問題：

1. 檢查 GitHub Issues
2. 查看詳細日誌
3. 驗證所有配置
4. 嘗試手動運行更新看詳細錯誤信息
