from huggingface_hub import HfApi, login
from config import HF_DATASET_REPO, SYMBOLS, TIMEFRAMES, HF_DATASET_PATH, get_file_name

def check_hf_files():
    """
    Check which files exist on HuggingFace dataset using HfApi.list_repo_files()
    This helps identify which symbols need initial creation
    """
    hf_token = input("Enter your HuggingFace token: ").strip()
    
    print(f"\nLogging in to HuggingFace...")
    try:
        login(token=hf_token)
        print("Login successful!\n")
    except Exception as e:
        print(f"Login error: {e}")
        return
    
    print(f"Checking files in {HF_DATASET_REPO}...\n")
    
    try:
        api = HfApi()
        
        # Use list_repo_files() with repo_type="dataset"
        all_files = list(api.list_repo_files(
            repo_id=HF_DATASET_REPO,
            repo_type="dataset",
            token=hf_token
        ))
        
        print(f"Dataset found: {HF_DATASET_REPO}")
        print(f"Total files: {len(all_files)}\n")
        
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
        
        if existing_count == 0:
            print("(No files found yet)")
        
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
        if total_expected > 0:
            print(f"Progress:        {existing_count * 100 // total_expected}%")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        print("\nTroubleshooting:")
        print("1. Verify HF token is correct")
        print("2. Check dataset exists at: https://huggingface.co/datasets/zongowo111/v2-crypto-ohlcv-data")
        print("3. Ensure you have permission to access this dataset")
        print("4. Try generating a new token at: https://huggingface.co/settings/tokens")

if __name__ == "__main__":
    check_hf_files()