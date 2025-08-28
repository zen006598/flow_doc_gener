from typing import Any
from typing_extensions import Annotated
from autogen_core.tools import FunctionTool

from src.model import DependencyModel, FuncMapModel

async def create_dependency_tools(
    run_id: str
    ) -> dict[str, FunctionTool]:
    """
    Create closure-based dependency tools using DependencyModel and FileFunctionsMapModel
    
    Args:
        run_id: The run_id to use for model queries (hidden from LLM)
        
    Returns:
        Dictionary of dependency tool functions with run_id pre-bound
    """
    
    dependency_model = DependencyModel(run_id)
    func_map_model = FuncMapModel(run_id)
        
    async def find_caller_by_dep(
        file_id: Annotated[int, "The ID of the file to get dependencies from"],
        component: Annotated[str, "The name of the caller component"],
        expr: Annotated[str, "The expression to match in the call"]
    ) -> list[dict[str, Any]]:
        """Find dependency target file details by file ID, component and expression
        
        Finds all target files and their detailed information for calls to specific expressions
        within a specific component of the specified file. Used for precise tracking of 
        specific method call flows and complete information of target entities.
        
        Args:
        - file_id: The file ID where the call originates (caller's file)
        - component: The name of the calling component (caller's class/component)
        - expr: The call expression to match (specific method call statement)
        
        Returns:
        - List[Dict[str, Any]]: List of called target file details, each containing:
          - file_id: Target file ID
          - type: Target entity type (class, interface, etc.)
          - component: Target component name
          - method: Called method name
        
        Use cases:
        - Track complete flow of specific method calls
        - Analyze which files and components are affected by a specific call
        - Get detailed call information of target components
        
        Example:
        input: file_id=209, component="Controller", expr="service.GetData()"
        output: [
            {
                "file_id": 527,
                "type": "class",
                "component": "DataService",
                "method": "GetData"
            }
        ]
        """
        try:
            deps = dependency_model.find_callee_by_caller(file_id, component, expr)
            res = []
            
            for dep in deps:
                func_map = func_map_model.get_by_component_and_function(
                    dep.callee_entity, dep.call.method, dep.callee_file_if)
                
                if not func_map:
                    continue
                
                res.append({
                    "file_id": func_map.file_id,
                    "type": func_map.type,
                    "component": func_map.ciname,  # 使用被呼叫者的組件名
                    "method": dep.call.method,       # 被呼叫的方法名
                })
                
            return res
        
        except Exception as e:
            return []
        
    async def get_func_map(
        fid: Annotated[int, "The ID of the file to get function snippet for"],
        component: Annotated[str, "The name of the function component"],
        func: Annotated[str, "The name of the function to get snippet for"]
        ) -> dict[str, Any]:
        """取得指定組件中特定函數的呼叫片段
        
        根據組件名稱和函數名稱，從 fcalls 中取得該函數內部的所有方法呼叫資訊。
        返回格式為包含 file_id、component、function 和 calls 的字典。
        
        參數：
        - fid: 檔案ID
        - component: 組件名稱（對應 FunctionAnalysisEntity.ciname）
        - func: 函數名
        
        返回：
        - Dict[str, Any]: 包含函數呼叫詳細資訊的字典
        - file_id: 檔案ID
        - path: 檔案位置
        - component: 組件名
        - type: 實體類型
        - calls: List[Dict[str, str]] 包含 method 和 expr 的呼叫片段列表
        
        使用場景：
        - 分析特定組件中特定函數的內部方法呼叫
        - 追蹤函數如何使用其他服務或函數
        
        範例：
        input: file_id=241, component_name="UserController", function_name="GetUser"
        output: {
            "file_id": 241,
            "path": "src/Controllers/UserController.cs",
            "component": "UserController",
            "type": "class",
            "calls": [{"method": "FindByIdAsync", "expr": "userRepository.FindByIdAsync(id)"}]
        }
        """
        try:
            entity = func_map_model.get_by_component_and_function(
                component, func, fid)
            
            if not entity:
                return {}
            
            calls = entity.fcalls.get(func, []) if entity.fcalls else []

            return {
                "file_id": entity.file_id,
                "path": entity.path,
                "component": entity.ciname,
                "type": entity.type,
                "calls": [{"method": call.method, "expr": call.expr} for call in calls]
            }
        except Exception as e:
            return {}
    
    get_func_map_tool = FunctionTool(
        get_func_map,
        description="取得指定檔案中特定函數的呼叫片段，用於分析函數內部的方法呼叫",
        strict=True
    )
    
    find_caller_by_dep_tool = FunctionTool(
        find_caller_by_dep,
        description="根據檔案ID和表達式查詢可能的相依性組件",
        strict=True
    )
    
    tools = {
        "get_func_map": get_func_map_tool,
        "find_caller_by_dep": find_caller_by_dep_tool,
    }
    
    return tools