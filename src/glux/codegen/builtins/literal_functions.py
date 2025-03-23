"""
字面量相關函數實現模塊
包含字符串、模板字符串和數字字面量生成的實現
"""

from typing import List, Dict, Any, Optional, Tuple, Union
import logging
import re

from ..base_generator import CodeGenerator
from ...parser import ast_nodes


class LiteralFunctions:
    """字面量相關函數的實現類"""

    def __init__(self, parent):
        """
        初始化字面量函數模塊
        
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
        
    def generate_string_literal(self, expr, indent=4) -> Dict:
        """
        生成字符串字面量的 LLVM IR 代碼
        
        Args:
            expr: 字符串字面量表達式
            indent: 縮進空格數
            
        Returns:
            Dict: 包含生成的代碼、臨時變量名和類型的字典
        """
        result = ""
        spaces = " " * indent
        
        # 獲取字符串信息
        str_idx, char_count = self.parent._get_string_info(expr.value)
        byte_length = self.parent.string_length_map[str_idx]
        
        # 創建指向全局字符串的指針
        tmp_var = self.parent.var_counter
        result += f"{spaces}%tmp_{tmp_var} = getelementptr inbounds ([{byte_length} x i8], [{byte_length} x i8]* @.str.{str_idx}, i32 0, i32 0)\n"
        self.parent.var_counter += 1
        
        return {
            'code': result,
            'tmp': tmp_var,
            'type': 'i8*'
        }
        
    def generate_template_literal(self, expr, indent=4) -> Dict:
        """
        生成模板字符串的 LLVM IR 代碼
        
        Args:
            expr: 模板字符串表達式
            indent: 縮進空格數
            
        Returns:
            Dict: 包含生成的代碼、臨時變量名和類型的字典
        """
        result = ""
        spaces = " " * indent
        
        # 解析模板字符串，提取純文本部分和變量引用
        template_str = expr.value
        text_parts, var_refs = self.parse_template_literal_variables(template_str)
        
        # 如果沒有變量引用，直接作為普通字符串處理
        if not var_refs:
            return self.generate_string_literal(ast_nodes.StringLiteral(template_str), indent)
        
        # 為 sprintf 創建一個足夠大的緩衝區
        buf_var = self.parent.var_counter
        result += f"{spaces}%buf_{buf_var} = alloca [1024 x i8]\n"
        result += f"{spaces}%ptr_{buf_var} = getelementptr inbounds [1024 x i8], [1024 x i8]* %buf_{buf_var}, i32 0, i32 0\n"
        self.parent.var_counter += 1
        
        # 處理第一部分文本
        first_text = text_parts[0]
        text_idx, _ = self.parent._get_string_info(first_text)
        text_byte_length = self.parent.string_length_map[text_idx]
        
        # 複製第一部分文本到緩衝區
        result += f"{spaces}%strcpy_result_{buf_var} = call i8* @strcpy(i8* %ptr_{buf_var}, i8* getelementptr inbounds ([{text_byte_length} x i8], [{text_byte_length} x i8]* @.str.{text_idx}, i32 0, i32 0))\n"
        
        # 處理其餘文本部分和變量引用
        for i, (var_ref, text_part) in enumerate(zip(var_refs, text_parts[1:]), 1):
            # 處理變量引用
            var_name = var_ref.strip()
            
            if var_name in self.parent.variables:
                var_type = self.parent.variables[var_name].get('type', '')
                
                if var_type == 'i32':
                    # 整數類型
                    fmt_str = "%d"
                    fmt_idx, _ = self.parent._get_string_info(fmt_str)
                    fmt_byte_length = self.parent.string_length_map[fmt_idx]
                    
                    tmp_buf_var = self.parent.var_counter
                    result += f"{spaces}%buf_{tmp_buf_var} = alloca [64 x i8]\n"
                    result += f"{spaces}%ptr_{tmp_buf_var} = getelementptr inbounds [64 x i8], [64 x i8]* %buf_{tmp_buf_var}, i32 0, i32 0\n"
                    result += f"{spaces}%fmt_{tmp_buf_var} = getelementptr inbounds ([{fmt_byte_length} x i8], [{fmt_byte_length} x i8]* @.str.0, i32 0, i32 0)\n"
                    result += f"{spaces}call i32 (i8*, i8*, ...) @sprintf(i8* %ptr_{tmp_buf_var}, i8* %fmt_{tmp_buf_var}, i32 %{var_name})\n"
                    
                    # 連接到結果緩衝區
                    result += f"{spaces}%strcat_result_{tmp_buf_var} = call i8* @strcat(i8* %strcpy_result_{buf_var}, i8* %ptr_{tmp_buf_var})\n"
                    self.parent.var_counter += 1
                    
                elif var_type == 'double':
                    # 浮點數類型
                    fmt_str = "%f"
                    fmt_idx, _ = self.parent._get_string_info(fmt_str)
                    fmt_byte_length = self.parent.string_length_map[fmt_idx]
                    
                    tmp_buf_var = self.parent.var_counter
                    result += f"{spaces}%buf_{tmp_buf_var} = alloca [64 x i8]\n"
                    result += f"{spaces}%ptr_{tmp_buf_var} = getelementptr inbounds [64 x i8], [64 x i8]* %buf_{tmp_buf_var}, i32 0, i32 0\n"
                    result += f"{spaces}%fmt_{tmp_buf_var} = getelementptr inbounds ([{fmt_byte_length} x i8], [{fmt_byte_length} x i8]* @.str.1, i32 0, i32 0)\n"
                    result += f"{spaces}call i32 (i8*, i8*, ...) @sprintf(i8* %ptr_{tmp_buf_var}, i8* %fmt_{tmp_buf_var}, double %{var_name})\n"
                    
                    # 連接到結果緩衝區
                    result += f"{spaces}%strcat_result_{tmp_buf_var} = call i8* @strcat(i8* %strcpy_result_{buf_var}, i8* %ptr_{tmp_buf_var})\n"
                    self.parent.var_counter += 1
                    
                elif var_type == 'i8*':
                    # 字符串類型
                    # 直接連接字符串
                    result += f"{spaces}%strcat_result_{buf_var}_{i} = call i8* @strcat(i8* %strcpy_result_{buf_var}, i8* %{var_name})\n"
                else:
                    self.logger.error(f"不支持的變量類型: {var_type}")
                    # 使用空字符串替代
                    empty_str = ""
                    empty_idx, _ = self.parent._get_string_info(empty_str)
                    empty_byte_length = self.parent.string_length_map[empty_idx]
                    result += f"{spaces}%strcat_result_{buf_var}_{i} = call i8* @strcat(i8* %strcpy_result_{buf_var}, i8* getelementptr inbounds ([{empty_byte_length} x i8], [{empty_byte_length} x i8]* @.str.{empty_idx}, i32 0, i32 0))\n"
            else:
                self.logger.error(f"未定義的變量: {var_name}")
                # 使用空字符串替代
                empty_str = ""
                empty_idx, _ = self.parent._get_string_info(empty_str)
                empty_byte_length = self.parent.string_length_map[empty_idx]
                result += f"{spaces}%strcat_result_{buf_var}_{i} = call i8* @strcat(i8* %strcpy_result_{buf_var}, i8* getelementptr inbounds ([{empty_byte_length} x i8], [{empty_byte_length} x i8]* @.str.{empty_idx}, i32 0, i32 0))\n"
            
            # 添加後續文本
            if text_part:
                text_idx, _ = self.parent._get_string_info(text_part)
                text_byte_length = self.parent.string_length_map[text_idx]
                result += f"{spaces}%strcat_text_{buf_var}_{i} = call i8* @strcat(i8* %strcpy_result_{buf_var}, i8* getelementptr inbounds ([{text_byte_length} x i8], [{text_byte_length} x i8]* @.str.{text_idx}, i32 0, i32 0))\n"
        
        # 返回最終結果
        return {
            'code': result,
            'tmp': f"ptr_{buf_var}",
            'type': 'i8*'
        }
        
    def parse_template_literal_variables(self, template_str: str) -> Tuple[List[str], List[str]]:
        """
        解析模板字符串，提取純文本部分和變量引用
        
        Args:
            template_str: 模板字符串，如 "Hello, ${name}!"
            
        Returns:
            Tuple[List[str], List[str]]: 第一個列表包含純文本部分，第二個列表包含變量引用
        """
        # 匹配 ${...} 模式
        pattern = r'\${(.+?)}'
        
        # 查找所有匹配
        matches = re.finditer(pattern, template_str)
        
        # 提取文本部分和變量引用
        text_parts = []
        var_refs = []
        
        # 起始索引
        start_idx = 0
        
        for match in matches:
            # 提取當前匹配前的文本
            text_before = template_str[start_idx:match.start()]
            text_parts.append(text_before)
            
            # 提取變量引用
            var_ref = match.group(1)
            var_refs.append(var_ref)
            
            # 更新起始索引
            start_idx = match.end()
        
        # 添加最後一部分文本
        text_parts.append(template_str[start_idx:])
        
        return text_parts, var_refs
        
    def generate_number_literal(self, expr, indent=4) -> Dict:
        """
        生成數字字面量的 LLVM IR 代碼
        
        Args:
            expr: 數字字面量表達式
            indent: 縮進空格數
            
        Returns:
            Dict: 包含生成的代碼、臨時變量名和類型的字典
        """
        result = ""
        spaces = " " * indent
        
        if isinstance(expr, ast_nodes.Number):
            # 整數字面量
            tmp_var = self.parent.var_counter
            result += f"{spaces}%tmp_{tmp_var} = add i32 0, {expr.value}\n"
            self.parent.var_counter += 1
            
            return {
                'code': result,
                'tmp': tmp_var,
                'type': 'i32'
            }
        elif isinstance(expr, ast_nodes.Float):
            # 浮點數字面量
            tmp_var = self.parent.var_counter
            result += f"{spaces}%tmp_{tmp_var} = fadd double 0.0, {expr.value}\n"
            self.parent.var_counter += 1
            
            return {
                'code': result,
                'tmp': tmp_var,
                'type': 'double'
            }
        else:
            self.logger.error(f"不支持的數字字面量類型: {type(expr)}")
            return {
                'code': f"{spaces}; 不支持的數字字面量類型: {type(expr)}\n",
                'tmp': 0,
                'type': 'i32'
            } 