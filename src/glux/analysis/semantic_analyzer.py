"""
語義分析器模組
負責對AST進行語義分析，檢查程式的語法正確性和語義正確性
"""

from typing import List, Dict, Optional, Any
import logging

from ..parser import ast_nodes
from ..utils.symbol_table import SymbolTable
from ..utils.error import SemanticError
from ..type_system import TypeSystem, TypeKind, GluxType
from .symbol_analyzer import SymbolAnalyzer
from .type_checker import TypeChecker
from .control_flow_analyzer import ControlFlowAnalyzer


class SemanticAnalyzer:
    """
    語義分析器類
    整合符號分析、類型檢查和控制流分析
    """
    
    def __init__(self):
        """
        初始化語義分析器
        """
        self.symbol_table = SymbolTable()
        self.errors = []
        self.warnings = []
        self.logger = logging.getLogger("SemanticAnalyzer")
        
        # 初始化內建類型
        self._initialize_builtin_types()
    
    def analyze(self, ast: ast_nodes.Module) -> bool:
        """
        分析AST節點
        
        Args:
            ast: AST根節點
        
        Returns:
            分析是否成功（沒有錯誤）
        """
        self.logger.info("開始語義分析")
        
        # 重置錯誤和警告列表
        self.errors = []
        self.warnings = []
        
        try:
            # 符號分析
            symbol_analyzer = SymbolAnalyzer(self.symbol_table)
            symbol_analyzer.analyze_module(ast)
            self.errors.extend(symbol_analyzer.errors)
            self.warnings.extend(symbol_analyzer.warnings)
            
            # 檢查是否有任何符號分析錯誤
            if len(symbol_analyzer.errors) > 0:
                self.logger.error(f"符號分析發現 {len(symbol_analyzer.errors)} 個錯誤")
                return False
            
            # 類型檢查
            type_checker = TypeChecker(self.symbol_table)
            for decl in ast.statements:
                type_checker.check_declaration(decl)
            self.errors.extend(type_checker.errors)
            self.warnings.extend(type_checker.warnings)
            
            # 檢查是否有任何類型檢查錯誤
            if len(type_checker.errors) > 0:
                self.logger.error(f"類型檢查發現 {len(type_checker.errors)} 個錯誤")
                return False
            
            # 控制流分析
            control_flow_analyzer = ControlFlowAnalyzer(self.symbol_table)
            control_flow_analyzer.analyze_module(ast)
            self.errors.extend(control_flow_analyzer.errors)
            self.warnings.extend(control_flow_analyzer.warnings)
            
            # 檢查是否有任何控制流分析錯誤
            if len(control_flow_analyzer.errors) > 0:
                self.logger.error(f"控制流分析發現 {len(control_flow_analyzer.errors)} 個錯誤")
                return False
            
            # 如果沒有錯誤，則分析成功
            if len(self.errors) == 0:
                if len(self.warnings) > 0:
                    self.logger.warning(f"語義分析完成，有 {len(self.warnings)} 個警告")
                else:
                    self.logger.info("語義分析成功完成")
                return True
            else:
                self.logger.error(f"語義分析發現 {len(self.errors)} 個錯誤")
                return False
        except Exception as e:
            self.logger.error(f"語義分析時發生異常: {str(e)}", exc_info=True)
            self.errors.append(f"語義分析時發生內部錯誤: {str(e)}")
            return False
    
    def get_errors(self) -> List[str]:
        """
        獲取語義分析錯誤列表
        
        Returns:
            錯誤訊息列表
        """
        return self.errors
    
    def get_warnings(self) -> List[str]:
        """
        獲取語義分析警告列表
        
        Returns:
            警告訊息列表
        """
        return self.warnings
    
    def _initialize_builtin_types(self):
        """
        初始化內建類型
        """
        # 基本類型
        self.symbol_table.define_builtin_type("void", TypeSystem.get_type("void"))
        self.symbol_table.define_builtin_type("bool", TypeSystem.get_type("bool"))
        
        # 整數類型
        self.symbol_table.define_builtin_type("i8", TypeSystem.get_type("i8"))
        self.symbol_table.define_builtin_type("i16", TypeSystem.get_type("i16"))
        self.symbol_table.define_builtin_type("i32", TypeSystem.get_type("i32"))
        self.symbol_table.define_builtin_type("i64", TypeSystem.get_type("i64"))
        self.symbol_table.define_builtin_type("u8", TypeSystem.get_type("u8"))
        self.symbol_table.define_builtin_type("u16", TypeSystem.get_type("u16"))
        self.symbol_table.define_builtin_type("u32", TypeSystem.get_type("u32"))
        self.symbol_table.define_builtin_type("u64", TypeSystem.get_type("u64"))
        
        # 別名
        self.symbol_table.define_builtin_type("int", TypeSystem.get_type("i32"))
        self.symbol_table.define_builtin_type("uint", TypeSystem.get_type("u32"))
        self.symbol_table.define_builtin_type("byte", TypeSystem.get_type("u8"))
        
        # 浮點類型
        self.symbol_table.define_builtin_type("f32", TypeSystem.get_type("f32"))
        self.symbol_table.define_builtin_type("f64", TypeSystem.get_type("f64"))
        
        # 別名
        self.symbol_table.define_builtin_type("float", TypeSystem.get_type("f32"))
        self.symbol_table.define_builtin_type("double", TypeSystem.get_type("f64"))
        
        # 字符和字符串
        self.symbol_table.define_builtin_type("char", TypeSystem.get_type("char"))
        self.symbol_table.define_builtin_type("string", TypeSystem.get_type("string"))
        
        # 通用類型
        self.symbol_table.define_builtin_type("any", TypeSystem.get_type("any"))
        self.symbol_table.define_builtin_type("null", TypeSystem.get_type("null"))
        
        # 初始化內建函數
        self._initialize_builtin_functions()
    
    def _initialize_builtin_functions(self):
        """
        初始化內建函數
        """
        # 打印函數
        print_type = TypeSystem.create_function_type(
            TypeSystem.get_type("void"),
            [TypeSystem.get_type("any")],
            ["value"]
        )
        self.symbol_table.define_builtin_function("print", print_type)
        
        # 獲取字符串長度
        len_type = TypeSystem.create_function_type(
            TypeSystem.get_type("int"),
            [TypeSystem.get_type("string")],
            ["str"]
        )
        self.symbol_table.define_builtin_function("len", len_type)
        
        # 類型轉換函數
        int_cast_type = TypeSystem.create_function_type(
            TypeSystem.get_type("int"),
            [TypeSystem.get_type("any")],
            ["value"]
        )
        self.symbol_table.define_builtin_function("int", int_cast_type)
        
        float_cast_type = TypeSystem.create_function_type(
            TypeSystem.get_type("float"),
            [TypeSystem.get_type("any")],
            ["value"]
        )
        self.symbol_table.define_builtin_function("float", float_cast_type)
        
        bool_cast_type = TypeSystem.create_function_type(
            TypeSystem.get_type("bool"),
            [TypeSystem.get_type("any")],
            ["value"]
        )
        self.symbol_table.define_builtin_function("bool", bool_cast_type)
        
        string_cast_type = TypeSystem.create_function_type(
            TypeSystem.get_type("string"),
            [TypeSystem.get_type("any")],
            ["value"]
        )
        self.symbol_table.define_builtin_function("string", string_cast_type)
        
        # 新增 copy 函數
        copy_type = TypeSystem.create_function_type(
            TypeSystem.get_type("any"),
            [TypeSystem.get_type("any")],
            ["value"]
        )
        self.symbol_table.define_builtin_function("copy", copy_type)
        
        # 新增 error 函數
        error_type = TypeSystem.create_function_type(
            TypeSystem.get_type("error"),
            [TypeSystem.get_type("string")],
            ["message"]
        )
        self.symbol_table.define_builtin_function("error", error_type)
        
        # 新增 is_error 函數
        is_error_type = TypeSystem.create_function_type(
            TypeSystem.get_type("bool"),
            [TypeSystem.get_type("any")],
            ["value"]
        )
        self.symbol_table.define_builtin_function("is_error", is_error_type)
        
        # 新增 println 函數
        println_type = TypeSystem.create_function_type(
            TypeSystem.get_type("void"),
            [TypeSystem.get_type("any")],
            ["value"]
        )
        self.symbol_table.define_builtin_function("println", println_type)
        
        # 新增 sleep 函數
        sleep_type = TypeSystem.create_function_type(
            TypeSystem.get_type("void"),
            [TypeSystem.get_type("int")],
            ["milliseconds"]
        )
        self.symbol_table.define_builtin_function("sleep", sleep_type)
    
    def analyze_comparison_chain(self, expr):
        """
        處理連續比較運算，如 0 < x < 8
        將連續比較轉換為使用 and 連接的多個比較
        
        Args:
            expr: 連續比較表達式
            
        Returns:
            處理後的表達式
        """
        # 確保有連續比較的結構
        if not hasattr(expr, 'comparisons') or len(expr.comparisons) < 2:
            return expr
        
        # 分解連續比較為多個 AND 連接的單一比較
        left = expr.left
        result = None
        
        for op, right in expr.comparisons:
            # 創建當前比較
            current_comp = ast_nodes.BinaryExpr(left, op, right)
            
            # 更新左側為當前右側，準備下一次比較
            left = right
            
            # 將比較結果與之前的結果用 AND 連接
            if result is None:
                result = current_comp
            else:
                result = ast_nodes.LogicalExpr(result, 'and', current_comp)
        
        return result
    
    def analyze_type_inference(self, expr):
        """
        根據數值範圍推導整數和浮點數類型
        
        Args:
            expr: 表達式
            
        Returns:
            推導出的類型
        """
        if isinstance(expr, ast_nodes.IntLiteral):
            # 使用TypeSystem的infer_numeric_type方法推導整數類型
            type_name = TypeSystem.infer_numeric_type(expr.value)
            return self.symbol_table.get_type(type_name)
        
        elif isinstance(expr, ast_nodes.FloatLiteral):
            # 使用TypeSystem的infer_numeric_type方法推導浮點數類型
            type_name = TypeSystem.infer_numeric_type(expr.value)
            return self.symbol_table.get_type(type_name)
        
        return None 