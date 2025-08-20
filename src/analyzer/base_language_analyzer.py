from typing import Dict, Any
from abc import ABC, abstractmethod
from tree_sitter_language_pack import get_language, get_parser

class BaseLanguageAnalyzer(ABC):
    """語言分析器基類"""
    
    def __init__(self, programming_language: str):
        self.programming_language = programming_language
        self.lang = get_language(programming_language)
        self.parser = get_parser(programming_language)
    
    def extract_text(self, node, source_code: bytes) -> str:
        return source_code[node.start_byte:node.end_byte].decode('utf-8').strip()
    
    @abstractmethod
    def analyze_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """
        分析單個文件，返回標準格式的結果
        
        Returns:
            {
                'path': str,
                'functions': List[str],
                'classes': List[str], 
                'calls': List[str] 或 List[Dict] (詳細調用信息)
            }
        """
        pass
