import os
from typing import List
from tinydb import TinyDB, Query

from src.entity.entry_point_entity import EntryPointEntity


class EntryPointModel:
    def __init__(self, run_id: str, table: str = "entry"):
        db_dir = f"cache/{run_id}"
        os.makedirs(db_dir, exist_ok=True)
        self.db = TinyDB(f"{db_dir}/{table}.json")
        
    def batch_insert(self, data: List[EntryPointEntity]):
        """Insert multiple entry point entities at once"""
        self.db.insert_multiple([entry.model_dump() for entry in data])
        
    def all(self) -> List[EntryPointEntity]:
        """Get all entry point records"""
        return [EntryPointEntity(**record) for record in self.db.all()]
    
    def has_data(self) -> bool:
        return len(self.db) > 0