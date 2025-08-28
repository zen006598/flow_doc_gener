import os
from tinydb import TinyDB, Query

from src.entity import DependencyEntity


class DependencyModel:
    def __init__(self, run_id: str, table: str = "dep"):
        db_dir = f"cache/{run_id}"
        os.makedirs(db_dir, exist_ok=True)
        self.db = TinyDB(f"{db_dir}/{table}.json")

    def has_data(self) -> bool:
        return len(self.db) > 0
    
    def find_callee_by_caller(self, file_id: int, component: str, expr: str) -> list[DependencyEntity]:
        """Find dependencies by file ID and expression"""
        Dep = Query()
        results = self.db.search(
            (Dep['caller_file_id'] == file_id )&
            (Dep['caller_entity'] == component) &
            (Dep['call']['expr'] == expr)
        )
        
        return [DependencyEntity(**r) for r in results]

    def batch_insert(self, deps_data: list[DependencyEntity]):
        """Insert multiple dependency entities at once"""
        self.db.insert_multiple([dep.model_dump() for dep in deps_data])
    