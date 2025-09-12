from typing import Optional
from pydantic import BaseModel, Field


class ExternalApi(BaseModel):
    endpoint: str = Field(..., description="External API endpoint")
    method: str = Field(..., description="HTTP method for external API")


class CallerInfo(BaseModel):
    file_id: int = Field(..., description="Caller's file ID")
    method: str = Field(..., description="Caller's method name")


class CalleeInfo(BaseModel):
    file_id: int = Field(..., description="Callee's file ID")
    method: str = Field(..., description="Callee's method name")


class DataAccess(BaseModel):
    r: list[str] = Field(default_factory=list, description="Tables or data sources read")
    w: list[str] = Field(default_factory=list, description="Tables or data sources written")


class CallChain(BaseModel):
    component: str = Field(..., description="Component name")
    method: str = Field(..., description="Method name")
    caller: CallerInfo = Field(..., description="Caller information")
    callee: CalleeInfo = Field(..., description="Callee information")
    data_access: DataAccess = Field(default_factory=DataAccess, description="Data access information")
    role: str = Field(..., description="Role of this component in the architecture")
    desc: str = Field(default="", description="Function description")
    confidence: float = Field(default=0.0, description="Confidence score")


class FeatureAnalysisEntity(BaseModel):
    entry_func_name: str = Field(..., description="Entry point function name")
    entry_component_name: str = Field(..., description="Entry point component name")
    http_url: Optional[str] = Field(None, description="HTTP URL endpoint")
    http_method: Optional[str] = Field(None, description="HTTP method")
    include_file_id: list[int] = Field(default_factory=list, description="List of file IDs involved")
    parameters: list[str] = Field(default_factory=list, description="Function parameters")
    external_api: list[ExternalApi] = Field(default_factory=list, description="External APIs called")
    table_read: list[str] = Field(default_factory=list, description="Tables read")
    table_write: list[str] = Field(default_factory=list, description="Tables written")
    call_chains: list[CallChain] = Field(default_factory=list, description="Call chain information")
    summary: str = Field(default="", description="Summary of the feature")
