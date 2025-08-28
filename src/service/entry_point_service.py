import json
from typing import Any, Optional

from src.agent.entry_point_detect_agent import EntryPointDetectorAgent
from src.core.config import Config
from src.entity import EntryPointEntity
from src.model import EntryPointModel, FuncMapModel, SourceCodeModel
from autogen_agentchat.ui import Console

from src.utils import extract_json_response

class EntryPointService:
    def __init__(self, 
        config: Config,
        entry_point_model: EntryPointModel,
        file_function_map_model: FuncMapModel,
        source_code_model :SourceCodeModel,
        agent: EntryPointDetectorAgent):
        self.config = config
        self.entry_point_model = entry_point_model
        self.file_function_map_model = file_function_map_model
        self.source_code_model = source_code_model
        self.agent = agent
        
    def _has_cache(self) -> bool:
        return self.entry_point_model.has_data()
    
    def _save_cache(self, entry_points):
        self.entry_point_model.batch_insert(entry_points)
    
    def _lost_func_map_data(self) -> bool:
        return not self.file_function_map_model.has_data()
    
    async def ensure_entry_points(self, appoint_entries: Optional[list[str]] = None) -> bool:
        
        if self._has_cache():
            print(f"Use cached entry points")
            return True
        
        print(f"Extracting entry points")
        
        if self._lost_func_map_data():
            print(f"Error: No file function map data found")
            return False
        
        entry_points_data = None
        
        if appoint_entries:
            entry_points_data = self._extract_manually(appoint_entries)
        else:
            entry_points_data = await self._extract_with_ai()
        
        if not entry_points_data:
            print(f"No entry points found")
            return False
        
        self._save_cache(entry_points_data)
        print(f"{len(entry_points_data)} entry points is founded")
        return True
    
    def _extract_manually(self, appoint_entries: list[Any]):
        """
        從 FileFunctionsMapModel 中提取指定的 entry points
        
        Args:
            appoint_entries: 指定的入口點函數名稱列表
            
        Returns:
            list of entry point
        """
        entries = []
        
        for idx, entry_spec in enumerate(appoint_entries, start=1):
            # 解析 "class_name.function_name" 格式
            class_name, function_name = entry_spec.split(".", 1)
            
            fid = self.file_function_map_model.get_id_by_class_and_function(
                class_name, function_name)
            
            if fid == -1:
                continue
                
            entry = EntryPointEntity(
                entry_id=idx,
                file_id=fid,
                component=class_name, 
                name=function_name,
                confidence=1.0,
                reason=""
            )
            entries.append(entry)
        
        return entries
    
    
    async def _extract_with_ai(self) -> list[EntryPointEntity]:
        # Get file function mappings
        func_map = self.file_function_map_model.list_by_type("class")
        # Collect file_ids from func_map
        file_ids = [entity.file_id for entity in func_map]
        dir_structure = self.source_code_model.list_structure_by_ids(file_ids)
        
        # Convert entities to dict format and remove empty fields
        files_list = []
        for m in func_map:
            data = m.model_dump(exclude_none=True)
            files_list.append(data)
        
        prompt = {
            "dir_structure": dir_structure,
            "files": files_list
        }
        
        agent = await self.agent.get_agent()
        res = await Console(agent.run_stream(task=json.dumps(prompt)))
        
        if not (res.messages and res.messages[-1] and res.messages[-1].content):
            return []
        
        final_content = extract_json_response(res.messages[-1].content)
        
        if not final_content:
            print("警告：無法從 AI 回應中提取有效的 JSON")
            return []
        
        entry_points_data = json.loads(final_content)

        if not entry_points_data or "entries" not in entry_points_data:
            return []
            
        entries = []
        for idx, entry in enumerate(entry_points_data["entries"], start=1):
            entry_point = EntryPointEntity(
                entry_id=idx,
                file_id=entry["file_id"],
                component=entry["component"], 
                name=entry["name"],
                confidence=entry.get("confidence", 1.0),
                reason=entry.get("reason", "")
            )
            entries.append(entry_point)
        return entries