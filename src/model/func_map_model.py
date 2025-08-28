import os
from typing import Optional
from tinydb import TinyDB, Query

from src.entity import FuncMapEntity

class FuncMapModel:
    def __init__(self, run_id: str, table: str = "func_map"):
        db_dir = f"cache/{run_id}"
        os.makedirs(db_dir, exist_ok=True)
        self.db = TinyDB(f"{db_dir}/{table}.json")

    def has_data(self) -> bool:
        return len(self.db) > 0
    
    def list_by_type(self, file_type: str) -> list[FuncMapEntity]:
        """List all files of a specific type (e.g., 'class', 'interface')"""
        File = Query()
        results = self.db.search(File.type == file_type)
        return [FuncMapEntity(**record) for record in results]
    
    def get_id_by_class_and_function(self, class_name: str, function_name: str) -> int:
        """Find all entities that contain both the specified class and function (not supports partial classes)"""
        File = Query()
        results = self.db.search(
            (File.ciname == class_name) & (File.funcs.any([function_name]))
        )
        
        if not results:
            return -1
    
        return results[0]['file_id']
    
    def get_by_component_and_function(self, 
            component_name: str, function_name: str, file_id: int) -> Optional[FuncMapEntity]:
        """Get function analysis entity by component name, function name and file id"""
        File = Query()
        results = self.db.search(
            (File.ciname == component_name) & 
            (File.funcs.any([function_name])) & 
            (File.file_id == file_id)
        )
        
        if results:
            return FuncMapEntity(**results[0])
        return None

    def batch_insert(self, files_data: list[FuncMapEntity]):
        """Insert multiple file function mapping entities at once"""
        self.db.insert_multiple([file_entity.model_dump() for file_entity in files_data])
    