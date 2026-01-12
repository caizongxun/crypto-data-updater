"""
Colab 上執行 - 一次性抓取所有 38 個幣種的日線 (1d) 歷史數據

使用方式:
1. 複製此檔案的全部內容
2. 貼到 Google Colab 的一個 cell
3. 執行
4. 輸入你的 HuggingFace token
5. 等待完成
"""

print("\n" + "=" * 70)
print("COLAB INITIAL 1D KLINES FETCH")
print("=" * 70)

print("\nStep 1: Installing packages...")
!pip install -q pandas pyarrow huggingface-hub requests numpy
print("Packages installed.\n")

print("Step 2: Setting up directories...")
import os
os.makedirs('/tmp/crypto-data', exist_ok=True)
os.chdir('/tmp/crypto-data')
print("Directory ready.\n")

print("Step 3: Downloading config files from GitHub...")
!curl -s -L https://raw.githubusercontent.com/caizongxun/crypto-data-updater/main/config.py -o config.py
!curl -s -L https://raw.githubusercontent.com/caizongxun/crypto-data-updater/main/initial_1d_fetcher.py -o initial_1d_fetcher.py
print("Files downloaded.\n")

print("Step 4: Clearing Python module cache...")
import sys
for mod in list(sys.modules.keys()):
    if any(x in mod for x in ['config', 'initial', 'fetcher']):
        if mod in sys.modules:
            del sys.modules[mod]
print("Cache cleared.\n")

print("=" * 70)
print("Step 5: Starting 1D Klines Fetch")
print("=" * 70)
print()

from initial_1d_fetcher import Initial1dFetcher

hf_token = input("Enter your HuggingFace token: ")

if not hf_token or len(hf_token.strip()) == 0:
    print("Error: Token cannot be empty")
    exit(1)

fetcher = Initial1dFetcher(hf_token=hf_token)
success_count, failed_count = fetcher.process_all_1d()
fetcher.print_summary(success_count, failed_count)

print("\n" + "=" * 70)
print("COLAB EXECUTION COMPLETED")
print("=" * 70)
print("Your 1d klines are now on HuggingFace!")
print("Daily updates will run automatically from tomorrow.")
print()
