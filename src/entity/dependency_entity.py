from pydantic import BaseModel

from src.entity.func_call_entity import FuncCallEntity

class DependencyEntity(BaseModel):
    caller_file_id: int
    caller_entity: str
    caller_func: str
    callee_file_if: int
    callee_entity: str
    call: FuncCallEntity