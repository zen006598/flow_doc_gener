from pydantic import BaseModel, Field


class CallNode(BaseModel):
    file_id: int = Field(..., description="Resolved callee file id")
    method: str = Field(..., description="Resolved callee method/function name")
    reason: str = Field(..., description="Why this node is included (delegation/impl/etc.)")


class CallChainResultEntity(BaseModel):
    file_id: int = Field(..., description="Entry point file id")
    name: str = Field(..., description="Entry function name")
    component: str = Field(..., description="Class/component containing the entry function")
    call_chain: list[CallNode] = Field(default_factory=list, description="Flattened list of discovered nodes")
    stop_reason: str = Field(..., description="Why traversal stopped (<= 30 words)")


class EntryPoint(BaseModel):
    name: str = Field(..., description="Entry function name")
    component: str = Field(..., description="Class/component containing the entry function")
    file_id: int = Field(..., description="ID of the file containing the entry function")