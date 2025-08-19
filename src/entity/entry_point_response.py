from typing import List
from pydantic import BaseModel
from src.entity.entry_point import EntryPoint

class EntryPointResponse(BaseModel):
    entries: List[EntryPoint]