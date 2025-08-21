from typing import List, Dict, Any
import json
from src.model.snapshot_manager import SnapshotManager
from src.utils.extract_json_response import extract_json_response


class EntryPointExtractor:
    """從 dependence data 中提取 entry points，支援手動指定和 AI 分析兩種模式"""
    
    def __init__(self, snapshot_manager: SnapshotManager):
        self.snapshot_manager = snapshot_manager
    
    def extract_manually(self, file_deps: Dict[str, Any], appoint_entries: List[str], 
                        run_id: str, entry_point_cache_file: str) -> int:
        """
        從 dependence data 中提取指定的 entry points 並儲存
        
        Args:
            file_deps: dependence cache 的數據
            appoint_entries: 指定的入口點函數名稱列表
            run_id: 運行 ID
            entry_point_cache_file: entry point cache 檔案名
            
        Returns:
            提取到的 entry points 數量
        """
        entries = []
        files = file_deps.get("files", {})
        
        for entry_name in appoint_entries:
            for file_id, file_info in files.items():
                if entry_name in file_info.get("func", []):
                    # 從 cls 陣列取得 component 名稱，如果為空則從路徑解析
                    cls_list = file_info.get("cls", [])
                    component = cls_list[0] if cls_list else file_info.get("path", "").split("/")[-1].replace(".cs", "")
                    
                    entry = {
                        "file_id": int(file_id),
                        "component": component,
                        "name": entry_name,
                        "reason": "manually_appointed"
                    }
                    entries.append(entry)
                    break
        
        entry_points_data = {"entries": entries}
        self.snapshot_manager.save_file(run_id, entry_point_cache_file, entry_points_data)
        
        return len(entries)
    
    async def extract_with_agent(self, client, file_deps: Dict[str, Any], 
                                run_id: str, entry_point_cache_file: str) -> int:
        """
        使用 AI agent 分析 entry points 並儲存
        
        Args:
            client: OpenAI client 實例
            file_deps: dependence cache 的數據  
            run_id: 運行 ID
            entry_point_cache_file: entry point cache 檔案名
            
        Returns:
            提取到的 entry points 數量
        """
        from autogen_agentchat.ui import Console
        from src.agent.entry_point_detector import entry_point_detector
        
        # 創建 detector agent
        detector_agent = await entry_point_detector(
            client=client, 
            run_id=run_id, 
            snapshot_manager=self.snapshot_manager
        )
        
        # 準備 prompt 數據
        detect_prompt = {
            "files": file_deps["files"],
            "deps": file_deps["deps"]
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
            return 0
        
        try:
            # 解析並儲存結果
            entry_points_data = json.loads(final_content)
            self.snapshot_manager.save_file(run_id, entry_point_cache_file, entry_points_data)
            
            entries_count = len(entry_points_data.get("entries", []))
            return entries_count
            
        except json.JSONDecodeError as e:
            print(f"解析 AI 回應時發生錯誤: {e}")
            return 0