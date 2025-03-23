class TypeChecker:
    """語義分析階段的型別檢查器"""
    
    def __init__(self):
        self.symbol_table = {}  # 符號表
        self.current_function = None
        self.error_count = 0
        
    def _infer_numeric_type(self, value):
        """根據數值自動推導最合適的數值型別"""
        if isinstance(value, int):
            # 對整數值，根據範圍選擇適當的int型別
            if -128 <= value <= 127:
                return "int8"
            elif -32768 <= value <= 32767:
                return "int16"
            elif -2147483648 <= value <= 2147483647:
                return "int32"
            else:
                return "int64"
        elif isinstance(value, float):
            # 對浮點數，暫時簡單處理，後期可增加精度判斷邏輯
            if abs(value) < 3.4e38 and len(str(value).split('.')[-1]) <= 7:
                return "float32"
            else:
                return "float64"
        else:
            # 非數值型別返回None
            return None
    
    def _infer_type_from_literal(self, node):
        """從字面量推導型別"""
        if isinstance(node, ast_nodes.NumberLiteral):
            if '.' in node.value:
                # 浮點數字面量
                value = float(node.value)
                return self._infer_numeric_type(value)
            else:
                # 整數字面量
                # 處理數字分隔符，如 1_000_000
                clean_value = node.value.replace('_', '')
                value = int(clean_value)
                return self._infer_numeric_type(value)
        elif isinstance(node, ast_nodes.StringLiteral):
            return "string"
        elif isinstance(node, ast_nodes.BooleanLiteral):
            return "bool"
        elif isinstance(node, ast_nodes.NullLiteral):
            return "null"
        else:
            return "unknown"
    
    def _is_type_compatible(self, source_type, target_type):
        """檢查源型別是否可以賦值給目標型別"""
        # 簡單情況：相同型別
        if source_type == target_type:
            return True
            
        # 數值型別的兼容性檢查
        numeric_types = ["int8", "int16", "int32", "int64", "float32", "float64"]
        if source_type in numeric_types and target_type in numeric_types:
            # 整數到浮點數的隱式轉換是允許的
            if source_type.startswith("int") and target_type.startswith("float"):
                return True
                
            # 同類型（整數或浮點數）間的向上轉換是允許的
            if source_type.startswith("int") and target_type.startswith("int"):
                source_size = int(source_type[3:])
                target_size = int(target_type[3:])
                return source_size <= target_size
                
            if source_type.startswith("float") and target_type.startswith("float"):
                source_size = int(source_type[5:])
                target_size = int(target_type[5:])
                return source_size <= target_size
                
        # 其他兼容性規則...
        
        return False
        
    def visit_var_declaration(self, node):
        """訪問變數聲明節點"""
        # 解析初始化表達式
        init_value = node.initializer.accept(self)
        
        # 如果沒有顯式指定型別，從初始值推導
        if node.var_type is None:
            inferred_type = self._infer_type_from_literal(node.initializer)
            node.var_type = inferred_type
        
        # 檢查初始值型別與變數型別是否兼容
        if not self._is_type_compatible(init_value, node.var_type):
            self._report_error(f"型別不兼容: 無法將 {init_value} 型別賦值給 {node.var_type} 型別變數 '{node.name}'")
        
        # 將變數添加到符號表
        self.symbol_table[node.name] = {
            "kind": "variable",
            "type": node.var_type,
            "is_constant": False
        }
        
        return node.var_type
        
    def visit_const_declaration(self, node):
        """訪問常數聲明節點"""
        # 解析初始化表達式
        init_value = node.initializer.accept(self)
        
        # 如果沒有顯式指定型別，從初始值推導
        if node.const_type is None:
            inferred_type = self._infer_type_from_literal(node.initializer)
            node.const_type = inferred_type
        
        # 檢查初始值型別與常數型別是否兼容
        if not self._is_type_compatible(init_value, node.const_type):
            self._report_error(f"型別不兼容: 無法將 {init_value} 型別賦值給 {node.const_type} 型別常數 '{node.name}'")
        
        # 將常數添加到符號表
        self.symbol_table[node.name] = {
            "kind": "constant",
            "type": node.const_type,
            "is_constant": True
        }
        
        return node.const_type
        
    def _report_error(self, message):
        """報告型別錯誤"""
        print(f"型別錯誤: {message}")
        self.error_count += 1 