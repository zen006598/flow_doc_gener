from src.analyzer.language_analyze_provider import LanguageAnalyzeProvider
from src.entity import FuncMapEntity
from src.model import SourceCodeModel, FuncMapModel


class FuncMapService:
    def __init__(self,
        file_function_map_model: FuncMapModel,
        source_code_model: SourceCodeModel,
        lang_provider: LanguageAnalyzeProvider,
        ):
        self.file_function_map_model = file_function_map_model
        self.source_code_model = source_code_model
        self.lang_provider = lang_provider
        
    def has_cache(self) -> bool:
        return self.file_function_map_model.has_data()
    
    def save_cache(self, func_map: list[FuncMapEntity]) -> None:
        self.file_function_map_model.batch_insert(func_map)
    
    def analyze_file(self) -> list[FuncMapEntity]:
        source_code_entities = self.source_code_model.all()
        
        if source_code_entities is None:
            raise ValueError("No source code data found for run_id")

        func_map = []
        for ent in source_code_entities:
            if not ent.content:
                continue
            
            lang_analyzer = self.lang_provider.get_analyzer_from_path(ent.path)
            
            if not lang_analyzer:
                continue
            
            function_analysis_entities = lang_analyzer.analyze_file(ent)
            # 只保留有意義的實體
            meaningful_entities = [
                function_analysis_entity for function_analysis_entity in function_analysis_entities 
                if function_analysis_entity.funcs or function_analysis_entity.fcalls
            ]
            
            func_map.extend(meaningful_entities)
        
        return func_map
