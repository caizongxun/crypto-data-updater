# 設置指南

## 快速開始

### 步驟 1: 準備 HuggingFace Token

1. 訪問 https://huggingface.co/settings/tokens
2. 點擊「New token」
3. 選擇「Write」權限
4. 創建並複製 token

### 步驟 2: 使用 Google Colab 進行初始數據更新

#### 方法 A: 直接在 Colab 中執行

1. 打開 Google Colab: https://colab.research.google.com/

2. 在第一個 Cell 中執行:
```python
!git clone https://github.com/caizongxun/crypto-data-updater.git
%cd crypto-data-updater
!pip install -q pandas pyarrow huggingface-hub requests numpy
```

3. 在第二個 Cell 中執行:
```python
from colab_updater import main, setup_colab_environment
main()
```

4. 當提示輸入時，粘貼你的 HuggingFace token

5. 確認開始更新 (輸入 `yes`)

#### 方法 B: 下載並修改

1. 從 GitHub 克隆倉庫
2. 修改 `colab_updater.py` 中的 token 處理邏輯
3. 上傳到 Colab

### 步驟 3: 設置 GitHub Actions 自動更新

#### 3.1 Fork 或克隆倉庫

```bash
git clone https://github.com/caizongxun/crypto-data-updater.git
cd crypto-data-updater
```

#### 3.2 添加 Secret

1. 進入你的 GitHub 倉庫
2. 點擊 Settings 標籤
3. 左側菜單: Security > Secrets and variables > Actions
4. 點擊 "New repository secret"
5. Name: `HF_TOKEN`
6. Value: 粘貼你的 HuggingFace token
7. 點擊 "Add secret"

#### 3.3 啟用 GitHub Actions

1. 點擊 Actions 標籤
2. 如果提示，點擊「I understand my workflows, go ahead and enable them」

#### 3.4 驗證設置

1. Actions 標籤 > Hourly Crypto Data Update
2. 點擊 "Run workflow" 進行手動測試
3. 選擇 main 分支
4. 點擊 "Run workflow"
5. 等待執行完成，檢查日誌

## 工作流程說明

### Colab 更新流程

```
Colab 執行
  ↓
下載 HuggingFace 上的現有數據
  ↓
從 Binance API 獲取最新 K線
  ↓
合併並去重
  ↓
數據驗證
  ↓
上傳到 HuggingFace
```

### GitHub Actions 自動流程

```
每小時觸發 (0 點)
  ↓
設置 Python 環境
  ↓
安裝依賴
  ↓
執行更新 (同 Colab 流程)
  ↓
提交並推送更新到 GitHub (如有變更)
```

## 數據更新周期

- 15m 時間框架: 每小時增加 4 根 K線
- 1h 時間框架: 每小時增加 1 根 K線
- 共 22 個交易對
- 每次更新: 22 * (4 + 1) = 110 根 K線

## 監控和日誌

### GitHub Actions 日誌

1. 進入 Actions 標籤
2. 點擊最近的工作流執行
3. 點擊 "update-data" Job
4. 查看詳細日誌

### HuggingFace 數據驗證

1. 訪問 https://huggingface.co/datasets/zongowo111/v2-crypto-ohlcv-data
2. 檢查各幣種文件的修改時間
3. 驗證文件大小是否增加

## 常見問題

### Q: 如何確認更新成功？
A: 
1. 檢查 GitHub Actions 日誌
2. 查看 HuggingFace 數據集中文件的修改時間
3. 數據集主頁應顯示最新的更新時間

### Q: 如何修改更新時間？
A: 編輯 `.github/workflows/hourly-update.yml` 文件中的 `cron` 參數
```yaml
on:
  schedule:
    - cron: '0 * * * *'  # 改為自己想要的時間
```

### Q: 如何添加新的交易對？
A: 編輯 `config.py` 中的 `SYMBOLS` 列表
```python
SYMBOLS = [
    # 現有的...
    'NEWUSDT'  # 新交易對
]
```

### Q: Token 過期了怎麼辦？
A:
1. 生成新的 HuggingFace token
2. 更新 GitHub Secrets 中的 `HF_TOKEN`
3. 下次執行時會使用新 token

## 故障排除

### 錯誤: "HF_TOKEN not found"

檢查:
1. GitHub Secrets 已正確添加
2. Secret 名稱為 `HF_TOKEN`
3. Token 有寫入權限

### 錯誤: "Download from HuggingFace failed"

檢查:
1. HuggingFace 網絡連接
2. Token 權限
3. 數據集路徑是否正確

### 錯誤: "Binance API error"

檢查:
1. Binance 服務狀態
2. 網絡連接
3. API 請求速率限制

## 成本考慮

- GitHub Actions: 免費 (標準額度)
- HuggingFace 存儲: 免費額度應足夠
- Binance API: 免費

## 安全注意事項

1. 不要在代碼中硬編碼 token
2. 使用 GitHub Secrets 存儲敏感信息
3. 定期檢查 Actions 日誌
4. 不要將 `.env` 文件提交到 Git

## 升級指南

### 更新倉庫代碼

```bash
cd crypto-data-updater
git pull origin main
```

### 更新依賴

```bash
pip install --upgrade -r requirements.txt
```

## 下一步

1. 確認初始數據更新完成
2. 驗證自動化工作流運行
3. 監控數據質量
4. 根據需要調整配置
