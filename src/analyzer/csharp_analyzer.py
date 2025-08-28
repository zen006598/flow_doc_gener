from typing import List, Dict
from tree_sitter import Query, QueryCursor
from src.analyzer.base_language_analyzer import BaseLanguageAnalyzer
from src.entity.func_map_entity import FuncMapEntity
from src.entity.func_call_entity import FuncCallEntity
from src.entity.source_code_entity import SourceCodeEntity

class CSharpAnalyzer(BaseLanguageAnalyzer):
    """C# 語言分析器"""
    
    def __init__(self):
        super().__init__("csharp")
        self.common_methods = [
            "GetHashCode", "Equals", "ToString", "ToInt", "GetType",
            "Dispose", "Close", "Finalize", "Clone", "Add", 
            "AddRange", "Clear", "Contains", "CopyTo", "Remove", 
            "Ok", "nameof", "NotFound", "BadRequest"
        ]
        
        self.queries = {
            "entities": """
                [
                    (class_declaration 
                        name: (identifier) @entity_name
                        body: (declaration_list) @entity_body
                    ) @entity
                    (interface_declaration
                        name: (identifier) @entity_name  
                        body: (declaration_list) @entity_body
                    ) @entity
                ]
            """,
            "methods_in_entity": """
                (method_declaration 
                    name: (identifier) @method_name
                    body: (block)? @method_body
                )
            """,
            "member_calls": """
                (invocation_expression
                    function: (member_access_expression
                        expression: (_) @receiver
                        name: (identifier) @method
                    )
                ) @full_expression
            """,
            "direct_calls": """
                (invocation_expression
                    function: (identifier) @function
                ) @full_expression
            """
        }
    
    def analyze_file(self, source_code_entity: SourceCodeEntity) -> List[FuncMapEntity]:
        code_bytes = source_code_entity.content.encode("utf-8")
        tree = self.parser.parse(code_bytes)
        
        entities = []
        
        entity_query = Query(self.lang, self.queries["entities"])
        entity_cursor = QueryCursor(entity_query)
        entity_matches = entity_cursor.matches(tree.root_node)
        
        for match in entity_matches:
            captures = match[1]
            
            entity_name = None
            entity_body = None
            entity_node = None
            
            for capture_name, nodes in captures.items():
                for node in nodes:
                    if capture_name == "entity_name":
                        entity_name = self.extract_text(node, code_bytes)
                    elif capture_name == "entity_body":
                        entity_body = node
                    elif capture_name == "entity":
                        entity_node = node
            
            if not entity_name or not entity_body:
                continue
            
            # 判斷實體類型
            entity_type = "interface" if "interface_declaration" in entity_node.type else "class"
            
            # 分析這個實體內的方法
            if entity_type == "interface":
                # Interface 只提取方法聲明
                method_names = self._extract_interface_methods(entity_body, code_bytes)
                methods = {}  # Interface 沒有實現，fcalls 為空
            else:
                # Class 分析方法實現和調用
                methods = self._analyze_methods_in_entity(entity_body, code_bytes)
                method_names = list(methods.keys())
            
            entities.append(FuncMapEntity(
                ciname=entity_name,
                file_id=source_code_entity.file_id,
                path=source_code_entity.path,
                type=entity_type,
                funcs=method_names,
                fcalls=methods
            ))
        
        return entities
    
    def _extract_interface_methods(self, interface_body, source_code: bytes) -> List[str]:
        """提取接口中的方法聲明"""
        method_query = Query(self.lang, """
            (method_declaration 
                name: (identifier) @method_name
            )
        """)
        method_cursor = QueryCursor(method_query)
        method_matches = method_cursor.matches(interface_body)
        
        method_names = []
        for match in method_matches:
            captures = match[1]
            for capture_name, nodes in captures.items():
                if capture_name == "method_name":
                    for node in nodes:
                        method_name = self.extract_text(node, source_code)
                        method_names.append(method_name)
        
        return method_names
    
    def _analyze_methods_in_entity(self, entity_body, source_code: bytes) -> Dict[str, List[FuncCallEntity]]:
        """分析實體內的方法及其調用"""
        method_query = Query(self.lang, self.queries["methods_in_entity"])
        method_cursor = QueryCursor(method_query)
        method_matches = method_cursor.matches(entity_body)
        
        methods = {}
        
        for match in method_matches:
            captures = match[1]
            
            method_name = None
            method_body = None
            
            for capture_name, nodes in captures.items():
                for node in nodes:
                    if capture_name == "method_name":
                        method_name = self.extract_text(node, source_code)
                    elif capture_name == "method_body":
                        method_body = node
            
            if method_name and method_body:
                # 分析方法內的調用
                calls = self._analyze_calls_in_method(method_body, source_code)
                if calls:  # 只記錄有調用的方法
                    methods[method_name] = calls
        
        return methods
    
    def _analyze_calls_in_method(self, method_body, source_code: bytes) -> List[FuncCallEntity]:
        """分析方法內的調用"""
        calls = []
        seen_methods = set()
        
        # 分析成員調用
        member_calls = self._find_calls_in_node(method_body, source_code, "member_calls")
        calls.extend(member_calls)
        
        # 分析直接調用  
        direct_calls = self._find_calls_in_node(method_body, source_code, "direct_calls")
        calls.extend(direct_calls)
        
        # 去重
        unique_calls = []
        for call in calls:
            if call.method not in seen_methods:
                seen_methods.add(call.method)
                unique_calls.append(call)
        
        return unique_calls
    
    def _find_calls_in_node(self, node, source_code: bytes, call_type: str) -> List[FuncCallEntity]:
        """在指定節點內查找調用"""
        query = Query(self.lang, self.queries[call_type])
        cursor = QueryCursor(query)
        matches = cursor.matches(node)
        
        calls = []
        
        for match in matches:
            captures = match[1]
            
            method = None
            full_expr = None
            
            if call_type == "member_calls":
                for capture_name, nodes in captures.items():
                    for node_item in nodes:
                        if capture_name == "method":
                            method = self.extract_text(node_item, source_code)
                        elif capture_name == "full_expression":
                            full_expr = self.extract_text(node_item, source_code)
                            full_expr = "".join(full_expr.split())
                            
            elif call_type == "direct_calls":
                for capture_name, nodes in captures.items():
                    for node_item in nodes:
                        if capture_name == "function":
                            method = self.extract_text(node_item, source_code)
                        elif capture_name == "full_expression":
                            full_expr = self.extract_text(node_item, source_code)
                            full_expr = "".join(full_expr.split())
            
            if method and method not in self.common_methods:
                calls.append(FuncCallEntity(
                    method=method,
                    expr=full_expr
                ))
        
        return calls
    

