from pathlib import Path
from src.analyzer.base_language_analyzer import BaseLanguageAnalyzer
from src.analyzer.csharp_analyzer import CSharpAnalyzer


class LanguageAnalyzeProvider:
    def __init__(self):
        self.analyzer_pairs = {
            '.cs': CSharpAnalyzer()
        }

    def get_analyzer_from_path(self, file_path: str) -> BaseLanguageAnalyzer:
        extension = Path(file_path).suffix.lower()
        return self.analyzer_pairs.get(extension)
