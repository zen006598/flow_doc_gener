import os

from tinydb import TinyDB

class EntryPointModel:
    def __init__(self, run_id: str, table: str = "entry"):
        db_dir = f"cache/{run_id}"
        os.makedirs(db_dir, exist_ok=True)
        self.db = TinyDB(f"{db_dir}/{table}.json")
        
    def batch_insert(self, data):
        self.db.insert_multiple(data)
        
    def all(self):
        return self.db.all()
    
    def has_data(self) -> bool:
        return len(self.db) > 0