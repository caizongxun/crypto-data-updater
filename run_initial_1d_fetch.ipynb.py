#!/usr/bin/env python3
"""
初始化腳本：一次性抓取所有 38 個幣種的日線 (1d) 歷史數據

使用方式:
  python run_initial_1d_fetch.ipynb.py

或在 Jupyter Notebook 中:
  1. 上傳此檔案到 Colab/Notebook
  2. 分別執行各 cell
"""

print("\n" + "=" * 70)
print("STEP 1: Setup Environment")
print("=" * 70)

%mkdir -p crypto-data-updater
%cd crypto-data-updater

print("Downloading required files...")
!curl -L https://raw.githubusercontent.com/caizongxun/crypto-data-updater/main/config.py -o config.py
!curl -L https://raw.githubusercontent.com/caizongxun/crypto-data-updater/main/initial_1d_fetcher.py -o initial_1d_fetcher.py

print("Files downloaded successfully.\n")

print("=" * 70)
print("STEP 2: Install Packages")
print("=" * 70)

!pip install -q pandas pyarrow huggingface-hub requests numpy

print("Packages installed successfully.\n")

print("=" * 70)
print("STEP 3: Clear Python Module Cache")
print("=" * 70)

import sys
for mod in list(sys.modules.keys()):
    if any(x in mod for x in ['config', 'initial']):
        del sys.modules[mod]

print("Cache cleared.\n")

print("=" * 70)
print("STEP 4: Run Initial 1D Fetcher")
print("=" * 70)

from initial_1d_fetcher import Initial1dFetcher

hf_token = input("\nEnter your HuggingFace token: ")

fetcher = Initial1dFetcher(hf_token=hf_token)
success_count, failed_count = fetcher.process_all_1d()
fetcher.print_summary(success_count, failed_count)

print("\nSetup complete! Your 1d klines are now on HuggingFace.")
print("Future daily updates will run automatically via GitHub Actions.")
print()
