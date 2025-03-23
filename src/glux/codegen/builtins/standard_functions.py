from abc import ABC
from typing import Dict, Any, List, Optional
import traceback
import logging

from src.glux.codegen.builtins import BuiltinModule


class StandardFunctions(BuiltinModule):
    """標準內置函數模塊"""

    def __init__(self, parent=None):
        """
        初始化標準函數模塊
        
        Args:
            parent: 父級代碼生成器
        """
        super().__init__()
        self.parent = parent
        self.logger = parent.logger if parent and hasattr(parent, 'logger') else logging.getLogger(__name__)
    
    def set_parent(self, parent):
        """設置父級代碼生成器"""
        self.parent = parent
    
    def initialize(self, context=None):
        """初始化標準函數模組"""
        self.context = context
        
        # 處理context為None的情況
        if context is None:
            self.logger.debug("標準函數模組初始化：LLVM上下文尚未準備就緒，僅完成初步初始化")
            return
            
        # 正常初始化流程
        self.logger.debug("開始初始化標準函數模組...")
        
        # 聲明標準函數
        self._declare_standard_functions()
        
        self.logger.debug("標準函數模組初始化完成")
        
        return self
    
    def _declare_standard_functions(self):
        """聲明所有標準函數到LLVM模塊"""
        # 檢查LLVM上下文是否就緒
        if self.context is None:
            self.parent.logger.warning("無法聲明標準函數：LLVM上下文未初始化")
            return
            
        try:
            # 類型轉換函數
            self._declare_string_function()
            self._declare_int_function()
            self._declare_float_function()
            self._declare_bool_function()
            
            # 輔助函數
            self._declare_len_function()
            self._declare_sleep_function()
            self._declare_copy_function()
            self._declare_error_function()
            
            self.logger.debug("標準函數聲明完成")
        except Exception as e:
            self.logger.error(f"聲明標準函數時出錯: {e}")
            traceback.print_exc()
    
    def _declare_string_function(self):
        """聲明string()函數，用於將其他類型轉換為字串"""
        self.logger.info("聲明string()函數")
        # TODO: 實現將各類型轉換為字串的函數
    
    def _declare_int_function(self):
        """聲明int()函數，用於將其他類型轉換為整數"""
        self.logger.info("聲明int()函數")
        # TODO: 實現將各類型轉換為整數的函數
    
    def _declare_float_function(self):
        """聲明float()函數，用於將其他類型轉換為浮點數"""
        self.logger.info("聲明float()函數")
        # TODO: 實現將各類型轉換為浮點數的函數
    
    def _declare_bool_function(self):
        """聲明bool()函數，用於將其他類型轉換為布爾值"""
        self.logger.info("聲明bool()函數")
        # TODO: 實現將各類型轉換為布爾值的函數
    
    def _declare_len_function(self):
        """聲明len()函數，用於獲取集合或字串的長度"""
        self.logger.info("聲明len()函數")
        # TODO: 實現獲取長度的函數
    
    def _declare_sleep_function(self):
        """聲明sleep()函數，用於暫停執行"""
        self.logger.info("聲明sleep()函數")
        # TODO: 實現暫停執行的函數
    
    def _declare_copy_function(self):
        """聲明copy()函數，用於深拷貝"""
        self.logger.info("聲明copy()函數")
        # TODO: 實現深拷貝函數
    
    def _declare_error_function(self):
        """聲明error()函數，用於生成錯誤對象"""
        self.logger.info("聲明error()函數")
        # TODO: 實現生成錯誤對象的函數
    
    def generate_string_conversion(self, value, value_type, builder=None):
        """生成將給定值轉換為字串的代碼"""
        if builder is None:
            builder = self.parent.builder
        
        # 根據值類型選擇適當的轉換方法
        if value_type == 'i32' or value_type == 'i64':
            return self._int_to_string(value, builder)
        elif value_type == 'double':
            return self._float_to_string(value, builder)
        elif value_type == 'i1':
            return self._bool_to_string(value, builder)
        elif value_type == 'i8*':
            # 已經是字串了
            return value
        else:
            self.logger.warning(f"不支持將類型 {value_type} 轉換為字串")
            # 返回一個默認字串 "<unknown>"
            unknown_str = self.parent.declare_string("<unknown>")
            return unknown_str
    
    def _int_to_string(self, value, builder):
        """將整數轉換為字串"""
        # 調用運行時函數進行轉換
        int_to_str_func = self.parent.module.get_global('__glux_int_to_string')
        if int_to_str_func is None:
            self.logger.error("找不到 __glux_int_to_string 函數")
            # 返回默認字串
            return self.parent.declare_string("<error>")
        
        result = builder.call(int_to_str_func, [value])
        return result
    
    def _float_to_string(self, value, builder):
        """將浮點數轉換為字串"""
        # 調用運行時函數進行轉換
        float_to_str_func = self.parent.module.get_global('__glux_float_to_string')
        if float_to_str_func is None:
            self.logger.error("找不到 __glux_float_to_string 函數")
            # 返回默認字串
            return self.parent.declare_string("<error>")
        
        result = builder.call(float_to_str_func, [value])
        return result
    
    def _bool_to_string(self, value, builder):
        """將布爾值轉換為字串"""
        # 創建條件選擇
        true_str = self.parent.declare_string("true")
        false_str = self.parent.declare_string("false")
        result = builder.select(value, true_str, false_str)
        return result 