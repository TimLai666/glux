"""
符號分析器模組
負責處理符號定義和作用域分析
"""

from typing import Dict, Set, List, Optional
import logging

from ..parser import ast_nodes
from ..type_system.type_system import TypeSystem
from ..type_system.type_defs import GluxType
from ..utils.symbol_table import SymbolTable, SymbolKind, Symbol


class SymbolAnalyzer:
    """
    符號分析器類
    負責處理符號定義和作用域分析，包括變數、常數、函數、類型等符號
    """
    
    def __init__(self, symbol_table: SymbolTable):
        """
        初始化符號分析器
        
        Args:
            symbol_table: 符號表
        """
        self.symbol_table = symbol_table
        self.errors = []
        self.warnings = []
        self.logger = logging.getLogger("SymbolAnalyzer")
        
        # 追蹤未使用的符號
        self.defined_symbols: Set[str] = set()
        self.used_symbols: Set[str] = set()
        
        # 定義內建函數
        self.defined_symbols.add("println")
        self.defined_symbols.add("print")
        self.defined_symbols.add("len")
        self.defined_symbols.add("sleep")
        self.defined_symbols.add("int")
        self.defined_symbols.add("float")
        self.defined_symbols.add("bool")
        self.defined_symbols.add("string")
        self.defined_symbols.add("copy")
        self.defined_symbols.add("error")
        self.defined_symbols.add("is_error")
    
    def analyze_module(self, module: ast_nodes.Module):
        """
        分析模組
        
        Args:
            module: 模組節點
        """
        # 第一輪：收集符號
        for decl in module.statements:
            self._collect_symbols(decl)
        
        # 第二輪：檢查符號引用
        for decl in module.statements:
            self._analyze_node(decl)
        
        # 檢查未使用的符號
        self._check_unused_symbols()
    
    def _collect_symbols(self, node: ast_nodes.ASTNode):
        """
        收集模塊中的符號
        這一步驟用於處理符號的前向引用，允許函數和類型在使用前宣告
        
        Args:
            node: AST節點
        """
        if isinstance(node, ast_nodes.FunctionDeclaration):
            # 預先宣告函數
            self._pre_declare_function(node)
        elif isinstance(node, ast_nodes.StructDeclaration):
            # 預先宣告結構體
            self._pre_declare_struct(node)
        # 其他類型的節點不需要預先宣告
    
    def _pre_declare_function(self, func: ast_nodes.FunctionDeclaration):
        """
        預先宣告函數符號 (用於實現函數互相呼叫)
        
        Args:
            func: 函數宣告節點
        """
        # 處理回傳型別
        return_type = None
        if func.return_type:
            type_name = func.return_type.name
            type_symbol = self.symbol_table.resolve_type(type_name)
            if type_symbol:
                return_type = type_symbol.type_info
            # 未定義的類型暫時忽略，等實際分析時再處理
        
        # 處理參數類型
        param_types = []
        param_names = []
        for param in func.params:
            param_type = None
            if param.type_hint:  # 改為使用type_hint
                type_name = param.type_hint.name
                type_symbol = self.symbol_table.resolve_type(type_name)
                if type_symbol:
                    param_type = type_symbol.type_info
                # 未定義的類型暫時忽略，等實際分析時再處理
            
            param_types.append(param_type)
            param_names.append(param.name)
        
        # 建立函數類型
        func_type = TypeSystem.create_function_type(return_type, param_types, param_names)
        
        # 在符號表中定義函數
        self.symbol_table.define(
            func.name,
            SymbolKind.FUNCTION,
            func_type,
            is_mutable=False,
            is_initialized=True
        )
        
        # 記錄已定義的符號
        self.defined_symbols.add(func.name)
    
    def _pre_declare_struct(self, struct: ast_nodes.StructDeclaration):
        """
        預先宣告結構體
        
        Args:
            struct: 結構體宣告節點
        """
        # 建立結構體類型，暫時不處理欄位
        struct_type = TypeSystem.create_struct_type(struct.name)
        
        # 在符號表中定義結構體類型
        self.symbol_table.define_type(struct.name, struct_type)
        
        # 記錄已定義的符號
        self.defined_symbols.add(struct.name)
    
    def _analyze_node(self, node: ast_nodes.ASTNode):
        """
        分析節點
        
        Args:
            node: AST節點
        """
        if isinstance(node, ast_nodes.FunctionDeclaration):
            self._analyze_function_declaration(node)
        elif isinstance(node, ast_nodes.StructDeclaration):
            self._analyze_struct_declaration(node)
        elif isinstance(node, ast_nodes.VarDeclaration):
            self._analyze_var_declaration(node)
        elif isinstance(node, ast_nodes.ConstDeclaration):
            self._analyze_const_declaration(node)
        elif isinstance(node, ast_nodes.ImportDeclaration):
            self._analyze_import_declaration(node)
        elif isinstance(node, ast_nodes.ExpressionStatement):
            self._analyze_statement(node)
        # 其他類型的節點
    
    def _analyze_function_declaration(self, func: ast_nodes.FunctionDeclaration):
        """
        分析函數宣告
        
        Args:
            func: 函數宣告節點
        """
        # 函數已在預宣告階段處理過，這裡主要處理函數體
        
        # 設置返回類型
        return_type = None
        if func.return_type:
            type_name = func.return_type.name
            type_symbol = self.symbol_table.resolve_type(type_name)
            if type_symbol:
                return_type = type_symbol.type_info
            else:
                self.errors.append(f"未知返回類型 '{type_name}' 在函數 '{func.name}'")
        
        self.symbol_table.set_current_function_return_type(return_type)
        
        # 進入函數作用域
        self.symbol_table.enter_scope(f"function {func.name}")
        
        # 定義參數
        for param in func.params:
            param_type = None
            if param.type_hint:
                type_name = param.type_hint.name
                type_symbol = self.symbol_table.resolve_type(type_name)
                if type_symbol:
                    param_type = type_symbol.type_info
                else:
                    self.errors.append(f"未知參數類型 '{type_name}' 於參數 '{param.name}' 在函數 '{func.name}'")
            
            # 在函數作用域中定義參數
            self.symbol_table.define(
                param.name,
                SymbolKind.PARAMETER,
                param_type,
                is_mutable=True,
                is_initialized=True
            )
            
            # 記錄已定義的符號
            self.defined_symbols.add(param.name)
        
        # 分析函數體
        if isinstance(func.body, ast_nodes.BlockStatement):
            # 處理 BlockStatement
            for stmt in func.body.statements:
                self._analyze_statement(stmt)
        else:
            # 處理語句列表
            for stmt in func.body:
                self._analyze_statement(stmt)
        
        # 離開函數作用域
        self.symbol_table.exit_scope()
        
        # 清除當前函數返回類型
        self.symbol_table.set_current_function_return_type(None)
    
    def _analyze_struct_declaration(self, struct: ast_nodes.StructDeclaration):
        """
        分析結構體宣告
        
        Args:
            struct: 結構體宣告節點
        """
        # 結構體類型在預宣告階段已經建立，這裡主要處理欄位
        
        # 獲取結構體類型
        type_symbol = self.symbol_table.resolve_type(struct.name)
        if not type_symbol:
            # 這種情況不應該發生，但為了穩健性還是加上檢查
            self.errors.append(f"結構體類型 '{struct.name}' 未定義")
            return
        
        struct_type = type_symbol.type_info
        
        # 處理欄位
        field_names = []
        field_types = []
        
        for field in struct.fields:
            field_names.append(field.name)
            
            field_type = None
            if field.type_annotation:
                type_name = field.type_annotation.name
                field_type_symbol = self.symbol_table.resolve_type(type_name)
                if field_type_symbol:
                    field_type = field_type_symbol.type_info
                else:
                    self.errors.append(f"未知欄位類型 '{type_name}' 於欄位 '{field.name}' 在結構體 '{struct.name}'")
                    field_type = TypeSystem.get_type("any")  # 使用any作為後備
            else:
                self.errors.append(f"欄位 '{field.name}' 在結構體 '{struct.name}' 中沒有類型標註")
                field_type = TypeSystem.get_type("any")  # 使用any作為後備
            
            field_types.append(field_type)
        
        # 更新結構體類型的欄位信息
        struct_type.field_names = field_names
        struct_type.field_types = field_types
    
    def _analyze_var_declaration(self, var: ast_nodes.VarDeclaration):
        """
        分析變數聲明
        
        Args:
            var: 變數聲明節點
        """
        # 檢查變數名是否已被使用
        if self.symbol_table.resolve_current_scope(var.name):
            self.errors.append(f"變數 '{var.name}' 已在當前作用域中定義")
            return
        
        # 處理類型標註
        var_type = None
        if var.type_hint and hasattr(var.type_hint, 'name'):
            type_name = var.type_hint.name
            type_symbol = self.symbol_table.resolve_type(type_name)
            if type_symbol:
                var_type = type_symbol.type_info
            else:
                self.errors.append(f"未知變數類型 '{type_name}' 在變數 '{var.name}'")
        
        # 假設變數是可變的，並且有初始化值
        is_mutable = True
        
        # 在符號表中定義變數
        self.symbol_table.define_variable(
            var.name,
            var_type,
            is_mutable=is_mutable,
            is_initialized=var.value is not None
        )
        
        # 記錄已定義的符號
        self.defined_symbols.add(var.name)
        
        # 分析初始化表達式
        if var.value:
            self._analyze_expression(var.value)
    
    def _analyze_const_declaration(self, const: ast_nodes.ConstDeclaration):
        """
        分析常數宣告
        
        Args:
            const: 常數宣告節點
        """
        # 檢查常數名稱是否已定義
        if self.symbol_table.resolve_current_scope(const.name):
            self.errors.append(f"常數 '{const.name}' 已在當前作用域中定義")
            return
        
        # 處理類型標註
        const_type = None
        if const.type_hint:
            type_name = const.type_hint.name
            type_symbol = self.symbol_table.resolve_type(type_name)
            if type_symbol:
                const_type = type_symbol.type_info
            else:
                self.errors.append(f"未知常數類型 '{type_name}' 在常數 '{const.name}'")
        
        # 在符號表中定義常數
        self.symbol_table.define_constant(
            const.name,
            const_type,
            is_initialized=const.value is not None
        )
        
        # 記錄已定義的符號
        self.defined_symbols.add(const.name)
        
        # 分析初始化表達式
        if const.value:
            self._analyze_expression(const.value)
    
    def _analyze_import_declaration(self, import_decl: ast_nodes.ImportDeclaration):
        """
        分析導入宣告
        
        Args:
            import_decl: 導入宣告節點
        """
        # 在當前作用域記錄導入的符號
        if import_decl.module_path:
            # 處理 from ... import ... 語句
            for item in import_decl.imported_items:
                # 把導入的符號添加到符號表
                self.symbol_table.define(
                    item,
                    SymbolKind.IMPORTED,
                    None,  # 類型會在類型檢查階段確定
                    is_mutable=False,
                    is_initialized=True,
                    module_path=import_decl.module_path
                )
                self.defined_symbols.add(item)
        else:
            # 處理 import ... 語句
            for item in import_decl.imported_items:
                # 記錄導入模塊名
                self.symbol_table.define(
                    item,
                    SymbolKind.MODULE,
                    None,
                    is_mutable=False,
                    is_initialized=True
                )
                self.defined_symbols.add(item)
    
    def _analyze_statement(self, stmt):
        """
        分析語句
        
        Args:
            stmt: 語句節點
        """
        if isinstance(stmt, ast_nodes.ExpressionStatement):
            self._analyze_expression(stmt.expression)
        elif isinstance(stmt, ast_nodes.BlockStatement):
            self.symbol_table.enter_scope("block")
            for sub_stmt in stmt.statements:
                self._analyze_statement(sub_stmt)
            self.symbol_table.exit_scope()
        elif isinstance(stmt, ast_nodes.IfStatement):
            self._analyze_if_statement(stmt)
        elif isinstance(stmt, ast_nodes.WhileStatement):
            self._analyze_while_statement(stmt)
        elif isinstance(stmt, ast_nodes.ForStatement):
            self._analyze_for_statement(stmt)
        elif isinstance(stmt, ast_nodes.ReturnStatement):
            self._analyze_return_statement(stmt)
        elif isinstance(stmt, ast_nodes.VarDeclaration):
            self._analyze_var_declaration(stmt)
        elif isinstance(stmt, ast_nodes.ConstDeclaration):
            self._analyze_const_declaration(stmt)
    
    def _analyze_if_statement(self, stmt: ast_nodes.IfStatement):
        """
        分析if語句
        
        Args:
            stmt: if語句節點
        """
        # 分析條件表達式
        self._analyze_expression(stmt.condition)
        
        # 分析then分支
        self.symbol_table.enter_scope("if-then")
        for sub_stmt in stmt.then_branch:
            self._analyze_statement(sub_stmt)
        self.symbol_table.exit_scope()
        
        # 分析else分支
        if stmt.else_branch:
            self.symbol_table.enter_scope("if-else")
            for sub_stmt in stmt.else_branch:
                self._analyze_statement(sub_stmt)
            self.symbol_table.exit_scope()
    
    def _analyze_while_statement(self, stmt: ast_nodes.WhileStatement):
        """
        分析while語句
        
        Args:
            stmt: while語句節點
        """
        # 分析條件表達式
        self._analyze_expression(stmt.condition)
        
        # 分析循環體
        self.symbol_table.enter_loop()
        self.symbol_table.enter_scope("while")
        for sub_stmt in stmt.body:
            self._analyze_statement(sub_stmt)
        self.symbol_table.exit_scope()
        self.symbol_table.exit_loop()
    
    def _analyze_for_statement(self, stmt: ast_nodes.ForStatement):
        """
        分析for語句
        
        Args:
            stmt: for語句節點
        """
        # 分析可迭代對象表達式
        self._analyze_expression(stmt.iterable)
        
        # 分析循環體
        self.symbol_table.enter_loop()
        self.symbol_table.enter_scope("for")
        
        # 在作用域中定義迭代變數
        if isinstance(stmt.iterator, list):
            for iterator_name in stmt.iterator:
                self.symbol_table.define(
                    iterator_name,
                    SymbolKind.VARIABLE,
                    None,  # 類型將在類型檢查階段確定
                    is_mutable=True,
                    is_initialized=True
                )
                self.defined_symbols.add(iterator_name)
        else:
            # 單個迭代變數
            self.symbol_table.define(
                stmt.iterator,
                SymbolKind.VARIABLE,
                None,  # 類型將在類型檢查階段確定
                is_mutable=True,
                is_initialized=True
            )
            self.defined_symbols.add(stmt.iterator)
        
        # 分析循環體
        for sub_stmt in stmt.body:
            self._analyze_statement(sub_stmt)
        
        # 離開作用域
        self.symbol_table.exit_scope()
        self.symbol_table.exit_loop()
    
    def _analyze_return_statement(self, stmt: ast_nodes.Return):
        """
        分析return語句
        
        Args:
            stmt: return語句節點
        """
        # 分析返回表達式
        if stmt.value:
            self._analyze_expression(stmt.value)
    
    def _analyze_expression(self, expr):
        """
        分析表達式
        
        Args:
            expr: 表達式節點
        """
        if isinstance(expr, ast_nodes.Literal):
            pass  # 字面量不需要符號分析
        elif isinstance(expr, ast_nodes.Variable):
            self._analyze_variable(expr)
        elif isinstance(expr, ast_nodes.BinaryExpr):
            self._analyze_expression(expr.left)
            self._analyze_expression(expr.right)
        elif isinstance(expr, ast_nodes.UnaryExpr):
            self._analyze_expression(expr.operand)
        elif isinstance(expr, ast_nodes.CallExpr):
            self._analyze_call_expr(expr)
        elif isinstance(expr, ast_nodes.MemberAccess):
            self._analyze_expression(expr.object)
        elif isinstance(expr, ast_nodes.IndexAccess):
            self._analyze_expression(expr.object)
            self._analyze_expression(expr.index)
        elif isinstance(expr, ast_nodes.GroupingExpression):
            self._analyze_expression(expr.expression)
        elif isinstance(expr, ast_nodes.AssignmentExpr):
            self._analyze_assignment_expr(expr)
    
    def _analyze_variable(self, var: ast_nodes.Variable):
        """
        分析變數引用
        
        Args:
            var: 變數節點
        """
        # 檢查變數是否已定義
        if var.name not in self.defined_symbols and not self.symbol_table.resolve(var.name):
            self.errors.append(f"未定義的變數 '{var.name}'")
        
        # 標記變數為已使用
        self.used_symbols.add(var.name)
    
    def _analyze_call_expr(self, expr: ast_nodes.CallExpr):
        """
        分析函數調用表達式
        
        Args:
            expr: 函數調用表達式節點
        """
        # 分析被調用對象
        self._analyze_expression(expr.callee)
        
        # 檢查是否調用內建函數
        if isinstance(expr.callee, ast_nodes.Variable):
            if expr.callee.name in self._get_built_in_functions():
                # 內建函數無需在符號表中定義，但標記為已使用
                self.used_symbols.add(expr.callee.name)
        
        # 分析參數
        for arg in expr.arguments:
            self._analyze_expression(arg)
    
    def _get_built_in_functions(self) -> set:
        """
        獲取內建函數列表
        
        Returns:
            內建函數名稱集合
        """
        return {
            "print", "println", "len", "sleep", "copy", 
            "error", "is_error", "string", "int", "float",
            "bool"
        }
    
    def _analyze_assignment_expr(self, expr: ast_nodes.AssignmentExpr):
        """
        分析賦值表達式
        
        Args:
            expr: 賦值表達式節點
        """
        # 分析右值
        self._analyze_expression(expr.value)
        
        # 分析左值
        if isinstance(expr.target, ast_nodes.Variable):
            # 檢查變數是否已定義
            symbol = self.symbol_table.resolve(expr.target.name)
            if not symbol:
                self.errors.append(f"未定義的變數 '{expr.target.name}'")
                return
            
            # 檢查變數是否為常量
            if symbol.kind == SymbolKind.CONST:
                self.errors.append(f"無法賦值給常量 '{expr.target.name}'")
                return
            
            # 檢查變數是否為不可變變數
            if not symbol.is_mutable:
                self.errors.append(f"無法賦值給不可變變數 '{expr.target.name}'")
                return
            
            # 標記變數為已使用和已初始化
            self.symbol_table.mark_symbol_used(expr.target.name)
            self.symbol_table.mark_symbol_initialized(expr.target.name)
            self.used_symbols.add(expr.target.name)
        elif isinstance(expr.target, ast_nodes.MemberAccess):
            # 分析對象
            self._analyze_expression(expr.target.object)
        elif isinstance(expr.target, ast_nodes.IndexAccess):
            # 分析對象和索引
            self._analyze_expression(expr.target.object)
            self._analyze_expression(expr.target.index)
        else:
            self.errors.append("無效的賦值目標")
    
    def _check_unused_symbols(self):
        """
        檢查未使用的符號
        """
        for name in self.defined_symbols:
            if name not in self.used_symbols:
                symbol = self.symbol_table.resolve(name)
                if symbol and symbol.kind in [SymbolKind.VARIABLE, SymbolKind.PARAMETER, SymbolKind.CONST]:
                    self.warnings.append(f"變數 '{name}' 已定義但未使用") 