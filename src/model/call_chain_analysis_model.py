import os
from typing import Optional
from tinydb import TinyDB, Query

from src.entity import CallChainResultEntity


class CallChainAnalysisModel:
    def __init__(self, run_id: str, table: str = "call_chain_analysis"):
        db_dir = f"cache/{run_id}"
        os.makedirs(db_dir, exist_ok=True)
        self.db = TinyDB(f"{db_dir}/{table}.json")

    def has_data(self) -> bool:
        return len(self.db) > 0
    
    def all(self):
        """Get all call chain analysis records"""
        return self.db.all()
    
    def insert(self, call_chain_result: CallChainResultEntity):
        """Insert a single call chain analysis result"""
        self.db.insert(call_chain_result.model_dump())
    
    def find_by_component_and_entry(self, component: str, entry_name: str) -> Optional[CallChainResultEntity]:
        """Find call chain analysis by component and entry name"""
        CallChain = Query()
        results = self.db.search(
            (CallChain.component == component) & (CallChain.name == entry_name)
        )
        if results:
            return CallChainResultEntity(**results[0])
        return None