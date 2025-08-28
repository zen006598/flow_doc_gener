from pydantic import BaseModel
from typing import List, Dict

from src.entity.func_call_entity import FuncCallEntity


class FuncMapEntity(BaseModel):
    ciname: str
    file_id: int
    path: str
    type: str
    funcs: List[str]
    fcalls: Dict[str, List[FuncCallEntity]]