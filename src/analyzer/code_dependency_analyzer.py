from src.entity.dependency_entity import DependencyEntity
from src.entity.func_map_entity import FuncMapEntity

class CodeDependencyAnalyzer:
    def analyze_project(self, function_analysis_entities:  list[FuncMapEntity]) -> list[DependencyEntity]:
        """建立實體間的依賴關係"""
        method_to_entities = self.build_method_index(function_analysis_entities)

        dependencies = []
        seen = set()
        
        for entity in function_analysis_entities:
            caller_file_id = entity.file_id
            caller_name = entity.ciname
            
            # 分析此實體的所有方法調用
            for func_name, calls in entity.fcalls.items():
                for call in calls:
                    call_method = call.method
                    
                    # 查找被調用方法屬於哪些實體（可能有多個同名方法）
                    target_entities = method_to_entities.get(call_method, [])
                    
                    # 為每個匹配的 class 實體建立依賴關係
                    for target_entity in target_entities:
                        callee_file_id = target_entity.file_id
                        callee_name = target_entity.ciname
                        
                        # 避免重複記錄
                        key = (caller_file_id, f"{caller_name}.{func_name}", callee_file_id)
                        if key not in seen:
                            seen.add(key)
                            dependencies.append(DependencyEntity(
                                caller_file_id=caller_file_id,
                                caller_entity=caller_name,
                                caller_func=func_name,
                                callee_file_if=callee_file_id,
                                callee_entity=callee_name,
                                call=call
                            ))
        
        return dependencies
    
    def build_method_index(self, entities: list[FuncMapEntity]) -> dict[str, list[FuncMapEntity]]:
        """建立方法名到實體列表的映射索引，只包含 class 類型實體"""
        method_to_entities = {}
        
        for entity in entities:
            # 只為 class 類型的實體建立索引
            if entity.type == 'class':
                for func_name in entity.funcs:
                    if func_name not in method_to_entities:
                        method_to_entities[func_name] = []
                    method_to_entities[func_name].append(entity)
        
        return method_to_entities    