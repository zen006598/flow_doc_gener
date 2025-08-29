from pydantic import BaseModel
from typing import Literal


class FeatureStatusEntity(BaseModel):
    id: int
    component: str
    name: str
    state: Literal['pending', 'running', 'done', 'failed']
    retry_count: int = 0