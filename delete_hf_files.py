from huggingface_hub import HfApi, login
from config import HF_DATASET_REPO, SYMBOLS, TIMEFRAMES, HF_DATASET_PATH, get_file_name
import time

def delete_all_files():
    """
    Delete all files in klines folder on HuggingFace dataset.
    This prepares for fresh historical data download.
    """
    hf_token = input("Enter your HuggingFace token: ").strip()
    
    print(f"\nLogging in to HuggingFace...")
    try:
        login(token=hf_token)
        print("Login successful!\n")
    except Exception as e:
        print(f"Login error: {e}")
        return
    
    api = HfApi()
    
    print(f"Fetching files from {HF_DATASET_REPO}/{HF_DATASET_PATH}...\n")
    
    try:
        all_files = list(api.list_repo_files(
            repo_id=HF_DATASET_REPO,
            repo_type="dataset",
            token=hf_token
        ))
        
        # Filter files in klines folder
        klines_files = [f for f in all_files if f.startswith(f"{HF_DATASET_PATH}/")]
        
        if not klines_files:
            print("No files found in klines folder.")
            return
        
        print(f"Found {len(klines_files)} files to delete:")
        print("=" * 60)
        
        # Group by symbol for display
        files_by_symbol = {}
        for file_path in klines_files:
            parts = file_path.split('/')
            if len(parts) >= 3:
                symbol = parts[1]
                if symbol not in files_by_symbol:
                    files_by_symbol[symbol] = []
                files_by_symbol[symbol].append(parts[2])
        
        for symbol in sorted(files_by_symbol.keys()):
            print(f"{symbol:12} -> {', '.join(sorted(files_by_symbol[symbol]))}")
        
        print("\n" + "=" * 60)
        confirm = input(f"\nDelete all {len(klines_files)} files? (yes/no): ").strip().lower()
        
        if confirm != 'yes':
            print("Cancelled.")
            return
        
        print(f"\nDeleting files...\n")
        
        deleted_count = 0
        failed_count = 0
        
        for i, file_path in enumerate(klines_files, 1):
            try:
                api.delete_file(
                    path_in_repo=file_path,
                    repo_id=HF_DATASET_REPO,
                    repo_type="dataset",
                    token=hf_token,
                    commit_message=f"Delete {file_path}"
                )
                deleted_count += 1
                print(f"[{i}/{len(klines_files)}] Deleted: {file_path}")
                
                # Small delay to avoid rate limiting
                time.sleep(0.5)
            except Exception as e:
                failed_count += 1
                print(f"[{i}/{len(klines_files)}] Failed to delete {file_path}: {str(e)[:80]}")
        
        print(f"\n" + "=" * 60)
        print(f"Deletion Summary:")
        print(f"  Successful: {deleted_count}")
        print(f"  Failed: {failed_count}")
        print(f"  Total: {len(klines_files)}")
        print(f"\nFolder structure remains (empty):")
        print(f"  {HF_DATASET_REPO}/")
        print(f"    {HF_DATASET_PATH}/")
        print(f"      (ready for new data)")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        print("\nTroubleshooting:")
        print("1. Verify HF token is correct")
        print("2. Check dataset exists")
        print("3. Ensure you have write permission")
        print("4. Try a new token from: https://huggingface.co/settings/tokens")

if __name__ == "__main__":
    delete_all_files()