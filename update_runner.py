import os
import sys
from data_handler import DataHandler
from config import SYMBOLS, TIMEFRAMES
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def main():
    print("="*60)
    print("Hourly Crypto Data Update - GitHub Actions Version")
    print("="*60)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    hf_token = os.getenv('HF_TOKEN')
    if not hf_token:
        logging.error("Error: HF_TOKEN environment variable is not set")
        sys.exit(1)
    
    handler = DataHandler(hf_token=hf_token)
    
    logging.info(f"Configuration: {len(SYMBOLS)} symbols, {len(TIMEFRAMES)} timeframes")
    logging.info(f"Total tasks: {len(SYMBOLS) * len(TIMEFRAMES)}")
    print()
    
    logging.info("Starting hourly update process...")
    print()
    
    results = handler.process_all()
    
    print()
    print("="*60)
    print("Update Results Summary")
    print("="*60)
    
    successful = sum(1 for v in results.values() if v == "SUCCESS")
    failed = sum(1 for v in results.values() if v == "FAILED")
    
    logging.info(f"Successful updates: {successful}")
    logging.info(f"Failed updates: {failed}")
    logging.info(f"Total: {successful + failed}")
    
    if failed > 0:
        logging.warning("Failed updates:")
        for key, status in results.items():
            if status == "FAILED":
                logging.warning(f"  - {key}")
    
    print()
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())