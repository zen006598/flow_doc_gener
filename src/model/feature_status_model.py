import os
from typing import Optional
from tinydb import TinyDB, Query

from src.entity.feature_status_entity import FeatureStatusEntity


class FeatureStatusModel:
    def __init__(self, run_id: str, table: str = "feat_status"):
        db_dir = f"cache/{run_id}"
        os.makedirs(db_dir, exist_ok=True)
        self.db = TinyDB(f"{db_dir}/{table}.json")
        self.Q = Query()

    def get(self, id: int) -> Optional[FeatureStatusEntity]:
        row = self.db.get(self.Q.id == id)
        if row is None:
            return None
        return FeatureStatusEntity(**row)

    def batch_insert(self, entities: list[FeatureStatusEntity]) -> None:
        self.db.insert_multiple([entity.model_dump() for entity in entities])

    def to_running(self, id: int) -> None:
        self.db.update({"state": "running"}, self.Q.id == id)

    def to_done(self, id: int) -> None:
        self.db.update({"state": "done"}, self.Q.id == id)

    def to_failed(self, id: int) -> None:
        self.db.update({"state": "failed"}, self.Q.id == id)

    def get_retry_count(self, id: int) -> int:
        row = self.db.get(self.Q.id == id)
        if row is None:
            return 0
        return int(row.get("retry_count", 0))

    def inc_retry(self, id: int) -> int:
        row = self.db.get(self.Q.id == id)
        new_rc = int(row.get("retry_count", 0)) + 1
        self.db.update({"retry_count": new_rc}, self.Q.id == id)
        return new_rc

    def truncate(self) -> None:
        """Drop all records from the feature status table"""
        self.db.truncate()

    def get_pending_or_failed_entries(self, max_retry: int = 3) -> list[FeatureStatusEntity]:
        """Get entries that are pending or failed but haven't exceeded max retry count"""
        results = self.db.search(
            (self.Q.state.one_of(['pending', 'failed'])) & 
            (self.Q.retry_count < max_retry)
        )
        return [FeatureStatusEntity(**record) for record in results]

    def has_pending_work(self, max_retry: int = 3) -> bool:
        """Check if there are still entries to process"""
        return len(self.get_pending_or_failed_entries(max_retry)) > 0