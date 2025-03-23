"""
打印函數模組
負責生成打印相關的LLVM IR代碼
"""

from typing import List, Dict, Optional, Any
import logging

from ...parser import ast_nodes
from ..code_generator import CodeGenerator
from ..builtins import BuiltinModule


class PrintFunctions(BuiltinModule):
    """
    打印函數模組
    負責生成打印相關的LLVM IR代碼，如print和println函數
    """
    
    def __init__(self, parent=None):
        """初始化打印函數模組"""
        super().__init__(parent)
        self.parent = parent
        self.logger = None
        if parent and hasattr(parent, 'logger'):
            self.logger = parent.logger
        
    def set_parent(self, parent):
        """設置父級代碼生成器"""
        self.parent = parent
        if parent and hasattr(parent, 'logger'):
            self.logger = parent.logger
        return self
    
    def initialize(self, context=None):
        """初始化模塊（抽象方法實現）"""
        # 調用init方法來實際執行初始化
        return self.init()
    
    def init(self):
        """初始化模塊，註冊內建函數"""
        if not self.parent or not hasattr(self.parent, 'symbol_table'):
            if self.logger:
                self.logger.error("無法註冊內建函數：無父級代碼生成器或符號表")
            return False
            
        # 註冊print和println函數
        try:
            self.parent.symbol_table.register_builtin('print', 'function', return_type='void')
            self.parent.symbol_table.register_builtin('println', 'function', return_type='void')
            if self.logger:
                self.logger.debug("成功註冊內建打印函數")
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"註冊內建打印函數時出錯: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def generate_print(self, args: List[ast_nodes.Expression]) -> str:
        """
        生成print函數調用的LLVM IR代碼
        
        Args:
            args: 打印函數的參數列表
            
        Returns:
            str: 生成的LLVM IR代碼
        """
        # 如果沒有參數，則直接返回空代碼
        if not args or len(args) == 0:
            return "    ; 警告：print函數調用沒有參數\n"
        
        result = "    ; 處理print函數調用\n"
        
        # 逐一處理每個參數
        for i, arg in enumerate(args):
            if isinstance(arg, ast_nodes.StringLiteral):
                # 字符串參數
                string_idx = self.parent._add_global_string(arg.value)
                result += f"    %print_ptr_{i} = getelementptr [{self.parent.string_length_map[string_idx]} x i8], [{self.parent.string_length_map[string_idx]} x i8]* @.str.{string_idx}, i64 0, i64 0\n"
                result += f"    %print_result_{i} = call i32 (i8*, ...) @printf(i8* %print_ptr_{i})\n"
            elif isinstance(arg, ast_nodes.TemplateLiteral):
                # 模板字符串參數
                template_code = self.parent._generate_string_interpolation(arg)
                result += template_code
            elif isinstance(arg, ast_nodes.Number):
                # 數字參數
                if "." in str(arg.value) or "e" in str(arg.value).lower():
                    # 浮點數
                    format_idx = self.parent._add_global_string("%f")
                    result += f"    %print_ptr_{i} = getelementptr [{self.parent.string_length_map[format_idx]} x i8], [{self.parent.string_length_map[format_idx]} x i8]* @.str.{format_idx}, i64 0, i64 0\n"
                    result += f"    %print_result_{i} = call i32 (i8*, ...) @printf(i8* %print_ptr_{i}, double {arg.value})\n"
                else:
                    # 整數
                    format_idx = self.parent._add_global_string("%d")
                    result += f"    %print_ptr_{i} = getelementptr [{self.parent.string_length_map[format_idx]} x i8], [{self.parent.string_length_map[format_idx]} x i8]* @.str.{format_idx}, i64 0, i64 0\n"
                    result += f"    %print_result_{i} = call i32 (i8*, ...) @printf(i8* %print_ptr_{i}, i32 {arg.value})\n"
            elif isinstance(arg, ast_nodes.Variable):
                # 變量參數
                var_name = arg.name
                if var_name in self.parent.variables:
                    var_type = self.parent.variables[var_name].get('type', '')
                    
                    # 處理不同類型的變量
                    if var_type in ['int', 'i32']:
                        # 整數變量
                        format_idx = self.parent._add_global_string("%d")
                        result += f"    %print_ptr_{i} = getelementptr [{self.parent.string_length_map[format_idx]} x i8], [{self.parent.string_length_map[format_idx]} x i8]* @.str.{format_idx}, i64 0, i64 0\n"
                        if var_name in self.parent.global_variable_map:
                            # 全局變量
                            result += f"    %print_val_{i} = load i32, i32* @{var_name}\n"
                        else:
                            # 局部變量
                            result += f"    %print_val_{i} = load i32, i32* %{var_name}\n"
                        result += f"    %print_result_{i} = call i32 (i8*, ...) @printf(i8* %print_ptr_{i}, i32 %print_val_{i})\n"
                    elif var_type in ['double', 'float']:
                        # 浮點變量
                        format_idx = self.parent._add_global_string("%f")
                        result += f"    %print_ptr_{i} = getelementptr [{self.parent.string_length_map[format_idx]} x i8], [{self.parent.string_length_map[format_idx]} x i8]* @.str.{format_idx}, i64 0, i64 0\n"
                        if var_name in self.parent.global_variable_map:
                            # 全局浮點變量
                            result += f"    %print_val_{i} = load double, double* @{var_name}\n"
                        else:
                            # 局部浮點變量
                            result += f"    %print_val_{i} = load double, double* %{var_name}\n"
                        result += f"    %print_result_{i} = call i32 (i8*, ...) @printf(i8* %print_ptr_{i}, double %print_val_{i})\n"
                    elif var_type.startswith('string'):
                        # 字符串變量
                        format_idx = self.parent._add_global_string("%s")
                        result += f"    %print_ptr_{i} = getelementptr [{self.parent.string_length_map[format_idx]} x i8], [{self.parent.string_length_map[format_idx]} x i8]* @.str.{format_idx}, i64 0, i64 0\n"
                        if var_name in self.parent.global_variable_map:
                            # 全局字符串
                            result += f"    %print_val_{i} = load i8*, i8** @{var_name}\n"
                        else:
                            # 局部字符串
                            result += f"    %print_val_{i} = load i8*, i8** %{var_name}\n"
                        result += f"    %print_result_{i} = call i32 (i8*, ...) @printf(i8* %print_ptr_{i}, i8* %print_val_{i})\n"
                    else:
                        # 不支持的類型
                        result += f"    ; 警告：不支持的變量類型 '{var_type}' 用於打印\n"
                else:
                    # 未找到變量
                    result += f"    ; 警告：找不到變量 '{var_name}' 的類型信息\n"
            elif isinstance(arg, ast_nodes.BinaryExpr):
                # 二元表達式
                expr_result = self.parent._generate_binary_expression(arg)
                result += expr_result['code']
                
                if expr_result['type'] == 'i32':
                    # 整數表達式
                    format_idx = self.parent._add_global_string("%d")
                    result += f"    %print_ptr_{i} = getelementptr [{self.parent.string_length_map[format_idx]} x i8], [{self.parent.string_length_map[format_idx]} x i8]* @.str.{format_idx}, i64 0, i64 0\n"
                    result += f"    %print_result_{i} = call i32 (i8*, ...) @printf(i8* %print_ptr_{i}, i32 %tmp_{expr_result['tmp']})\n"
                elif expr_result['type'] == 'double':
                    # 浮點表達式
                    format_idx = self.parent._add_global_string("%f")
                    result += f"    %print_ptr_{i} = getelementptr [{self.parent.string_length_map[format_idx]} x i8], [{self.parent.string_length_map[format_idx]} x i8]* @.str.{format_idx}, i64 0, i64 0\n"
                    result += f"    %print_result_{i} = call i32 (i8*, ...) @printf(i8* %print_ptr_{i}, double %tmp_{expr_result['tmp']})\n"
                elif expr_result['type'].startswith('string'):
                    # 字符串表達式
                    format_idx = self.parent._add_global_string("%s")
                    result += f"    %print_ptr_{i} = getelementptr [{self.parent.string_length_map[format_idx]} x i8], [{self.parent.string_length_map[format_idx]} x i8]* @.str.{format_idx}, i64 0, i64 0\n"
                    result += f"    %print_result_{i} = call i32 (i8*, ...) @printf(i8* %print_ptr_{i}, i8* %tmp_{expr_result['tmp']})\n"
            else:
                # 不支持的參數類型
                result += f"    ; 警告：不支持的print參數類型 {type(arg)}\n"
                
        return result
    
    def generate_println(self, args):
        """
        生成println函數調用的LLVM IR代碼
        
        Args:
            args: 要打印的參數列表
        
        Returns:
            str: 包含LLVM IR代碼的字符串
        """
        result = "    ; println函數調用\n"
        
        if not args or len(args) == 0:
            # 無參數時，僅打印換行符
            result += f"    %println_result_0 = call i32 @printf(i8* getelementptr inbounds ([2 x i8], [2 x i8]* @.str.6, i64 0, i64 0))\n"
            return result
        
        # 獲取參數
        arg = args[0]
        
        if isinstance(arg, ast_nodes.StringLiteral):
            # 添加字符串到全局變量
            string_value = arg.value
            string_idx = self.parent._add_global_string(string_value)
            
            # 獲取字符串長度
            if string_idx in self.parent.string_length_map:
                byte_length = self.parent.string_length_map[string_idx]
                
                # 獲取字符串指針
                result += f"    %println_str_ptr = getelementptr inbounds [{byte_length} x i8], [{byte_length} x i8]* @.str.{string_idx}, i64 0, i64 0\n"
                
                # 打印字符串
                result += f"    %println_result = call i32 @printf(i8* %println_str_ptr)\n"
                
                # 添加換行符
                result += f"    %println_newline = call i32 @printf(i8* getelementptr inbounds ([2 x i8], [2 x i8]* @.str.6, i64 0, i64 0))\n"
            else:
                result += f"    ; 錯誤：找不到字符串 \"{string_value}\" 的長度信息\n"
        elif isinstance(arg, ast_nodes.Number):
            # 打印數字 + 換行符
            if "." in str(arg.value):
                # 浮點數
                result += f"    %println_float = fpext float {arg.value} to double\n"
                result += f"    %println_result_0 = call i32 (i8*, ...) @printf(i8* getelementptr inbounds ([4 x i8], [4 x i8]* @.str.5, i64 0, i64 0), double %println_float)\n"
            else:
                # 整數
                result += f"    %println_result_0 = call i32 (i8*, ...) @printf(i8* getelementptr inbounds ([4 x i8], [4 x i8]* @.str.3, i64 0, i64 0), i32 {arg.value})\n"
        else:
            # 其他類型：作為未知類型處理
            result += f"    ; 警告：不支持的println參數類型 {type(arg)}，使用默認信息\n"
            result += f"    %println_result_0 = call i32 @printf(i8* getelementptr inbounds ([12 x i8], [12 x i8]* @.str.0, i64 0, i64 0))\n"
        
        return result 