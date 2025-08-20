import os
import json
from typing import Dict, Any, Optional, List
from pathlib import Path


class SnapshotManager:
    """Manager class for handling snapshot operations in src/cache directory"""
    
    def __init__(self, cache_dir: str = "src/cache"):
        self.cache_dir = cache_dir
        
    def _get_run_cache_dir(self, run_id: str) -> str:
        """Get the cache directory for a specific run_id"""
        return os.path.join(self.cache_dir, run_id)
    
    def _ensure_cache_dir(self, run_id: str) -> str:
        """Ensure cache directory exists for the run_id"""
        cache_dir = self._get_run_cache_dir(run_id)
        os.makedirs(cache_dir, exist_ok=True)
        return cache_dir
    
    def save_file(self, run_id: str, filename: str, data: Any, as_json: bool = True) -> bool:
        """
        Save data to a file in the cache directory
        
        Args:
            run_id: Unique identifier for the run
            filename: Name of the file to save
            data: Data to save
            as_json: Whether to save as JSON (default: True)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            cache_dir = self._ensure_cache_dir(run_id)
            file_path = os.path.join(cache_dir, filename)
            
            if as_json:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            else:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(str(data))
            
            return True
        except Exception as e:
            print(f"Error saving file {filename} for run_id {run_id}: {e}")
            return False
    
    def load_file(self, run_id: str, filename: str, as_json: bool = True) -> Optional[Any]:
        """
        Load data from a file in the cache directory
        
        Args:
            run_id: Unique identifier for the run
            filename: Name of the file to load
            as_json: Whether to load as JSON (default: True)
            
        Returns:
            Loaded data or None if file doesn't exist or error occurs
        """
        try:
            cache_dir = self._get_run_cache_dir(run_id)
            file_path = os.path.join(cache_dir, filename)
            
            if not os.path.exists(file_path):
                return None
            
            if as_json:
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()
                    
        except Exception as e:
            print(f"Error loading file {filename} for run_id {run_id}: {e}")
            return None
    
    def file_exists(self, run_id: str, filename: str) -> bool:
        """
        Check if a file exists in the cache directory
        
        Args:
            run_id: Unique identifier for the run
            filename: Name of the file to check
            
        Returns:
            bool: True if file exists, False otherwise
        """
        cache_dir = self._get_run_cache_dir(run_id)
        file_path = os.path.join(cache_dir, filename)
        return os.path.exists(file_path)
    
    def delete_file(self, run_id: str, filename: str) -> bool:
        """
        Delete a file from the cache directory
        
        Args:
            run_id: Unique identifier for the run
            filename: Name of the file to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            cache_dir = self._get_run_cache_dir(run_id)
            file_path = os.path.join(cache_dir, filename)
            
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception as e:
            print(f"Error deleting file {filename} for run_id {run_id}: {e}")
            return False
    
    def list_files(self, run_id: str) -> List[str]:
        """
        List all files in the cache directory for a run_id
        
        Args:
            run_id: Unique identifier for the run
            
        Returns:
            List of filenames in the cache directory
        """
        cache_dir = self._get_run_cache_dir(run_id)
        
        if not os.path.exists(cache_dir):
            return []
        
        try:
            return [f for f in os.listdir(cache_dir) if os.path.isfile(os.path.join(cache_dir, f))]
        except Exception as e:
            print(f"Error listing files for run_id {run_id}: {e}")
            return []
    
    def run_exists(self, run_id: str) -> bool:
        """
        Check if a run directory exists and has files
        
        Args:
            run_id: Unique identifier for the run
            
        Returns:
            bool: True if run directory exists and has files, False otherwise
        """
        cache_dir = self._get_run_cache_dir(run_id)
        
        if not os.path.exists(cache_dir):
            return False
        
        try:
            files = os.listdir(cache_dir)
            return len(files) > 0
        except Exception:
            return False
    
    def delete_run(self, run_id: str) -> bool:
        """
        Delete entire run directory and all its files
        
        Args:
            run_id: Unique identifier for the run
            
        Returns:
            bool: True if successful, False otherwise
        """
        import shutil
        
        try:
            cache_dir = self._get_run_cache_dir(run_id)
            
            if os.path.exists(cache_dir):
                shutil.rmtree(cache_dir)
                return True
            return False
        except Exception as e:
            print(f"Error deleting run directory for run_id {run_id}: {e}")
            return False
    
    def list_runs(self) -> List[str]:
        """
        List all available run_ids in the cache directory
        
        Returns:
            List of run_ids (directory names)
        """
        if not os.path.exists(self.cache_dir):
            return []
        
        try:
            return [d for d in os.listdir(self.cache_dir) 
                   if os.path.isdir(os.path.join(self.cache_dir, d))]
        except Exception as e:
            print(f"Error listing runs: {e}")
            return []
    
    def get_file_path(self, run_id: str, filename: str) -> str:
        """
        Get the full file path for a file in the cache
        
        Args:
            run_id: Unique identifier for the run
            filename: Name of the file
            
        Returns:
            Full file path
        """
        cache_dir = self._get_run_cache_dir(run_id)
        return os.path.join(cache_dir, filename)