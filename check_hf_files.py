from huggingface_hub import HfApi, login
from config import HF_DATASET_REPO, SYMBOLS, TIMEFRAMES, HF_DATASET_PATH, get_file_name

def check_hf_files():
    """
    Check which files exist on HuggingFace dataset
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
        api = HfApi(token=hf_token)
        
        repo_info = api.repo_info(
            repo_id=HF_DATASET_REPO,
            repo_type="dataset"
        )
        print(f"Dataset found: {repo_info.repo_id}")
        print(f"Last modified: {repo_info.last_modified}\n")
        
        existing_files = {}
        missing_files = {}
        
        for symbol in SYMBOLS:
            existing_files[symbol] = []
            missing_files[symbol] = []
            
            for timeframe in TIMEFRAMES:
                file_name = get_file_name(symbol, timeframe)
                file_path = f"{HF_DATASET_PATH}/{symbol}/{file_name}"
                
                try:
                    file_info = api.file_info(
                        repo_id=HF_DATASET_REPO,
                        filename=file_path,
                        repo_type="dataset"
                    )
                    existing_files[symbol].append(timeframe)
                except:
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
        print("1. Verify HF token is correct")
        print("2. Check dataset access at: https://huggingface.co/datasets/zongowo111/v2-crypto-ohlcv-data")
        print("3. Ensure you have permission to access this dataset")

if __name__ == "__main__":
    check_hf_files()