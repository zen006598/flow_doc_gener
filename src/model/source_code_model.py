import os
from tinydb import TinyDB, Query

from src.entity import SourceCodeEntity


class SourceCodeModel:
    
    def __init__(self, run_id: str, table: str = "src"):
        db_dir = f"cache/{run_id}"
        os.makedirs(db_dir, exist_ok=True)
        self.db = TinyDB(f"{db_dir}/{table}.json")
        
    def get_content_by_id(self, fid: int) -> str:
        src = Query()
        result = self.db.search(src.file_id == fid)
        if result:
            return result[0].get("content", "")
        return ""
    
    def list_structure(self) -> dict:
        all_entries = self.db.all()
        return {entry["file_id"]: entry["path"] for entry in all_entries if "file_id" in entry and "path" in entry}
    
    def list_structure_by_ids(self, ids: list[int]) -> dict:
        src = Query()
        files = self.db.search(src.file_id.one_of(ids))
        return {
            f["file_id"]: f["path"]
            for f in files 
            if "file_id" in f and "path" in f
        }
    
    def all(self) -> list[SourceCodeEntity]:
        return [SourceCodeEntity(**s) for s in self.db.all()]
    
    def batch_insert(self, files_data: list[SourceCodeEntity]):
        """Insert multiple source code files at once"""
        self.db.insert_multiple([file_entity.model_dump() for file_entity in files_data])
        
    def has_data(self) -> bool:
        return len(self.db) > 0
    
    def find_by_id(self, fids: list[int]) -> list[SourceCodeEntity]:
        """Get multiple records by list of file IDs"""
        src = Query()
        results = []
        for fid in fids:
            result = self.db.search(src.file_id == fid)
            if result:
                results.append(SourceCodeEntity(**result[0]))
        return results