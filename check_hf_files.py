import os
from huggingface_hub import list_repo_files
from config import HF_DATASET_REPO, SYMBOLS, TIMEFRAMES, HF_DATASET_PATH, get_file_name

def check_hf_files():
    """
    Check which files exist on HuggingFace dataset
    This helps identify which symbols need initial creation
    """
    hf_token = input("Enter your HuggingFace token: ").strip()
    
    print(f"\nChecking files in {HF_DATASET_REPO} (Dataset)...\n")
    
    try:
        all_files = list_repo_files(
            repo_id=HF_DATASET_REPO,
            repo_type="dataset",
            token=hf_token
        )
        
        print(f"Total files found: {len(all_files)}\n")
        
        existing_files = {}
        missing_files = {}
        
        for symbol in SYMBOLS:
            existing_files[symbol] = []
            missing_files[symbol] = []
            
            for timeframe in TIMEFRAMES:
                file_name = get_file_name(symbol, timeframe)
                file_path = f"{HF_DATASET_PATH}/{symbol}/{file_name}"
                
                if file_path in all_files:
                    existing_files[symbol].append(timeframe)
                else:
                    missing_files[symbol].append(timeframe)
        
        print("\nExisting Files:")
        print("=" * 60)
        existing_count = 0
        for symbol, timeframes in existing_files.items():
            if timeframes:
                print(f"{symbol:12} -> {', '.join(timeframes)}")
                existing_count += len(timeframes)
        
        print("\n\nMissing Files (will be created on first update):")
        print("=" * 60)
        missing_count = 0
        for symbol, timeframes in missing_files.items():
            if timeframes:
                print(f"{symbol:12} -> {', '.join(timeframes)}")
                missing_count += len(timeframes)
        
        print(f"\n\nStatistics:")
        print("=" * 60)
        total_expected = len(SYMBOLS) * len(TIMEFRAMES)
        print(f"Total existing:  {existing_count}/{total_expected}")
        print(f"Total missing:   {missing_count}/{total_expected}")
        print(f"Progress:        {existing_count * 100 // total_expected}%")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        print("\nTroubleshooting:")
        print("1. Verify HF token is correct and has read access")
        print("2. Verify dataset access at: https://huggingface.co/datasets/zongowo111/v2-crypto-ohlcv-data")
        print("3. Ensure dataset exists and is not private/gated without permission")

if __name__ == "__main__":
    check_hf_files()