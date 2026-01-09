import os
from huggingface_hub import list_repo_files, hf_hub_url
from config import HF_DATASET_REPO, SYMBOLS, TIMEFRAMES, HF_DATASET_PATH

def check_hf_files():
    """
    Check which files exist on HuggingFace
    This helps identify which symbols need initial creation
    """
    hf_token = input("Enter your HuggingFace token: ").strip()
    
    print(f"\nChecking files in {HF_DATASET_REPO}...\n")
    
    try:
        all_files = list_repo_files(
            repo_id=HF_DATASET_REPO,
            token=hf_token
        )
        
        existing_files = {}
        missing_files = {}
        
        for symbol in SYMBOLS:
            existing_files[symbol] = []
            missing_files[symbol] = []
            
            for timeframe in TIMEFRAMES:
                file_name = f"{symbol.replace('USDT', '')}_{timeframe}.parquet"
                file_path = f"{HF_DATASET_PATH}/{symbol}/{file_name}"
                
                if file_path in all_files:
                    existing_files[symbol].append(timeframe)
                else:
                    missing_files[symbol].append(timeframe)
        
        print("\nExisting Files:")
        print("=" * 50)
        for symbol, timeframes in existing_files.items():
            if timeframes:
                print(f"{symbol}: {', '.join(timeframes)}")
        
        print("\n\nMissing Files (need to be created):")
        print("=" * 50)
        missing_count = 0
        for symbol, timeframes in missing_files.items():
            if timeframes:
                print(f"{symbol}: {', '.join(timeframes)}")
                missing_count += len(timeframes)
        
        print(f"\n\nTotal existing: {sum(len(v) for v in existing_files.values())}")
        print(f"Total missing: {missing_count}")
        print(f"Total expected: {len(SYMBOLS) * len(TIMEFRAMES)}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        print("\nMake sure:")
        print("1. Your HF token is correct")
        print("2. You have access to the dataset")
        print("3. The repository exists")

if __name__ == "__main__":
    check_hf_files()