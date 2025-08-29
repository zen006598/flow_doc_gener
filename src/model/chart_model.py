import os
from typing import Optional
from tinydb import TinyDB, Query

from src.entity import ChartEntity


class ChartModel:
    def __init__(self, run_id: str, table: str = "chart"):
        db_dir = f"cache/{run_id}"
        os.makedirs(db_dir, exist_ok=True)
        self.db = TinyDB(f"{db_dir}/{table}.json")
        self.q = Query()

    def get(self, id: int) -> Optional[ChartEntity]:
        row = self.db.search(self.q['entry_id'] == id )
        if row:
            return ChartEntity(**row[0])
        return None
    
    def is_exist(self, id: int) -> bool:
        return self.db.contains(self.q['entry_id'] == id)

    def insert(self, entity: ChartEntity) -> None:
        self.db.insert(entity.model_dump())
    