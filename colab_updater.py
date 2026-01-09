import os
from data_handler import DataHandler
from config import SYMBOLS, TIMEFRAMES
from datetime import datetime

def setup_colab_environment():
    """Setup environment in Google Colab"""
    print("Setting up Colab environment...")
    os.system('pip install -q pandas pyarrow huggingface-hub requests numpy')
    print("Environment setup completed")

def main():
    print("="*60)
    print("Crypto Data Updater - Colab Version")
    print("="*60)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    hf_token = input("Please enter your HuggingFace API token: ").strip()
    
    if not hf_token:
        print("Error: HuggingFace token is required")
        return
    
    handler = DataHandler(hf_token=hf_token)
    
    print()
    print("Configuration:")
    print(f"Total symbols: {len(SYMBOLS)}")
    print(f"Timeframes: {TIMEFRAMES}")
    print(f"Total tasks: {len(SYMBOLS) * len(TIMEFRAMES)}")
    print()
    
    proceed = input("Proceed with data update? (yes/no): ").strip().lower()
    if proceed != 'yes':
        print("Operation cancelled")
        return
    
    print()
    print("Starting data update process...")
    print()
    
    results = handler.process_all()
    
    print()
    print("="*60)
    print("Update Results Summary")
    print("="*60)
    
    successful = sum(1 for v in results.values() if v == "SUCCESS")
    failed = sum(1 for v in results.values() if v == "FAILED")
    
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Total: {successful + failed}")
    print()
    
    if failed > 0:
        print("Failed updates:")
        for key, status in results.items():
            if status == "FAILED":
                print(f"  - {key}")
    
    print()
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

if __name__ == "__main__":
    setup_colab_environment()
    main()