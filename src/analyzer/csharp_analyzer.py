from typing import List, Dict, Any
from tree_sitter import Query, QueryCursor
from src.analyzer.base_language_analyzer import BaseLanguageAnalyzer

class CSharpAnalyzer(BaseLanguageAnalyzer):
    """C# 語言分析器"""
    
    def __init__(self):
        super().__init__("csharp")
        self.common_methods = [
            "GetHashCode", "Equals", "ToString", "ToInt", "GetType",
            "Dispose", "Close", "Finalize", "Clone", "Add", 
            "AddRange", "Clear", "Contains", "CopyTo", "Remove", 
            "RemoveAt", "Insert", "InsertRange", "IndexOf", "LastIndexOf", 
            "Sort", "Reverse", "Where", "Select", "SelectMany", 
            "OrderBy", "OrderByDescending", "ThenBy", "ThenByDescending", "GroupBy", 
            "Join", "GroupJoin", "Distinct", "Skip", "SkipWhile", 
            "Take", "TakeWhile", "ToList", "ToArray", "ToDictionary", 
            "ToLookup", "First", "FirstOrDefault", "Single", "SingleOrDefault", 
            "Last", "LastOrDefault", "Any", "All", "Count", 
            "LongCount", "Sum", "Average", "Max", "Min", 
            "Aggregate", "ElementAt", "ElementAtOrDefault", "SequenceEqual", "Contains", 
            "DefaultIfEmpty", "Concat", "Union", "Intersect", "Except",
            "Zip", "Chunk", "Step", "IsNullOrEmpty", "IsNullOrWhiteSpace",
            "GetEnumerator", "SaveChangesAsync", "Regex", "int", "string", 
            "bool", "float", "double", "decimal", "DateTime", 
            "TimeSpan", "Guid", "List", "Dictionary", "HashSet", 
            "Queue", "Stack", "Array", "IEnumerable", "IEnumerator",
            "IQueryable", "ICollection", "IList", "IDictionary", "IReadOnlyList", 
            "IReadOnlyCollection", "IAsyncEnumerable", "IAsyncEnumerator", "Ok", "nameof", "Enum", "GetValues", "MethodBase", "GetCurrentMethod", "NotFound", "BadRequest"
        ]
        
        self.queries = {
            "function_with_calls": """
                (method_declaration 
                    name: (identifier) @function_name
                    body: (block) @function_body
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
            """,
            "functions": """
                (method_declaration name: (identifier) @name)
            """,
            "classes": """
                (class_declaration name: (identifier) @name)
            """,
            "interfaces": """
                (interface_declaration name: (identifier) @name)
            """
        }
    
    def analyze_member_calls(self, tree, source_code: bytes) -> List[Dict]:
        query = Query(self.lang, self.queries["member_calls"])
        cursor = QueryCursor(query)
        matches = cursor.matches(tree.root_node)
        
        calls = []
        seen_signatures = set()
        
        for match in matches:
            captures = match[1]
            
            call_info = {}
            receiver = None
            method = None
            full_expr = None
            
            for capture_name, nodes in captures.items():
                for node in nodes:
                    if capture_name == "receiver":
                        receiver = self.extract_text(node, source_code)
                    elif capture_name == "method":
                        method = self.extract_text(node, source_code)
                    elif capture_name == "full_expression":
                        full_expr = self.extract_text(node, source_code)
                        full_expr = "".join(full_expr.split())
            
            if method and method not in self.common_methods:
                signature = f"{receiver}.{method}" if receiver else method
                
                if signature not in seen_signatures:
                    seen_signatures.add(signature)
                    
                    call_info = {
                        "method": method,
                        "receiver": receiver,
                        "full_expression": full_expr
                    }
                    
                    calls.append(call_info)
        
        return calls
    
    def analyze_function_calls(self, tree, source_code: bytes) -> Dict[str, List[Dict]]:
        """分析每個函數內的調用"""
        query = Query(self.lang, self.queries["function_with_calls"])
        cursor = QueryCursor(query)
        matches = cursor.matches(tree.root_node)
        
        function_calls = {}
        
        for match in matches:
            captures = match[1]  # captures 是 dict: {capture_name: [nodes]}
            
            function_name = None
            function_body = None
            
            if "function_name" in captures:
                for node_item in captures["function_name"]:
                    function_name = self.extract_text(node_item, source_code)
                    break  # 取第一個
            
            if "function_body" in captures:
                for node_item in captures["function_body"]:
                    function_body = node_item
                    break  # 取第一個
            
            if function_name and function_body:
                # 分析這個函數體內的調用
                calls_in_function = []
                
                # 在函數體內查找成員調用
                member_calls = self.find_calls_in_node(function_body, source_code, "member_calls")
                calls_in_function.extend(member_calls)
                
                # 在函數體內查找直接調用
                direct_calls = self.find_calls_in_node(function_body, source_code, "direct_calls")
                calls_in_function.extend(direct_calls)
                
                if calls_in_function:  # 只記錄有調用的函數
                    function_calls[function_name] = calls_in_function
        
        return function_calls
    
    def find_calls_in_node(self, node, source_code: bytes, call_type: str) -> List[Dict]:
        """在指定節點內查找調用"""
        query = Query(self.lang, self.queries[call_type])
        cursor = QueryCursor(query)
        matches = cursor.matches(node)
        
        calls = []
        seen_methods = set()
        
        for match in matches:
            captures = match[1]  # captures 是 dict: {capture_name: [nodes]}
            
            if call_type == "member_calls":
                method = None
                full_expr = None
                
                if "method" in captures:
                    for node_item in captures["method"]:
                        method = self.extract_text(node_item, source_code)
                        break  # 取第一個
                
                if "full_expression" in captures:
                    for node_item in captures["full_expression"]:
                        full_expr = self.extract_text(node_item, source_code)
                        full_expr = "".join(full_expr.split())
                        break  # 取第一個
                
                if method and method not in self.common_methods and method not in seen_methods:
                    seen_methods.add(method)
                    calls.append({
                        "method": method,
                        "expr": full_expr
                    })
            
            elif call_type == "direct_calls":
                func_name = None
                full_expr = None
                
                # 修正：正確處理 captures
                if "function" in captures:
                    for node_item in captures["function"]:
                        func_name = self.extract_text(node_item, source_code)
                        break  # 取第一個
                
                if "full_expression" in captures:
                    for node_item in captures["full_expression"]:
                        full_expr = self.extract_text(node_item, source_code)
                        full_expr = "".join(full_expr.split())
                        break  # 取第一個
                
                if func_name and func_name not in self.common_methods and func_name not in seen_methods:
                    seen_methods.add(func_name)
                    calls.append({
                        "method": func_name,
                        "expr": full_expr
                    })
        
        return calls
    
    def analyze_direct_calls(self, tree, source_code: bytes) -> List[Dict]:
        query = Query(self.lang, self.queries["direct_calls"])
        cursor = QueryCursor(query)
        matches = cursor.matches(tree.root_node)
        
        calls = []
        seen_functions = set()
        
        for match in matches:
            captures = match[1]
            
            func_name = None
            full_expr = None
            
            # 先提取所有 capture 的內容
            for capture_name, nodes in captures.items():
                for node in nodes:
                    if capture_name == "function":
                        func_name = self.extract_text(node, source_code)
                    elif capture_name == "full_expression":
                        full_expr = self.extract_text(node, source_code)
                        full_expr = "".join(full_expr.split())
            
            if func_name and func_name not in self.common_methods and func_name not in seen_functions:
                seen_functions.add(func_name)
                
                calls.append({
                    "method": func_name,
                    "full_expression": full_expr
                })
        
        return calls
    
    def extract_symbols(self, tree, source_code: bytes, symbol_type: str) -> List[str]:
        """提取函數或類名"""
        query = Query(self.lang, self.queries[symbol_type])
        cursor = QueryCursor(query)
        matches = cursor.matches(tree.root_node)
        
        symbols = set()
        for match in matches:
            captures = match[1]
            for capture_name, nodes in captures.items():
                if capture_name == "name":
                    for node in nodes:
                        symbol = self.extract_text(node, source_code)
                        symbols.add(symbol)
        
        return sorted(list(symbols))
    
    def analyze_file(self, content: str) -> Dict[str, Any]:
        code_bytes = content.encode("utf-8")
        tree = self.parser.parse(code_bytes)
        
        # 分析函數
        function_calls = self.analyze_function_calls(tree, code_bytes)
        
        # 提取函數、類和介面
        functions = self.extract_symbols(tree, code_bytes, "functions")
        classes = self.extract_symbols(tree, code_bytes, "classes")
        interfaces = self.extract_symbols(tree, code_bytes, "interfaces")
        
        # 提取所有調用的簡單列表（用於向後兼容）
        all_calls = []
        for func_name, calls in function_calls.items():
            for call in calls:
                if call['method'] not in all_calls:
                    all_calls.append(call['method'])
        
        return {
            'func': functions,
            'cls': classes,
            'interfaces': interfaces,
            'calls': all_calls,
            'fcalls': function_calls 
        }
