from src.entity import FuncMapEntity, DependencyEntity
from src.model import DependencyModel, FuncMapModel
from src.analyzer.code_dependency_analyzer import CodeDependencyAnalyzer

class DependencyService:
    def __init__(self,
        dependency_model: DependencyModel, 
        func_map_model: FuncMapModel, 
        dep_analyzer: CodeDependencyAnalyzer,
        ):
        self.dependency_model = dependency_model
        self.dep_analyzer = dep_analyzer
        self.func_map_model = func_map_model
        
    def has_cache(self) -> bool:
        return self.dependency_model.has_data()

    def analyze_dependencies(self) -> list[DependencyEntity]:
        func_maps = self.func_map_model.all()
        if not func_maps:
            raise ValueError("Function map is empty, cannot analyze dependencies.")
        
        return self.dep_analyzer.analyze_project(func_maps)
    
    def save_cache(self, dependencies: list[FuncMapEntity]) -> None:
        self.dependency_model.batch_insert(dependencies)