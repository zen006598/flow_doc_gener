from typing import Dict, List, Any, Callable
from typing_extensions import Annotated
from autogen_core.tools import FunctionTool
from autogen_core import CancellationToken

from src.core.config import Config
from src.model.snapshot_manager import SnapshotManager

async def create_dependency_tools(
    snapshot_manager: SnapshotManager, 
    run_id: str
    ) -> Dict[str, FunctionTool]:
    """
    Create closure-based dependency tools that hide run_id from LLM while providing snapshot access
    
    Args:
        snapshot_manager: SnapshotManager instance for snapshot operations
        run_id: The run_id to use for snapshot queries (hidden from LLM)
        
    Returns:
        Dictionary of dependency tool functions with run_id pre-bound
    """
    
    conf = Config()
    dependency_cache_file = conf.cache_file_name_map["dependence"]
    
    async def get_deps_to(file_id: Annotated[int, "The ID of the file to get dependencies to"]) -> List[Dict[str, Any]]:
        """取得所有指向特定檔案的相依性關係 (向上追蹤)
        
        找出誰呼叫了指定檔案中的函數，用於分析該檔案的使用者或呼叫者。
        每個相依性項目包含：
        - from: 發起呼叫的檔案ID
        - from_func: 發起呼叫的函數名稱
        - to: 被呼叫的目標檔案ID (即輸入的file_id)
        - to_func: 被呼叫的目標函數名稱
        - call: 呼叫的詳細資訊 (method, expr)
        
        使用場景：
        - 找出某個Service被哪些Controller使用
        - 分析某個Repository被哪些Service呼叫
        - 追蹤某個工具函數的使用情況
        """
        try:
            snapshot_data = snapshot_manager.load_file(run_id, dependency_cache_file)
            if not snapshot_data or "deps" not in snapshot_data:
                return []
            
            result = []
            for d in snapshot_data["deps"]:
                if int(d["to"]) == file_id:
                    result.append(d)
            
            return result
        except Exception as e:
            return []
    
    async def get_deps_from(file_id: Annotated[int, "The ID of the file to get dependencies from"]) -> List[Dict[str, Any]]:
        """取得所有從特定檔案發起的相依性關係 (向下追蹤)
        
        找出指定檔案中的函數呼叫了哪些其他函數，用於分析該檔案的對外相依性。
        每個相依性項目包含：
        - from: 發起呼叫的檔案ID (即輸入的file_id)
        - from_func: 發起呼叫的函數名稱
        - to: 被呼叫的目標檔案ID
        - call: 被呼叫的目標函數的詳細資訊 (method, expr)
        
        使用場景：
        - 分析某個Controller呼叫了哪些Service
        - 查看某個Service依賴哪些Repository
        """
        try:
            snapshot_data = snapshot_manager.load_file(run_id, dependency_cache_file)
            if not snapshot_data or "deps" not in snapshot_data:
                return []
            
            result = []
            for d in snapshot_data["deps"]:
                if int(d["from"]) == file_id:
                    result.append(d)
            
            return result
        except Exception as e:
            return []
    
    async def get_file(file_id: Annotated[int, "The ID of the file to get information for"]) -> Dict[str, Any]:
        """取得檔案的詳細資訊
        
        根據檔案ID獲取完整的檔案資訊，包含路徑、定義的類別和函數、以及呼叫關係。
        返回的檔案資訊包含：
        - path: 檔案的完整路徑，用於判斷檔案類型和架構層級
        - cls: 該檔案中定義的類別列表，用於識別設計模式
        - funcs: 該檔案中定義的函數列表，用於識別進入點
        - calls: 該檔案中呼叫到的方法列表，簡化版用於快速檢查
        - fcalls: 詳細的函數呼叫資訊，包含每個函數內部的呼叫細節
        
        使用場景：
        - 分析檔案類型 (Controller, Service, Repository)
        - 識別進入點函數 (Main, Execute, Handle)
        - 了解檔案的內部結構和對外呼叫
        - 判斷檔案在架構中的角色和層級
        """
        try:
            snapshot_data = snapshot_manager.load_file(run_id, dependency_cache_file)
            if not snapshot_data or "files" not in snapshot_data:
                raise ValueError(f"file {file_id} not found")
            
            file_id_str = str(file_id)
            if file_id_str not in snapshot_data["files"]:
                raise ValueError(f"file {file_id} not found")
            
            return snapshot_data["files"][file_id_str]
        except Exception as e:
            raise ValueError(f"file {file_id} not found")
    
    # Create FunctionTool instances with strict=True
    get_deps_to_tool = FunctionTool(
        get_deps_to,
        description="向上追蹤相依性：找出所有呼叫指定檔案的其他檔案和函數，用於分析誰在使用這個檔案",
        strict=True
    )
    
    get_deps_from_tool = FunctionTool(
        get_deps_from,
        description="向下追蹤相依性：找出指定檔案呼叫的所有其他檔案和函數，用於分析這個檔案的對外相依性",
        strict=True
    )
    
    get_file_tool = FunctionTool(
        get_file,
        description="取得檔案資訊：包含路徑、定義的類別函數、呼叫關係等，用於分析檔案類型和架構角色",
        strict=True
    )
    
    # Return dictionary of tool functions
    tools = {
        "get_deps_to": get_deps_to_tool,
        "get_deps_from": get_deps_from_tool,
        "get_file": get_file_tool,
    }
    
    return tools