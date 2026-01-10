import os
import json
import logging
from typing import Dict, List, Optional
from pathlib import Path
import subprocess
import pandas as pd

logger = logging.getLogger(__name__)

class GitHubCacheManager:
    """
    管理 GitHub 上的快取資料夾，存放待上傳的 parquet 檔案
    支援本地操作和 GitHub 直接推送
    """
    
    def __init__(self, repo_owner: str, repo_name: str, cache_dir: str = "data/cache"):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.cache_dir = cache_dir
        self.local_cache_path = Path(cache_dir)
        self.local_cache_path.mkdir(parents=True, exist_ok=True)
        
        # 快取索引檔案 (用來追蹤已上傳的檔案)
        self.cache_index_file = self.local_cache_path / "cache_index.json"
        self.cache_index = self._load_cache_index()
    
    def _load_cache_index(self) -> Dict:
        """
        讀取快取索引
        """
        if self.cache_index_file.exists():
            try:
                with open(self.cache_index_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache index: {e}")
                return {}
        return {}
    
    def _save_cache_index(self):
        """
        保存快取索引
        """
        try:
            with open(self.cache_index_file, 'w') as f:
                json.dump(self.cache_index, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save cache index: {e}")
    
    def save_to_cache(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str
    ) -> bool:
        """
        將合併後的資料存到本地快取
        """
        try:
            symbol_dir = self.local_cache_path / symbol
            symbol_dir.mkdir(exist_ok=True)
            
            filename = f"{symbol.replace('USDT', '')}_{timeframe}.parquet"
            filepath = symbol_dir / filename
            
            df.to_parquet(filepath, index=False, compression='snappy')
            
            # 更新索引
            key = f"{symbol}_{timeframe}"
            self.cache_index[key] = {
                "filename": filename,
                "symbol": symbol,
                "timeframe": timeframe,
                "rows": len(df),
                "status": "cached",  # cached = 待上傳, uploaded = 已上傳
                "filepath": str(filepath)
            }
            self._save_cache_index()
            
            logger.info(f"Saved to cache: {symbol} {timeframe} ({len(df)} rows)")
            return True
        except Exception as e:
            logger.error(f"Failed to save to cache: {e}")
            return False
    
    def get_cached_files(self, status: str = "cached") -> List[Dict]:
        """
        取得快取中的檔案 (按狀態篩選)
        status: "cached" (待上傳) 或 "uploaded" (已上傳)
        """
        return [v for v in self.cache_index.values() if v.get("status") == status]
    
    def mark_as_uploaded(self, symbol: str, timeframe: str) -> bool:
        """
        標記檔案為已上傳
        """
        try:
            key = f"{symbol}_{timeframe}"
            if key in self.cache_index:
                self.cache_index[key]["status"] = "uploaded"
                self._save_cache_index()
                logger.info(f"Marked as uploaded: {symbol} {timeframe}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to mark as uploaded: {e}")
            return False
    
    def get_cache_stats(self) -> Dict:
        """
        取得快取統計資訊
        """
        cached_files = self.get_cached_files("cached")
        uploaded_files = self.get_cached_files("uploaded")
        total_rows = sum(f.get("rows", 0) for f in cached_files)
        total_size_mb = sum(
            Path(f["filepath"]).stat().st_size / (1024 * 1024)
            for f in cached_files
            if Path(f["filepath"]).exists()
        )
        
        return {
            "cached_count": len(cached_files),
            "uploaded_count": len(uploaded_files),
            "total_rows_cached": total_rows,
            "total_size_mb": round(total_size_mb, 2),
            "cached_files": cached_files
        }
    
    def cleanup_uploaded(self):
        """
        刪除已上傳的本地檔案
        """
        try:
            uploaded_files = self.get_cached_files("uploaded")
            count = 0
            for file_info in uploaded_files:
                filepath = Path(file_info["filepath"])
                if filepath.exists():
                    filepath.unlink()
                    count += 1
            
            # 刪除空的符號資料夾
            for symbol_dir in self.local_cache_path.iterdir():
                if symbol_dir.is_dir() and symbol_dir.name != ".git":
                    if not list(symbol_dir.glob("*.parquet")):
                        symbol_dir.rmdir()
            
            logger.info(f"Cleaned up {count} uploaded files")
            return True
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
            return False
    
    def push_to_github(self, commit_message: str = "Update crypto data cache") -> bool:
        """
        將快取推送到 GitHub
        """
        try:
            # 檢查是否有改變
            result = subprocess.run(
                ["git", "status", "--porcelain", self.cache_dir],
                cwd=".",
                capture_output=True,
                text=True
            )
            
            if not result.stdout.strip():
                logger.info("No changes to push")
                return True
            
            # 加入快取
            subprocess.run(
                ["git", "add", self.cache_dir],
                cwd=".",
                check=True
            )
            
            # 提交
            subprocess.run(
                ["git", "commit", "-m", commit_message],
                cwd=".",
                check=True
            )
            
            # 推送
            subprocess.run(
                ["git", "push", "origin", "main"],
                cwd=".",
                check=True
            )
            
            logger.info("Successfully pushed to GitHub")
            return True
        except Exception as e:
            logger.error(f"Failed to push to GitHub: {e}")
            return False
