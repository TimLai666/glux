"""
類型檢查器模塊
負責檢查表達式和語句的類型正確性，以及類型推導
"""

from typing import List, Dict, Any, Optional, Union, Set
import logging

from ..parser import ast_nodes
from ..type_system.type_system import TypeSystem
from ..type_system.type_defs import GluxType, TypeKind
from ..utils.symbol_table import SymbolTable, SymbolKind
from ..lexer.lexer import TokenType


class TypeChecker:
    """
    類型檢查器類
    負責檢查表達式和語句的類型正確性，以及類型推導
    """
    
    def __init__(self, symbol_table: SymbolTable):
        """
        初始化類型檢查器
        
        Args:
            symbol_table: 符號表
        """
        self.symbol_table = symbol_table
        self.errors = []
        self.warnings = []
        self.logger = logging.getLogger("TypeChecker")
        
        # 緩存表達式類型
        self.expr_types: Dict[ast_nodes.Expression, GluxType] = {}
    
    def check_declaration(self, decl: ast_nodes.Declaration):
        """
        檢查頂層宣告的類型正確性
        
        Args:
            decl: 宣告節點
        """
        if isinstance(decl, ast_nodes.FunctionDeclaration):
            self._check_function_declaration(decl)
        elif isinstance(decl, ast_nodes.StructDeclaration):
            self._check_struct_declaration(decl)
        elif isinstance(decl, ast_nodes.VarDeclaration):
            self._check_var_declaration(decl)
        elif isinstance(decl, ast_nodes.ConstDeclaration):
            self._check_const_declaration(decl)
    
    def _check_function_declaration(self, func: ast_nodes.FunctionDeclaration):
        """
        檢查函數宣告的類型正確性
        
        Args:
            func: 函數宣告節點
        """
        # 設置當前函數的返回類型
        return_type = None
        if func.return_type:
            return_type_name = func.return_type.name
            type_symbol = self.symbol_table.resolve_type(return_type_name)
            if not type_symbol:
                self.errors.append(f"未知返回類型 '{return_type_name}' 在函數 '{func.name}'")
            else:
                return_type = type_symbol.type_info
        
        self.symbol_table.set_current_function_return_type(return_type)
        
        # 創建函數作用域
        self.symbol_table.enter_scope(f"function {func.name}")
        
        # 檢查參數
        for param in func.params:
            param_type = None
            if param.type_annotation:
                param_type_name = param.type_annotation.name
                type_symbol = self.symbol_table.resolve_type(param_type_name)
                if not type_symbol:
                    self.errors.append(f"未知參數類型 '{param_type_name}' 於參數 '{param.name}' 在函數 '{func.name}'")
                else:
                    param_type = type_symbol.type_info
            
            # 在函數作用域中定義參數
            self.symbol_table.define(
                param.name, 
                SymbolKind.PARAMETER,
                param_type,
                is_mutable=True,
                is_initialized=True
            )
        
        # 檢查函數體
        if isinstance(func.body, ast_nodes.BlockStatement):
            # 處理 BlockStatement
            for stmt in func.body.statements:
                self._check_statement(stmt)
        else:
            # 處理語句列表
            for stmt in func.body:
                self._check_statement(stmt)
        
        # 離開函數作用域
        self.symbol_table.exit_scope()
        
        # 清除當前函數返回類型
        self.symbol_table.set_current_function_return_type(None)
    
    def _check_struct_declaration(self, struct: ast_nodes.StructDeclaration):
        """
        檢查結構體宣告的類型正確性
        
        Args:
            struct: 結構體宣告節點
        """
        # 檢查結構體欄位類型
        for field in struct.fields:
            if field.type_annotation:
                field_type_name = field.type_annotation.name
                type_symbol = self.symbol_table.resolve_type(field_type_name)
                if not type_symbol:
                    self.errors.append(f"未知欄位類型 '{field_type_name}' 於欄位 '{field.name}' 在結構體 '{struct.name}'")
    
    def _check_var_declaration(self, var: ast_nodes.VarDeclaration):
        """
        檢查變數宣告的類型正確性
        
        Args:
            var: 變數宣告節點
        """
        # 獲取初始化表達式類型
        init_type = self._check_expression(var.value)
        
        # 檢查顯式類型標註
        if var.type_hint:
            if hasattr(var.type_hint, 'name'):
                var_type_name = var.type_hint.name
                type_symbol = self.symbol_table.resolve_type(var_type_name)
                if not type_symbol:
                    self.errors.append(f"未知變數類型 '{var_type_name}' 在變數 '{var.name}'")
                    return
                
                var_type = type_symbol.type_info
                
                # 檢查初始化表達式類型與宣告類型是否兼容
                if init_type and not TypeSystem.is_type_compatible(init_type.name, var_type.name):
                    self.errors.append(f"類型不兼容: 無法將 '{init_type.name}' 類型賦值給 '{var_type.name}' 類型的變數 '{var.name}'")
            else:
                # 如果 type_hint 不是一個有 name 屬性的對象（例如它是一個 Number 對象）
                # 我們將使用初始化表達式的類型
                if not init_type:
                    self.errors.append(f"無法推斷變數 '{var.name}' 的類型")
                    return
                var_type = init_type
                self.warnings.append(f"變數 '{var.name}' 的類型標註格式不正確，使用推導類型 '{var_type.name}'")
        else:
            # 如果沒有類型標註，使用初始化表達式類型
            if not init_type:
                self.errors.append(f"無法推斷變數 '{var.name}' 的類型")
                return
            
            var_type = init_type
        
        # 更新符號類型
        symbol = self.symbol_table.resolve(var.name)
        if symbol:
            symbol.type_info = var_type
            symbol.is_initialized = True
    
    def _check_const_declaration(self, const: ast_nodes.ConstDeclaration):
        """
        檢查常數宣告的類型正確性
        
        Args:
            const: 常數宣告節點
        """
        # 獲取初始化表達式類型
        init_type = self._check_expression(const.value)
        
        # 檢查顯式類型標註
        if const.type_hint:
            const_type_name = const.type_hint.name
            type_symbol = self.symbol_table.resolve_type(const_type_name)
            if not type_symbol:
                self.errors.append(f"未知常數類型 '{const_type_name}' 在常數 '{const.name}'")
                return
            
            const_type = type_symbol.type_info
            
            # 檢查初始化表達式類型與宣告類型是否兼容
            if init_type and not TypeSystem.is_type_compatible(init_type.name, const_type.name):
                self.errors.append(f"類型不兼容: 無法將 '{init_type.name}' 類型賦值給 '{const_type.name}' 類型的常數 '{const.name}'")
        else:
            # 如果沒有類型標註，使用初始化表達式類型
            if not init_type:
                self.errors.append(f"無法推斷常數 '{const.name}' 的類型")
                return
            
            const_type = init_type
        
        # 更新符號類型
        symbol = self.symbol_table.resolve(const.name)
        if symbol:
            symbol.type_info = const_type
            symbol.is_initialized = True
    
    def _check_statement(self, stmt):
        """
        檢查語句的類型正確性
        
        Args:
            stmt: 語句節點
        """
        if isinstance(stmt, ast_nodes.ExpressionStatement):
            self._check_expression(stmt.expression)
        elif isinstance(stmt, ast_nodes.BlockStatement):
            self.symbol_table.enter_scope("block")
            for sub_stmt in stmt.statements:
                self._check_statement(sub_stmt)
            self.symbol_table.exit_scope()
        elif isinstance(stmt, ast_nodes.UnsafeBlockStatement):
            self._check_unsafe_block_statement(stmt)
        elif isinstance(stmt, ast_nodes.IfStatement):
            self._check_if_statement(stmt)
        elif isinstance(stmt, ast_nodes.WhileStatement):
            self._check_while_statement(stmt)
        elif isinstance(stmt, ast_nodes.ForStatement):
            self._check_for_statement(stmt)
        elif isinstance(stmt, ast_nodes.ReturnStatement):
            self._check_return_statement(stmt)
        elif isinstance(stmt, ast_nodes.VarDeclaration):
            self._check_var_declaration(stmt)
        elif isinstance(stmt, ast_nodes.ConstDeclaration):
            self._check_const_declaration(stmt)
    
    def _check_unsafe_block_statement(self, stmt: ast_nodes.UnsafeBlockStatement):
        """
        檢查 unsafe 區塊語句的類型正確性
        
        Args:
            stmt: unsafe 區塊語句節點
        """
        # 標記進入 unsafe 區塊
        self.symbol_table.enter_unsafe_block()
        
        # 進入作用域
        self.symbol_table.enter_scope("unsafe")
        
        # 檢查區塊中的每個語句
        for sub_stmt in stmt.statements:
            self._check_statement(sub_stmt)
        
        # 離開作用域
        self.symbol_table.exit_scope()
        
        # 標記離開 unsafe 區塊
        self.symbol_table.exit_unsafe_block()
    
    def _check_if_statement(self, stmt: ast_nodes.IfStatement):
        """
        檢查if語句的類型正確性
        
        Args:
            stmt: if語句節點
        """
        # 檢查條件表達式類型
        cond_type = self._check_expression(stmt.condition)
        if cond_type and cond_type.name != "bool":
            self.errors.append(f"If條件表達式必須是布爾類型，得到的是 '{cond_type.name}'")
        
        # 檢查then分支
        self.symbol_table.enter_scope("if-then")
        for sub_stmt in stmt.then_branch:
            self._check_statement(sub_stmt)
        self.symbol_table.exit_scope()
        
        # 檢查else分支
        if stmt.else_branch:
            self.symbol_table.enter_scope("if-else")
            for sub_stmt in stmt.else_branch:
                self._check_statement(sub_stmt)
            self.symbol_table.exit_scope()
    
    def _check_while_statement(self, stmt: ast_nodes.WhileStatement):
        """
        檢查while循環的類型正確性
        
        Args:
            stmt: while循環節點
        """
        # 檢查條件表達式類型
        cond_type = self._check_expression(stmt.condition)
        if cond_type and cond_type.name != "bool":
            self.errors.append(f"While條件表達式必須是布爾類型，得到的是 '{cond_type.name}'")
        
        # 檢查循環體
        self.symbol_table.enter_loop()
        self.symbol_table.enter_scope("while")
        for sub_stmt in stmt.body:
            self._check_statement(sub_stmt)
        self.symbol_table.exit_scope()
        self.symbol_table.exit_loop()
    
    def _check_for_statement(self, stmt: ast_nodes.ForStatement):
        """
        檢查for循環的類型正確性
        
        Args:
            stmt: for循環節點
        """
        # 檢查可迭代對象表達式類型
        iter_type = self._check_expression(stmt.iterable)
        element_type = None
        
        # 確定元素類型
        if iter_type:
            if iter_type.is_array() or iter_type.is_list():
                element_type = iter_type.element_type
            elif iter_type.name.startswith("[]"):  # 數組類型
                element_type_name = iter_type.name[2:]
                type_symbol = self.symbol_table.resolve_type(element_type_name)
                if type_symbol:
                    element_type = type_symbol.type_info
            elif iter_type.name == "string":
                # 字符串迭代產生字符
                element_type = TypeSystem.get_type("char")
            elif iter_type.name.startswith("map<"):
                # Map迭代產生鍵
                element_type = iter_type.key_type
        
        if not element_type:
            self.errors.append(f"For循環的可迭代對象必須是可迭代類型，得到的是 '{iter_type.name if iter_type else 'unknown'}'")
            element_type = TypeSystem.get_type("any")  # 使用any作為後備
        
        # 進入循環體作用域
        self.symbol_table.enter_loop()
        self.symbol_table.enter_scope("for")
        
        # 在作用域中定義迭代變數
        if isinstance(stmt.iterator, list):
            if len(stmt.iterator) > 2:
                self.errors.append(f"For循環最多支持兩個迭代變數，得到了 {len(stmt.iterator)} 個")
            
            if len(stmt.iterator) >= 1:
                # 第一個迭代變數 (鍵或索引或值)
                self.symbol_table.define_variable(stmt.iterator[0], element_type, True, True)
            
            if len(stmt.iterator) >= 2 and iter_type and iter_type.is_map():
                # 第二個迭代變數 (值，僅用於map)
                self.symbol_table.define_variable(stmt.iterator[1], iter_type.value_type, True, True)
        else:
            # 單個迭代變數
            self.symbol_table.define_variable(stmt.iterator, element_type, True, True)
        
        # 檢查循環體
        for sub_stmt in stmt.body:
            self._check_statement(sub_stmt)
        
        # 離開作用域
        self.symbol_table.exit_scope()
        self.symbol_table.exit_loop()
    
    def _check_return_statement(self, stmt: ast_nodes.Return):
        """
        檢查return語句的類型正確性
        
        Args:
            stmt: return語句節點
        """
        # 獲取當前函數的返回類型
        expected_type = self.symbol_table.get_current_function_return_type()
        
        if not stmt.value and expected_type and expected_type.name != "void":
            self.errors.append(f"函數期望返回 '{expected_type.name}' 類型，但無返回值")
            return
        
        if not stmt.value:
            return
        
        # 檢查返回表達式類型
        actual_type = self._check_expression(stmt.value)
        
        if expected_type and actual_type:
            if not TypeSystem.is_type_compatible(actual_type.name, expected_type.name):
                self.errors.append(
                    f"返回類型不匹配: 期望 '{expected_type.name}'，得到 '{actual_type.name}'"
                )
    
    def _check_binary_expr(self, expr: ast_nodes.BinaryExpr) -> Optional[GluxType]:
        """
        檢查二元表達式
        
        Args:
            expr: 二元表達式節點
            
        Returns:
            表達式類型或None（如果有錯誤）
        """
        # 檢查左右操作數
        left_type = self._check_expression(expr.left)
        right_type = self._check_expression(expr.right)
        
        if not left_type or not right_type:
            return None
        
        # 檢查是否為連續比較的一部分
        if hasattr(expr, 'is_part_of_chain') and expr.is_part_of_chain:
            # 連續比較的每一部分必須返回布爾值
            return TypeSystem.get_type("bool")
        
        # 獲取二元運算符
        op = getattr(expr, 'op', getattr(expr, 'operator', None))
        if op is None:
            self.errors.append(f"二元表達式缺少運算符")
            return None
            
        # 根據運算符類型處理
        if op in ['==', '!=', '<', '<=', '>', '>=']:
            # 比較運算符 - 檢查操作數類型是否可比較
            if not self._are_comparable_types(left_type.name, right_type.name):
                self.errors.append(f"無法比較類型 '{left_type.name}' 和 '{right_type.name}'")
                return None
            
            # 比較運算符返回布爾值
            return TypeSystem.get_type("bool")
        
        elif op in ['+', '-', '*', '/', '%']:
            # 算術運算符
            
            # 特殊處理: 字符串連接
            if op == '+' and (left_type.name == 'string' or right_type.name == 'string'):
                # 字符串連接 - 任何類型都可以與字符串連接，結果是字符串
                return TypeSystem.get_type("string")
            
            # 數值運算 - 檢查操作數是否為數值類型
            if not self._is_numeric_type(left_type.name) or not self._is_numeric_type(right_type.name):
                self.errors.append(f"運算符 '{op}' 要求數值類型，但得到 '{left_type.name}' 和 '{right_type.name}'")
                return None
            
            # 獲取共同類型
            common_type_name = TypeSystem.get_common_type(left_type.name, right_type.name)
            if not common_type_name:
                self.errors.append(f"無法找到 '{left_type.name}' 和 '{right_type.name}' 的共同類型")
                return None
            
            return TypeSystem.get_type(common_type_name)
        
        elif op in ['&', '|', '^', '<<', '>>']:
            # 位元運算符 - 只適用於整數類型
            if not self._is_integer_type(left_type.name) or not self._is_integer_type(right_type.name):
                self.errors.append(f"位元運算符 '{op}' 要求整數類型，但得到 '{left_type.name}' 和 '{right_type.name}'")
                return None
            
            # 位移運算符需要在 unsafe 區塊中
            if op in ['<<', '>>'] and not self.symbol_table.is_in_unsafe_block():
                self.errors.append(f"位移運算符 '{op}' 必須在 unsafe 區塊中使用")
                return None
            
            # 位元運算返回操作數的共同類型
            common_type_name = TypeSystem.get_common_type(left_type.name, right_type.name)
            if not common_type_name:
                self.errors.append(f"無法找到 '{left_type.name}' 和 '{right_type.name}' 的共同類型")
                return None
            
            return TypeSystem.get_type(common_type_name)
        
        else:
            self.errors.append(f"未知的二元運算符: '{op}'")
            return None
            
    def _check_comparison_chain(self, expr: ast_nodes.ComparisonChain) -> Optional[GluxType]:
        """
        檢查連續比較表達式，例如 0 < x < 10
        
        Args:
            expr: 連續比較表達式節點
            
        Returns:
            表達式類型（布爾型）或None（如果有錯誤）
        """
        # 檢查左側表達式
        left_type = self._check_expression(expr.left)
        if not left_type:
            return None
        
        # 檢查每個比較
        last_type = left_type
        for op, right in expr.comparisons:
            right_type = self._check_expression(right)
            if not right_type:
                return None
            
            # 檢查操作數類型是否可比較
            if not self._are_comparable_types(last_type.name, right_type.name):
                self.errors.append(f"無法比較類型 '{last_type.name}' 和 '{right_type.name}'")
                return None
            
            # 更新最後看到的類型
            last_type = right_type
        
        # 連續比較返回布爾值
        return TypeSystem.get_type("bool")

    def _check_expression(self, expr) -> Optional[GluxType]:
        """
        檢查表達式
        
        Args:
            expr: 表達式節點
            
        Returns:
            表達式類型或None（如果有錯誤）
        """
        # 處理 None 表達式
        if expr is None:
            self.errors.append(f"表達式為 None")
            return None
            
        # 檢查表達式是否已經被緩存
        if expr in self.expr_types:
            return self.expr_types[expr]
        
        # 根據表達式類型進行檢查
        if isinstance(expr, ast_nodes.Literal):
            result_type = self._check_literal(expr)
        elif isinstance(expr, ast_nodes.Variable):
            result_type = self._check_variable(expr)
        elif isinstance(expr, ast_nodes.BinaryExpr):
            result_type = self._check_binary_expr(expr)
        elif isinstance(expr, ast_nodes.UnaryExpr):
            result_type = self._check_unary_expr(expr)
        elif isinstance(expr, ast_nodes.CallExpr):
            result_type = self._check_call_expr(expr)
        elif isinstance(expr, ast_nodes.MemberAccess):
            result_type = self._check_member_access(expr)
        elif isinstance(expr, ast_nodes.IndexAccess):
            result_type = self._check_index_access(expr)
        elif isinstance(expr, ast_nodes.AssignmentExpr):
            result_type = self._check_assignment_expr(expr)
        elif isinstance(expr, ast_nodes.ComparisonChain):
            result_type = self._check_comparison_chain(expr)
        elif isinstance(expr, ast_nodes.GroupingExpression):
            result_type = self._check_expression(expr.expression)
        elif isinstance(expr, ast_nodes.ConditionalExpression):
            result_type = self._check_conditional_expr(expr)
        elif isinstance(expr, ast_nodes.Number):
            # 直接處理 Number 節點
            result_type = self._check_number_literal(expr)
        elif isinstance(expr, ast_nodes.Float):
            # 直接處理 Float 節點
            result_type = self._check_float_literal(expr)
        elif isinstance(expr, ast_nodes.StringLiteral):
            # 直接處理 StringLiteral 節點
            result_type = TypeSystem.get_type("string")
        elif isinstance(expr, ast_nodes.Boolean) or isinstance(expr, ast_nodes.BooleanLiteral):
            # 直接處理 Boolean 節點
            result_type = TypeSystem.get_type("bool")
        else:
            self.errors.append(f"未知的表達式類型: {type(expr).__name__}")
            return None
        
        # 緩存表達式類型
        if result_type:
            self.expr_types[expr] = result_type
        
        return result_type
    
    def _check_literal(self, literal: ast_nodes.Literal) -> GluxType:
        """
        檢查字面量的類型
        
        Args:
            literal: 字面量節點
            
        Returns:
            字面量類型
        """
        if isinstance(literal, ast_nodes.Number):
            # 根據整數大小選擇適當的類型
            value = int(literal.value)
            if -128 <= value <= 127:
                return TypeSystem.get_type("i8")
            elif -32768 <= value <= 32767:
                return TypeSystem.get_type("i16")
            elif -2147483648 <= value <= 2147483647:
                return TypeSystem.get_type("i32")
            else:
                return TypeSystem.get_type("i64")
        elif isinstance(literal, ast_nodes.Float):
            # 目前使用f32作為預設浮點類型
            return TypeSystem.get_type("f32")
        elif isinstance(literal, ast_nodes.StringLiteral):
            return TypeSystem.get_type("string")
        elif isinstance(literal, ast_nodes.Boolean) or isinstance(literal, ast_nodes.BooleanLiteral):
            return TypeSystem.get_type("bool")
        elif hasattr(literal, 'value_type'):
            # 向後兼容：處理舊版字面量格式
            if literal.value_type == "int":
                return TypeSystem.get_type("i32")
            elif literal.value_type == "float":
                return TypeSystem.get_type("f32")
            elif literal.value_type == "string":
                return TypeSystem.get_type("string")
            elif literal.value_type == "bool":
                return TypeSystem.get_type("bool")
            elif literal.value_type == "char":
                return TypeSystem.get_type("char")
            elif literal.value_type == "null":
                return TypeSystem.get_type("null")
        
        # 未知類型
        self.errors.append(f"未知的字面量類型: {type(literal).__name__}")
        return TypeSystem.get_type("any")
    
    def _check_variable(self, var: ast_nodes.Variable) -> Optional[GluxType]:
        """
        檢查變數引用的類型
        
        Args:
            var: 變數節點
            
        Returns:
            變數類型，如果變數未定義則返回None
        """
        # 特殊處理內建的類型轉換函數，包括 string, int, float, bool 等
        # 這些名稱既是類型名，也是函數名
        conversion_functions = ['string', 'int', 'float', 'bool']
        if var.name in conversion_functions:
            # 為內建的轉換函數創建函數類型
            return_type = TypeSystem.get_type(var.name)
            param_type = TypeSystem.get_type("any")
            
            # 創建函數類型
            func_type = GluxType(f"{var.name}_conversion", TypeKind.FUNCTION)
            func_type.params = [param_type]
            func_type.param_types = [param_type]  # 同時設置 param_types 屬性
            func_type.param_names = ["value"]
            func_type.return_type = return_type
            
            # 將函數類型設為可調用
            func_type.is_function = lambda: True
            
            return func_type
        
        # 查找變數符號
        symbol = self.symbol_table.resolve(var.name)
        if not symbol:
            self.errors.append(f"未定義的變數 '{var.name}'")
            return None
        
        # 標記變數為已使用
        self.symbol_table.mark_symbol_used(var.name)
        
        # 檢查是否已初始化
        if not symbol.is_initialized and symbol.kind != SymbolKind.PARAMETER:
            self.warnings.append(f"變數 '{var.name}' 可能在初始化前使用")
        
        return symbol.type_info
    
    def _check_unary_expr(self, expr: ast_nodes.UnaryExpr) -> Optional[GluxType]:
        """
        檢查一元表達式
        
        Args:
            expr: 一元表達式節點
            
        Returns:
            表達式類型或None（如果有錯誤）
        """
        # 檢查操作數
        operand_type = self._check_expression(expr.operand)
        
        if not operand_type:
            return None
        
        # 根據運算符類型檢查
        if expr.op == '+' or expr.op == '-':
            # 一元加減法 - 檢查操作數是否為數值類型
            if not self._is_numeric_type(operand_type.name):
                self.errors.append(f"一元運算符 '{expr.op}' 要求數值類型，但得到 '{operand_type.name}'")
                return None
            
            return operand_type
        
        elif expr.op == '!':
            # 邏輯否定 - 操作數必須是布爾類型
            if operand_type.name != 'bool':
                self.errors.append(f"一元運算符 '{expr.op}' 要求布爾類型，但得到 '{operand_type.name}'")
                return None
            
            return TypeSystem.get_type("bool")
        
        elif expr.op == '~':
            # 按位取反 - 操作數必須是整數類型
            if not self._is_integer_type(operand_type.name):
                self.errors.append(f"一元運算符 '{expr.op}' 要求整數類型，但得到 '{operand_type.name}'")
                return None
            
            # 按位取反需要在 unsafe 區塊中
            if not self.symbol_table.is_in_unsafe_block():
                self.errors.append(f"按位取反運算符 '{expr.op}' 必須在 unsafe 區塊中使用")
                return None
            
            return operand_type
        
        else:
            self.errors.append(f"未知的一元運算符: '{expr.op}'")
            return None
    
    def _check_call_expr(self, expr: ast_nodes.CallExpr) -> Optional[GluxType]:
        """
        檢查函數調用表達式的類型
        
        Args:
            expr: 函數調用表達式節點
            
        Returns:
            函數返回類型
        """
        # 檢查被調用對象類型
        callee_type = self._check_expression(expr.callee)
        if not callee_type:
            return None
        
        # 獲取函數名稱
        func_name = None
        if isinstance(expr.callee, ast_nodes.Variable):
            func_name = expr.callee.name
        
        # 檢查是否為函數類型
        if not callee_type.is_function():
            self.errors.append(f"無法調用非函數類型 '{callee_type.name}'")
            return None
        
        # 檢查參數個數
        if callee_type.param_types and len(expr.arguments) != len(callee_type.param_types):
            self.errors.append(
                f"函數調用 '{func_name or 'anonymous'}' 參數數量不匹配："
                f"期望 {len(callee_type.param_types)} 個，得到 {len(expr.arguments)} 個"
            )
        
        # 檢查參數類型
        for i, arg in enumerate(expr.arguments):
            if i >= len(callee_type.param_types):
                break
            
            arg_type = self._check_expression(arg)
            if arg_type and callee_type.param_types[i]:
                if not TypeSystem.is_type_compatible(arg_type.name, callee_type.param_types[i].name):
                    param_name = callee_type.param_names[i] if callee_type.param_names and i < len(callee_type.param_names) else f"#{i+1}"
                    self.errors.append(
                        f"函數調用 '{func_name or 'anonymous'}' 參數類型不匹配："
                        f"參數 '{param_name}' 期望類型 '{callee_type.param_types[i].name}'，"
                        f"得到 '{arg_type.name}'"
                    )
        
        # 返回函數返回類型
        return callee_type.return_type
    
    def _check_member_access(self, expr: ast_nodes.MemberAccess) -> Optional[GluxType]:
        """
        檢查成員訪問表達式的類型
        
        Args:
            expr: 成員訪問表達式節點
            
        Returns:
            成員類型
        """
        # 檢查對象類型
        obj_type = self._check_expression(expr.object)
        if not obj_type:
            return None
        
        # 檢查結構體類型
        if obj_type.is_struct():
            # 獲取結構體欄位
            if not obj_type.field_names or not obj_type.field_types:
                self.errors.append(f"類型 '{obj_type.name}' 沒有欄位信息")
                return None
            
            # 查找欄位
            try:
                field_index = obj_type.field_names.index(expr.member)
                return obj_type.field_types[field_index]
            except ValueError:
                self.errors.append(f"結構體 '{obj_type.name}' 沒有名為 '{expr.member}' 的欄位")
                return None
        
        # 檢查模塊或命名空間
        if obj_type.name == "module" or obj_type.name == "namespace":
            # 在將來的實現中處理
            self.errors.append(f"尚未支持模塊或命名空間成員訪問")
            return None
        
        self.errors.append(f"類型 '{obj_type.name}' 不支持成員訪問操作")
        return None
    
    def _check_index_access(self, expr: ast_nodes.IndexAccess) -> Optional[GluxType]:
        """
        檢查索引訪問表達式的類型
        
        Args:
            expr: 索引訪問表達式節點
            
        Returns:
            索引結果類型
        """
        # 檢查對象類型
        obj_type = self._check_expression(expr.object)
        if not obj_type:
            return None
        
        # 檢查索引類型
        index_type = self._check_expression(expr.index)
        if index_type and not index_type.is_integer():
            self.errors.append(f"索引必須是整數類型，得到 '{index_type.name}'")
        
        # 數組類型
        if obj_type.is_array():
            return obj_type.element_type
        
        # 列表類型
        if obj_type.is_list():
            return obj_type.element_type
        
        # 字符串類型 (返回字符)
        if obj_type.name == "string":
            return TypeSystem.get_type("char")
        
        # 映射類型
        if obj_type.is_map():
            # 檢查鍵類型
            if index_type and obj_type.key_type and not TypeSystem.is_type_compatible(index_type.name, obj_type.key_type.name):
                self.errors.append(
                    f"映射索引類型不匹配: 期望 '{obj_type.key_type.name}'，得到 '{index_type.name}'"
                )
            
            return obj_type.value_type
        
        self.errors.append(f"類型 '{obj_type.name}' 不支持索引訪問操作")
        return None
    
    def _check_assignment_expr(self, expr: ast_nodes.AssignmentExpr) -> Optional[GluxType]:
        """
        檢查賦值表達式的類型
        
        Args:
            expr: 賦值表達式節點
            
        Returns:
            賦值結果類型（通常是左側變數的類型）
        """
        # 檢查左值和右值類型
        target_type = None
        
        # 變數賦值
        if isinstance(expr.target, ast_nodes.Variable):
            # 檢查變數是否已定義
            symbol = self.symbol_table.resolve(expr.target.name)
            if not symbol:
                self.errors.append(f"未定義的變數 '{expr.target.name}'")
                return None
            
            # 檢查變數是否為常量
            if symbol.kind == SymbolKind.CONST:
                self.errors.append(f"無法賦值給常量 '{expr.target.name}'")
                return None
            
            # 檢查變數是否為不可變變數
            if not symbol.is_mutable:
                self.errors.append(f"無法賦值給不可變變數 '{expr.target.name}'")
                return None
            
            target_type = symbol.type_info
            
            # 標記變數為已初始化
            self.symbol_table.mark_symbol_initialized(expr.target.name)
        
        # 成員賦值
        elif isinstance(expr.target, ast_nodes.MemberAccess):
            obj_type = self._check_expression(expr.target.object)
            if not obj_type:
                return None
            
            # 檢查是否為結構體類型
            if obj_type.is_struct():
                # 獲取結構體欄位
                if not obj_type.field_names or not obj_type.field_types:
                    self.errors.append(f"類型 '{obj_type.name}' 沒有欄位信息")
                    return None
                
                # 查找欄位
                try:
                    field_index = obj_type.field_names.index(expr.target.member)
                    target_type = obj_type.field_types[field_index]
                except ValueError:
                    self.errors.append(f"結構體 '{obj_type.name}' 沒有名為 '{expr.target.member}' 的欄位")
                    return None
            else:
                self.errors.append(f"類型 '{obj_type.name}' 不支持成員賦值操作")
                return None
        
        # 索引賦值
        elif isinstance(expr.target, ast_nodes.IndexAccess):
            obj_type = self._check_expression(expr.target.object)
            if not obj_type:
                return None
            
            # 檢查索引類型
            index_type = self._check_expression(expr.target.index)
            if index_type and not index_type.is_integer():
                self.errors.append(f"索引必須是整數類型，得到 '{index_type.name}'")
            
            # 數組類型
            if obj_type.is_array():
                target_type = obj_type.element_type
            
            # 列表類型
            elif obj_type.is_list():
                target_type = obj_type.element_type
            
            # 映射類型
            elif obj_type.is_map():
                # 檢查鍵類型
                if index_type and obj_type.key_type and not TypeSystem.is_type_compatible(index_type.name, obj_type.key_type.name):
                    self.errors.append(
                        f"映射索引類型不匹配: 期望 '{obj_type.key_type.name}'，得到 '{index_type.name}'"
                    )
                
                target_type = obj_type.value_type
            else:
                self.errors.append(f"類型 '{obj_type.name}' 不支持索引賦值操作")
                return None
        else:
            self.errors.append(f"無效的賦值目標")
            return None
        
        # 檢查右值類型
        value_type = self._check_expression(expr.value)
        if target_type and value_type:
            if not TypeSystem.is_type_compatible(value_type.name, target_type.name):
                self.errors.append(
                    f"賦值類型不匹配: 無法將 '{value_type.name}' 類型賦值給 '{target_type.name}' 類型"
                )
        
        return target_type
    
    def _check_number_literal(self, literal: ast_nodes.Number) -> GluxType:
        """處理數字字面量"""
        value = int(literal.value)
        if -128 <= value <= 127:
            return TypeSystem.get_type("i8")
        elif -32768 <= value <= 32767:
            return TypeSystem.get_type("i16")
        elif -2147483648 <= value <= 2147483647:
            return TypeSystem.get_type("i32")
        else:
            return TypeSystem.get_type("i64")
            
    def _check_float_literal(self, literal: ast_nodes.Float) -> GluxType:
        """處理浮點數字面量"""
        return TypeSystem.get_type("f32")

    def _is_numeric_type(self, type_name: str) -> bool:
        """
        檢查類型是否為數值類型
        
        Args:
            type_name: 類型名稱
            
        Returns:
            是否為數值類型
        """
        return TypeSystem.is_numeric_type(type_name)
    
    def _is_integer_type(self, type_name: str) -> bool:
        """
        檢查類型是否為整數類型
        
        Args:
            type_name: 類型名稱
            
        Returns:
            是否為整數類型
        """
        return TypeSystem.is_integer_type(type_name)
    
    def _are_comparable_types(self, left_type: str, right_type: str) -> bool:
        """
        檢查兩個類型是否可比較
        
        Args:
            left_type: 左側類型名稱
            right_type: 右側類型名稱
            
        Returns:
            兩個類型是否可比較
        """
        # 相同類型可以比較
        if left_type == right_type:
            return True
        
        # 數值類型可以互相比較
        if self._is_numeric_type(left_type) and self._is_numeric_type(right_type):
            return True
        
        # 其他情況不可比較
        return False

    def _check_conditional_expr(self, expr: ast_nodes.ConditionalExpression) -> Optional[GluxType]:
        """
        檢查三元運算符表達式的類型正確性
        
        Args:
            expr: 三元運算符表達式節點
            
        Returns:
            表達式類型或None（如果有錯誤）
        """
        # 檢查條件表達式，必須是布爾類型
        condition_type = self._check_expression(expr.condition)
        if condition_type and condition_type.name != "bool":
            self.errors.append(f"條件表達式必須是布爾類型，得到 '{condition_type.name}'")
        
        # 檢查 then 和 else 分支表達式
        then_type = self._check_expression(expr.then_expr)
        else_type = self._check_expression(expr.else_expr)
        
        # 如果任一分支為 None，則無法確定類型
        if not then_type or not else_type:
            return None
        
        # 嘗試找到兩個分支的共同類型
        common_type_name = TypeSystem.get_common_type(then_type.name, else_type.name)
        if not common_type_name:
            self.errors.append(f"三元運算符的兩個分支必須有共同類型，得到 '{then_type.name}' 和 '{else_type.name}'")
            return None
        
        # 返回共同類型
        return TypeSystem.get_type(common_type_name) 