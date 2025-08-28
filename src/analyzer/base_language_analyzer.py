from typing import List
from abc import ABC, abstractmethod
from tree_sitter_language_pack import get_language, get_parser

from src.entity.func_map_entity import FuncMapEntity
from src.entity.source_code_entity import SourceCodeEntity

class BaseLanguageAnalyzer(ABC):
    """語言分析器基類"""
    
    def __init__(self, programming_language: str):
        self.programming_language = programming_language
        self.lang = get_language(programming_language)
        self.parser = get_parser(programming_language)
    
    def extract_text(self, node, source_code: bytes) -> str:
        return source_code[node.start_byte:node.end_byte].decode('utf-8').strip()
    
    @abstractmethod
    def analyze_file(source_code_entity: SourceCodeEntity) -> List[FuncMapEntity]:
        """
        分析單個文件，返回實體列表
        
        Returns:
            List[{
                'ciname': str,
                'file_id': int,
                'path': str,
                'type': str,
                'funcs': List[str],
                'fcalls': Dict[str, List[Dict]]
            }]
        """
        pass
