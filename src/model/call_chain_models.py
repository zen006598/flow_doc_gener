from typing import List
from pydantic import BaseModel, Field


class CallNode(BaseModel):
    file_id: int = Field(..., description="Resolved callee file id")
    method: str = Field(..., description="Resolved callee method/function name")
    reason: str = Field(..., description="Why this node is included (delegation/impl/etc.)")


class CallChainResult(BaseModel):
    file_id: int = Field(..., description="Entry point file id")
    name: str = Field(..., description="Entry function name")
    call_chain: List[CallNode] = Field(default_factory=list, description="Flattened list of discovered nodes")
    stop_reason: str = Field(..., description="Why traversal stopped (<= 30 words)")
    
    def extract_all_file_ids(self) -> List[int]:
        """
        Extract all file IDs involved in this call chain analysis
        
        Returns:
            List of unique file IDs including entry point and all nodes in call chain
        """
        file_ids = set()
        
        # Add entry point file_id
        file_ids.add(self.file_id)
        
        # Add file_ids from all call chain nodes
        for node in self.call_chain:
            file_ids.add(node.file_id)
        
        return list(file_ids)


class EntryPoint(BaseModel):
    name: str = Field(..., description="Entry function name")
    component: str = Field(..., description="Class/component containing the entry function")
    file_id: int = Field(..., description="ID of the file containing the entry function")