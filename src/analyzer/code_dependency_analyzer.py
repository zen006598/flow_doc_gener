from typing import Dict, Any, Optional
from pathlib import Path

from src.analyzer.base_language_analyzer import BaseLanguageAnalyzer
from src.analyzer.csharp_analyzer import CSharpAnalyzer
from src.model.snapshot_manager import SnapshotManager

class CodeDependencyAnalyzer:
    def __init__(self, snapshot_manager: SnapshotManager):
        self.language_analyzers = {
            'csharp': CSharpAnalyzer()
        }
        self.snapshot_manager = snapshot_manager
        
        self.lang_map = {
            '.cs': 'csharp'
        }
    
    def get_lang_from_path(self, file_path: str) -> str:
        suffix = Path(file_path).suffix.lower()
        return self.lang_map.get(suffix, 'text')
    
    def get_analyzer(self, programming_lang: str) -> Optional[BaseLanguageAnalyzer]:
        return self.language_analyzers.get(programming_lang)

    def analyze_project(self, run_id: str, file_name: str) -> Dict[str, Any]:
        """
        從 FileManager 快照數據中分析項目
        """
        snapshot_data = self.snapshot_manager.load_file(run_id, file_name)
        
        if not snapshot_data:
            raise ValueError("No data found")
        
        dir_structure = snapshot_data.get("dir_structure", {})
        contents = snapshot_data.get("contents", {})
        
        # 第一步：使用對應的語言分析器提取所有符號
        file_symbols = {}
        
        for file_id, file_path in dir_structure.items():
            content = contents.get(str(file_id), "")
            
            if not content:
                continue
            
            programming_lang = self.get_lang_from_path(file_path)
            analyzer = self.get_analyzer(programming_lang)
            
            if analyzer:
                symbols = analyzer.analyze_file(file_path, content)
                
                # 過濾掉沒有實際內容的文件（只有類定義，沒有函數、調用）
                has_meaningful_content = (
                    symbols.get('func') or 
                    symbols.get('calls') or
                    symbols.get('fcalls')
                )
                
                if not has_meaningful_content:
                    continue
            else:
                continue
            
            file_symbols[file_id] = symbols

        # 建立函數級別的依賴
        function_dependencies = []
        
        for file_id, file_info in file_symbols.items():
            function_calls = file_info.get('fcalls', {})
            
            for func_name, calls in function_calls.items():
                for call in calls:
                    call_method = call['method']
                    
                    # 查找這個調用對應的定義位置
                    for target_file_id, target_info in file_symbols.items():
                        if call_method in target_info.get('func', []):
                            function_dependencies.append({
                                'from': file_id,
                                'from_func': func_name,
                                'to': target_file_id,
                                'call': {
                                    'method': call['method'],
                                    'expr': call.get('expr', '')
                                }
                            })
                        elif call_method in target_info.get('cls', []):
                            function_dependencies.append({
                                'from': file_id,
                                'from_func': func_name,
                                'to': target_file_id,
                                'call': {
                                    'method': call['method'],
                                    'expr': call.get('expr', '')
                                }
                            })
        
        # 去重
        unique_func_deps = []
        seen = set()
        for dep in function_dependencies:
            key = (dep['from'], dep['from_func'], dep['to'])
            if key not in seen:
                seen.add(key)
                unique_func_deps.append(dep)
        
        return {
            'files': file_symbols,
            'deps': unique_func_deps
        }