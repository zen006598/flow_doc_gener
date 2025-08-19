from typing import Optional
from pydantic import BaseModel

class EntryPoint(BaseModel):
    entry_id: int
    file_id: int
    path: str
    func: Optional[str] = None
    reason: str

