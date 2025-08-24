import os
from typing import List
from tinydb import TinyDB, Query


class FileFunctionsMapModel:
    def __init__(self, run_id: str, table: str = "file_functions_map"):
        db_dir = f"cache/{run_id}"
        os.makedirs(db_dir, exist_ok=True)
        self.db = TinyDB(f"{db_dir}/{table}.json")

    def has_data(self) -> bool:
        return len(self.db) > 0
    
    def all(self):
        """Get all file function mapping records"""
        return self.db.all()
    
    def find_by_class_and_function(self, class_name: str, function_name: str) -> List[dict]:
        """Find all files that contain both the specified class and function"""
        File = Query()
        return self.db.search(
            (File.cls.any([class_name])) & (File.func.any([function_name]))
        )
    
    def find_by_file_id(self, file_id: int) -> dict:
        """Find file by file ID"""
        File = Query()
        results = self.db.search(File.file_id == file_id)
        return results[0] if results else {}
    
    def get_function_calls(self, file_id: int, function_name: str) -> List[dict]:
        """Get function calls for a specific function in a file"""
        file_info = self.find_by_file_id(file_id)
        if file_info and "fcalls" in file_info:
            return file_info["fcalls"].get(function_name, [])
        return []
    
    def batch_insert(self, deps_data):
        self.db.insert_multiple(deps_data)