from typing_extensions import Annotated
from autogen_core.tools import FunctionTool
from src.model import SourceCodeModel


async def create_source_code_tools(
    run_id: str
    ) -> dict[str, FunctionTool]:
    """
    Create closure-based tools that hide run_id from LLM while providing SourceCodeModel access
    
    Args:
        run_id: The run_id to use for SourceCodeModel queries (hidden from LLM)
        
    Returns:
        Dictionary of tool functions with run_id pre-bound
    """
    
    source_code_model = SourceCodeModel(run_id)
    
    async def get_file_content(file_id: Annotated[int, "The ID of the file to retrieve"]) -> str:
        """Get content of a specific file by file_id"""
        try:
            return source_code_model.get_content_by_id(file_id)
        except Exception as e:
            return f"Error retrieving file {file_id}: {str(e)}"

    # Create FunctionTool instances with strict=True
    get_file_content_tool = FunctionTool(
        get_file_content, 
        description="Get the source code content of a file by its ID",
        strict=True
    )

    tools = {
        "get_file_content": get_file_content_tool,
    }
    
    return tools
