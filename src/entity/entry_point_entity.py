from pydantic import BaseModel
from typing import Optional


class EntryPointEntity(BaseModel):
    entry_id: int
    file_id: int
    component: str
    name: str
    confidence: float = 1.0
    reason: Optional[str] = None