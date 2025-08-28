from pydantic import BaseModel

class FuncCallEntity(BaseModel):
    method: str
    expr: str