"""
代碼生成器模組
負責將AST轉換為LLVM IR
"""

import logging
from typing import Dict, List, Optional, Any, Set, Tuple

from ..parser import ast_nodes
from ..type_system.type_system import TypeSystem
from ..type_system.type_defs import GluxType, TypeKind
from .base_generator import CodeGenerator


class LLVMCodeGenerator(CodeGenerator):
    """
    LLVM代碼生成器類
    將AST轉換為LLVM IR
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """初始化代碼生成器"""
        super().__init__(logger)
        self.string_counter = 0
        self.global_strings = {}
        self.var_counter = 0
        self.label_counter = 0
        self.function_counter = 0
        self.thread_counter = 0
        self.result_data = {}  # 保存併發任務的結果
        self.spawn_funcs = []  # 保存所有需要生成的併發函數
        self.error_instances = {}  # 保存錯誤實例
        self.error_counter = 0
        self.variables = {}  # 用於存儲變量類型信息
        self.symbol_table = None  # 符號表，用於在代碼生成階段獲取類型信息
        self.global_string_map = {}  # 保存所有全局字符串
        self.string_escape_cache = {}  # 保存轉義後的字符串和長度
        
    def _add_global_string(self, string: str) -> int:
        """
        添加全局字符串並返回索引
        
        Args:
            string: 要添加的字符串
            
        Returns:
            int: 字符串索引
        """
        # 如果字符串已經存在，直接返回索引
        if string in self.global_string_map:
            return self.global_string_map[string]
        
        # 否則，添加新字符串並返回新索引
        idx = len(self.global_string_map)
        self.global_string_map[string] = idx
        
        # 不再保存轉義後的字符串和長度
        escaped = self._escape_string(string)
        self.string_escape_cache = self.string_escape_cache or {}
        self.string_escape_cache[string] = escaped
        
        return idx
        
    def _get_byte_length(self, string: str) -> int:
        """
        計算字符串的位元組長度（包括空字符）
        
        Args:
            string: 輸入字符串
            
        Returns:
            int: 位元組長度
        """
        # 使用 UTF-8 編碼計算字符串的實際位元組長度
        byte_length = len(string.encode('utf-8'))
        return byte_length + 1  # +1 是為了包含 null 結束符
        
    def set_symbol_table(self, symbol_table):
        """設置符號表"""
        self.symbol_table = symbol_table
    
    def generate(self, ast):
        """生成 LLVM IR 代碼"""
        # 初始化計數器和數據結構
        self.var_counter = 0
        self.if_counter = 0
        self.while_counter = 0
        self.string_counter = 0
        self.temp_counter = 0
        self.current_function = None
        self.global_variable_map = {}
        self.local_variable_map = {}
        self.function_type_map = {}
        self.global_string_map = {}
        self.escaped_string_cache = {}
        
        # 存儲 AST 以備用
        if isinstance(ast, list):
            self.ast = ast
        else:
            # 如果 AST 是一個單一的對象而不是列表，將其轉換為列表
            if hasattr(ast, 'statements'):
                self.ast = ast.statements
            else:
                self.ast = [ast]

        # 收集字符串和信息
        self._collect_strings_from_ast(self.ast)

        # 生成 LLVM IR 代碼
        result = ""
        
        # 添加標準庫函數的聲明
        result += 'declare i32 @printf(i8* nocapture readonly, ...)\n'
        result += 'declare i32 @sprintf(i8* nocapture, i8* nocapture readonly, ...\n)\n'
        result += 'declare i32 @sleep(i32)\n'
        result += 'declare i64 @strlen(i8*)\n'
        result += 'declare i8* @malloc(i64)\n'
        result += 'declare i8* @strcpy(i8*, i8*)\n'
        result += 'declare void @free(i8*)\n'
        
        # 添加錯誤處理函數
        result += '; 錯誤處理函數\n'
        result += 'define void @print_error(i8* %msg) {\n'
        result += '    %1 = call i32 (i8*, ...) @printf(i8* %msg)\n'
        result += '    ret void\n'
        result += '}\n\n'
        
        # 生成全局變量
        for var_name, var_info in self.global_variable_map.items():
            var_type = var_info["type"]
            if var_type.startswith("string"):
                result += f'@{var_name} = global i8* null\n'
            elif var_type == "int":
                result += f'@{var_name} = global i32 0\n'
            elif var_type == "float" or var_type == "double":
                result += f'@{var_name} = global double 0.0\n'
            elif var_type == "bool":
                result += f'@{var_name} = global i1 false\n'
        
        # 生成全局字符串
        for string, idx in sorted(self.global_string_map.items(), key=lambda x: x[1]):
            # 對字符串進行簡單轉義處理
            escaped_string = self._escape_string(string)
            
            # 計算字符串長度（包括終止符）
            char_count = len(escaped_string.replace('\\', '').replace('\\00', '\0')) + 1
            
            # 生成全局字符串定義
            result += f'@.str.{idx} = private unnamed_addr constant [{char_count} x i8] c"{escaped_string}", align 1\n'
        
        # 添加空行
        result += '\n'
        
        # 定義 main 函數
        result += 'define i32 @main() {\n'
        result += 'entry:\n'
        
        # 處理所有語句
        result += '    ; 開始處理語句\n'
        for statement in self.ast:
            result += self._generate_statement(statement, 4)
        
        # 返回語句
        result += '    ret i32 0\n'
        result += '}\n'
        
        # 輸出生成的 LLVM IR 代碼，用於調試
        print("\n=== 生成的 LLVM IR 代碼 ===")
        print(result)
        print("=== LLVM IR 代碼結束 ===\n")
        
        self.logger.info(f"生成了 {len(result.splitlines())} 行LLVM IR代碼")
        return result
        
    def _generate_statement(self, stmt, indent=4):
        """生成單個語句的代碼"""
        # 創建縮進字符串
        indent_str = " " * indent
        
        result = f"{indent_str}; 開始處理語句\n"
        if isinstance(stmt, ast_nodes.ExpressionStatement):
            result += f"{indent_str}; 處理表達式語句\n"
            expr = stmt.expression
            if isinstance(expr, ast_nodes.CallExpression) and isinstance(expr.callee, ast_nodes.Variable):
                result += f"{indent_str}; 處理函數調用: {expr.callee.name}\n"
                if expr.callee.name == "println":
                    result += self._generate_println(expr.arguments)
                elif expr.callee.name == "print":
                    result += self._generate_print(expr.arguments)
                elif expr.callee.name == "error":
                    result += self._generate_error(expr)
                elif expr.callee.name == "is_error":
                    result += self._generate_is_error(expr)
                elif expr.callee.name == "sleep":
                    result += self._generate_sleep(expr)
                else:
                    # 其他函數調用
                    result += self._generate_function_call(expr)
            elif isinstance(expr, ast_nodes.SpawnExpression):
                result += self._generate_spawn(expr)
            elif isinstance(expr, ast_nodes.AwaitExpression):
                result += self._generate_await(expr)
            elif isinstance(expr, ast_nodes.BinaryExpr):
                result += self._generate_binary_expr(expr)
            elif isinstance(expr, ast_nodes.UnaryExpr):
                result += self._generate_unary_expr(expr)
            elif isinstance(expr, ast_nodes.AssignmentExpression):
                result += self._generate_assignment(expr)
            else:
                result += f"{indent_str}; 未處理的表達式類型: {type(expr)}\n"
        elif isinstance(stmt, ast_nodes.VarDeclaration):
            result += f"{indent_str}; 處理變量聲明\n"
            result += self._generate_var_declaration(stmt)
        elif isinstance(stmt, ast_nodes.ReturnStatement):
            result += f"{indent_str}; 處理返回語句\n"
            result += self._generate_return(stmt)
        elif isinstance(stmt, ast_nodes.BreakStatement):
            result += f"{indent_str}br label %end_loop\n"
        elif isinstance(stmt, ast_nodes.ContinueStatement):
            result += f"{indent_str}br label %continue_loop\n"
        elif isinstance(stmt, ast_nodes.If):
            result += f"{indent_str}; 處理if語句\n"
            result += self._generate_if(stmt)
        elif isinstance(stmt, ast_nodes.WhileStatement):
            result += f"{indent_str}; 處理while循環\n"
            result += self._generate_while(stmt)
        elif isinstance(stmt, ast_nodes.ForStatement):
            result += f"{indent_str}; 處理for循環\n"
            result += self._generate_for(stmt)
        else:
            result += f"{indent_str}; 未處理的語句類型: {type(stmt)}\n"
        
        return result
    
    def _collect_strings_from_ast(self, ast):
        """從 AST 中收集所有字符串"""
        # 檢查 AST 是否為列表
        if not isinstance(ast, list):
            # 單一語句，可能是單行代碼
            if hasattr(ast, 'statements'):
                statements = ast.statements
            else:
                # 無語句，直接返回
                return
        else:
            statements = ast
        
        # 遍歷所有語句收集字符串
        for stmt in statements:
            self._collect_strings_from_statement(stmt)

    def _collect_strings_from_statement(self, stmt):
        """從單個語句中收集字符串"""
        if isinstance(stmt, ast_nodes.ExpressionStatement):
            expr = stmt.expression
            if isinstance(expr, ast_nodes.CallExpression):
                # 處理函數調用中的字符串
                if hasattr(expr, 'callee') and isinstance(expr.callee, ast_nodes.Variable):
                    if expr.callee.name == "println" or expr.callee.name == "print":
                        for arg in expr.arguments:
                            if isinstance(arg, ast_nodes.StringLiteral):
                                # 添加字符串並加上換行符（對於 println）
                                if expr.callee.name == "println":
                                    self._add_global_string(arg.value + "\\0A\\00")
                                else:
                                    self._add_global_string(arg.value + "\\00")
                            elif isinstance(arg, ast_nodes.Variable):
                                # 添加格式字符串
                                if expr.callee.name == "println":
                                    self._add_global_string("%d\\0A\\00")  # 整數格式
                                    self._add_global_string("%f\\0A\\00")  # 浮點數格式
                                    self._add_global_string("%s\\0A\\00")  # 字符串格式
                                else:
                                    self._add_global_string("%d\\00")
                                    self._add_global_string("%f\\00")
                                    self._add_global_string("%s\\00")
                            elif isinstance(arg, ast_nodes.BinaryExpr):
                                # 處理二元表達式
                                self._collect_strings_from_expr(arg)

    def _collect_strings_from_expr(self, expr):
        """從表達式中收集字符串"""
        if isinstance(expr, ast_nodes.StringLiteral):
            self._add_global_string(expr.value + "\\00")
        elif isinstance(expr, ast_nodes.BinaryExpr):
            # 遞歸處理左右表達式
            self._collect_strings_from_expr(expr.left)
            self._collect_strings_from_expr(expr.right)

    def _generate_println(self, args):
        """
        生成 println 函數調用的 LLVM IR 代碼
        """
        result = "    ; println 函數調用\n"
        
        if not args:
            # 打印空行（只有換行符）
            newline_str = "\\0A\\00"
            str_idx, char_count = self._get_string_info(newline_str)
            result += f"    %println_str_{self.var_counter} = call i32 (i8*, ...) @printf(i8* getelementptr inbounds ([{char_count} x i8], [{char_count} x i8]* @.str.{str_idx}, i32 0, i32 0))\n"
            self.var_counter += 1
            return result
        
        for i, arg in enumerate(args):
            if isinstance(arg, ast_nodes.StringLiteral):
                # 字符串參數需要添加換行符
                string_val = arg.value + "\\0A\\00"  # 添加換行符和終止符
                str_idx, char_count = self._get_string_info(string_val)
                
                # 生成 printf 調用
                result += f"    %println_str_{self.var_counter} = call i32 (i8*, ...) @printf(i8* getelementptr inbounds ([{char_count} x i8], [{char_count} x i8]* @.str.{str_idx}, i32 0, i32 0))\n"
                self.var_counter += 1
            
            elif isinstance(arg, ast_nodes.Number):
                # 整數參數
                format_str = "%d\\0A\\00"  # 整數格式 + 換行符 + 終止符
                str_idx, char_count = self._get_string_info(format_str)
                
                # 生成 printf 調用
                result += f"    %println_int_{self.var_counter} = call i32 (i8*, ...) @printf(i8* getelementptr inbounds ([{char_count} x i8], [{char_count} x i8]* @.str.{str_idx}, i32 0, i32 0), i32 {arg.value})\n"
                self.var_counter += 1
            
            elif isinstance(arg, ast_nodes.Float):
                # 浮點數參數
                format_str = "%f\\0A\\00"  # 浮點數格式 + 換行符 + 終止符
                str_idx, char_count = self._get_string_info(format_str)
                
                # 生成 printf 調用
                result += f"    %println_float_{self.var_counter} = call i32 (i8*, ...) @printf(i8* getelementptr inbounds ([{char_count} x i8], [{char_count} x i8]* @.str.{str_idx}, i32 0, i32 0), double {arg.value})\n"
                self.var_counter += 1
            
            elif isinstance(arg, ast_nodes.Variable):
                # 變量參數
                var_name = arg.name
                if var_name in self.variables:
                    var_type = self.variables[var_name]['type']
                    
                    if var_type == 'i32':
                        # 整數變量
                        format_str = "%d\\0A\\00"
                        str_idx, char_count = self._get_string_info(format_str)
                        
                        # 加載變量值
                        result += f"    %var_val_{self.var_counter} = load i32, i32* %{var_name}\n"
                        
                        # 生成 printf 調用
                        result += f"    %println_format_{self.var_counter} = getelementptr inbounds ([{char_count} x i8], [{char_count} x i8]* @.str.{str_idx}, i32 0, i32 0)\n"
                        result += f"    %println_call_{self.var_counter} = call i32 (i8*, ...) @printf(i8* %println_format_{self.var_counter}, i32 %var_val_{self.var_counter})\n"
                        self.var_counter += 1
                    
                    elif var_type in ('float', 'double'):
                        # 浮點數變量
                        format_str = "%f\\0A\\00"
                        str_idx, char_count = self._get_string_info(format_str)
                        
                        # 加載變量值
                        result += f"    %var_val_{self.var_counter} = load {var_type}, {var_type}* %{var_name}\n"
                        
                        # 生成 printf 調用
                        result += f"    %println_format_{self.var_counter} = getelementptr inbounds ([{char_count} x i8], [{char_count} x i8]* @.str.{str_idx}, i32 0, i32 0)\n"
                        result += f"    %println_call_{self.var_counter} = call i32 (i8*, ...) @printf(i8* %println_format_{self.var_counter}, {var_type} %var_val_{self.var_counter})\n"
                        self.var_counter += 1
                    
                    elif var_type == 'i8*':
                        # 字符串變量
                        format_str = "%s\\0A\\00"
                        str_idx, char_count = self._get_string_info(format_str)
                        
                        # 加載變量值
                        result += f"    %var_val_{self.var_counter} = load i8*, i8** %{var_name}\n"
                        
                        # 生成 printf 調用
                        result += f"    %println_format_{self.var_counter} = getelementptr inbounds ([{char_count} x i8], [{char_count} x i8]* @.str.{str_idx}, i32 0, i32 0)\n"
                        result += f"    %println_call_{self.var_counter} = call i32 (i8*, ...) @printf(i8* %println_format_{self.var_counter}, i8* %var_val_{self.var_counter})\n"
                        self.var_counter += 1
                    
                    else:
                        # 未知類型變量，默認使用整數格式
                        format_str = "%d\\0A\\00"
                        str_idx, char_count = self._get_string_info(format_str)
                        
                        # 生成警告
                        result += f"    ; 警告：未知變量類型 {var_type}，默認使用整數格式\n"
                        
                        # 加載變量值
                        result += f"    %var_val_{self.var_counter} = load i32, i32* %{var_name}\n"
                        
                        # 生成 printf 調用
                        result += f"    %println_format_{self.var_counter} = getelementptr inbounds ([{char_count} x i8], [{char_count} x i8]* @.str.{str_idx}, i32 0, i32 0)\n"
                        result += f"    %println_call_{self.var_counter} = call i32 (i8*, ...) @printf(i8* %println_format_{self.var_counter}, i32 %var_val_{self.var_counter})\n"
                        self.var_counter += 1
                else:
                    # 變量未定義
                    default_msg = "變量未定義\\0A\\00"
                    str_idx, char_count = self._get_string_info(default_msg)
                    
                    # 生成 printf 調用
                    result += f"    %println_undefined_{self.var_counter} = call i32 (i8*, ...) @printf(i8* getelementptr inbounds ([{char_count} x i8], [{char_count} x i8]* @.str.{str_idx}, i32 0, i32 0))\n"
                    self.var_counter += 1
            
            elif isinstance(arg, ast_nodes.BinaryExpr):
                # 處理二元表達式
                if self._is_string_concatenation(arg):
                    # 處理字符串連接
                    result += self._generate_string_interpolation(arg)
                else:
                    # 數值表達式
                    binary_result = self._generate_binary_expr(arg)
                    result += binary_result['code']
                    
                    if binary_result['type'] == 'i32':
                        # 整數結果
                        format_str = "%d\\0A\\00"
                        str_idx, char_count = self._get_string_info(format_str)
                        
                        # 生成 printf 調用
                        result += f"    %print_format_{self.var_counter} = getelementptr inbounds ([{char_count} x i8], [{char_count} x i8]* @.str.{str_idx}, i32 0, i32 0)\n"
                        result += f"    %print_call_{self.var_counter} = call i32 (i8*, ...) @printf(i8* %print_format_{self.var_counter}, i32 %tmp_{binary_result['tmp']})\n"
                        self.var_counter += 1
                    elif binary_result['type'] in ('float', 'double'):
                        # 浮點數結果
                        format_str = "%f\\0A\\00"
                        str_idx, char_count = self._get_string_info(format_str)
                        
                        # 生成 printf 調用
                        result += f"    %print_format_{self.var_counter} = getelementptr inbounds ([{char_count} x i8], [{char_count} x i8]* @.str.{str_idx}, i32 0, i32 0)\n"
                        result += f"    %print_call_{self.var_counter} = call i32 (i8*, ...) @printf(i8* %print_format_{self.var_counter}, {binary_result['type']} %tmp_{binary_result['tmp']})\n"
                        self.var_counter += 1
            
            else:
                # 未處理的參數類型
                result += f"    ; 未處理的參數類型: {type(arg)}\n"
        
        return result

    def _generate_var_declaration(self, stmt):
        """代理方法，保持 API 相容性，將調用轉發給實際實現"""
        # 確保兼容舊版 CodeGenerator 的方法調用
        if hasattr(self, "_generate_var_declaration_impl"):
            return self._generate_var_declaration_impl(stmt)
        
        """生成變量聲明的 LLVM IR 代碼"""
        result = ""
        var_name = stmt.name
        
        if stmt.value:
            if isinstance(stmt.value, ast_nodes.Number):
                # 整數初始化
                value = stmt.value.value
                # 為新變量分配空間
                result += f"    %{var_name} = alloca i32\n"
                result += f"    store i32 {value}, i32* %{var_name}\n"
                # 記錄變量信息
                self.variables[var_name] = {'type': 'i32'}
            elif isinstance(stmt.value, ast_nodes.Float):
                # 浮點數初始化
                value = stmt.value.value
                # 為新變量分配空間 (使用 double)
                result += f"    %{var_name} = alloca double\n"
                result += f"    store double {value}, double* %{var_name}\n"
                # 記錄變量信息
                self.variables[var_name] = {'type': 'double'}
            elif isinstance(stmt.value, ast_nodes.StringLiteral):
                # 字符串初始化
                value = stmt.value.value
                # 添加全局字符串常量（包含null終止符）
                str_idx = self._add_global_string(value + "\\00")
                # 為新變量分配空間 (i8** 表示指向字符數組的指針)
                result += f"    %{var_name} = alloca i8*\n"
                # 存儲字符串指針
                result += f"    %str_ptr_{self.var_counter} = getelementptr inbounds ([{len(value) + 1} x i8], [{len(value) + 1} x i8]* @.str.{str_idx}, i32 0, i32 0)\n"
                result += f"    store i8* %str_ptr_{self.var_counter}, i8** %{var_name}\n"
                self.var_counter += 1
                # 記錄變量信息
                self.variables[var_name] = {'type': 'i8*'}
            elif isinstance(stmt.value, ast_nodes.BinaryExpr):
                # 檢查是否是字符串插值
                if self._is_string_interpolation(stmt.value):
                    # 字符串插值，當作字符串處理
                    result += f"    %{var_name} = alloca i8*\n"
                    self.variables[var_name] = {'type': 'i8*'}
                    
                    # 使用臨時變量創建格式化字符串
                    temp_str = f"temp_{self.var_counter}"
                    self.var_counter += 1
                    result += f"    %{temp_str} = alloca i8*\n"
                    
                    # 生成插值代碼，將結果存入臨時變量
                    interp_code = self._generate_string_interpolation_for_var(stmt.value, temp_str)
                    result += interp_code
                    
                    # 將臨時變量的值複製到目標變量
                    result += f"    %{temp_str}_load = load i8*, i8** %{temp_str}\n"
                    result += f"    store i8* %{temp_str}_load, i8** %{var_name}\n"
                else:
                    # 普通二元表達式初始化
                    binary_result = self._generate_binary_expr(stmt.value)
                    result += binary_result['code']
                    # 為新變量分配空間
                    result += f"    %{var_name} = alloca {binary_result['type']}\n"
                    result += f"    store {binary_result['type']} %tmp_{binary_result['tmp']}, {binary_result['type']}* %{var_name}\n"
                    # 記錄變量信息
                    self.variables[var_name] = {'type': binary_result['type']}
            elif isinstance(stmt.value, ast_nodes.Variable):
                # 變量初始化
                src_name = stmt.value.name
                if src_name in self.variables:
                    src_type = self.variables[src_name]['type']
                    # 為新變量分配相同類型的空間
                    result += f"    %{var_name} = alloca {src_type}\n"
                    # 加載源變量值
                    result += f"    %src_val_{self.var_counter} = load {src_type}, {src_type}* %{src_name}\n"
                    # 存儲到目標變量
                    result += f"    store {src_type} %src_val_{self.var_counter}, {src_type}* %{var_name}\n"
                    self.var_counter += 1
                    # 記錄變量信息
                    self.variables[var_name] = {'type': src_type}
                else:
                    # 源變量未找到，默認使用 i32 類型
                    result += f"    ; 警告：變量 {src_name} 未定義，使用默認 i32 類型\n"
                    result += f"    %{var_name} = alloca i32\n"
                    result += f"    %src_val_{self.var_counter} = load i32, i32* %{src_name}\n"
                    result += f"    store i32 %src_val_{self.var_counter}, i32* %{var_name}\n"
                    self.var_counter += 1
                    # 記錄變量信息
                    self.variables[var_name] = {'type': 'i32'}
            else:
                # 其他未處理的初始化器類型
                result += f"    ; 未處理的初始化器類型：{type(stmt.value).__name__}\n"
                # 默認使用 i32 類型
                result += f"    %{var_name} = alloca i32\n"
                # 記錄變量信息
                self.variables[var_name] = {'type': 'i32'}
        else:
            # 無初始化值，默認分配 i32 類型空間
            result += f"    %{var_name} = alloca i32\n"
            # 記錄變量信息
            self.variables[var_name] = {'type': 'i32'}
        
        return result

    def _generate_string_interpolation_for_var(self, expr, target_var):
        """
        為字符串插值生成 LLVM IR 代碼，並將結果保存到變量中
        
        Args:
            expr: 二元表達式，其中 + 操作符連接兩個字符串相關的表達式
            target_var: 存儲結果的目標變量
        
        Returns:
            str: 生成的 LLVM IR 代碼
        """
        # 預先添加所有可能需要的格式字符串
        self._add_global_string("%d\\00")  # 整數格式
        self._add_global_string("%f\\00")  # 浮點數格式
        self._add_global_string("%s\\00")  # 字符串格式
        
        result = "    ; 生成字符串插值並保存到變量\n"
        
        # 處理左表達式
        left_code = ""
        left_value = ""
        left_format = ""
        
        if isinstance(expr.left, ast_nodes.StringLiteral):
            # 左側是字符串字面量
            left_content = expr.left.value.replace('\\', '\\\\').replace('"', '\\"')
            left_format = left_content
        elif isinstance(expr.left, ast_nodes.Variable):
            # 左側是變量
            var_name = expr.left.name
            if var_name in self.variables:
                var_info = self.variables[var_name]
                var_type = var_info.get('type', 'i32')
                
                if var_type == 'i32':
                    left_format = "%d"
                    self._add_global_string(left_format)
                    left_code += f"    %var_left_{self.var_counter} = load i32, i32* %{var_name}\n"
                    left_value = f", i32 %var_left_{self.var_counter}"
                elif var_type in ('float', 'double'):
                    left_format = "%f"
                    self._add_global_string(left_format)
                    left_code += f"    %var_left_{self.var_counter} = load {var_type}, {var_type}* %{var_name}\n"
                    left_value = f", {var_type} %var_left_{self.var_counter}"
                elif var_type == 'i8*':
                    left_format = "%s"
                    self._add_global_string(left_format)
                    left_code += f"    %var_left_{self.var_counter} = load i8*, i8** %{var_name}\n"
                    left_value = f", i8* %var_left_{self.var_counter}"
            else:
                # 未知變量，假設為整數
                left_format = "%d"
                self._add_global_string(left_format)
                left_code += f"    %var_left_{self.var_counter} = load i32, i32* %{var_name}\n"
                left_value = f", i32 %var_left_{self.var_counter}"
        elif isinstance(expr.left, ast_nodes.Number):
            # 左側是整數字面量
            left_format = str(expr.left.value)
        elif isinstance(expr.left, ast_nodes.Float):
            # 左側是浮點數字面量
            left_format = str(expr.left.value)
        elif isinstance(expr.left, ast_nodes.BinaryExpr):
            # 處理二元表達式
            binary_result = self._generate_binary_expr(expr.left)
            left_code += binary_result['code']
            if binary_result['type'] == 'i32':
                left_format = "%d"
                left_value = f", i32 %tmp_{binary_result['tmp']}"
            elif binary_result['type'] in ('float', 'double'):
                left_format = "%f"
                left_value = f", {binary_result['type']} %tmp_{binary_result['tmp']}"
        
        # 處理右表達式
        right_code = ""
        right_value = ""
        right_format = ""
        
        if isinstance(expr.right, ast_nodes.StringLiteral):
            # 右側是字符串字面量
            right_content = expr.right.value.replace('\\', '\\\\').replace('"', '\\"')
            right_format = right_content
        elif isinstance(expr.right, ast_nodes.Variable):
            # 右側是變量
            var_name = expr.right.name
            if var_name in self.variables:
                var_info = self.variables[var_name]
                var_type = var_info.get('type', 'i32')
                
                if var_type == 'i32':
                    right_format = "%d"
                    self._add_global_string(right_format)
                    right_code += f"    %var_right_{self.var_counter} = load i32, i32* %{var_name}\n"
                    right_value = f", i32 %var_right_{self.var_counter}"
                elif var_type in ('float', 'double'):
                    right_format = "%f"
                    self._add_global_string(right_format)
                    right_code += f"    %var_right_{self.var_counter} = load {var_type}, {var_type}* %{var_name}\n"
                    right_value = f", {var_type} %var_right_{self.var_counter}"
                elif var_type == 'i8*':
                    right_format = "%s"
                    self._add_global_string(right_format)
                    right_code += f"    %var_right_{self.var_counter} = load i8*, i8** %{var_name}\n"
                    right_value = f", i8* %var_right_{self.var_counter}"
            else:
                # 未知變量，假設為整數
                right_format = "%d"
                self._add_global_string(right_format)
                right_code += f"    %var_right_{self.var_counter} = load i32, i32* %{var_name}\n"
                right_value = f", i32 %var_right_{self.var_counter}"
        elif isinstance(expr.right, ast_nodes.Number):
            # 右側是整數字面量
            right_format = str(expr.right.value)
        elif isinstance(expr.right, ast_nodes.Float):
            # 右側是浮點數字面量
            right_format = str(expr.right.value)
        elif isinstance(expr.right, ast_nodes.BinaryExpr):
            # 處理二元表達式
            binary_result = self._generate_binary_expr(expr.right)
            right_code += binary_result['code']
            if binary_result['type'] == 'i32':
                right_format = "%d"
                right_value = f", i32 %tmp_{binary_result['tmp']}"
            elif binary_result['type'] in ('float', 'double'):
                right_format = "%f"
                right_value = f", {binary_result['type']} %tmp_{binary_result['tmp']}"
        
        # 合併左右表達式代碼
        result += left_code + right_code
        
        # 創建包含左右格式的格式字符串
        combined_format = left_format + right_format + "\\00"
        
        # 添加格式字符串
        str_idx, char_count = self._get_string_info(combined_format)
        
        # 明確指定緩衝區大小並正確聲明類型
        result += f"    %temp_buffer_{self.var_counter} = alloca [256 x i8]\n"  # 創建固定大小的數組
        result += f"    %buffer_ptr_{self.var_counter} = getelementptr inbounds [256 x i8], [256 x i8]* %temp_buffer_{self.var_counter}, i32 0, i32 0\n"
        
        # 使用 sprintf 格式化字符串
        result += f"    %format_str_{self.var_counter} = getelementptr inbounds [{char_count} x i8], [{char_count} x i8]* @.str.{str_idx}, i32 0, i32 0\n"
        result += f"    call i32 (i8*, i8*, ...) @sprintf(i8* %buffer_ptr_{self.var_counter}, i8* %format_str_{self.var_counter}{left_value}{right_value})\n"
        
        # 給目標變量存儲結果
        result += f"    store i8* %buffer_ptr_{self.var_counter}, i8** %{target_var}\n"
        
        self.var_counter += 1
        return result

    def _generate_string_interpolation(self, expr, target_var=None):
        """生成字符串插值的 LLVM IR 代碼"""
        # 預先添加所有需要的格式字符串
        self._add_global_string("%s\\0A\\00")  # 字符串換行格式
        
        # 如果提供了目標變量，則使用更專用的函數
        if target_var:
            return self._generate_string_interpolation_for_var(expr, target_var)
            
        result = "    ; 生成字符串插值\n"
        
        # 處理左表達式
        left_code = ""
        left_value = ""
        left_format = ""
        
        if isinstance(expr.left, ast_nodes.StringLiteral):
            # 左側是字符串字面量
            left_content = expr.left.value.replace('\\', '\\\\').replace('"', '\\"')
            left_format = left_content
        elif isinstance(expr.left, ast_nodes.Variable):
            # 左側是變量
            var_name = expr.left.name
            if var_name in self.variables:
                var_info = self.variables[var_name]
                var_type = var_info.get('type', 'i32')
                
                if var_type == 'i32':
                    left_format = "%d"
                    left_code += f"    %var_left_{self.var_counter} = load i32, i32* %{var_name}\n"
                    left_value = f", i32 %var_left_{self.var_counter}"
                elif var_type in ('float', 'double'):
                    left_format = "%f"
                    left_code += f"    %var_left_{self.var_counter} = load {var_type}, {var_type}* %{var_name}\n"
                    left_value = f", {var_type} %var_left_{self.var_counter}"
                elif var_type == 'i8*':
                    left_format = "%s"
                    left_code += f"    %var_left_{self.var_counter} = load i8*, i8** %{var_name}\n"
                    left_value = f", i8* %var_left_{self.var_counter}"
            else:
                # 未知變量，假設為整數
                left_format = "%d"
                left_code += f"    %var_left_{self.var_counter} = load i32, i32* %{var_name}\n"
                left_value = f", i32 %var_left_{self.var_counter}"
        elif isinstance(expr.left, ast_nodes.Number):
            # 左側是整數字面量
            left_format = str(expr.left.value)
            left_code = ""
            left_value = ""
        elif isinstance(expr.left, ast_nodes.Float):
            # 左側是浮點數字面量
            left_format = str(expr.left.value)
            left_code = ""
            left_value = ""
        elif isinstance(expr.left, ast_nodes.BinaryExpr) and self._is_string_interpolation(expr.left):
            # 左側是嵌套的字符串插值
            nested_result = self._generate_string_interpolation(expr.left)
            left_code += nested_result
            right_result = self._generate_string_interpolation(expr.right)
            return left_code + right_result
        elif isinstance(expr.left, ast_nodes.BinaryExpr):
            # 處理二元表達式
            binary_result = self._generate_binary_expr(expr.left)
            left_code += binary_result['code']
            if binary_result['type'] == 'i32':
                left_format = "%d"
                left_value = f", i32 %tmp_{binary_result['tmp']}"
            elif binary_result['type'] in ('float', 'double'):
                left_format = "%f"
                left_value = f", {binary_result['type']} %tmp_{binary_result['tmp']}"
            else:
                left_format = "%s"
                left_value = f", {binary_result['type']} %tmp_{binary_result['tmp']}"
        
        # 處理右表達式
        right_code = ""
        right_value = ""
        right_format = ""
        
        if isinstance(expr.right, ast_nodes.StringLiteral):
            # 右側是字符串字面量
            right_content = expr.right.value.replace('\\', '\\\\').replace('"', '\\"')
            right_format = right_content
        elif isinstance(expr.right, ast_nodes.Variable):
            # 右側是變量
            var_name = expr.right.name
            if var_name in self.variables:
                var_info = self.variables[var_name]
                var_type = var_info.get('type', 'i32')
                
                if var_type == 'i32':
                    right_format = "%d"
                    right_code += f"    %var_right_{self.var_counter} = load i32, i32* %{var_name}\n"
                    right_value = f", i32 %var_right_{self.var_counter}"
                elif var_type in ('float', 'double'):
                    right_format = "%f"
                    right_code += f"    %var_right_{self.var_counter} = load {var_type}, {var_type}* %{var_name}\n"
                    right_value = f", {var_type} %var_right_{self.var_counter}"
                elif var_type == 'i8*':
                    right_format = "%s"
                    right_code += f"    %var_right_{self.var_counter} = load i8*, i8** %{var_name}\n"
                    right_value = f", i8* %var_right_{self.var_counter}"
            else:
                # 未知變量，假設為整數
                right_format = "%d"
                right_code += f"    %var_right_{self.var_counter} = load i32, i32* %{var_name}\n"
                right_value = f", i32 %var_right_{self.var_counter}"
        elif isinstance(expr.right, ast_nodes.Number):
            # 右側是整數字面量
            right_format = str(expr.right.value)
            right_code = ""
            right_value = ""
        elif isinstance(expr.right, ast_nodes.Float):
            # 右側是浮點數字面量
            right_format = str(expr.right.value)
            right_code = ""
            right_value = ""
        elif isinstance(expr.right, ast_nodes.BinaryExpr) and self._is_string_interpolation(expr.right):
            # 右側是嵌套的字符串插值
            nested_result = self._generate_string_interpolation(expr.right)
            right_code += nested_result
            return left_code + right_code
        elif isinstance(expr.right, ast_nodes.BinaryExpr):
            # 處理二元表達式
            binary_result = self._generate_binary_expr(expr.right)
            right_code += binary_result['code']
            if binary_result['type'] == 'i32':
                right_format = "%d"
                right_value = f", i32 %tmp_{binary_result['tmp']}"
            elif binary_result['type'] in ('float', 'double'):
                right_format = "%f"
                right_value = f", {binary_result['type']} %tmp_{binary_result['tmp']}"
            else:
                right_format = "%s"
                right_value = f", {binary_result['type']} %tmp_{binary_result['tmp']}"
        
        # 合併左右表達式代碼
        result += left_code + right_code
        
        # 創建包含左右格式的格式字符串
        combined_format = left_format + right_format + "\\00"
        
        # 添加格式字符串
        str_idx, _ = self._get_string_info(combined_format)
        
        # 明確指定緩衝區大小並正確聲明類型
        result += f"    %temp_buffer_{self.var_counter} = alloca [256 x i8]\n"  # 創建固定大小的數組
        result += f"    %buffer_ptr_{self.var_counter} = getelementptr inbounds [256 x i8], [256 x i8]* %temp_buffer_{self.var_counter}, i32 0, i32 0\n"
        
        # 使用 sprintf 格式化字符串
        result += f"    %format_str_{self.var_counter} = getelementptr inbounds [0 x i8], [0 x i8]* @.str.{str_idx}, i32 0, i32 0\n"
        result += f"    call i32 (i8*, i8*, ...) @sprintf(i8* %buffer_ptr_{self.var_counter}, i8* %format_str_{self.var_counter}{left_value}{right_value})\n"
        
        # 直接打印結果字符串
        format_str = "%s\\0A\\00"  # %s 格式化加換行符
        print_str_idx, print_byte_len = self._get_string_info(format_str)
        
        result += f"    %print_format_{self.var_counter} = getelementptr inbounds [{print_byte_len} x i8], [{print_byte_len} x i8]* @.str.{print_str_idx}, i32 0, i32 0\n"
        result += f"    %print_result_{self.var_counter} = call i32 (i8*, ...) @printf(i8* %print_format_{self.var_counter}, i8* %buffer_ptr_{self.var_counter})\n"
        
        self.var_counter += 1
        return result

    def _generate_error_functions(self):
        """
        生成錯誤處理函數的 LLVM IR 代碼
        
        Returns:
            str: 生成的 LLVM IR 代碼
        """
        result = ""
        
        # 生成錯誤處理函數，如 print_error
        result += "; 錯誤處理函數\n"
        result += "define void @print_error(i8* %msg) {\n"
        result += "    %1 = call i32 (i8*, ...) @printf(i8* %msg)\n"
        result += "    ret void\n"
        result += "}\n\n"
        
        return result

    def _is_string_interpolation(self, expr):
        """
        判斷表達式是否為字符串插值表達式
        
        Args:
            expr: 表達式對象
            
        Returns:
            bool: 如果是字符串插值表達式則返回 True，否則返回 False
        """
        # 檢查是否為二元表達式，且操作符為 +
        if not isinstance(expr, ast_nodes.BinaryExpr) or expr.operator != '+':
            return False
        
        # 檢查是否至少有一個操作數是字符串類型
        left_is_string = (isinstance(expr.left, ast_nodes.StringLiteral) or 
                         (isinstance(expr.left, ast_nodes.Variable) and 
                          expr.left.name in self.variables and 
                          self.variables[expr.left.name].get('type') == 'i8*'))
        
        right_is_string = (isinstance(expr.right, ast_nodes.StringLiteral) or 
                          (isinstance(expr.right, ast_nodes.Variable) and 
                           expr.right.name in self.variables and 
                           self.variables[expr.right.name].get('type') == 'i8*'))
        
        # 如果左右操作數中至少有一個是字符串，則認為是字符串插值
        return left_is_string or right_is_string

    def _escape_string(self, string):
        """對字符串進行轉義"""
        result = ""
        for char in string:
            if char == '\n':
                result += "\\0A"
            elif char == '\t':
                result += "\\09"
            elif char == '\r':
                result += "\\0D"
            elif char == '\0':
                result += "\\00"
            elif char == '\\':
                # 檢查反斜杠後是否有 0A 或 00 序列
                if string.find("\\0A", string.find(char)) > 0:
                    result += "\\"  # 只添加單個反斜杠，後面會添加正確的 \0A
                elif string.find("\\00", string.find(char)) > 0:
                    result += "\\"  # 只添加單個反斜杠，後面會添加正確的 \00
                else:
                    result += "\\\\"  # 一般反斜杠轉義
            elif char == '"':
                result += "\\\""
            else:
                result += char
        
        # 檢查字符串是否已經包含 \0A\00（換行符+終止符）
        if "\\0A\\00" not in string and "\\00" not in string:
            # 字符串不包含終止符，添加一個
            result += "\\00"
        
        return result

    def _get_string_info(self, string):
        """獲取字符串信息：全局索引和字節長度"""
        if string not in self.global_string_map:
            idx = len(self.global_string_map)
            self.global_string_map[string] = idx
        
        idx = self.global_string_map[string]
        # 計算字符串實際字節長度（包括空終止符）
        escaped_string = self._escape_string(string)
        # 在這裡使用與 generate 方法中相同的計算方式，確保一致性
        char_count = len(escaped_string.replace('\\', '').replace('\\00', '\0')) + 1
        return idx, char_count