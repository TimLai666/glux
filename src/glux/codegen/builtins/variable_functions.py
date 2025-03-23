"""
變量處理相關函數實現模塊
包含變量聲明、賦值等功能
"""

from typing import List, Dict, Any, Optional, Tuple
import logging

from ..builtins import BuiltinModule
from ...parser import ast_nodes


class VariableFunctions(BuiltinModule):
    """變量函數模塊，用於處理變量聲明、賦值和引用"""
    
    def __init__(self, parent=None):
        """初始化變量函數模塊"""
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
        """初始化模塊，可以在此註冊內建變量相關函數（如果需要）"""
        if not self.parent or not hasattr(self.parent, 'symbol_table'):
            if self.logger:
                self.logger.error("無法初始化變量函數模塊：無父級代碼生成器或符號表")
            return False
            
        # 目前沒有需要註冊的內建變量函數
        if self.logger:
            self.logger.debug("變量函數模塊初始化完成")
        return True
        
    def generate_var_declaration(self, stmt):
        """
        生成變量聲明的 LLVM IR 代碼
        
        Args:
            stmt: 變量聲明語句對象
            
        Returns:
            str: 生成的 LLVM IR 代碼
        """
        if stmt.name in self.parent.variables:
            self.logger.error(f"變量重複聲明: {stmt.name}")
            return f"    ; Error: 變量 {stmt.name} 已經聲明\n"
            
        # 生成初始值表達式
        if not stmt.value:
            self.logger.error(f"變量 {stmt.name} 沒有初始值")
            return f"    ; Error: 變量 {stmt.name} 沒有初始值\n"
            
        value_result = self.parent._generate_expression(stmt.value)
        if not value_result:
            self.logger.error(f"無法生成變量 {stmt.name} 的初始值")
            return f"    ; Error: 無法生成變量 {stmt.name} 的初始值\n"
            
        result = value_result['code']
        
        # 生成 alloca 指令
        alloca_var = self.parent.var_counter
        result += f"    %{stmt.name} = alloca {value_result['type']}\n"
        self.parent.var_counter += 1
        
        # 生成 store 指令
        result += f"    store {value_result['type']} %tmp_{value_result['tmp']}, {value_result['type']}* %{stmt.name}\n"
        
        # 記錄變量信息
        self.parent.variables[stmt.name] = {
            'type': value_result['type'],
            'is_global': False,
            'is_constant': stmt.is_constant
        }
        
        return result
        
    def generate_variable_reference(self, variable):
        """
        生成變量引用的 LLVM IR 代碼
        
        Args:
            variable: 變量引用對象
            
        Returns:
            Dict: 包含生成的代碼、臨時變量名和類型的字典
        """
        result = ""
        
        # 檢查變量是否存在
        if variable.name not in self.parent.variables:
            self.logger.error(f"未定義的變量: {variable.name}")
            # 為了避免返回None導致類型錯誤，返回一個默認的錯誤字典
            tmp_var = self.parent.var_counter
            result += f"    ; 錯誤: 未定義的變量 {variable.name}\n"
            result += f"    %tmp_{tmp_var} = add i32 0, 0 ; 使用默認值0代替未定義變量\n"
            self.parent.var_counter += 1
            
            return {
                'code': result,
                'tmp': tmp_var,
                'type': 'i32'  # 默認使用整數類型
            }
            
        var_info = self.parent.variables[variable.name]
        var_type = var_info['type']
        
        # 生成 load 指令
        tmp_var = self.parent.var_counter
        result += f"    %tmp_{tmp_var} = load {var_type}, {var_type}* %{variable.name}\n"
        self.parent.var_counter += 1
        
        return {
            'code': result,
            'tmp': tmp_var,
            'type': var_type
        }
        
    def generate_assignment(self, stmt):
        """
        生成賦值語句的 LLVM IR 代碼
        
        Args:
            stmt: 賦值語句對象
            
        Returns:
            str: 生成的 LLVM IR 代碼
        """
        result = ""
        
        # 檢查變量是否存在
        if stmt.target.name not in self.parent.variables:
            self.logger.error(f"未定義的變量: {stmt.target.name}")
            return f"    ; Error: 未定義的變量 {stmt.target.name}\n"
            
        var_info = self.parent.variables[stmt.target.name]
        
        # 檢查變量是否為常量
        if var_info.get('is_constant', False):
            self.logger.error(f"無法對常量 {stmt.target.name} 賦值")
            return f"    ; Error: 無法對常量 {stmt.target.name} 賦值\n"
            
        # 生成值表達式
        value_result = self.parent._generate_expression(stmt.value)
        if not value_result:
            self.logger.error(f"無法生成賦值表達式")
            return f"    ; Error: 無法生成賦值表達式\n"
            
        result += value_result['code']
        
        # 類型檢查和轉換
        if value_result['type'] != var_info['type']:
            if var_info['type'] == 'i32' and value_result['type'] == 'double':
                # 浮點數轉整數
                tmp_var = self.parent.var_counter
                result += f"    %tmp_{tmp_var} = fptosi double %tmp_{value_result['tmp']} to i32\n"
                value_result['tmp'] = tmp_var
                value_result['type'] = 'i32'
                self.parent.var_counter += 1
            elif var_info['type'] == 'double' and value_result['type'] == 'i32':
                # 整數轉浮點數
                tmp_var = self.parent.var_counter
                result += f"    %tmp_{tmp_var} = sitofp i32 %tmp_{value_result['tmp']} to double\n"
                value_result['tmp'] = tmp_var
                value_result['type'] = 'double'
                self.parent.var_counter += 1
            else:
                self.logger.error(f"類型不匹配: 嘗試將 {value_result['type']} 類型賦值給 {var_info['type']} 類型的變量")
                return f"    ; Error: 類型不匹配，嘗試將 {value_result['type']} 類型賦值給 {var_info['type']} 類型的變量\n"
                
        # 生成 store 指令
        result += f"    store {var_info['type']} %tmp_{value_result['tmp']}, {var_info['type']}* %{stmt.target.name}\n"
        
        return result 