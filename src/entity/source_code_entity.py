from pydantic import BaseModel


class SourceCodeEntity(BaseModel):
    file_id: int
    path: str
    content: str