"""
字符串處理相關函數實現模塊
包含字符串轉義、字符串信息獲取、字符串長度計算等功能
"""

from typing import List, Dict, Any, Optional, Tuple
import logging

from ..base_generator import CodeGenerator
from ...parser import ast_nodes


class StringFunctions:
    """字符串處理相關函數的實現類"""

    def __init__(self, parent):
        """
        初始化字符串處理函數模塊
        
        Args:
            parent: 代碼生成器實例，提供共享方法和屬性
        """
        self.parent = parent
        self.logger = parent.logger or logging.getLogger(self.__class__.__name__)
    
    def set_parent(self, parent):
        """設置父對象"""
        self.parent = parent
        return self
        
    def initialize(self, context=None):
        """初始化模組"""
        return self
        
    def escape_string(self, s: str) -> str:
        """
        將字符串進行轉義處理，處理特殊字符
        
        Args:
            s: 原始字符串
            
        Returns:
            str: 轉義後的字符串
        """
        result = ""
        i = 0
        while i < len(s):
            if s[i] == '\\':
                if i + 1 < len(s):
                    if s[i+1] == 'n':
                        result += '\\0A'  # 換行符的十六進制ASCII碼
                        i += 2
                    elif s[i+1] == 't':
                        result += '\\09'  # 製表符的十六進制ASCII碼
                        i += 2
                    elif s[i+1] == 'r':
                        result += '\\0D'  # 回車符的十六進制ASCII碼
                        i += 2
                    elif s[i+1] == '0':
                        result += '\\00'  # 空字符的十六進制ASCII碼
                        i += 2
                    elif s[i+1] == '"':
                        result += '\\"'  # 雙引號
                        i += 2
                    elif s[i+1] == '\'':
                        result += '\\\''  # 單引號
                        i += 2
                    elif s[i+1] == '\\':
                        result += '\\\\'  # 反斜線
                        i += 2
                    else:
                        result += s[i:i+2]
                        i += 2
                else:
                    result += s[i]
                    i += 1
            else:
                # 檢查是否需要進行UTF-8編碼
                if ord(s[i]) >= 128:
                    # 使用UTF-8編碼
                    utf8_bytes = s[i].encode('utf-8')
                    for byte in utf8_bytes:
                        result += f'\\{byte:02X}'
                else:
                    result += s[i]
                i += 1
        
        return result
        
    def get_string_info(self, string: str) -> Tuple[int, int]:
        """
        獲取字符串的索引和字符數量，如果字符串不存在於全局字符串表中，則添加
        
        Args:
            string: 原始字符串
            
        Returns:
            Tuple[int, int]: 字符串在全局字符串表中的索引和字符數量
        """
        # 檢查字符串是否已經添加
        for i, s in enumerate(self.parent.global_strings):
            if s == string:
                return i, len(string)
        
        # 添加新字符串
        return self.parent._add_global_string(string), len(string)
        
    def get_byte_length(self, string: str) -> int:
        """
        計算字符串的字節長度，包括UTF-8編碼和結尾空字符
        
        Args:
            string: 原始字符串
            
        Returns:
            int: 字符串的字節長度
        """
        # 轉換為UTF-8並計算長度，加1是為了結尾的空字符
        return len(string.encode('utf-8')) + 1
        
    def collect_strings_from_ast(self, ast):
        """
        從AST收集所有字符串字面量
        
        Args:
            ast: 抽象語法樹
            
        Returns:
            None
        """
        if isinstance(ast, ast_nodes.Module):
            # 遍歷模塊中的所有語句
            for stmt in ast.statements:
                self.collect_strings_from_statement(stmt)
            
            # 處理主塊
            if ast.main_block:
                for stmt in ast.main_block.statements:
                    self.collect_strings_from_statement(stmt)
                    
    def collect_strings_from_statement(self, stmt):
        """
        從語句中收集所有字符串字面量
        
        Args:
            stmt: 語句對象
            
        Returns:
            None
        """
        if isinstance(stmt, ast_nodes.ExpressionStatement):
            # 表達式語句
            self.parent._collect_strings_from_expr(stmt.expression)
            
        elif isinstance(stmt, ast_nodes.VarDeclaration):
            # 變量聲明
            if stmt.initializer:
                self.parent._collect_strings_from_expr(stmt.initializer)
                
        elif isinstance(stmt, ast_nodes.AssignmentStmt):
            # 賦值語句
            self.parent._collect_strings_from_expr(stmt.right)
            
        elif isinstance(stmt, ast_nodes.IfStatement):
            # If語句
            self.parent._collect_strings_from_expr(stmt.condition)
            
            for body_stmt in stmt.then_branch:
                self.collect_strings_from_statement(body_stmt)
            
            if stmt.else_branch:
                for else_stmt in stmt.else_branch:
                    self.collect_strings_from_statement(else_stmt)
                    
        elif isinstance(stmt, ast_nodes.WhileStatement):
            # While語句
            self.parent._collect_strings_from_expr(stmt.condition)
            
            for body_stmt in stmt.body:
                self.collect_strings_from_statement(body_stmt)
                
        elif isinstance(stmt, ast_nodes.ForStatement):
            # For語句
            if stmt.initializer:
                self.collect_strings_from_statement(stmt.initializer)
            
            if stmt.condition:
                self.parent._collect_strings_from_expr(stmt.condition)
            
            if stmt.increment:
                self.parent._collect_strings_from_expr(stmt.increment)
            
            for body_stmt in stmt.body:
                self.collect_strings_from_statement(body_stmt)
                
        elif isinstance(stmt, ast_nodes.ReturnStatement):
            # Return語句
            if stmt.value:
                self.parent._collect_strings_from_expr(stmt.value)
                
        # 添加更多語句類型處理...
        
    def collect_strings_from_expr(self, expr):
        """
        從表達式中收集所有字符串字面量
        
        Args:
            expr: 表達式對象
            
        Returns:
            None
        """
        if isinstance(expr, ast_nodes.StringLiteral):
            # 字符串字面量
            self.parent._add_global_string(expr.value)
            
        elif isinstance(expr, ast_nodes.TemplateLiteral):
            # 模板字符串
            # 解析模板字符串，提取純文本部分和變量引用
            if hasattr(self.parent, '_literal_functions'):
                text_parts, var_refs = self.parent._literal_functions.parse_template_literal_variables(expr.value)
                
                # 添加所有文本部分
                for text in text_parts:
                    if text:
                        self.parent._add_global_string(text)
                
                # 添加格式化字符串
                self.parent._add_global_string("%d")  # 整數格式
                self.parent._add_global_string("%f")  # 浮點數格式
                self.parent._add_global_string("%s")  # 字符串格式
                self.parent._add_global_string("")    # 空字符串
            else:
                # 如果尚未初始化 _literal_functions，則簡單處理
                self.parent._add_global_string(expr.value)
            
        elif isinstance(expr, ast_nodes.BinaryExpr):
            # 二元表達式
            self.parent._collect_strings_from_expr(expr.left)
            self.parent._collect_strings_from_expr(expr.right)
            
        elif isinstance(expr, ast_nodes.UnaryExpr):
            # 一元表達式
            self.parent._collect_strings_from_expr(expr.right)
            
        elif isinstance(expr, ast_nodes.CallExpression):
            # 函數調用
            for arg in expr.arguments:
                self.parent._collect_strings_from_expr(arg)
                
        elif isinstance(expr, ast_nodes.GroupingExpr):
            # 分組表達式
            self.parent._collect_strings_from_expr(expr.expression)
            
        # 添加更多表達式類型處理...
        
    def generate_string_interpolation(self, expr, target_var=None) -> Any:
        """
        生成字符串插值的 LLVM IR 代碼
        
        Args:
            expr: 需要進行插值的表達式
            target_var: 目標變量名（可選）
            
        Returns:
            str 或 Dict: 生成的LLVM IR代碼或包含代碼、臨時變量名和類型的字典
        """
        # 處理字符串連接操作
        if isinstance(expr, ast_nodes.BinaryExpr) and expr.operator == '+':
            if isinstance(expr.left, ast_nodes.StringLiteral) and isinstance(expr.right, ast_nodes.StringLiteral):
                # 連接兩個字符串字面量
                # 獲取左側字符串資訊
                left_str_idx, left_char_count = self.parent._get_string_info(expr.left.value)
                left_byte_length = self.parent.string_length_map[left_str_idx]
                
                # 獲取右側字符串資訊
                right_str_idx, right_char_count = self.parent._get_string_info(expr.right.value)
                right_byte_length = self.parent.string_length_map[right_str_idx]
                
                # 連接兩個字符串
                result = ""
                tmp_var = self.parent.var_counter if target_var is None else target_var
                
                result += f"    %tmp_{tmp_var}_left = getelementptr inbounds ([{left_byte_length} x i8], [{left_byte_length} x i8]* @.str.{left_str_idx}, i32 0, i32 0)\n"
                result += f"    %tmp_{tmp_var}_right = getelementptr inbounds ([{right_byte_length} x i8], [{right_byte_length} x i8]* @.str.{right_str_idx}, i32 0, i32 0)\n"
                
                # 計算字符串長度
                result += f"    %len_left_{tmp_var} = call i64 @strlen(i8* %tmp_{tmp_var}_left)\n"
                result += f"    %len_right_{tmp_var} = call i64 @strlen(i8* %tmp_{tmp_var}_right)\n"
                result += f"    %total_len_{tmp_var} = add i64 %len_left_{tmp_var}, %len_right_{tmp_var}\n"
                result += f"    %total_with_null_{tmp_var} = add i64 %total_len_{tmp_var}, 1\n"
                
                # 分配內存
                result += f"    %buf_{tmp_var} = call i8* @malloc(i64 %total_with_null_{tmp_var})\n"
                
                # 複製第一個字符串
                result += f"    %strcpy_result_{tmp_var} = call i8* @strcpy(i8* %buf_{tmp_var}, i8* %tmp_{tmp_var}_left)\n"
                
                # 連接第二個字符串
                result += f"    %strcat_result_{tmp_var} = call i8* @strcat(i8* %strcpy_result_{tmp_var}, i8* %tmp_{tmp_var}_right)\n"
                
                # 轉換指針類型
                result += f"    %tmp_{tmp_var} = bitcast i8* %strcat_result_{tmp_var} to i8*\n"
                
                if target_var is None:
                    self.parent.var_counter += 1
                
                return {
                    'code': result,
                    'tmp': tmp_var,
                    'type': 'i8*'
                }
            
            elif isinstance(expr.left, ast_nodes.StringLiteral) or isinstance(expr.right, ast_nodes.StringLiteral) or self.parent._is_string_concatenation(expr.left) or self.parent._is_string_concatenation(expr.right):
                # 處理字符串和其他類型的連接
                result = ""
                
                # 處理左側
                if isinstance(expr.left, ast_nodes.StringLiteral):
                    left_result = self.parent._generate_string_literal(expr.left)
                elif isinstance(expr.left, ast_nodes.BinaryExpr) and self.parent._is_string_concatenation(expr.left):
                    left_result = self.generate_string_interpolation(expr.left)
                else:
                    left_result = self.parent._generate_expression(expr.left)
                
                # 處理右側
                if isinstance(expr.right, ast_nodes.StringLiteral):
                    right_result = self.parent._generate_string_literal(expr.right)
                elif isinstance(expr.right, ast_nodes.BinaryExpr) and self.parent._is_string_concatenation(expr.right):
                    right_result = self.generate_string_interpolation(expr.right)
                else:
                    right_result = self.parent._generate_expression(expr.right)
                
                # 添加左側代碼
                result += left_result['code']
                
                # 添加右側代碼
                result += right_result['code']
                
                # 轉換右側為字符串（如果需要）
                if right_result['type'] != 'i8*':
                    tmp_var = self.parent.var_counter
                    
                    if right_result['type'] == 'i32':
                        # 整數轉字符串
                        result += f"    %buf_{tmp_var} = alloca [64 x i8]\n"
                        result += f"    %ptr_{tmp_var} = getelementptr inbounds [64 x i8], [64 x i8]* %buf_{tmp_var}, i32 0, i32 0\n"
                        
                        # 使用 sprintf 將整數轉換為字符串
                        fmt_str = "%d"
                        fmt_idx, _ = self.parent._get_string_info(fmt_str)
                        fmt_byte_length = self.parent.string_length_map[fmt_idx]
                        
                        result += f"    %fmt_{tmp_var} = getelementptr inbounds ([{fmt_byte_length} x i8], [{fmt_byte_length} x i8]* @.str.0, i32 0, i32 0)\n"
                        result += f"    call i32 (i8*, i8*, ...) @sprintf(i8* %ptr_{tmp_var}, i8* %fmt_{tmp_var}, i32 %tmp_{right_result['tmp']})\n"
                        
                        right_tmp = f"ptr_{tmp_var}"
                    elif right_result['type'] == 'double':
                        # 浮點數轉字符串
                        result += f"    %buf_{tmp_var} = alloca [64 x i8]\n"
                        result += f"    %ptr_{tmp_var} = getelementptr inbounds [64 x i8], [64 x i8]* %buf_{tmp_var}, i32 0, i32 0\n"
                        
                        # 使用 sprintf 將浮點數轉換為字符串
                        fmt_str = "%f"
                        fmt_idx, _ = self.parent._get_string_info(fmt_str)
                        fmt_byte_length = self.parent.string_length_map[fmt_idx]
                        
                        result += f"    %fmt_{tmp_var} = getelementptr inbounds ([{fmt_byte_length} x i8], [{fmt_byte_length} x i8]* @.str.1, i32 0, i32 0)\n"
                        result += f"    call i32 (i8*, i8*, ...) @sprintf(i8* %ptr_{tmp_var}, i8* %fmt_{tmp_var}, double %tmp_{right_result['tmp']})\n"
                        
                        right_tmp = f"ptr_{tmp_var}"
                    else:
                        # 不支持的類型
                        self.logger.error(f"不支持的字符串連接類型: {right_result['type']}")
                        
                        # 使用空字符串
                        empty_str = ""
                        empty_idx, _ = self.parent._get_string_info(empty_str)
                        empty_byte_length = self.parent.string_length_map[empty_idx]
                        
                        result += f"    %tmp_{tmp_var} = getelementptr inbounds ([{empty_byte_length} x i8], [{empty_byte_length} x i8]* @.str.{empty_idx}, i32 0, i32 0)\n"
                        right_tmp = f"tmp_{tmp_var}"
                    
                    self.parent.var_counter += 1
                else:
                    right_tmp = f"tmp_{right_result['tmp']}"
                
                # 連接字符串
                res_tmp = self.parent.var_counter if target_var is None else target_var
                
                # 計算字符串長度
                result += f"    %len_left_{res_tmp} = call i64 @strlen(i8* %tmp_{left_result['tmp']})\n"
                result += f"    %len_right_{res_tmp} = call i64 @strlen(i8* %{right_tmp})\n"
                result += f"    %total_len_{res_tmp} = add i64 %len_left_{res_tmp}, %len_right_{res_tmp}\n"
                result += f"    %total_with_null_{res_tmp} = add i64 %total_len_{res_tmp}, 1\n"
                
                # 分配內存
                result += f"    %buf_{res_tmp} = call i8* @malloc(i64 %total_with_null_{res_tmp})\n"
                
                # 複製第一個字符串
                result += f"    %strcpy_result_{res_tmp} = call i8* @strcpy(i8* %buf_{res_tmp}, i8* %tmp_{left_result['tmp']})\n"
                
                # 連接第二個字符串
                result += f"    %strcat_result_{res_tmp} = call i8* @strcat(i8* %strcpy_result_{res_tmp}, i8* %{right_tmp})\n"
                
                # 轉換指針類型
                result += f"    %tmp_{res_tmp} = bitcast i8* %strcat_result_{res_tmp} to i8*\n"
                
                res_type = 'i8*'
                
                if target_var is None:
                    self.parent.var_counter += 1
                
                return {
                    'code': result,
                    'tmp': res_tmp,
                    'type': res_type
                }
            
        # 處理單一字符串
        if isinstance(expr, ast_nodes.StringLiteral):
            return self.parent._generate_string_literal(expr)
        
        # 處理其他表達式
        return self.parent._generate_expression(expr)
        
    def generate_string_interpolation_for_var(self, expr, target_var):
        """
        為指定變量生成字符串插值的 LLVM IR 代碼
        
        Args:
            expr: 需要進行插值的表達式
            target_var: 目標變量名
            
        Returns:
            str: 生成的 LLVM IR 代碼
        """
        result = self.generate_string_interpolation(expr, target_var)
        return result['code'] 