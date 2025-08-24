import os
from typing import List
from tinydb import TinyDB, Query

class SourceCodeModel:
    
    def __init__(self, run_id: str, table: str = "src"):
        db_dir = f"cache/{run_id}"
        os.makedirs(db_dir, exist_ok=True)
        self.db = TinyDB(f"{db_dir}/{table}.json")
        
    def get_content_by_id(self, fid: int) -> str:
        src = Query()
        result = self.db.search(src.id == fid)
        if result:
            return result[0].get("content", "")
        return ""
    
    def list_structure(self) -> dict:
        all_entries = self.db.all()
        return {entry["id"]: entry["path"] for entry in all_entries if "id" in entry and "path" in entry}
    
    def batch_insert(self, files_data):
        """Insert multiple source code files at once"""
        self.db.insert_multiple(files_data)
        
    def has_data(self) -> bool:
        return len(self.db) > 0
    
    def list(self, fids: List[int]) -> List[dict]:
        """Get multiple records by list of file IDs"""
        src = Query()
        results = []
        for fid in fids:
            result = self.db.search(src.id == fid)
            if result:
                results.append(result[0])
        return results