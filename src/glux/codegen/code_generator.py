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
        
    def generate(self, ast):
        """生成 LLVM IR 代碼"""
        self.result = ""
        self.var_counter = 0  # 變量計數器
        self.label_counter = 0  # 標籤計數器
        self.string_counter = 0  # 字符串計數器
        self.error_counter = 0  # 錯誤計數器
        self.string_map = {}  # 字符串映射 (轉義字符串 -> 索引)
        self.global_strings = {}  # 全局字符串 (變量名 -> 值)
        self.error_instances = {}  # 錯誤實例 (索引 -> (代碼, 消息))
        self.result_data = {}  # 重置結果數據字典
        
        # 第一步：收集所有字符串和函數定義
        self._collect_items(ast)
        
        # 生成模塊頭
        self.result += "; 這是生成的 LLVM IR 代碼\n"
        self.result += "declare i32 @printf(i8*, ...)\n\n"
        
        # 生成任務和併發相關的結構體定義
        self.result += "; 併發相關的結構體定義\n"
        self.result += "%task_struct = type { i8*, i1, i32 }\n"  # 函數指針, 是否完成, 結果值
        
        # 生成元組類型定義（用於多await結果）
        self.result += "; 元組類型定義\n"
        self.result += "%tuple2_struct = type { i32, i32 }\n"
        self.result += "%tuple3_struct = type { i32, i32, i32 }\n"
        self.result += "%tuple4_struct = type { i32, i32, i32, i32 }\n"
        
        # 生成全局字符串定義
        for string, idx in sorted(self.string_map.items(), key=lambda x: x[1]):
            # 計算字符串在UTF-8下的實際字節長度
            byte_len = self._get_byte_length(string)
            
            # 生成全局字符串常量定義
            self.result += f'@.str.{idx} = private unnamed_addr constant [{byte_len} x i8] c"{string}", align 1\n'
        
        self.result += "\n"  # 加一個空行分隔
        
        # 生成錯誤類型定義
        if self.error_counter > 0:
            self.result += "\n; 錯誤類型定義\n"
            self.result += "%error_t = type { i32, i8* }\n\n"
            
            # 生成全局錯誤實例
            for error_idx, (error_code, error_msg) in self.error_instances.items():
                self.result += f"@error_{error_idx} = private global %error_t {{ i32 {error_code}, i8* null }}\n"
            
            # 生成錯誤處理函數
            self.result += "\n; 錯誤處理函數\n"
            self.result += "define %error_t @create_error(i32 %code, i8* %message) {\n"
            self.result += "    %error = alloca %error_t\n"
            self.result += "    %code_ptr = getelementptr %error_t, %error, i32 0, i32 0\n"
            self.result += "    store i32 %code, i32* %code_ptr\n"
            self.result += "    %msg_ptr = getelementptr %error_t, %error, i32 0, i32 1\n"
            self.result += "    store i8* %message, i8** %msg_ptr\n"
            self.result += "    %result = load %error_t, %error\n"
            self.result += "    ret %error_t %result\n"
            self.result += "}\n\n"
            
            self.result += "define i1 @is_error_check(i8* %value) {\n"
            self.result += "    %is_error = icmp ne i8* %value, null\n"
            self.result += "    ret i1 %is_error\n"
            self.result += "}\n\n"
        
        # 生成主函數
        self.result += "define i32 @main() {\n"
        
        # 生成語句的代碼
        for stmt in ast.statements:
            if isinstance(stmt, ast_nodes.ExpressionStatement):
                expr = stmt.expression
                if isinstance(expr, ast_nodes.CallExpression) and isinstance(expr.callee, ast_nodes.Variable):
                    if expr.callee.name == "println":
                        self.result += self._generate_println(expr)
                    elif expr.callee.name == "error":
                        self.result += self._generate_error(expr)
                    elif expr.callee.name == "is_error":
                        self.result += self._generate_is_error(expr)
                    elif expr.callee.name == "sleep":
                        self.result += self._generate_sleep(expr)
                elif isinstance(expr, ast_nodes.SpawnExpression):
                    self.result += self._generate_spawn(expr)
                elif isinstance(expr, ast_nodes.AwaitExpression):
                    self.result += self._generate_await(expr)
                elif isinstance(expr, ast_nodes.GetExpression):
                    # 處理成員訪問（如：results.0）
                    self.result += self._generate_member_access(expr)
                elif isinstance(expr, ast_nodes.ConditionalExpression):
                    # 處理條件表達式（三元運算符）
                    self.result += self._generate_conditional_expression(expr)
            elif isinstance(stmt, ast_nodes.IfStatement):
                self.result += self._generate_if_statement(stmt)
            elif isinstance(stmt, ast_nodes.VarDeclaration):
                self.result += self._generate_var_declaration(stmt)
            elif isinstance(stmt, ast_nodes.ConstDeclaration):
                self.result += self._generate_const_declaration(stmt)
        
        # 生成函數返回
        self.result += "    ret i32 0\n"
        self.result += "}\n"
        
        return self.result
        
    def _collect_items(self, ast):
        """收集 AST 中的所有字符串和函數定義"""
        # 迭代所有語句
        for stmt in ast.statements:
            self._collect_items_from_stmt(stmt)
    
    def _collect_items_from_stmt(self, stmt):
        """從單個語句收集項目"""
        if isinstance(stmt, ast_nodes.ExpressionStatement):
            expr = stmt.expression
            if isinstance(expr, ast_nodes.CallExpression) and isinstance(expr.callee, ast_nodes.Variable):
                if expr.callee.name == "println":
                    # 處理 println 調用中的字符串
                    for arg in expr.arguments:
                        if isinstance(arg, ast_nodes.StringLiteral):
                            # 添加帶換行符的字符串
                            self._add_global_string(arg.value + "\\0A\\00")
                        elif isinstance(arg, ast_nodes.Variable):
                            # 添加整數格式字符串
                            self._add_global_string("%d\\0A\\00")
                elif expr.callee.name == "error":
                    # 處理 error 函數調用
                    if expr.arguments:
                        # 收集錯誤消息字符串
                        self._collect_string_from_expr(expr.arguments[0])
                        # 給這個錯誤實例分配一個索引
                        error_idx = self.error_counter
                        self.error_counter += 1
                        # 保存錯誤代碼（若提供）和錯誤消息
                        error_code = 1  # 默認錯誤代碼
                        if len(expr.arguments) > 1:
                            # 如果提供了錯誤代碼，使用它
                            if isinstance(expr.arguments[1], ast_nodes.Number):
                                error_code = expr.arguments[1].value
                        self.error_instances[error_idx] = (error_code, expr.arguments[0])
        elif isinstance(stmt, ast_nodes.IfStatement):
            # 處理條件表達式
            if isinstance(stmt.condition, ast_nodes.BinaryExpr):
                if isinstance(stmt.condition.left, ast_nodes.StringLiteral):
                    self._collect_string_from_expr(stmt.condition.left)
                if isinstance(stmt.condition.right, ast_nodes.StringLiteral):
                    self._collect_string_from_expr(stmt.condition.right)
            
            # 處理 then 分支
            if isinstance(stmt.body, ast_nodes.BlockStatement):
                # 如果是 BlockStatement，迭代其中的語句
                for s in stmt.body.statements:
                    self._collect_items_from_stmt(s)
            elif isinstance(stmt.body, list):
                # 如果是語句列表，迭代處理
                for s in stmt.body:
                    self._collect_items_from_stmt(s)
            else:
                # 單個語句
                self._collect_items_from_stmt(stmt.body)
            
            # 處理 else 分支（如果有）
            if stmt.else_body:
                if isinstance(stmt.else_body, ast_nodes.BlockStatement):
                    # 如果是 BlockStatement，迭代其中的語句
                    for s in stmt.else_body.statements:
                        self._collect_items_from_stmt(s)
                elif isinstance(stmt.else_body, list):
                    # 如果是語句列表，迭代處理
                    for s in stmt.else_body:
                        self._collect_items_from_stmt(s)
                else:
                    # 單個語句
                    self._collect_items_from_stmt(stmt.else_body)
        elif isinstance(stmt, ast_nodes.VarDeclaration):
            # 處理變量聲明的初始化表達式
            if stmt.value and isinstance(stmt.value, ast_nodes.StringLiteral):
                self._collect_string_from_expr(stmt.value)
        elif isinstance(stmt, ast_nodes.ConstDeclaration):
            # 處理常量聲明的初始化表達式
            if stmt.value and isinstance(stmt.value, ast_nodes.StringLiteral):
                self._collect_string_from_expr(stmt.value)
    
    def _collect_expr_items(self, expr):
        """從單個表達式收集項目"""
        if isinstance(expr, ast_nodes.StringLiteral):
            # 處理字符串字面量
            if hasattr(expr, 'is_raw') and expr.is_raw:
                # 處理模板字符串（反引號）
                string_value = expr.value
                if '${' in string_value:
                    # 模板字符串包含插值表達式
                    pass
            else:
                # 普通字符串
                string_value = expr.value + "\\00"
                self._add_global_string(string_value)
        elif isinstance(expr, ast_nodes.CallExpression):
            # 處理函數調用中的參數
            for arg in expr.arguments:
                self._collect_expr_items(arg)
        elif isinstance(expr, ast_nodes.BinaryExpr):
            # 處理二元表達式的左右操作數
            self._collect_expr_items(expr.left)
            self._collect_expr_items(expr.right)
        elif isinstance(expr, ast_nodes.GetExpression):
            # 處理成員訪問表達式
            self._collect_expr_items(expr.object)
        elif isinstance(expr, ast_nodes.SpawnExpression):
            # 處理 spawn 表達式
            if isinstance(expr.function_call, ast_nodes.CallExpression):
                self._collect_expr_items(expr.function_call)
        elif isinstance(expr, ast_nodes.AwaitExpression):
            # 處理 await 表達式
            for task_expr in expr.expressions:
                self._collect_expr_items(task_expr)
        elif isinstance(expr, ast_nodes.ConditionalExpression):
            # 處理條件表達式（三元運算符）
            self._collect_expr_items(expr.condition)
            self._collect_expr_items(expr.then_expr)
            self._collect_expr_items(expr.else_expr)

    def _generate_conditional_expression(self, expr):
        """生成條件表達式（三元運算符）的 LLVM IR 代碼"""
        result = "    ; 條件表達式（三元運算符）\n"
        
        # 生成唯一的標籤
        then_label = f"cond_then_{self.label_counter}"
        else_label = f"cond_else_{self.label_counter}"
        end_label = f"cond_end_{self.label_counter}"
        self.label_counter += 1
        
        # 為結果分配內存
        result += f"    %cond_result_{self.var_counter} = alloca i32\n"
        
        # 生成條件表達式
        if isinstance(expr.condition, ast_nodes.BinaryExpr):
            # 處理二元表達式作為條件
            if expr.condition.operator in ["<", ">", "<=", ">=", "==", "!="]:
                # 比較運算
                cond_result = self._generate_comparison(expr.condition)
                result += cond_result
                result += f"    %cond_value_{self.var_counter} = load i1, i1* %comp_result_{self.var_counter-1}\n"
            else:
                # 其他二元運算，假設結果為真
                # 這裡可以添加更多處理，例如檢查結果是否為0
                result += f"    ; 警告：將使用二元運算結果作為布爾值\n"
                result += f"    %cond_value_{self.var_counter} = icmp ne i32 1, 0\n"
        else:
            # 假設是變量或其他表達式
            # 這裡可以添加更多處理
            result += f"    ; 警告：將使用表達式結果作為布爾值\n"
            result += f"    %cond_value_{self.var_counter} = icmp ne i32 1, 0\n"
        
        # 條件跳轉
        result += f"    br i1 %cond_value_{self.var_counter}, label %{then_label}, label %{else_label}\n"
        
        # then 分支
        result += f"\n{then_label}:\n"
        # 生成 then 表達式的代碼
        if isinstance(expr.then_expr, ast_nodes.Number):
            result += f"    store i32 {expr.then_expr.value}, i32* %cond_result_{self.var_counter}\n"
        else:
            # 可以添加更多表達式處理
            result += f"    ; 警告：未處理的表達式類型 {type(expr.then_expr)}\n"
            result += f"    store i32 1, i32* %cond_result_{self.var_counter}\n"
        
        result += f"    br label %{end_label}\n"
        
        # else 分支
        result += f"\n{else_label}:\n"
        # 生成 else 表達式的代碼
        if isinstance(expr.else_expr, ast_nodes.Number):
            result += f"    store i32 {expr.else_expr.value}, i32* %cond_result_{self.var_counter}\n"
        else:
            # 可以添加更多表達式處理
            result += f"    ; 警告：未處理的表達式類型 {type(expr.else_expr)}\n"
            result += f"    store i32 0, i32* %cond_result_{self.var_counter}\n"
        
        result += f"    br label %{end_label}\n"
        
        # 結束標籤
        result += f"\n{end_label}:\n"
        
        self.var_counter += 1
        return result
    
    def _collect_string_from_expr(self, expr):
        """從表達式中收集字符串"""
        if isinstance(expr, ast_nodes.StringLiteral):
            # 檢查是否是反引號字符串（模板字符串）
            if hasattr(expr, 'is_raw') and expr.is_raw:
                # 處理模板字符串中的插值
                template_str = expr.value
                
                # 對於簡單起見，將所有變量插值處理為整數格式化字符串
                formatted_str = ""
                i = 0
                while i < len(template_str):
                    if template_str[i:i+2] == "${" and i + 2 < len(template_str):
                        # 找到插值結束位置
                        j = i + 2
                        while j < len(template_str) and template_str[j] != "}":
                            j += 1
                        
                        if j < len(template_str):  # 找到了結束括號
                            # 添加%d作為變量插值的佔位符
                            formatted_str += "%d"
                            i = j + 1  # 跳過整個${...}部分
                        else:
                            # 未閉合的插值表達式，保留原樣
                            formatted_str += template_str[i]
                            i += 1
                    else:
                        formatted_str += template_str[i]
                        i += 1
                
                # 將處理後的字符串添加為全局常量
                self._add_global_string(formatted_str + "\\0A\\00")
                
                # 同時添加整數格式字符串，用於加載變量
                self._add_global_string("%d\\00")
            else:
                # 普通字符串字面量
                self._add_global_string(expr.value + "\\00")
        elif isinstance(expr, ast_nodes.BinaryExpr) and expr.operator == "+":
            # 處理字符串連接
            self._collect_string_from_expr(expr.left)
            self._collect_string_from_expr(expr.right)
        elif isinstance(expr, ast_nodes.Variable):
            # 變量，添加整數格式字符串
            self._add_global_string("%d\\00")
        elif isinstance(expr, ast_nodes.Number):
            # 數字，不需要特殊處理
            pass
        elif isinstance(expr, ast_nodes.StringInterpolation):
            # 處理字符串插值對象
            for part in expr.parts:
                self._collect_string_from_expr(part)
        elif isinstance(expr, ast_nodes.CallExpression):
            # 處理函數調用參數
            for arg in expr.arguments:
                self._collect_string_from_expr(arg)
    
    def _generate_println(self, expr):
        """生成 println 函數調用的 LLVM IR 代碼"""
        result = ""
        
        if not expr.arguments:
            # 如果沒有參數，則打印空行
            format_str = "\\0A\\00"  # 換行符加空終止符
            format_str_idx = self._add_global_string(format_str)
            byte_len = self._get_byte_length(format_str)
            result += f"    call i32 (i8*, ...) @printf(i8* getelementptr inbounds ([{byte_len} x i8], [{byte_len} x i8]* @.str.{format_str_idx}, i32 0, i32 0))\n"
            return result
            
        # 處理 println 的參數
        for arg in expr.arguments:
            if isinstance(arg, ast_nodes.StringLiteral):
                # 直接打印字符串
                content = arg.value + "\\0A\\00"  # 添加換行符和空終止符
                str_idx = self._add_global_string(content)
                byte_len = self._get_byte_length(content)
                result += f"    call i32 (i8*, ...) @printf(i8* getelementptr inbounds ([{byte_len} x i8], [{byte_len} x i8]* @.str.{str_idx}, i32 0, i32 0))\n"
            elif isinstance(arg, ast_nodes.Number):
                # 打印數字
                format_str = "%d\\0A\\00"  # 整數格式加換行和空終止符
                format_str_idx = self._add_global_string(format_str)
                byte_len = self._get_byte_length(format_str)
                result += f"    call i32 (i8*, ...) @printf(i8* getelementptr inbounds ([{byte_len} x i8], [{byte_len} x i8]* @.str.{format_str_idx}, i32 0, i32 0), i32 {arg.value})\n"
            elif isinstance(arg, ast_nodes.Variable):
                # 假設變量是整數類型
                format_str = "%d\\0A\\00"  # 整數格式加換行和空終止符
                format_str_idx = self._add_global_string(format_str)
                byte_len = self._get_byte_length(format_str)
                result += f"    %var_{self.var_counter} = load i32, i32* %{arg.name}\n"
                result += f"    call i32 (i8*, ...) @printf(i8* getelementptr inbounds ([{byte_len} x i8], [{byte_len} x i8]* @.str.{format_str_idx}, i32 0, i32 0), i32 %var_{self.var_counter})\n"
                self.var_counter += 1
        
        return result
        
    def _generate_sleep(self, expr):
        """生成 sleep 語句的 LLVM IR"""
        result = "    ; 生成 sleep 調用\n"
        if len(expr.arguments) > 0:
            # 假設參數是常量整數
            if isinstance(expr.arguments[0], ast_nodes.Number):
                seconds = int(float(expr.arguments[0].value) * 1000)  # 轉換為毫秒
                result += f"    call void @sleep(i32 {seconds})\n"
        return result
    
    def _generate_spawn(self, expr):
        """生成 spawn 表達式的 LLVM IR 代碼"""
        result = "    ; spawn 表達式 - 創建並啟動一個新任務\n"
        
        if isinstance(expr, ast_nodes.SpawnExpression):
            function_call = expr.function_call
            if isinstance(function_call, ast_nodes.CallExpression):
                # 獲取函數名稱和參數
                if isinstance(function_call.callee, ast_nodes.Variable):
                    function_name = function_call.callee.name
                    
                    # 創建一個唯一的標識符來表示這個異步任務
                    task_id = self.var_counter
                    self.var_counter += 1
                    
                    # 分配任務結構體內存
                    result += f"    %task_{task_id} = alloca %task_struct\n"
                    
                    # 設置任務函數指針
                    result += f"    %task_func_ptr_{task_id} = getelementptr %task_struct, %task_struct* %task_{task_id}, i32 0, i32 0\n"
                    result += f"    store i8* @{function_name}, i8** %task_func_ptr_{task_id}\n"
                    
                    # 設置任務狀態（初始為未完成）
                    result += f"    %task_complete_ptr_{task_id} = getelementptr %task_struct, %task_struct* %task_{task_id}, i32 0, i32 1\n"
                    result += f"    store i1 false, i1* %task_complete_ptr_{task_id}\n"
                    
                    # 處理參數
                    args_str = ""
                    for i, arg in enumerate(function_call.arguments):
                        if isinstance(arg, ast_nodes.Number):
                            args_str += f", i32 {arg.value}"
                        elif isinstance(arg, ast_nodes.Variable):
                            result += f"    %spawn_arg_{task_id}_{i} = load i32, i32* %{arg.name}\n"
                            args_str += f", i32 %spawn_arg_{task_id}_{i}"
                    
                    # 調用函數
                    result += f"    %spawn_result_{task_id} = call i32 @{function_name}({args_str[2:] if args_str else ''})\n"
                    
                    # 存儲結果
                    result += f"    %task_result_ptr_{task_id} = getelementptr %task_struct, %task_struct* %task_{task_id}, i32 0, i32 2\n"
                    result += f"    store i32 %spawn_result_{task_id}, i32* %task_result_ptr_{task_id}\n"
                    
                    # 設置任務為已完成
                    result += f"    store i1 true, i1* %task_complete_ptr_{task_id}\n"
                    
                    # 將任務指針存儲在一個變數中
                    # 這個變數將被後續的 await 表達式使用
                    result += f"    ; 保存任務指針，以便後續 await 使用\n"
                    # 創建任務指針變數
                    result += f"    %task_var_{task_id} = alloca i8*\n"
                    # 將任務結構體指針轉換為 i8*
                    result += f"    %task_ptr_{task_id} = bitcast %task_struct* %task_{task_id} to i8*\n"
                    # 存儲任務指針
                    result += f"    store i8* %task_ptr_{task_id}, i8** %task_var_{task_id}\n"
                    
                    # 返回任務指針變數
                    # 不要依賴 expr 變數，直接使用任務 ID
                    self.result_data[expr] = (f"task_var_{task_id}", "i8*")
                    
                    return result
        
        # 處理錯誤情況
        return result + "    ; 無法解析 spawn 表達式，生成空代碼\n"

    def _generate_await(self, expr):
        """生成 await 表達式的 LLVM IR 代碼"""
        result = "    ; await 表達式 - 等待一個或多個異步任務完成\n"
        
        if isinstance(expr, ast_nodes.AwaitExpression):
            expressions = expr.expressions
            
            # 單一 await 處理
            if len(expressions) == 1:
                task_expr = expressions[0]
                if isinstance(task_expr, ast_nodes.CallExpression) and isinstance(task_expr.callee, ast_nodes.Variable):
                    task_var = task_expr.callee.name
                    
                    # 獲取任務變數名稱
                    # 這是從 spawn 表達式中獲取的任務指針變數
                    task_var_name = ""
                    for key, value in self.result_data.items():
                        if isinstance(key, ast_nodes.SpawnExpression) and isinstance(key.function_call, ast_nodes.CallExpression):
                            if isinstance(key.function_call.callee, ast_nodes.Variable) and key.function_call.callee.name == task_var:
                                task_var_name = value[0]
                                break
                    
                    # 如果找不到任務變數，使用一個默認的處理方式
                    if not task_var_name:
                        result += f"    ; 警告：無法找到任務 {task_var} 的指針變數\n"
                        result += f"    %await_result_{self.var_counter} = call i32 @{task_var}()\n"
                        self.var_counter += 1
                        return result
                    
                    # 獲取任務指針
                    result += f"    %await_task_ptr_{self.var_counter} = load i8*, i8** %{task_var_name}\n"
                    
                    # 獲取任務結果
                    result += f"    %await_task_{self.var_counter} = bitcast i8* %await_task_ptr_{self.var_counter} to %task_struct*\n"
                    result += f"    %await_result_ptr_{self.var_counter} = getelementptr %task_struct, %task_struct* %await_task_{self.var_counter}, i32 0, i32 2\n"
                    result += f"    %await_result_{self.var_counter} = load i32, i32* %await_result_ptr_{self.var_counter}\n"
                    
                    # 保存結果，以便後續使用
                    self.result_data[expr] = (f"await_result_{self.var_counter}", "i32")
                    
                    self.var_counter += 1
                    return result
            
            # 多 await 處理 (等待多個任務，返回結果元組)
            elif len(expressions) > 1:
                result += f"    ; 等待多個任務完成並返回結果元組\n"
                
                await_tuple_id = self.var_counter
                self.var_counter += 1
                
                # 分配結果元組空間
                result += f"    %await_tuple_{await_tuple_id} = alloca %tuple{len(expressions)}_struct\n"
                
                # 處理每個任務
                for i, task_expr in enumerate(expressions):
                    if isinstance(task_expr, ast_nodes.CallExpression) and isinstance(task_expr.callee, ast_nodes.Variable):
                        task_var = task_expr.callee.name
                        
                        # 獲取任務變數名稱
                        task_var_name = ""
                        for key, value in self.result_data.items():
                            if isinstance(key, ast_nodes.SpawnExpression) and isinstance(key.function_call, ast_nodes.CallExpression):
                                if isinstance(key.function_call.callee, ast_nodes.Variable) and key.function_call.callee.name == task_var:
                                    task_var_name = value[0]
                                    break
                        
                        # 如果找不到任務變數，使用一個默認的處理方式
                        if not task_var_name:
                            result += f"    ; 警告：無法找到任務 {task_var} 的指針變數\n"
                            result += f"    %await_result_{await_tuple_id}_{i} = call i32 @{task_var}()\n"
                        else:
                            # 獲取任務指針
                            result += f"    %await_task_ptr_{await_tuple_id}_{i} = load i8*, i8** %{task_var_name}\n"
                            
                            # 獲取任務結果
                            result += f"    %await_task_{await_tuple_id}_{i} = bitcast i8* %await_task_ptr_{await_tuple_id}_{i} to %task_struct*\n"
                            result += f"    %await_result_ptr_{await_tuple_id}_{i} = getelementptr %task_struct, %task_struct* %await_task_{await_tuple_id}_{i}, i32 0, i32 2\n"
                            result += f"    %await_result_{await_tuple_id}_{i} = load i32, i32* %await_result_ptr_{await_tuple_id}_{i}\n"
                        
                        # 存儲到元組中
                        result += f"    %tuple_elem_ptr_{await_tuple_id}_{i} = getelementptr %tuple{len(expressions)}_struct, %tuple{len(expressions)}_struct* %await_tuple_{await_tuple_id}, i32 0, i32 {i}\n"
                        result += f"    store i32 %await_result_{await_tuple_id}_{i}, i32* %tuple_elem_ptr_{await_tuple_id}_{i}\n"
                
                # 保存元組結果，以便後續使用
                self.result_data[expr] = (f"await_tuple_{await_tuple_id}", f"tuple{len(expressions)}_struct*")
                
                return result
        
        # 處理錯誤情況
        return result + "    ; 無法解析 await 表達式，生成空代碼\n"
    
    def _generate_var_declaration(self, stmt):
        """生成變量聲明的 LLVM IR 代碼"""
        result = "    ; 變量聲明\n"
        
        # 初始化變量
        if hasattr(stmt, 'value') and stmt.value is not None:
            # 處理 spawn 表達式
            if isinstance(stmt.value, ast_nodes.SpawnExpression):
                if stmt.value in self.result_data:
                    var_name, var_type = self.result_data[stmt.value]
                    # 為變量分配內存
                    result += f"    %{stmt.name} = alloca i8*\n"
                    # 從 spawn 表達式加載任務指針
                    result += f"    %spawn_val_{self.var_counter} = load i8*, i8** %{var_name}\n"
                    # 存儲到變量
                    result += f"    store i8* %spawn_val_{self.var_counter}, i8** %{stmt.name}\n"
                    self.var_counter += 1
                    return result
                else:
                    # 如果沒有找到 spawn 表達式的結果數據，使用默認處理
                    result += f"    ; 警告：找不到 spawn 表達式的結果數據\n"
                    result += f"    %{stmt.name} = alloca i8*\n"
                    result += f"    store i8* null, i8** %{stmt.name}\n"
                    return result
            
            # 處理 await 表達式
            elif isinstance(stmt.value, ast_nodes.AwaitExpression):
                if stmt.value in self.result_data:
                    var_name, var_type = self.result_data[stmt.value]
                    
                    if "tuple" in var_type:  # 元組類型 (多個 await 結果)
                        # 分配元組內存
                        result += f"    %{stmt.name} = alloca {var_type}\n"
                        # 從 await 結果複製元組數據
                        result += f"    %tuple_val_{self.var_counter} = load {var_type}, {var_type}* %{var_name}\n"
                        result += f"    store {var_type} %tuple_val_{self.var_counter}, {var_type}* %{stmt.name}\n"
                        self.var_counter += 1
                    else:  # 基本類型 (單個 await 結果)
                        # 分配變量內存
                        result += f"    %{stmt.name} = alloca i32\n"
                        # 將 await 結果存儲到變量
                        result += f"    store i32 %{var_name}, i32* %{stmt.name}\n"
                    
                    return result
                else:
                    # 如果沒有找到 await 表達式的結果數據，使用默認處理
                    result += f"    ; 警告：找不到 await 表達式的結果數據\n"
                    result += f"    %{stmt.name} = alloca i32\n"
                    result += f"    store i32 0, i32* %{stmt.name}\n"
                    return result
            
            # 其他類型的表達式處理 (原有代碼)
            result += f"    %{stmt.name} = alloca i32\n"
            
            if isinstance(stmt.value, ast_nodes.Number):
                result += f"    store i32 {stmt.value.value}, i32* %{stmt.name}\n"
            elif isinstance(stmt.value, ast_nodes.BinaryExpr):
                # 處理二元表達式
                if stmt.value.operator == "+":
                    # 加法運算
                    if isinstance(stmt.value.left, ast_nodes.Number) and isinstance(stmt.value.right, ast_nodes.Number):
                        # 兩個數字相加
                        value = int(stmt.value.left.value) + int(stmt.value.right.value)
                        result += f"    store i32 {value}, i32* %{stmt.name}\n"
                    else:
                        # 需要生成臨時變量
                        result += self._generate_binary_expr(stmt.value, stmt.name)
                elif stmt.value.operator in ["<", ">", "<=", ">=", "==", "!="]:
                    # 比較運算
                    result += self._generate_comparison(stmt.value, stmt.name)
            elif isinstance(stmt.value, ast_nodes.StringLiteral):
                # 處理字符串字面量
                # 檢查是否是原始字符串模板（反引號字符串）
                if hasattr(stmt.value, 'is_raw') and stmt.value.is_raw:
                    # 處理模板字符串
                    result += self._generate_template_string_var(stmt.value, stmt.name)
                else:
                    # 普通字符串
                    # 注意：這裡簡化處理，假設變量類型是 i32，實際應根據類型系統處理
                    result += f"    ; 警告：將字符串賦值給 i32 變量\n"
                    # 將字符串存儲為字符串指針
                    string_value = stmt.value.value + "\\00"
                    str_idx = self._add_global_string(string_value)
                    byte_len = self._get_byte_length(string_value)
                    result += f"    %str_ptr_{self.var_counter} = getelementptr inbounds ([{byte_len} x i8], [{byte_len} x i8]* @.str.{str_idx}, i32 0, i32 0)\n"
                    result += f"    %str_val_{self.var_counter} = ptrtoint i8* %str_ptr_{self.var_counter} to i32\n"
                    result += f"    store i32 %str_val_{self.var_counter}, i32* %{stmt.name}\n"
                    self.var_counter += 1
            elif isinstance(stmt.value, ast_nodes.Variable):
                # 變量賦值
                result += f"    %var_val_{self.var_counter} = load i32, i32* %{stmt.value.name}\n"
                result += f"    store i32 %var_val_{self.var_counter}, i32* %{stmt.name}\n"
                self.var_counter += 1
            elif isinstance(stmt.value, ast_nodes.CallExpression):
                # 函數調用結果賦值
                if isinstance(stmt.value.callee, ast_nodes.Variable):
                    if stmt.value.callee.name == "error":
                        result += self._generate_error(stmt.value)
                    # 可以添加其他函數的處理
            elif isinstance(stmt.value, ast_nodes.TemplateLiteral):
                # 處理模板字符串（反引號）
                result += self._generate_template_string_var(stmt.value, stmt.name)
            elif isinstance(stmt.value, ast_nodes.StringInterpolation):
                # 處理字符串插值對象
                result += self._generate_string_interpolation_var(stmt.value, stmt.name)
        else:
            # 沒有初始值
            result += f"    %{stmt.name} = alloca i32\n"
            result += f"    store i32 0, i32* %{stmt.name}\n"
        
        return result

    def _generate_const_declaration(self, stmt):
        """生成常量聲明的 LLVM IR 代碼"""
        result = "    ; 常量聲明\n"
        
        # 常量處理與變量類似，但使用全局變量
        result += f"    %{stmt.name} = alloca i32\n"
        
        # 初始化常量
        if hasattr(stmt, 'value') and stmt.value is not None:
            if isinstance(stmt.value, ast_nodes.Number):
                result += f"    store i32 {stmt.value.value}, i32* %{stmt.name}\n"
            elif isinstance(stmt.value, ast_nodes.BinaryExpr):
                # 處理二元表達式
                if stmt.value.operator == "+":
                    if isinstance(stmt.value.left, ast_nodes.Number) and isinstance(stmt.value.right, ast_nodes.Number):
                        value = stmt.value.left.value + stmt.value.right.value
                        result += f"    store i32 {value}, i32* %{stmt.name}\n"
                    else:
                        result += self._generate_binary_expr(stmt.value, stmt.name)
            # 可以添加更多類型的處理
        
        return result

    def _generate_binary_expr(self, expr, target_var):
        """生成二元表達式的 LLVM IR 代碼，結果存入目標變量"""
        result = "    ; 二元表達式\n"
        
        # 左操作數
        left_val = ""
        if isinstance(expr.left, ast_nodes.Number):
            left_val = str(expr.left.value)
        elif isinstance(expr.left, ast_nodes.Variable):
            result += f"    %left_{self.var_counter} = load i32, i32* %{expr.left.name}\n"
            left_val = f"%left_{self.var_counter}"
            self.var_counter += 1
        
        # 右操作數
        right_val = ""
        if isinstance(expr.right, ast_nodes.Number):
            right_val = str(expr.right.value)
        elif isinstance(expr.right, ast_nodes.Variable):
            result += f"    %right_{self.var_counter} = load i32, i32* %{expr.right.name}\n"
            right_val = f"%right_{self.var_counter}"
            self.var_counter += 1
        
        # 執行運算
        if expr.operator == "+":
            result += f"    %result_{self.var_counter} = add i32 {left_val}, {right_val}\n"
        elif expr.operator == "-":
            result += f"    %result_{self.var_counter} = sub i32 {left_val}, {right_val}\n"
        elif expr.operator == "*":
            result += f"    %result_{self.var_counter} = mul i32 {left_val}, {right_val}\n"
        elif expr.operator == "/":
            result += f"    %result_{self.var_counter} = sdiv i32 {left_val}, {right_val}\n"
        
        # 存儲結果
        result += f"    store i32 %result_{self.var_counter}, i32* %{target_var}\n"
        self.var_counter += 1
        
        return result

    def _generate_template_string(self, template_str, target_var):
        """生成模板字符串的 LLVM IR 代碼，結果存入目標變量"""
        result = "    ; 模板字符串\n"
        
        # 解析模板字符串中的變量插值
        parts = []
        current_part = ""
        i = 0
        while i < len(template_str):
            if template_str[i:i+2] == "${" and i + 2 < len(template_str):
                if current_part:
                    parts.append(("string", current_part))
                    current_part = ""
                # 找到插值結束位置
                j = i + 2
                while j < len(template_str) and template_str[j] != "}":
                    j += 1
                if j < len(template_str):
                    var_name = template_str[i+2:j]
                    parts.append(("var", var_name))
                    i = j + 1
                else:
                    current_part += template_str[i]
                    i += 1
            else:
                current_part += template_str[i]
                i += 1
        if current_part:
            parts.append(("string", current_part))
        
        # 根據解析結果生成代碼
        if parts:
            format_parts = []
            var_parts = []
            for part_type, part_value in parts:
                if part_type == "string":
                    format_parts.append(part_value)
                elif part_type == "var":
                    format_parts.append("%d")  # 假設變量是整數
                    var_parts.append(part_value)
            
            # 生成格式化字符串
            format_str = "".join(format_parts) + "\\00"
            format_str_idx = self._add_global_string(format_str)
            byte_len = self._get_byte_length(format_str)
            
            # 為模板字符串分配內存
            result += f"    %template_str_{self.var_counter} = alloca [{byte_len} x i8]\n"
            
            # 複製格式字符串
            result += f"    %template_src_{self.var_counter} = getelementptr inbounds ([{byte_len} x i8], [{byte_len} x i8]* @.str.{format_str_idx}, i32 0, i32 0)\n"
            result += f"    %template_dst_{self.var_counter} = getelementptr inbounds [{byte_len} x i8], [{byte_len} x i8]* %template_str_{self.var_counter}, i32 0, i32 0)\n"
            
            # 這裡簡化處理，實際上需要格式化字符串
            # 實際實現應該將字符串指針存儲到目標變量中
            result += f"    %str_ptr_{self.var_counter} = ptrtoint i8* %template_src_{self.var_counter} to i32\n"
            result += f"    store i32 %str_ptr_{self.var_counter}, i32* %{target_var}\n"
            
            self.var_counter += 1
        
        return result
    
    def _generate_error(self, expr):
        """生成 error 函數調用的 LLVM IR 代碼"""
        result = "    ; 創建一個錯誤\n"
        
        if not expr.arguments:
            return result  # 沒有參數則不處理
            
        # 獲取錯誤消息
        error_msg = expr.arguments[0]
        if isinstance(error_msg, ast_nodes.StringLiteral):
            error_str = error_msg.value + "\\00"  # 確保有空終止符
            str_idx = self._add_global_string(error_str)
            byte_len = self._get_byte_length(error_str)
            
            # 獲取錯誤代碼（如果提供）
            error_code = 1  # 默認錯誤代碼
            if len(expr.arguments) > 1 and isinstance(expr.arguments[1], ast_nodes.Number):
                error_code = expr.arguments[1].value
                
            # 創建錯誤對象
            result += f"    ; 使用錯誤消息 '{error_msg.value}' 和錯誤代碼 {error_code} 創建錯誤\n"
            
            # 分配錯誤結構體內存
            result += f"    %error_obj_{self.var_counter} = alloca %error_t\n"
            
            # 設置錯誤代碼
            result += f"    %error_code_ptr_{self.var_counter} = getelementptr %error_t, %error_t* %error_obj_{self.var_counter}, i32 0, i32 0\n"
            result += f"    store i32 {error_code}, i32* %error_code_ptr_{self.var_counter}\n"
            
            # 設置錯誤消息
            result += f"    %error_msg_ptr_{self.var_counter} = getelementptr %error_t, %error_t* %error_obj_{self.var_counter}, i32 0, i32 1\n"
            result += f"    %error_msg_{self.var_counter} = getelementptr inbounds ([{byte_len} x i8], [{byte_len} x i8]* @.str.{str_idx}, i32 0, i32 0)\n"
            result += f"    store i8* %error_msg_{self.var_counter}, i8** %error_msg_ptr_{self.var_counter}\n"
            
            # 返回錯誤對象指針
            result += f"    %error_ptr_{self.var_counter} = bitcast %error_t* %error_obj_{self.var_counter} to i8*\n"
            
            self.var_counter += 1
        
        return result
        
    def _generate_is_error(self, expr):
        """生成 is_error 函數調用的 LLVM IR 代碼"""
        result = "    ; 檢查是否為錯誤\n"
        
        if not expr.arguments:
            return result  # 沒有參數則不處理
            
        # 獲取需要檢查的變量
        var_to_check = expr.arguments[0]
        if isinstance(var_to_check, ast_nodes.Variable):
            result += f"    ; 檢查變量 '{var_to_check.name}' 是否為錯誤\n"
            
            # 加載變量值
            result += f"    %check_var_{self.var_counter} = load i8*, i8** %{var_to_check.name}\n"
            
            # 檢查變量是否為錯誤（簡化的實現：檢查指針是否為空）
            result += f"    %is_error_{self.var_counter} = call i1 @is_error_check(i8* %check_var_{self.var_counter})\n"
            
            # 返回檢查結果
            result += f"    %is_error_result_{self.var_counter} = zext i1 %is_error_{self.var_counter} to i32\n"
            
            self.var_counter += 1
        
        return result

    def _generate_template_string_var(self, template_literal, target_var):
        """生成模板字符串變量的 LLVM IR 代碼"""
        result = "    ; 模板字符串變量\n"
        
        template_str = template_literal.value
        
        # 解析模板字符串中的變量插值
        parts = []
        current_part = ""
        i = 0
        while i < len(template_str):
            if template_str[i:i+2] == "${" and i + 2 < len(template_str):
                if current_part:
                    parts.append(("string", current_part))
                    current_part = ""
                # 找到插值結束位置
                j = i + 2
                while j < len(template_str) and template_str[j] != "}":
                    j += 1
                if j < len(template_str):
                    var_name = template_str[i+2:j]
                    parts.append(("var", var_name))
                    i = j + 1
                else:
                    current_part += template_str[i]
                    i += 1
            else:
                current_part += template_str[i]
                i += 1
        if current_part:
            parts.append(("string", current_part))
        
        # 根據解析結果生成代碼
        if parts:
            format_parts = []
            var_parts = []
            for part_type, part_value in parts:
                if part_type == "string":
                    format_parts.append(part_value)
                elif part_type == "var":
                    format_parts.append("%d")  # 假設變量是整數
                    var_parts.append(part_value)
            
            # 生成格式化字符串
            format_str = "".join(format_parts) + "\\00"
            format_str_idx = self._add_global_string(format_str)
            byte_len = self._get_byte_length(format_str)
            
            # 直接使用全局字符串常量
            result += f"    %str_ptr_{self.var_counter} = getelementptr inbounds ([{byte_len} x i8], [{byte_len} x i8]* @.str.{format_str_idx}, i32 0, i32 0)\n"
            result += f"    %str_val_{self.var_counter} = ptrtoint i8* %str_ptr_{self.var_counter} to i32\n"
            result += f"    store i32 %str_val_{self.var_counter}, i32* %{target_var}\n"
            
            self.var_counter += 1
        
        return result

    def _generate_string_interpolation(self, expr):
        """生成字符串插值的 LLVM IR 代碼"""
        result = "    ; 字符串插值\n"
        
        if isinstance(expr, ast_nodes.BinaryExpr) and expr.operator == "+":
            # 第一種情況：直接連接兩個字符串字面量
            if isinstance(expr.left, ast_nodes.StringLiteral) and isinstance(expr.right, ast_nodes.StringLiteral):
                combined_str = expr.left.value + expr.right.value
                content = combined_str + "\\0A\\00"  # 添加換行符和空終止符
                str_idx = self._add_global_string(content)
                byte_len = self._get_byte_length(content)
                result += f"    call i32 (i8*, ...) @printf(i8* getelementptr inbounds ([{byte_len} x i8], [{byte_len} x i8]* @.str.{str_idx}, i32 0, i32 0))\n"
            # 第二種情況：字符串字面量 + 變量
            elif isinstance(expr.left, ast_nodes.StringLiteral) and isinstance(expr.right, ast_nodes.Variable):
                format_str = expr.left.value + "%d\\0A\\00"  # 假設變量是整數
                format_str_idx = self._add_global_string(format_str)
                byte_len = self._get_byte_length(format_str)
                result += f"    %var_{self.var_counter} = load i32, i32* %{expr.right.name}\n"
                result += f"    call i32 (i8*, ...) @printf(i8* getelementptr inbounds ([{byte_len} x i8], [{byte_len} x i8]* @.str.{format_str_idx}, i32 0, i32 0), i32 %var_{self.var_counter})\n"
                self.var_counter += 1
            # 第三種情況：變量 + 字符串字面量
            elif isinstance(expr.left, ast_nodes.Variable) and isinstance(expr.right, ast_nodes.StringLiteral):
                format_str = "%d" + expr.right.value + "\\0A\\00"  # 假設變量是整數
                format_str_idx = self._add_global_string(format_str)
                byte_len = self._get_byte_length(format_str)
                result += f"    %var_{self.var_counter} = load i32, i32* %{expr.left.name}\n"
                result += f"    call i32 (i8*, ...) @printf(i8* getelementptr inbounds ([{byte_len} x i8], [{byte_len} x i8]* @.str.{format_str_idx}, i32 0, i32 0), i32 %var_{self.var_counter})\n"
                self.var_counter += 1
            # 第四種情況：處理模板字符串（反引號）
            elif isinstance(expr.left, ast_nodes.StringLiteral) and isinstance(expr.right, ast_nodes.StringLiteral) and hasattr(expr, 'is_template') and expr.is_template:
                template_str = expr.left.value + expr.right.value
                # 解析模板字符串中的變量插值
                parts = []
                current_part = ""
                i = 0
                while i < len(template_str):
                    if template_str[i:i+2] == "${" and i + 2 < len(template_str):
                        if current_part:
                            parts.append(("string", current_part))
                            current_part = ""
                        # 找到插值結束位置
                        j = i + 2
                        while j < len(template_str) and template_str[j] != "}":
                            j += 1
                        if j < len(template_str):
                            var_name = template_str[i+2:j]
                            parts.append(("var", var_name))
                            i = j + 1
                        else:
                            current_part += template_str[i]
                            i += 1
                    else:
                        current_part += template_str[i]
                        i += 1
                if current_part:
                    parts.append(("string", current_part))
                
                # 根據解析結果生成代碼
                if parts:
                    format_parts = []
                    var_parts = []
                    for part_type, part_value in parts:
                        if part_type == "string":
                            format_parts.append(part_value)
                        elif part_type == "var":
                            format_parts.append("%d")  # 假設變量是整數
                            var_parts.append(part_value)
                    
                    format_str = "".join(format_parts) + "\\0A\\00"  # 添加換行符和空終止符
                    format_str_idx = self._add_global_string(format_str)
                    byte_len = self._get_byte_length(format_str)
                    
                    # 加載所有變量
                    var_loads = []
                    for i, var_name in enumerate(var_parts):
                        result += f"    %template_var_{self.var_counter}_{i} = load i32, i32* %{var_name}\n"
                        var_loads.append(f"i32 %template_var_{self.var_counter}_{i}")
                    
                    # 生成printf調用
                    printf_args = ", ".join(var_loads)
                    result += f"    call i32 (i8*, ...) @printf(i8* getelementptr inbounds ([{byte_len} x i8], [{byte_len} x i8]* @.str.{format_str_idx}, i32 0, i32 0){', ' + printf_args if printf_args else ''})\n"
                    
                    self.var_counter += 1
            # 其他情況：遞歸處理
            else:
                if isinstance(expr.left, ast_nodes.BinaryExpr) and expr.left.operator == "+":
                    result += self._generate_string_interpolation(expr.left)
                if isinstance(expr.right, ast_nodes.BinaryExpr) and expr.right.operator == "+":
                    result += self._generate_string_interpolation(expr.right)
        # 處理直接使用反引號（模板字符串）的情況
        elif isinstance(expr, ast_nodes.StringLiteral) and hasattr(expr, 'is_raw') and expr.is_raw:
            template_str = expr.value
            # 解析模板字符串，與上面類似
            parts = []
            current_part = ""
            i = 0
            while i < len(template_str):
                if template_str[i:i+2] == "${" and i + 2 < len(template_str):
                    if current_part:
                        parts.append(("string", current_part))
                        current_part = ""
                    # 找到插值結束位置
                    j = i + 2
                    while j < len(template_str) and template_str[j] != "}":
                        j += 1
                    if j < len(template_str):
                        var_name = template_str[i+2:j]
                        parts.append(("var", var_name))
                        i = j + 1
                    else:
                        current_part += template_str[i]
                        i += 1
                else:
                    current_part += template_str[i]
                    i += 1
            if current_part:
                parts.append(("string", current_part))
            
            # 根據解析結果生成代碼
            if parts:
                format_parts = []
                var_parts = []
                for part_type, part_value in parts:
                    if part_type == "string":
                        format_parts.append(part_value)
                    elif part_type == "var":
                        format_parts.append("%d")  # 假設變量是整數
                        var_parts.append(part_value)
                
                format_str = "".join(format_parts) + "\\0A\\00"  # 添加換行符和空終止符
                format_str_idx = self._add_global_string(format_str)
                byte_len = self._get_byte_length(format_str)
                
                # 加載所有變量
                var_loads = []
                for i, var_name in enumerate(var_parts):
                    result += f"    %template_var_{self.var_counter}_{i} = load i32, i32* %{var_name}\n"
                    var_loads.append(f"i32 %template_var_{self.var_counter}_{i}")
                
                # 生成printf調用
                printf_args = ", ".join(var_loads)
                result += f"    call i32 (i8*, ...) @printf(i8* getelementptr inbounds ([{byte_len} x i8], [{byte_len} x i8]* @.str.{format_str_idx}, i32 0, i32 0){', ' + printf_args if printf_args else ''})\n"
                
                self.var_counter += 1
        
        return result

    def _generate_string_interpolation_var(self, interpolation, target_var):
        """為字符串插值生成代碼並將結果存入目標變量"""
        result = "    ; 字符串插值變量\n"
        
        # 處理字符串插值的不同部分
        format_parts = []
        var_names = []
        
        for part in interpolation.parts:
            if isinstance(part, ast_nodes.StringLiteral):
                # 字符串部分
                format_parts.append(part.value)
            elif isinstance(part, ast_nodes.Variable):
                # 變量部分
                format_parts.append("%d")  # 假設變量是整數
                var_names.append(part.name)
        
        # 生成格式化字符串
        format_str = "".join(format_parts) + "\\00"
        format_str_idx = self._add_global_string(format_str)
        byte_len = self._get_byte_length(format_str)
        
        # 如果沒有變量插值，直接使用常量字符串
        if not var_names:
            result += f"    %str_ptr_{self.var_counter} = getelementptr inbounds ([{byte_len} x i8], [{byte_len} x i8]* @.str.{format_str_idx}, i32 0, i32 0)\n"
            result += f"    %str_val_{self.var_counter} = ptrtoint i8* %str_ptr_{self.var_counter} to i32\n"
            result += f"    store i32 %str_val_{self.var_counter}, i32* %{target_var}\n"
            self.var_counter += 1
            return result
        
        # 為插值變量分配內存空間
        temp_buffer_size = 256  # 假設緩衝區大小足夠
        result += f"    %temp_buffer_{self.var_counter} = alloca [{temp_buffer_size} x i8]\n"
        result += f"    %buffer_ptr_{self.var_counter} = getelementptr inbounds [{temp_buffer_size} x i8], [{temp_buffer_size} x i8]* %temp_buffer_{self.var_counter}, i32 0, i32 0)\n"
        
        # 獲取格式字符串指針
        result += f"    %format_ptr_{self.var_counter} = getelementptr inbounds ([{byte_len} x i8], [{byte_len} x i8]* @.str.{format_str_idx}, i32 0, i32 0)\n"
        
        # 加載所有變量
        var_loads = []
        for i, var_name in enumerate(var_names):
            result += f"    %interp_var_{self.var_counter}_{i} = load i32, i32* %{var_name}\n"
            var_loads.append(f"i32 %interp_var_{self.var_counter}_{i}")
        
        # 使用 sprintf 格式化字符串
        printf_args = ", ".join(var_loads)
        # 簡化實現：這裡我們實際上應該使用 sprintf，但為了簡單，我們直接設置指針
        result += f"    ; 在這裡應該調用 sprintf 來格式化字符串，但我們簡化處理\n"
        result += f"    ; sprintf(%buffer_ptr_{self.var_counter}, %format_ptr_{self.var_counter}, {printf_args})\n"
        
        # 直接將格式字符串指針存儲到變量中
        result += f"    %str_val_{self.var_counter} = ptrtoint i8* %format_ptr_{self.var_counter} to i32\n"
        result += f"    store i32 %str_val_{self.var_counter}, i32* %{target_var}\n"
        
        self.var_counter += 1
        
        return result

    def _get_byte_length(self, s):
        """計算字符串的字節長度，包括終止符"""
        # 將 "\n" 轉換為單個字符進行統計
        s = s.replace("\\n", "n")
        s = s.replace("\\t", "t")
        s = s.replace("\\\"", "\"")
        s = s.replace("\\\\", "\\")
        s = s.replace("\\0A", "\n")
        s = s.replace("\\00", "\0")
        s = s.replace("\\0", "\0")
        
        # 移除其他轉義字符前的反斜杠
        i = 0
        while i < len(s):
            if s[i] == '\\' and i + 1 < len(s):
                s = s[:i] + s[i+1:]
            else:
                i += 1
        
        # 將處理後的字符串轉換為UTF-8並計算字節長度
        utf8_bytes = s.encode('utf-8')
        return len(utf8_bytes)

    def _generate_comparison(self, expr, target_var=None):
        """生成比較運算的 LLVM IR 代碼"""
        result = "    ; 比較運算\n"
        
        # 左操作數
        left_val = ""
        if isinstance(expr.left, ast_nodes.Number):
            left_val = str(expr.left.value)
        elif isinstance(expr.left, ast_nodes.Variable):
            result += f"    %cmp_left_{self.var_counter} = load i32, i32* %{expr.left.name}\n"
            left_val = f"%cmp_left_{self.var_counter}"
            self.var_counter += 1
        
        # 右操作數
        right_val = ""
        if isinstance(expr.right, ast_nodes.Number):
            right_val = str(expr.right.value)
        elif isinstance(expr.right, ast_nodes.Variable):
            result += f"    %cmp_right_{self.var_counter} = load i32, i32* %{expr.right.name}\n"
            right_val = f"%cmp_right_{self.var_counter}"
            self.var_counter += 1
        
        # 執行比較運算
        llvm_op = ""
        if expr.operator == "<":
            llvm_op = "slt"  # 有符號小於
        elif expr.operator == ">":
            llvm_op = "sgt"  # 有符號大於
        elif expr.operator == "<=":
            llvm_op = "sle"  # 有符號小於等於
        elif expr.operator == ">=":
            llvm_op = "sge"  # 有符號大於等於
        elif expr.operator == "==":
            llvm_op = "eq"   # 等於
        elif expr.operator == "!=":
            llvm_op = "ne"   # 不等於
        
        # 生成比較指令
        result += f"    %cmp_result_{self.var_counter} = icmp {llvm_op} i32 {left_val}, {right_val}\n"
        
        # 如果需要將結果存入變量
        if target_var:
            # 將 i1 擴展為 i32
            result += f"    %cmp_ext_{self.var_counter} = zext i1 %cmp_result_{self.var_counter} to i32\n"
            result += f"    store i32 %cmp_ext_{self.var_counter}, i32* %{target_var}\n"
        
        self.var_counter += 1
        return result

    def _generate_if_statement(self, stmt):
        """生成 if 語句的 LLVM IR 代碼"""
        result = "    ; if 語句\n"
        
        # 生成唯一的標籤名
        then_label = f"if.then.{self.label_counter}"
        else_label = f"if.else.{self.label_counter}"
        end_label = f"if.end.{self.label_counter}"
        self.label_counter += 1
        
        # 生成條件表達式的代碼
        if isinstance(stmt.condition, ast_nodes.ComparisonChain):
            # 處理連續比較運算
            result += self._generate_comparison_chain(stmt.condition)
            condition_result = f"chain_result_{self.var_counter-1}"
        elif isinstance(stmt.condition, ast_nodes.BinaryExpr):
            # 處理二元比較運算
            result += self._generate_comparison(stmt.condition)
            condition_result = f"cmp_result_{self.var_counter-1}"
        elif isinstance(stmt.condition, ast_nodes.Variable):
            # 處理變量條件（假設變量是布爾值）
            result += f"    %if_cond_{self.var_counter} = load i32, i32* %{stmt.condition.name}\n"
            # 檢查是否為非零值
            result += f"    %cond_bool_{self.var_counter} = icmp ne i32 %if_cond_{self.var_counter}, 0\n"
            condition_result = f"cond_bool_{self.var_counter}"
            self.var_counter += 1
        else:
            # 處理其他類型的條件（默認為 true）
            result += f"    ; 無法識別的條件類型，默認為 true\n"
            result += f"    %default_cond_{self.var_counter} = add i1 1, 0\n"
            condition_result = f"default_cond_{self.var_counter}"
            self.var_counter += 1
        
        # 生成條件分支跳轉
        result += f"    br i1 %{condition_result}, label %{then_label}, label %{else_label if stmt.else_body else end_label}\n"
        
        # 生成 then 分支
        result += f"{then_label}:\n"
        
        # 處理 body 語句
        if isinstance(stmt.body, ast_nodes.BlockStatement):
            # 處理 BlockStatement
            for s in stmt.body.statements:
                if isinstance(s, ast_nodes.ExpressionStatement):
                    expr = s.expression
                    if isinstance(expr, ast_nodes.CallExpression) and isinstance(expr.callee, ast_nodes.Variable):
                        if expr.callee.name == "println":
                            result += self._generate_println(expr)
                elif isinstance(s, ast_nodes.VarDeclaration):
                    result += self._generate_var_declaration(s)
                elif isinstance(s, ast_nodes.ConstDeclaration):
                    result += self._generate_const_declaration(s)
                elif isinstance(s, ast_nodes.IfStatement):
                    result += self._generate_if_statement(s)
        else:
            # 嘗試處理作為單條語句的 body
            if isinstance(stmt.body, ast_nodes.ExpressionStatement):
                expr = stmt.body.expression
                if isinstance(expr, ast_nodes.CallExpression) and isinstance(expr.callee, ast_nodes.Variable):
                    if expr.callee.name == "println":
                        result += self._generate_println(expr)
        
        # 跳轉到結束
        result += f"    br label %{end_label}\n"
        
        # 生成 else 分支（如果存在）
        if stmt.else_body:
            result += f"{else_label}:\n"
            
            # 處理 else_body 語句
            if isinstance(stmt.else_body, ast_nodes.BlockStatement):
                # 處理 BlockStatement
                for s in stmt.else_body.statements:
                    if isinstance(s, ast_nodes.ExpressionStatement):
                        expr = s.expression
                        if isinstance(expr, ast_nodes.CallExpression) and isinstance(expr.callee, ast_nodes.Variable):
                            if expr.callee.name == "println":
                                result += self._generate_println(expr)
                    elif isinstance(s, ast_nodes.VarDeclaration):
                        result += self._generate_var_declaration(s)
                    elif isinstance(s, ast_nodes.ConstDeclaration):
                        result += self._generate_const_declaration(s)
                    elif isinstance(s, ast_nodes.IfStatement):
                        result += self._generate_if_statement(s)
            else:
                # 處理單條語句
                if isinstance(stmt.else_body, ast_nodes.ExpressionStatement):
                    expr = stmt.else_body.expression
                    if isinstance(expr, ast_nodes.CallExpression) and isinstance(expr.callee, ast_nodes.Variable):
                        if expr.callee.name == "println":
                            result += self._generate_println(expr)
                elif isinstance(stmt.else_body, ast_nodes.IfStatement):
                    # 處理 else if 語句
                    result += self._generate_if_statement(stmt.else_body)
            
            # 跳轉到結束
            result += f"    br label %{end_label}\n"
        
        # 結束標籤
        result += f"{end_label}:\n"
        
        return result

    def _generate_comparison_chain(self, expr):
        """生成連續比較運算的 LLVM IR 代碼"""
        result = "    ; 連續比較運算\n"
        
        # 獲取左側表達式和比較列表
        left_expr = expr.left
        comparisons = expr.comparisons
        
        # 處理左側值
        left_val = ""
        if isinstance(left_expr, ast_nodes.Number):
            left_val = str(left_expr.value)
            result += f"    %chain_left_0 = add i32 {left_val}, 0\n"
            left_reg = "chain_left_0"
        elif isinstance(left_expr, ast_nodes.Variable):
            result += f"    %chain_left_0 = load i32, i32* %{left_expr.name}\n"
            left_reg = "chain_left_0"
        else:
            # 無法處理的表達式，默認為 0
            result += f"    %chain_left_0 = add i32 0, 0\n"
            left_reg = "chain_left_0"
        
        # 默認結果為 true
        result += f"    %chain_result_0 = add i1 1, 0\n"
        result_reg = "chain_result_0"
        
        # 處理每個比較
        for i, (op, right_expr) in enumerate(comparisons):
            # 處理右側值
            right_val = ""
            if isinstance(right_expr, ast_nodes.Number):
                right_val = str(right_expr.value)
                result += f"    %chain_right_{i} = add i32 {right_val}, 0\n"
                right_reg = f"chain_right_{i}"
            elif isinstance(right_expr, ast_nodes.Variable):
                result += f"    %chain_right_{i} = load i32, i32* %{right_expr.name}\n"
                right_reg = f"chain_right_{i}"
            else:
                # 無法處理的表達式，默認為 0
                result += f"    %chain_right_{i} = add i32 0, 0\n"
                right_reg = f"chain_right_{i}"
            
            # 執行比較運算
            llvm_op = ""
            if op == "<":
                llvm_op = "slt"  # 有符號小於
            elif op == ">":
                llvm_op = "sgt"  # 有符號大於
            elif op == "<=":
                llvm_op = "sle"  # 有符號小於等於
            elif op == ">=":
                llvm_op = "sge"  # 有符號大於等於
            elif op == "==":
                llvm_op = "eq"   # 等於
            elif op == "!=":
                llvm_op = "ne"   # 不等於
            
            # 生成比較
            result += f"    %chain_cmp_{i} = icmp {llvm_op} i32 %{left_reg}, %{right_reg}\n"
            
            # 結合所有比較結果
            result += f"    %chain_and_{i} = and i1 %{result_reg}, %chain_cmp_{i}\n"
            result_reg = f"chain_and_{i}"
            
            # 更新左側值為右側值（用於下一個比較）
            left_reg = right_reg
        
        # 最終結果
        final_reg = self.var_counter
        result += f"    %chain_result_{final_reg} = add i1 %{result_reg}, 0\n"
        self.var_counter += 1
        
        return result

    def _add_global_string(self, string):
        """添加全局字符串常量並返回索引"""
        # 確保字符串以空終止符結尾
        if not string.endswith('\\00'):
            string = string + '\\00'
        
        # 將字符串加入字符串表
        if string not in self.string_map:
            self.string_map[string] = self.string_counter
            self.string_counter += 1
        
        return self.string_map[string]

    def _generate_member_access(self, expr):
        """生成成員訪問表達式的 LLVM IR 代碼"""
        result = "    ; 成員訪問\n"
        
        # 處理元組成員訪問（例如：results.0）
        if isinstance(expr, ast_nodes.GetExpression) and isinstance(expr.object, ast_nodes.Variable):
            # 嘗試解析成員名稱是否為數字（元組索引）
            try:
                member_index = int(expr.name)
                # 獲取變量名
                var_name = expr.object.name
                # 生成訪問元組元素的代碼
                result += f"    ; 訪問元組 {var_name} 的第 {member_index} 個元素\n"
                # 獲取元組元素指針
                result += f"    %tuple_elem_ptr_{self.var_counter} = getelementptr inbounds %tuple{member_index+1}_struct, %tuple{member_index+1}_struct* %{var_name}, i32 0, i32 {member_index}\n"
                # 加載元素值
                result += f"    %tuple_elem_{self.var_counter} = load i32, i32* %tuple_elem_ptr_{self.var_counter}\n"
                # 為結果分配內存
                result += f"    %member_result_{self.var_counter} = alloca i32\n"
                # 存儲結果
                result += f"    store i32 %tuple_elem_{self.var_counter}, i32* %member_result_{self.var_counter}\n"
                
                # 保存結果，以便後續使用
                self.result_data[expr] = (f"member_result_{self.var_counter}", "i32")
                
                self.var_counter += 1
                return result
            except ValueError:
                # 非數字索引，可能是一般的結構體成員訪問
                pass
        
        # 如果不是元組成員訪問，可以在這裡實現其他類型的成員訪問
        result += "    ; 未實現的成員訪問類型\n"
        
        return result

# 為了向後兼容，保留原有的CodeGenerator名稱
CodeGenerator = LLVMCodeGenerator 