from typing import Dict, List, Any
from typing_extensions import Annotated
from autogen_core.tools import FunctionTool

from src.model.dependency_model import DependencyModel
from src.model.file_functions_map_model import FileFunctionsMapModel

async def create_dependency_tools(
    run_id: str
    ) -> Dict[str, FunctionTool]:
    """
    Create closure-based dependency tools using DependencyModel and FileFunctionsMapModel
    
    Args:
        run_id: The run_id to use for model queries (hidden from LLM)
        
    Returns:
        Dictionary of dependency tool functions with run_id pre-bound
    """
    
    dependency_model = DependencyModel(run_id)
    file_functions_map_model = FileFunctionsMapModel(run_id)
    
    async def get_deps_to(file_id: Annotated[int, "The ID of the file to get dependencies to"]) -> List[Dict[str, Any]]:
        """取得所有指向特定檔案的相依性關係 (向上追蹤)
        
        找出誰呼叫了指定檔案中的函數，用於分析該檔案的使用者或呼叫者。
        每個相依性項目包含：
        - from: 發起呼叫的檔案ID
        - from_func: 發起呼叫的函數名稱
        - to: 被呼叫的目標檔案ID (即輸入的file_id)
        - call: 呼叫的詳細資訊 (method, expr)
        
        使用場景：
        - 找出某個Service被哪些Controller使用
        - 分析某個Repository被哪些Service呼叫
        - 追蹤某個工具函數的使用情況
        """
        try:
            return dependency_model.find_deps_to(file_id)
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
            return dependency_model.find_deps_from(file_id)
        except Exception as e:
            return []
        
    async def get_deps_by_file_id_and_expr(
        file_id: Annotated[int, "The ID of the file to get dependencies from"], 
        expr: Annotated[str, "The expression to match in the call"]
    ) -> List[int]:
        """根據檔案ID和表達式查詢相依性目標檔案
        
        找出指定檔案中呼叫特定表達式的所有目標檔案ID。
        用於精確追蹤特定方法呼叫的流向。
        
        參數：
        - file_id: 發起呼叫的檔案ID
        - expr: 要匹配的呼叫表達式
        
        返回：
        - List[int]: 被呼叫的目標檔案ID列表
        
        使用場景：
        - 追蹤特定方法呼叫的流向
        - 分析某個特定呼叫會影響哪些檔案
        - 精確定位相依性關係
        
        範例：
        input: file_id=209, expr="_PageAgentService.PageAgent(list.TotalCount.ToInt(),parameter.Ps,parameter.Pg)"
        output: [527, 570]
        """
        try:
            deps = dependency_model.find_deps_by_file_and_expr(file_id, expr)
            return [dep["to"] for dep in deps]
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
            file_info = file_functions_map_model.find_by_file_id(file_id)
            if not file_info:
                raise ValueError(f"file {file_id} not found")
            return file_info
        except Exception as e:
            raise ValueError(f"file {file_id} not found")
        
    async def get_function_snippet(
        file_id: Annotated[int, "The ID of the file to get function snippet for"],
        function_name: Annotated[str, "The name of the function to get snippet for"]
        ) -> Dict[str, Any]:
        """取得指定檔案中特定函數的呼叫片段
        
        根據檔案ID和函數名稱，從 fcalls 中取得該函數內部的所有方法呼叫資訊。
        返回格式為包含 file_id 和 calls 的字典，其中 calls 為包含 method 和 expr 的字典列表。
        
        參數：
        - file_id: 檔案ID
        - function_name: 函數名稱
        
        返回：
        - Dict[str, Any]: 包含 file_id 和 calls 的字典
          - file_id: 檔案ID
          - path: 檔案位置
          - calls: List[Dict[str, str]] 包含 method 和 expr 的呼叫片段列表
        
        使用場景：
        - 分析特定函數內部的方法呼叫
        - 追蹤函數如何使用其他服務或函數
        - 了解函數的實作細節
        
        範例：
        input: file_id=241, function_name="GetByNameKeywordAsync"
        output: {
            "file_id": 241,
            "calls": [{"method": "GetByNameKeywordAsync", "expr": "_CommunityEsRepository.GetByNameKeywordAsync(communityAliasNamePinyinKeyword)"}]
        }
        """
        try:
            file_info = file_functions_map_model.find_by_file_id(file_id)
            if not file_info:
                return {}
            
            function_calls = file_functions_map_model.get_function_calls(file_id, function_name)
            if function_calls:
                return {
                    "file_id": file_id,
                    "path": file_info.get("path", ""),
                    "calls": function_calls
                }
            return {}
        except Exception as e:
            return {}
                
    
    
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
    
    get_function_snippet_tool = FunctionTool(
        get_function_snippet,
        description="取得指定檔案中特定函數的呼叫片段，用於分析函數內部的方法呼叫",
        strict=True
    )
    
    get_deps_by_file_id_and_expr_tool = FunctionTool(
        get_deps_by_file_id_and_expr,
        description="根據檔案ID和表達式查詢相依性目標檔案，用於精確追蹤特定方法呼叫的流向",
        strict=True
    )
    
    # Return dictionary of tool functions
    tools = {
        "get_deps_to": get_deps_to_tool,
        "get_deps_from": get_deps_from_tool,
        "get_file": get_file_tool,
        "get_function_snippet": get_function_snippet_tool,
        "get_deps_by_file_id_and_expr": get_deps_by_file_id_and_expr_tool,
    }
    
    return tools