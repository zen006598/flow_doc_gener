from typing import Dict, Any, Optional
from pathlib import Path

from src.analyzer.base_language_analyzer import BaseLanguageAnalyzer
from src.analyzer.csharp_analyzer import CSharpAnalyzer
from src.model.source_code_model import SourceCodeModel

class CodeDependencyAnalyzer:
    def __init__(self, source_code_model: SourceCodeModel):
        self.language_analyzers = {
            'csharp': CSharpAnalyzer()
        }
        
        self.source_code_model = source_code_model
        
        self.lang_map = {
            '.cs': 'csharp'
        }
    
    def get_lang_from_path(self, file_path: str) -> str:
        suffix = Path(file_path).suffix.lower()
        return self.lang_map.get(suffix, 'text')
    
    def get_analyzer(self, programming_lang: str) -> Optional[BaseLanguageAnalyzer]:
        return self.language_analyzers.get(programming_lang)

    def analyze_project(self) -> Dict[str, Any]:
        """
        從 SourceCodeModel 數據中分析項目
        """
        dir_structure = self.source_code_model.list_structure()
        
        # 第一步：使用對應的語言分析器提取所有符號
        file_symbols = {}
        
        for file_id, file_path in dir_structure.items():
            content = self.source_code_model.get_content_by_id(int(file_id))
            
            if not content:
                continue
            
            programming_lang = self.get_lang_from_path(file_path)
            analyzer = self.get_analyzer(programming_lang)
            
            if analyzer:
                symbols = analyzer.analyze_file(content)
                
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
            
            symbols['file_id'] = int(file_id)
            symbols['path'] = file_path
            file_symbols[file_id] = symbols

        # 建立函數和類別的查找索引
        method_to_file = {}
        for file_id, file_info in file_symbols.items():
            for func in file_info.get('func', []):
                method_to_file[func] = file_id
            for cls in file_info.get('cls', []):
                method_to_file[cls] = file_id
        
        # 建立函數級別的依賴
        function_dependencies = []
        seen = set()
        
        for file_id, file_info in file_symbols.items():
            function_calls = file_info.get('fcalls', {})
            
            for func_name, calls in function_calls.items():
                for call in calls:
                    call_method = call['method']
                    target_file_id = method_to_file.get(call_method)
                    
                    if target_file_id:
                        key = (file_id, func_name, target_file_id)
                        if key not in seen:
                            seen.add(key)
                            function_dependencies.append({
                                'from': file_id,
                                'from_func': func_name,
                                'to': target_file_id,
                                'call': {
                                    'method': call['method'],
                                    'expr': call.get('expr', '')
                                }
                            })
        
        return {
            'files': list(file_symbols.values()),
            'deps': function_dependencies
        }