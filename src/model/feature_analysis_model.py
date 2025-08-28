import os
from typing import Optional
from tinydb import TinyDB, Query

from src.entity.feature_analysis_entity import FeatureAnalysisEntity


class FeatureAnalysisModel:
    def __init__(self, run_id: str, table: str = "feature"):
        db_dir = f"cache/{run_id}"
        os.makedirs(db_dir, exist_ok=True)
        self.db = TinyDB(f"{db_dir}/{table}.json")

    def has_data(self) -> bool:
        return len(self.db) > 0
    
    def insert(self, feature: FeatureAnalysisEntity):
        """Insert a single feature analysis result"""
        self.db.insert(feature.model_dump())
    
    def find_by_component_and_entry(self, component: str, entry_name: str) -> Optional[FeatureAnalysisEntity]:
        """Find feature analysis by component and entry name"""
        Feature = Query()
        results = self.db.search(
            (Feature.component == component) & (Feature.entry_name == entry_name)
        )
        if results:
            return FeatureAnalysisEntity(**results[0])
        return None