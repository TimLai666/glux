"""
控制流分析器模組
負責檢測程式中的控制流問題，如無法到達的代碼、缺少返回語句等
"""

from typing import List, Set, Dict, Optional, Any
import logging

from ..parser import ast_nodes
from ..utils.symbol_table import SymbolTable


class ControlFlowAnalyzer:
    """
    控制流分析器類
    負責檢測程式中的控制流問題，如無法到達的代碼、缺少返回語句等
    """
    
    def __init__(self, symbol_table: SymbolTable):
        """
        初始化控制流分析器
        
        Args:
            symbol_table: 符號表
        """
        self.symbol_table = symbol_table
        self.errors = []
        self.warnings = []
        self.logger = logging.getLogger("ControlFlowAnalyzer")
        
        # 當前分析的函數是否有返回語句
        self.has_return = False
        
        # 當前分析的函數名稱
        self.current_function = None
        
        # 分支終止狀態
        self.terminates = False
        
        # 當前是否在循環中
        self.in_loop = 0
        
        # 當前循環中是否有break語句
        self.has_break = False
    
    def analyze_module(self, module: ast_nodes.Module):
        """
        分析模組
        
        Args:
            module: 模組節點
        """
        # 分析模組中的所有聲明
        for decl in module.statements:
            self.analyze_node(decl)
    
    def analyze_node(self, node):
        """
        分析節點
        
        Args:
            node: AST節點
        """
        if isinstance(node, ast_nodes.FunctionDeclaration):
            self._analyze_function(node)
        elif isinstance(node, ast_nodes.Statement):
            self._analyze_statement(node)
        # 其他類型的節點暫時忽略
    
    def _analyze_function(self, func: ast_nodes.FunctionDeclaration):
        """
        分析函數
        
        Args:
            func: 函數宣告節點
        """
        self.current_function = func.name
        self.has_return = False
        
        # 獲取函數返回類型
        return_type = None
        if func.return_type:
            return_type_name = func.return_type.name
            type_symbol = self.symbol_table.resolve_type(return_type_name)
            if type_symbol:
                return_type = type_symbol.type_info
        
        needs_return = return_type and return_type.name != "void"
        
        # 分析函數體
        terminates = self._analyze_block(func.body)
        
        # 檢查是否缺少返回語句
        if needs_return and not terminates:
            self.errors.append(f"函數 '{func.name}' 的某些執行路徑可能沒有返回值")
        
        self.current_function = None
    
    def _analyze_block(self, statements: List[ast_nodes.Statement]) -> bool:
        """
        分析語句塊
        
        Args:
            statements: 語句列表或BlockStatement
            
        Returns:
            語句塊是否確定終止（如有返回語句或拋出異常）
        """
        terminates = False
        
        # 處理BlockStatement對象
        if isinstance(statements, ast_nodes.BlockStatement):
            statements = statements.statements
        
        for i, stmt in enumerate(statements):
            # 檢查前面的語句是否已終止，如果是，則後面的代碼無法到達
            if terminates:
                self.warnings.append(f"無法到達的代碼: {stmt}")
                continue
            
            # 分析語句
            terminates = self._analyze_statement(stmt)
        
        return terminates
    
    def _analyze_statement(self, stmt) -> bool:
        """
        分析語句
        
        Args:
            stmt: 語句節點
            
        Returns:
            語句是否確定終止執行流
        """
        if isinstance(stmt, ast_nodes.ExpressionStatement):
            return False  # 表達式語句不終止
        elif isinstance(stmt, ast_nodes.BlockStatement):
            return self._analyze_block(stmt.statements)
        elif isinstance(stmt, ast_nodes.IfStatement):
            return self._analyze_if_statement(stmt)
        elif isinstance(stmt, ast_nodes.WhileStatement):
            return self._analyze_while_statement(stmt)
        elif isinstance(stmt, ast_nodes.ForStatement):
            return self._analyze_for_statement(stmt)
        elif isinstance(stmt, ast_nodes.ReturnStatement):
            self.has_return = True
            return True  # 返回語句總是終止
        elif isinstance(stmt, ast_nodes.BreakStatement):
            self._check_break_validity()
            return False  # break不終止函數
        elif isinstance(stmt, ast_nodes.ContinueStatement):
            self._check_continue_validity()
            return False  # continue不終止函數
        elif isinstance(stmt, ast_nodes.VarDeclaration) or isinstance(stmt, ast_nodes.ConstDeclaration):
            return False  # 變數和常數宣告不終止
        else:
            return False  # 默認情況
    
    def _analyze_if_statement(self, stmt: ast_nodes.IfStatement) -> bool:
        """
        分析if語句
        
        Args:
            stmt: if語句節點
            
        Returns:
            if語句是否確定終止執行流
        """
        # 分析then分支
        then_terminates = self._analyze_block(stmt.then_branch)
        
        # 如果沒有else分支，則整個if語句不能保證終止
        if not stmt.else_branch:
            return False
        
        # 分析else分支
        else_terminates = self._analyze_block(stmt.else_branch)
        
        # 只有當兩個分支都終止時，整個if語句才終止
        return then_terminates and else_terminates
    
    def _analyze_while_statement(self, stmt: ast_nodes.WhileStatement) -> bool:
        """
        分析while語句
        
        Args:
            stmt: while語句節點
            
        Returns:
            while語句是否確定終止執行流
        """
        # 標記進入循環
        self.in_loop += 1
        self.has_break = False
        
        # 分析循環體
        body_terminates = self._analyze_block(stmt.body)
        
        # 檢查是否存在可能的無限循環
        if not self.has_break and self._is_always_true(stmt.condition):
            # 循環條件總是真且沒有break語句，可能是無限循環
            if body_terminates:
                # 但如果循環體終止（如有return語句），則無限循環沒有問題
                pass
            else:
                # 否則可能是無限循環
                self.warnings.append("可能的無限循環")
                return True  # 無限循環也是一種終止（程序永不返回）
        
        # 標記離開循環
        self.in_loop -= 1
        
        # while循環不能保證終止（除非檢測到無限循環）
        return False
    
    def _analyze_for_statement(self, stmt: ast_nodes.ForStatement) -> bool:
        """
        分析for語句
        
        Args:
            stmt: for語句節點
            
        Returns:
            for語句是否確定終止執行流
        """
        # 標記進入循環
        self.in_loop += 1
        self.has_break = False
        
        # 分析循環體
        body_terminates = self._analyze_block(stmt.body)
        
        # 標記離開循環
        self.in_loop -= 1
        
        # for循環不能保證終止
        return False
    
    def _check_break_validity(self):
        """
        檢查break語句的有效性
        """
        if self.in_loop <= 0:
            self.errors.append("break語句必須在循環內部")
        else:
            self.has_break = True
    
    def _check_continue_validity(self):
        """
        檢查continue語句的有效性
        """
        if self.in_loop <= 0:
            self.errors.append("continue語句必須在循環內部")
    
    def _is_always_true(self, expr) -> bool:
        """
        檢查表達式是否總是為真
        
        Args:
            expr: 表達式節點
            
        Returns:
            表達式是否總是為真
        """
        # 簡單實現，僅檢查明顯的情況
        if isinstance(expr, ast_nodes.Literal):
            if expr.value_type == "bool" and expr.value == True:
                return True
            return False
        
        # 更複雜的情況需要更詳細的分析
        return False 