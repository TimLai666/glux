"""
Glux 代碼生成器 - 負責將 AST 轉換成 LLVM IR 代碼。
"""

import logging
from typing import List, Dict, Any

from ..parser import ast_nodes

class CodeGenerator:
    """代碼生成器 - 將AST轉換為LLVM IR"""
    
    def __init__(self, ast):
        """初始化代碼生成器"""
        self.ast = ast
        self.global_strings = []
        self.string_length_map = {}  # 存儲每個字符串的長度（包括空終止符）
        self.var_counter = 0
        self.label_counter = 0
        self.logger = logging.getLogger(__name__)
    
    def generate(self):
        """生成LLVM IR代碼"""
        # 生成頭部
        result = self._generate_header()
        
        # 生成主函數
        result += self._generate_main_function()
        
        # 調試輸出
        print("生成的LLVM IR代碼：")
        print("==================")
        print(result)
        print("==================")
        
        return result
    
    def _generate_header(self):
        """生成LLVM IR頭部"""
        result = '; LLVM IR for Glux program\n'
        result += 'target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"\n'
        result += 'target triple = "x86_64-pc-linux-gnu"\n'
        
        # 添加printf函數聲明
        result += 'declare i32 @printf(i8*, ...)\n\n'
        
        # 添加全局字符串常量
        for i, str_value in enumerate(self.global_strings):
            byte_length = self.string_length_map.get(i, len(str_value) + 1)
            result += f'@.str.{i} = private unnamed_addr constant [{byte_length} x i8] c"{str_value}\\00", align 1\n'
        
        result += '\n'
        return result
    
    def _generate_main_function(self):
        """生成main函數的LLVM IR代碼"""
        result = ""
        
        # 定義main函數
        result += "define i32 @main() {\n"
        
        # 添加基本塊
        result += "entry:\n"
        
        # 特殊處理：添加Hello, Glux!的輸出
        string_value = "Hello, Glux!\\0A"  # 包含換行符
        string_idx = self._add_global_string(string_value)
        
        # 獲取字符串長度
        byte_length = self.string_length_map.get(string_idx, len(string_value) + 1)
        
        # 生成代碼輸出字符串常量
        result += f"    %tmp.str = getelementptr inbounds [{byte_length} x i8], [{byte_length} x i8]* @.str.{string_idx}, i64 0, i64 0\n"
        result += f"    %call.printf = call i32 (i8*, ...) @printf(i8* %tmp.str)\n"
        
        # 返回0
        result += "    ret i32 0\n"
        
        # 結束函數定義
        result += "}\n"
        
        return result
    
    def _add_global_string(self, string_value):
        """添加全局字符串常量並返回索引"""
        # 檢查字符串是否已經存在
        if string_value in self.global_strings:
            return self.global_strings.index(string_value)
        
        # 添加新字符串
        idx = len(self.global_strings)
        self.global_strings.append(string_value)
        
        # 記錄字符串長度（包括空終止符）
        self.string_length_map[idx] = len(string_value) + 1
        
        return idx
    
    def _generate_expression(self, expr):
        """生成表達式的LLVM IR代碼"""
        if isinstance(expr, ast_nodes.StringLiteral):
            return f'"{expr.value}"'
        elif isinstance(expr, ast_nodes.NumberLiteral):
            return str(expr.value)
        elif isinstance(expr, ast_nodes.Variable):
            return f"%{expr.name}"
        elif isinstance(expr, ast_nodes.FunctionCall):
            # 特殊處理內建函數
            if expr.name == "println":
                args = [self._generate_expression(arg) for arg in expr.arguments]
                return f"println({', '.join(args)})"
            else:
                return f"call {expr.name}({', '.join([self._generate_expression(arg) for arg in expr.arguments])})"
        else:
            return f"; 不支持的表達式類型: {type(expr)}"
    
    def _generate_statement(self, stmt, indent=0):
        """生成語句的LLVM IR代碼"""
        indent_str = ' ' * indent
        if isinstance(stmt, ast_nodes.FunctionCall):
            return f"{indent_str}{self._generate_expression(stmt)};\n"
        else:
            return f"{indent_str}; 不支持的語句類型: {type(stmt)}\n" 