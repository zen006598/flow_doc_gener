from src.analyzer.language_analyze_provider import LanguageAnalyzeProvider
from src.model.source_code_model import SourceCodeModel
from src.model.dependency_model import DependencyModel
from src.model.func_map_model import FuncMapModel
from src.analyzer.code_dependency_analyzer import CodeDependencyAnalyzer


class DependencyService:
    def __init__(self,
        dependency_model: DependencyModel, 
        file_function_map_model: FuncMapModel,
        source_code_model: SourceCodeModel,
        dep_analyzer: CodeDependencyAnalyzer,
        lang_provider: LanguageAnalyzeProvider,
        ):
        self.dependency_model = dependency_model
        self.file_function_map_model = file_function_map_model
        self.source_code_model = source_code_model
        self.dep_analyzer = dep_analyzer
        self.lang_provider = lang_provider
    
    async def ensure_dependencies(self) -> bool:
        
        if self.dependency_model.has_data() and self.file_function_map_model.has_data():
            print(f"Use cached dependencies")
            return True
        
        print(f"Analyzing dependencies")
        
        if not self.source_code_model.has_data():
            print(f"Error: No source code data found for run_id")
            return False
        
        source_code_entities = self.source_code_model.all()
        function_map = []
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
            
            function_map.extend(meaningful_entities)
            
        self.file_function_map_model.batch_insert(function_map)
        dep_map = self.dep_analyzer.analyze_project(function_map)
        self.dependency_model.batch_insert(dep_map)
                    
        return True