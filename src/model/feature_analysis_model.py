import os
from typing import List
from tinydb import TinyDB, Query


class FeatureAnalysisModel:
    def __init__(self, run_id: str, table: str = "feature_analysis"):
        db_dir = f"cache/{run_id}"
        os.makedirs(db_dir, exist_ok=True)
        self.db = TinyDB(f"{db_dir}/{table}.json")

    def has_data(self) -> bool:
        return len(self.db) > 0
    
    def all(self):
        """Get all feature analysis records"""
        return self.db.all()
    
    def insert(self, component: str, entry_name: str, analysis_data: dict):
        """Insert a single feature analysis result"""
        self.db.insert({
            "component": component,
            "entry_name": entry_name,
            "analysis_data": analysis_data
        })
    
    def find_by_component_and_entry(self, component: str, entry_name: str) -> dict:
        """Find feature analysis by component and entry name"""
        Feature = Query()
        results = self.db.search(
            (Feature.component == component) & (Feature.entry_name == entry_name)
        )
        return results[0] if results else {}
    
    def batch_insert(self, analysis_records: List[dict]):
        """Insert multiple feature analysis records"""
        self.db.insert_multiple(analysis_records)