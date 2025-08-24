import os
from typing import List
from tinydb import TinyDB, Query


class DependencyModel:
    def __init__(self, run_id: str, table: str = "dep"):
        db_dir = f"cache/{run_id}"
        os.makedirs(db_dir, exist_ok=True)
        self.db = TinyDB(f"{db_dir}/{table}.json")

    def has_data(self) -> bool:
        return len(self.db) > 0
    
    def all(self):
        """Get all dependency records"""
        return self.db.all()
    
    def find_deps_to(self, file_id: int) -> List[dict]:
        """Find all dependencies pointing to this file (who calls this file)"""
        Dep = Query()
        return self.db.search(Dep['to'] == file_id)
    
    def find_deps_from(self, file_id: int) -> List[dict]:
        """Find all dependencies from this file (what this file calls)"""
        Dep = Query()
        return self.db.search(Dep['from'] == file_id)
    
    def find_deps_by_file_and_expr(self, file_id: int, expr: str) -> List[dict]:
        """Find dependencies by file ID and expression"""
        Dep = Query()
        return self.db.search(
            (Dep['from'] == file_id) & (Dep['call']['expr'] == expr)
        )
    
    def batch_insert(self, deps_data):
        self.db.insert_multiple(deps_data)