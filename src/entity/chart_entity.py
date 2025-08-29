from pydantic import BaseModel

class ChartEntity(BaseModel):
    entry_id: int
    mermaid_flow_chart: str