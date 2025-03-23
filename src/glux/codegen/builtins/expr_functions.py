"""
表達式處理相關函數實現模塊
包含二元表達式處理和字符串連接判斷等功能
"""

from typing import List, Dict, Any, Optional, Tuple
import logging

from ..base_generator import CodeGenerator
from ...parser import ast_nodes


class ExprFunctions:
    """表達式處理相關函數的實現類"""

    def __init__(self, parent):
        """
        初始化表達式處理函數模塊
        
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
        
    def is_string_concatenation(self, expr):
        """
        檢查表達式是否為字符串連接
        
        Args:
            expr: 表達式對象
            
        Returns:
            bool: 是否為字符串連接
        """
        if not isinstance(expr, ast_nodes.BinaryExpr):
            return False
        
        if expr.operator != '+':
            return False
        
        # 檢查左右操作數是否包含字符串
        # 左操作數是字符串
        is_left_string = (
            isinstance(expr.left, ast_nodes.StringLiteral) or 
            (isinstance(expr.left, ast_nodes.Variable) and 
             expr.left.name in self.parent.variables and 
             self.parent.variables[expr.left.name].get('type') == 'i8*')
        )
        
        # 右操作數是字符串
        is_right_string = (
            isinstance(expr.right, ast_nodes.StringLiteral) or 
            (isinstance(expr.right, ast_nodes.Variable) and 
             expr.right.name in self.parent.variables and 
             self.parent.variables[expr.right.name].get('type') == 'i8*')
        )
        
        # 左操作數或右操作數是字符串連接表達式
        is_left_concat = isinstance(expr.left, ast_nodes.BinaryExpr) and self.is_string_concatenation(expr.left)
        is_right_concat = isinstance(expr.right, ast_nodes.BinaryExpr) and self.is_string_concatenation(expr.right)
        
        return is_left_string or is_right_string or is_left_concat or is_right_concat
        
    def generate_binary_expression(self, expr):
        """
        生成二元表達式的 LLVM IR 代碼
        
        Args:
            expr: 二元表達式對象
            
        Returns:
            Dict: 包含生成的代碼、臨時變量名和類型的字典
        """
        result = ""
        
        # 處理字符串連接
        if expr.operator == '+' and self.is_string_concatenation(expr):
            return self.parent._generate_string_interpolation(expr)
        
        # 處理左側表達式
        left_result = self.parent._generate_expression(expr.left)
        if not left_result:
            self.logger.error(f"無法處理的左側表達式類型: {type(expr.left)}")
            return None
        
        # 處理右側表達式
        right_result = self.parent._generate_expression(expr.right)
        if not right_result:
            self.logger.error(f"無法處理的右側表達式類型: {type(expr.right)}")
            return None
        
        # 合併代碼
        result += left_result['code']
        result += right_result['code']
        
        # 檢查類型是否一致
        if left_result['type'] != right_result['type']:
            # 類型轉換
            if left_result['type'] == 'i32' and right_result['type'] == 'double':
                # 整數轉浮點數
                tmp_var = self.parent.var_counter
                result += f"    %tmp_{tmp_var} = sitofp i32 %tmp_{left_result['tmp']} to double\n"
                left_result['tmp'] = tmp_var
                left_result['type'] = 'double'
                self.parent.var_counter += 1
            elif left_result['type'] == 'double' and right_result['type'] == 'i32':
                # 整數轉浮點數
                tmp_var = self.parent.var_counter
                result += f"    %tmp_{tmp_var} = sitofp i32 %tmp_{right_result['tmp']} to double\n"
                right_result['tmp'] = tmp_var
                right_result['type'] = 'double'
                self.parent.var_counter += 1
            else:
                self.logger.error(f"不支持的類型轉換: {left_result['type']} 和 {right_result['type']}")
                return None
        
        # 根據操作符生成代碼
        tmp_var = self.parent.var_counter
        self.parent.var_counter += 1
        
        if left_result['type'] == 'i32':
            # 整數運算
            if expr.operator == '+':
                result += f"    %tmp_{tmp_var} = add i32 %tmp_{left_result['tmp']}, %tmp_{right_result['tmp']}\n"
            elif expr.operator == '-':
                result += f"    %tmp_{tmp_var} = sub i32 %tmp_{left_result['tmp']}, %tmp_{right_result['tmp']}\n"
            elif expr.operator == '*':
                result += f"    %tmp_{tmp_var} = mul i32 %tmp_{left_result['tmp']}, %tmp_{right_result['tmp']}\n"
            elif expr.operator == '/':
                # 檢查除數是否為零
                zero_check_var = self.parent.var_counter
                result += f"    %iszero_{zero_check_var} = icmp eq i32 %tmp_{right_result['tmp']}, 0\n"
                self.parent.var_counter += 1
                
                # 條件分支
                div_block_var = self.parent.var_counter
                error_block_var = self.parent.var_counter + 1
                continue_block_var = self.parent.var_counter + 2
                self.parent.var_counter += 3
                
                result += f"    br i1 %iszero_{zero_check_var}, label %div_error_{error_block_var}, label %div_normal_{div_block_var}\n"
                
                # 正常除法
                result += f"div_normal_{div_block_var}:\n"
                result += f"    %tmp_{tmp_var} = sdiv i32 %tmp_{left_result['tmp']}, %tmp_{right_result['tmp']}\n"
                result += f"    br label %continue_{continue_block_var}\n"
                
                # 除零錯誤
                result += f"div_error_{error_block_var}:\n"
                # 獲取錯誤信息字符串
                error_msg = "Error: Division by zero"
                error_str_idx, _ = self.parent._get_string_info(error_msg)
                error_byte_length = self.parent.string_length_map[error_str_idx]
                
                # 打印錯誤信息
                result += f"    call void @print_error(i8* getelementptr inbounds ([{error_byte_length} x i8], [{error_byte_length} x i8]* @.str.{error_str_idx}, i32 0, i32 0))\n"
                result += f"    %tmp_{tmp_var} = add i32 0, 0\n"  # 除零返回0
                result += f"    br label %continue_{continue_block_var}\n"
                
                # 繼續執行
                result += f"continue_{continue_block_var}:\n"
                
            elif expr.operator == '%':
                # 檢查除數是否為零
                zero_check_var = self.parent.var_counter
                result += f"    %iszero_{zero_check_var} = icmp eq i32 %tmp_{right_result['tmp']}, 0\n"
                self.parent.var_counter += 1
                
                # 條件分支
                rem_block_var = self.parent.var_counter
                error_block_var = self.parent.var_counter + 1
                continue_block_var = self.parent.var_counter + 2
                self.parent.var_counter += 3
                
                result += f"    br i1 %iszero_{zero_check_var}, label %rem_error_{error_block_var}, label %rem_normal_{rem_block_var}\n"
                
                # 正常取餘
                result += f"rem_normal_{rem_block_var}:\n"
                result += f"    %tmp_{tmp_var} = srem i32 %tmp_{left_result['tmp']}, %tmp_{right_result['tmp']}\n"
                result += f"    br label %continue_{continue_block_var}\n"
                
                # 除零錯誤
                result += f"rem_error_{error_block_var}:\n"
                # 獲取錯誤信息字符串
                error_msg = "Error: Remainder by zero"
                error_str_idx, _ = self.parent._get_string_info(error_msg)
                error_byte_length = self.parent.string_length_map[error_str_idx]
                
                # 打印錯誤信息
                result += f"    call void @print_error(i8* getelementptr inbounds ([{error_byte_length} x i8], [{error_byte_length} x i8]* @.str.{error_str_idx}, i32 0, i32 0))\n"
                result += f"    %tmp_{tmp_var} = add i32 0, 0\n"  # 除零返回0
                result += f"    br label %continue_{continue_block_var}\n"
                
                # 繼續執行
                result += f"continue_{continue_block_var}:\n"
                
            # 比較運算符
            elif expr.operator == '==':
                result += f"    %cmp_{tmp_var} = icmp eq i32 %tmp_{left_result['tmp']}, %tmp_{right_result['tmp']}\n"
                result += f"    %tmp_{tmp_var} = zext i1 %cmp_{tmp_var} to i32\n"
            elif expr.operator == '!=':
                result += f"    %cmp_{tmp_var} = icmp ne i32 %tmp_{left_result['tmp']}, %tmp_{right_result['tmp']}\n"
                result += f"    %tmp_{tmp_var} = zext i1 %cmp_{tmp_var} to i32\n"
            elif expr.operator == '<':
                result += f"    %cmp_{tmp_var} = icmp slt i32 %tmp_{left_result['tmp']}, %tmp_{right_result['tmp']}\n"
                result += f"    %tmp_{tmp_var} = zext i1 %cmp_{tmp_var} to i32\n"
            elif expr.operator == '<=':
                result += f"    %cmp_{tmp_var} = icmp sle i32 %tmp_{left_result['tmp']}, %tmp_{right_result['tmp']}\n"
                result += f"    %tmp_{tmp_var} = zext i1 %cmp_{tmp_var} to i32\n"
            elif expr.operator == '>':
                result += f"    %cmp_{tmp_var} = icmp sgt i32 %tmp_{left_result['tmp']}, %tmp_{right_result['tmp']}\n"
                result += f"    %tmp_{tmp_var} = zext i1 %cmp_{tmp_var} to i32\n"
            elif expr.operator == '>=':
                result += f"    %cmp_{tmp_var} = icmp sge i32 %tmp_{left_result['tmp']}, %tmp_{right_result['tmp']}\n"
                result += f"    %tmp_{tmp_var} = zext i1 %cmp_{tmp_var} to i32\n"
            
            # 位運算符
            elif expr.operator == '&':
                result += f"    %tmp_{tmp_var} = and i32 %tmp_{left_result['tmp']}, %tmp_{right_result['tmp']}\n"
            elif expr.operator == '|':
                result += f"    %tmp_{tmp_var} = or i32 %tmp_{left_result['tmp']}, %tmp_{right_result['tmp']}\n"
            elif expr.operator == '^':
                result += f"    %tmp_{tmp_var} = xor i32 %tmp_{left_result['tmp']}, %tmp_{right_result['tmp']}\n"
            
            # 邏輯運算符
            elif expr.operator == 'and' or expr.operator == '&&':
                # 短路邏輯與
                # 先計算左側是否為假
                cmp_var = self.parent.var_counter
                result += f"    %cmp_{cmp_var} = icmp ne i32 %tmp_{left_result['tmp']}, 0\n"
                self.parent.var_counter += 1
                
                # 條件分支
                true_block_var = self.parent.var_counter
                false_block_var = self.parent.var_counter + 1
                continue_block_var = self.parent.var_counter + 2
                self.parent.var_counter += 3
                
                result += f"    br i1 %cmp_{cmp_var}, label %and_right_{true_block_var}, label %and_false_{false_block_var}\n"
                
                # 左側為真，計算右側
                result += f"and_right_{true_block_var}:\n"
                result += f"    %cmp_{tmp_var} = icmp ne i32 %tmp_{right_result['tmp']}, 0\n"
                result += f"    %tmp_{tmp_var} = zext i1 %cmp_{tmp_var} to i32\n"
                result += f"    br label %continue_{continue_block_var}\n"
                
                # 左側為假，直接返回0
                result += f"and_false_{false_block_var}:\n"
                result += f"    %tmp_{tmp_var}_false = add i32 0, 0\n"
                result += f"    br label %continue_{continue_block_var}\n"
                
                # 合併結果
                result += f"continue_{continue_block_var}:\n"
                merge_var = self.parent.var_counter
                result += f"    %tmp_{tmp_var} = phi i32 [ %tmp_{tmp_var}, %and_right_{true_block_var} ], [ %tmp_{tmp_var}_false, %and_false_{false_block_var} ]\n"
                
            elif expr.operator == 'or' or expr.operator == '||':
                # 短路邏輯或
                # 先計算左側是否為真
                cmp_var = self.parent.var_counter
                result += f"    %cmp_{cmp_var} = icmp ne i32 %tmp_{left_result['tmp']}, 0\n"
                self.parent.var_counter += 1
                
                # 條件分支
                true_block_var = self.parent.var_counter
                right_block_var = self.parent.var_counter + 1
                continue_block_var = self.parent.var_counter + 2
                self.parent.var_counter += 3
                
                result += f"    br i1 %cmp_{cmp_var}, label %or_true_{true_block_var}, label %or_right_{right_block_var}\n"
                
                # 左側為真，直接返回1
                result += f"or_true_{true_block_var}:\n"
                result += f"    %tmp_{tmp_var}_true = add i32 0, 1\n"
                result += f"    br label %continue_{continue_block_var}\n"
                
                # 左側為假，計算右側
                result += f"or_right_{right_block_var}:\n"
                result += f"    %cmp_{tmp_var} = icmp ne i32 %tmp_{right_result['tmp']}, 0\n"
                result += f"    %tmp_{tmp_var} = zext i1 %cmp_{tmp_var} to i32\n"
                result += f"    br label %continue_{continue_block_var}\n"
                
                # 合併結果
                result += f"continue_{continue_block_var}:\n"
                merge_var = self.parent.var_counter
                result += f"    %tmp_{tmp_var} = phi i32 [ %tmp_{tmp_var}_true, %or_true_{true_block_var} ], [ %tmp_{tmp_var}, %or_right_{right_block_var} ]\n"
                
            else:
                self.logger.error(f"不支持的整數運算符: {expr.operator}")
                return None
                
            return {
                'code': result,
                'tmp': tmp_var,
                'type': 'i32'
            }
            
        elif left_result['type'] == 'double':
            # 浮點數運算
            if expr.operator == '+':
                result += f"    %tmp_{tmp_var} = fadd double %tmp_{left_result['tmp']}, %tmp_{right_result['tmp']}\n"
            elif expr.operator == '-':
                result += f"    %tmp_{tmp_var} = fsub double %tmp_{left_result['tmp']}, %tmp_{right_result['tmp']}\n"
            elif expr.operator == '*':
                result += f"    %tmp_{tmp_var} = fmul double %tmp_{left_result['tmp']}, %tmp_{right_result['tmp']}\n"
            elif expr.operator == '/':
                # 檢查除數是否為零
                zero_check_var = self.parent.var_counter
                result += f"    %iszero_{zero_check_var} = fcmp oeq double %tmp_{right_result['tmp']}, 0.0\n"
                self.parent.var_counter += 1
                
                # 條件分支
                div_block_var = self.parent.var_counter
                error_block_var = self.parent.var_counter + 1
                continue_block_var = self.parent.var_counter + 2
                self.parent.var_counter += 3
                
                result += f"    br i1 %iszero_{zero_check_var}, label %div_error_{error_block_var}, label %div_normal_{div_block_var}\n"
                
                # 正常除法
                result += f"div_normal_{div_block_var}:\n"
                result += f"    %tmp_{tmp_var} = fdiv double %tmp_{left_result['tmp']}, %tmp_{right_result['tmp']}\n"
                result += f"    br label %continue_{continue_block_var}\n"
                
                # 除零錯誤
                result += f"div_error_{error_block_var}:\n"
                # 獲取錯誤信息字符串
                error_msg = "Error: Division by zero"
                error_str_idx, _ = self.parent._get_string_info(error_msg)
                error_byte_length = self.parent.string_length_map[error_str_idx]
                
                # 打印錯誤信息
                result += f"    call void @print_error(i8* getelementptr inbounds ([{error_byte_length} x i8], [{error_byte_length} x i8]* @.str.{error_str_idx}, i32 0, i32 0))\n"
                result += f"    %tmp_{tmp_var} = fadd double 0.0, 0.0\n"  # 除零返回0
                result += f"    br label %continue_{continue_block_var}\n"
                
                # 繼續執行
                result += f"continue_{continue_block_var}:\n"
                
            # 比較運算符
            elif expr.operator == '==':
                result += f"    %cmp_{tmp_var} = fcmp oeq double %tmp_{left_result['tmp']}, %tmp_{right_result['tmp']}\n"
                result += f"    %tmp_{tmp_var} = zext i1 %cmp_{tmp_var} to i32\n"
            elif expr.operator == '!=':
                result += f"    %cmp_{tmp_var} = fcmp one double %tmp_{left_result['tmp']}, %tmp_{right_result['tmp']}\n"
                result += f"    %tmp_{tmp_var} = zext i1 %cmp_{tmp_var} to i32\n"
            elif expr.operator == '<':
                result += f"    %cmp_{tmp_var} = fcmp olt double %tmp_{left_result['tmp']}, %tmp_{right_result['tmp']}\n"
                result += f"    %tmp_{tmp_var} = zext i1 %cmp_{tmp_var} to i32\n"
            elif expr.operator == '<=':
                result += f"    %cmp_{tmp_var} = fcmp ole double %tmp_{left_result['tmp']}, %tmp_{right_result['tmp']}\n"
                result += f"    %tmp_{tmp_var} = zext i1 %cmp_{tmp_var} to i32\n"
            elif expr.operator == '>':
                result += f"    %cmp_{tmp_var} = fcmp ogt double %tmp_{left_result['tmp']}, %tmp_{right_result['tmp']}\n"
                result += f"    %tmp_{tmp_var} = zext i1 %cmp_{tmp_var} to i32\n"
            elif expr.operator == '>=':
                result += f"    %cmp_{tmp_var} = fcmp oge double %tmp_{left_result['tmp']}, %tmp_{right_result['tmp']}\n"
                result += f"    %tmp_{tmp_var} = zext i1 %cmp_{tmp_var} to i32\n"
                
            else:
                self.logger.error(f"不支持的浮點數運算符: {expr.operator}")
                return None
                
            return {
                'code': result,
                'tmp': tmp_var,
                'type': 'double' if expr.operator in ['+', '-', '*', '/'] else 'i32'
            }
            
        elif left_result['type'] == 'i8*':
            # 字符串操作
            if expr.operator == '+':
                # 字符串連接
                return self.parent._generate_string_interpolation(expr)
                
            # 字符串比較
            elif expr.operator == '==':
                # 使用 strcmp 比較字符串
                cmp_var = self.parent.var_counter
                result += f"    %strcmp_{cmp_var} = call i32 @strcmp(i8* %tmp_{left_result['tmp']}, i8* %tmp_{right_result['tmp']})\n"
                result += f"    %cmp_{tmp_var} = icmp eq i32 %strcmp_{cmp_var}, 0\n"
                result += f"    %tmp_{tmp_var} = zext i1 %cmp_{tmp_var} to i32\n"
                self.parent.var_counter += 1
                
            elif expr.operator == '!=':
                # 使用 strcmp 比較字符串
                cmp_var = self.parent.var_counter
                result += f"    %strcmp_{cmp_var} = call i32 @strcmp(i8* %tmp_{left_result['tmp']}, i8* %tmp_{right_result['tmp']})\n"
                result += f"    %cmp_{tmp_var} = icmp ne i32 %strcmp_{cmp_var}, 0\n"
                result += f"    %tmp_{tmp_var} = zext i1 %cmp_{tmp_var} to i32\n"
                self.parent.var_counter += 1
                
            else:
                self.logger.error(f"不支持的字符串運算符: {expr.operator}")
                return None
                
            return {
                'code': result,
                'tmp': tmp_var,
                'type': 'i32'
            }
            
        else:
            self.logger.error(f"不支持的類型: {left_result['type']}")
            return None 