from typing import Dict, Callable
from typing_extensions import Annotated
from autogen_core.tools import FunctionTool
from autogen_core import CancellationToken

from src.core.config import Config
from src.model.snapshot_manager import SnapshotManager

async def create_source_code_tools(
    snapshot_manager: SnapshotManager, 
    run_id: str
    ) -> Dict[str, FunctionTool]:
    """
    Create closure-based tools that hide run_id from LLM while providing snapshot access
    
    Args:
        file_manager: FileManager instance for snapshot operations
        run_id: The run_id to use for snapshot queries (hidden from LLM)
        
    Returns:
        Dictionary of tool functions with run_id pre-bound
    """
    
    conf = Config()
    source_code_cache_file = conf.cache_file_name_map["source_code"]
    
    async def get_file_content(file_id: Annotated[int, "The ID of the file to retrieve"]) -> str:
        """Get content of a specific file by file_id"""
        try:
            snapshot_data = snapshot_manager.load_file(run_id, source_code_cache_file)
            if not snapshot_data:
                return ""
            
            contents = snapshot_data.get("contents", {})
            return contents.get(str(file_id), "")
        except Exception as e:
            return f"Error retrieving file {file_id}: {str(e)}"
    
    async def list_dir_structure() -> str:
        """List all files in the snapshot with their IDs and paths as JSON string"""
        try:
            snapshot_data = snapshot_manager.load_file(run_id, source_code_cache_file)
            if not snapshot_data:
                return "{}"
            
            dir_structure = snapshot_data.get("dir_structure", {})
            import json
            return json.dumps(dir_structure)
        except Exception as e:
            return f"Error listing files: {str(e)}"
    
    # Create FunctionTool instances with strict=True
    get_file_content_tool = FunctionTool(
        get_file_content, 
        description="Get the source code content of a file by its ID",
        strict=True
    )
    
    list_dir_structure_tool = FunctionTool(
        list_dir_structure,
        description="Get the complete project structure with file IDs and paths",
        strict=True
    )
    
    # Return dictionary of tool functions
    tools = {
        "get_file_content": get_file_content_tool,
        "list_dir_structure": list_dir_structure_tool,
    }
    
    return tools
