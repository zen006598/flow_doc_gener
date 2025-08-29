import os
from typing import Optional
from tinydb import TinyDB, Query

from src.entity.feature_analysis_entity import FeatureAnalysisEntity


class FeatureAnalysisModel:
    def __init__(self, run_id: str, table: str = "feat"):
        db_dir = f"cache/{run_id}"
        os.makedirs(db_dir, exist_ok=True)
        self.db = TinyDB(f"{db_dir}/{table}.json")
        self.q = Query()
    
    def has_data(self) -> bool:
        return len(self.db) > 0
    
    def insert(self, feature: FeatureAnalysisEntity):
        """Insert a single feature analysis result"""
        self.db.insert(feature.model_dump())
    
    def get_by_component_and_entry(self, component: str, entry_name: str) -> Optional[FeatureAnalysisEntity]:
        """Find feature analysis by component and entry name"""
        results = self.db.search(
            (self.q.entry_component_name == component) & (self.q.entry_func_name == entry_name)
        )
        
        if results:
            return FeatureAnalysisEntity(**results[0])
        return None