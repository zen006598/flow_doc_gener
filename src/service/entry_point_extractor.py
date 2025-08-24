from typing import List, Dict, Any
import json
from src.model.file_functions_map_model import FileFunctionsMapModel
from src.utils.extract_json_response import extract_json_response
from autogen_agentchat.ui import Console
from src.agent.entry_point_detector import entry_point_detector

class EntryPointExtractor:
    """從 FileFunctionsMapModel 中提取 entry points，支援手動指定和 AI 分析兩種模式"""
    
    def __init__(self, file_functions_map_model: FileFunctionsMapModel):
        self.file_functions_map_model = file_functions_map_model
    
    def extract_manually(self, appoint_entries: List[str]):
        """
        從 FileFunctionsMapModel 中提取指定的 entry points
        
        Args:
            appoint_entries: 指定的入口點函數名稱列表
            
        Returns:
            包含 entries 的字典
        """
        entries = []
        
        for entry_spec in appoint_entries:
            # 解析 "class_name.function_name" 格式
            class_name, function_name = entry_spec.split(".", 1)
            
            matching_files = self.file_functions_map_model.find_by_class_and_function(
                class_name, function_name
            )
            
            for file_info in matching_files:
                entry = {
                    "file_id": file_info.get("file_id"),
                    "component": class_name,
                    "name": function_name,
                    "reason": "manually_appointed"
                }
                entries.append(entry)
        
        return entries
    
    async def extract_with_agent(self, client, file_deps: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用 AI agent 分析 entry points
        
        Args:
            client: OpenAI client 實例
            file_deps: dependence cache 的數據  
            
        Returns:
            包含 entries 的字典，如果失敗則返回 None
        """
        
        detector_agent = await entry_point_detector(client=client)
        
        detect_prompt = {
            "dir_structure": {str(file_id): file_info["path"] for file_id, file_info in file_deps["files"].items()},
            "files": file_deps["files"]
        }
        
        # 執行 AI 分析
        result = await Console(detector_agent.run_stream(task=json.dumps(detect_prompt)))
        
        # 提取 JSON 回應
        final_msg = None
        if result.messages:
            final_msg = result.messages[-1]
        
        final_content = extract_json_response(final_msg.content)
        
        if not final_content:
            print("警告：無法從 AI 回應中提取有效的 JSON")
            return None
        
        try:
            # 解析結果
            entry_points_data = json.loads(final_content)
            return entry_points_data
            
        except json.JSONDecodeError as e:
            print(f"解析 AI 回應時發生錯誤: {e}")
            return None