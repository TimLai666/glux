from typing import Dict, Any, Optional
from src.glux.codegen.builtins import BuiltinModule
import logging


class TypeFunctions(BuiltinModule):
    """類型處理函數模塊"""

    def __init__(self, parent=None):
        """
        初始化類型函數模塊
        
        Args:
            parent: 父級代碼生成器
        """
        super().__init__()
        self.parent = parent
        self.logger = parent.logger if parent and hasattr(parent, 'logger') else logging.getLogger(__name__)
        self.defined_types = {}
        
    def set_parent(self, parent):
        """設置父級代碼生成器"""
        self.parent = parent
    
    def initialize(self, context=None):
        """初始化類型函數模組"""
        self.context = context
        
        # 處理context為None的情況
        if context is None:
            self.logger.debug("類型函數模組初始化：LLVM上下文尚未準備就緒，僅完成初步初始化")
            return
            
        # 正常初始化流程
        self.logger.debug("開始初始化類型函數模組...")
        
        # 聲明類型函數
        self._declare_type_functions()
        
        self.logger.debug("類型函數模組初始化完成")
        
        # 在完整的LLVM設置完成前跳過初始化
        if not hasattr(context, 'module') or context.module is None:
            return self
            
        # 定義基本類型
        self._define_basic_types()
        
        # 定義Future類型
        self._define_future_type()
        
        # 定義多值結果類型
        self._define_multi_result_type()
        
        return self
    
    def _declare_type_functions(self):
        """聲明所有類型函數到LLVM模塊"""
        # 檢查LLVM上下文是否就緒
        if self.context is None or not hasattr(self.context, 'module') or self.context.module is None:
            self.parent.logger.warning("無法聲明類型函數：LLVM上下文未初始化")
            return
            
        try:
            # 聲明各種類型轉換函數
            self._declare_type_conversion_functions()
            
            # 聲明類型檢查函數
            self._declare_type_check_functions()
            
            self.logger.debug("類型函數聲明完成")
        except Exception as e:
            self.logger.error(f"聲明類型函數時出錯: {e}")
            import traceback
            traceback.print_exc()
    
    def _declare_type_conversion_functions(self):
        """聲明類型轉換函數"""
        # 暫時為空，待實現
        pass
        
    def _declare_type_check_functions(self):
        """聲明類型檢查函數"""
        # 暫時為空，待實現
        pass
    
    def _define_basic_types(self):
        """定義基本類型"""
        # 映射Glux類型到LLVM類型
        self.type_map = {
            "void": self.parent.context.void_type,
            "bool": self.parent.context.i1_type,
            "int": self.parent.context.i32_type,
            "int8": self.parent.context.i8_type,
            "int16": self.parent.context.i16_type,
            "int32": self.parent.context.i32_type,
            "int64": self.parent.context.i64_type,
            "float": self.parent.context.float_type,
            "double": self.parent.context.double_type,
            "string": self.parent.context.i8_type.as_pointer(),
            "any": self.parent.context.void_ptr_type,
        }
        
        # 註冊已定義的類型
        for name, llvm_type in self.type_map.items():
            self.defined_types[name] = llvm_type
    
    def _define_future_type(self):
        """定義Future類型"""
        void_ptr_type = self.parent.context.void_ptr_type
        i32_type = self.parent.context.i32_type
        i1_type = self.parent.context.i1_type
        
        # Future結構體
        future_type = self.parent.context.get_identified_type("Future")
        future_type.set_body(
            void_ptr_type,  # 結果指針
            i32_type,       # 狀態標誌
            i1_type,        # 是否為多值Future
            i32_type,       # 結果類型ID
            i32_type,       # 任務ID
            self.parent.context.i8_type.as_pointer()  # 錯誤消息
        )
        
        # 註冊Future類型
        self.defined_types["Future"] = future_type
        self.parent.future_type = future_type
    
    def _define_multi_result_type(self):
        """定義多值結果類型"""
        # 多值結果本質上是一個void**指針
        multi_result_type = self.parent.context.void_ptr_type.as_pointer()
        
        # 註冊多值結果類型
        self.defined_types["MultiResult"] = multi_result_type
        self.parent.multi_result_type = multi_result_type
    
    def get_llvm_type(self, glux_type_name):
        """獲取Glux類型對應的LLVM類型"""
        if glux_type_name in self.defined_types:
            return self.defined_types[glux_type_name]
        
        # 處理泛型Future類型 Future<T>
        if glux_type_name.startswith("Future<") and glux_type_name.endswith(">"):
            # 提取內部類型
            inner_type = glux_type_name[7:-1]
            # Future類型總是指向Future結構體的指針
            return self.defined_types["Future"].as_pointer()
        
        # 處理數組類型 T[]
        if glux_type_name.endswith("[]"):
            # 提取元素類型
            element_type_name = glux_type_name[:-2]
            element_type = self.get_llvm_type(element_type_name)
            
            # 數組類型是指向元素類型的指針
            return element_type.as_pointer()
        
        # 未知類型，默認返回i8*
        self.logger.warning(f"未知類型: {glux_type_name}, 默認使用i8*")
        return self.parent.context.i8_type.as_pointer()
    
    def get_default_value(self, llvm_type):
        """獲取LLVM類型的默認值"""
        if llvm_type == self.parent.context.void_type:
            return None
        elif llvm_type == self.parent.context.i1_type:
            return self.parent.context.const_int(llvm_type, 0)
        elif llvm_type in [self.parent.context.i8_type, self.parent.context.i16_type,
                           self.parent.context.i32_type, self.parent.context.i64_type]:
            return self.parent.context.const_int(llvm_type, 0)
        elif llvm_type in [self.parent.context.float_type, self.parent.context.double_type]:
            return self.parent.context.const_real(llvm_type, 0.0)
        elif llvm_type.is_pointer:
            return self.parent.context.const_null(llvm_type)
        else:
            self.logger.warning(f"無法獲取默認值，未知類型: {llvm_type}")
            return self.parent.context.const_null(llvm_type)
    
    def is_compatible_types(self, source_type, target_type):
        """檢查兩個類型是否兼容（source可以賦值給target）"""
        # 相同類型
        if source_type == target_type:
            return True
        
        # 指針類型兼容性（void*可以和任何指針互換）
        if source_type.is_pointer and target_type.is_pointer:
            if source_type == self.parent.context.void_ptr_type or target_type == self.parent.context.void_ptr_type:
                return True
        
        # Future<T>的特殊處理
        if source_type == self.parent.future_type.as_pointer() and target_type == self.parent.future_type.as_pointer():
            return True
        
        # 整數類型的兼容性（小整數可以賦值給大整數）
        int_types = [self.parent.context.i8_type, self.parent.context.i16_type,
                     self.parent.context.i32_type, self.parent.context.i64_type]
        if source_type in int_types and target_type in int_types:
            return int_types.index(source_type) <= int_types.index(target_type)
        
        # 浮點類型的兼容性
        if source_type == self.parent.context.float_type and target_type == self.parent.context.double_type:
            return True
        
        # 整數到浮點數的隱式轉換
        if source_type in int_types and target_type in [self.parent.context.float_type, self.parent.context.double_type]:
            return True
        
        return False
    
    def get_future_type(self, value_type_name):
        """獲取對應值類型的Future類型"""
        return f"Future<{value_type_name}>"
    
    def get_type_id(self, type_name):
        """獲取類型ID（用於運行時類型判斷）"""
        type_ids = {
            "void": 0,
            "bool": 1,
            "int": 2,
            "int8": 3,
            "int16": 4,
            "int32": 5,
            "int64": 6,
            "float": 7,
            "double": 8,
            "string": 9,
            "any": 10,
        }
        
        # 提取泛型Future的內部類型
        if type_name.startswith("Future<") and type_name.endswith(">"):
            inner_type = type_name[7:-1]
            base_id = self.get_type_id(inner_type)
            return 100 + base_id  # Future<T>的ID是T的ID加100
        
        # 提取數組的元素類型
        if type_name.endswith("[]"):
            element_type = type_name[:-2]
            base_id = self.get_type_id(element_type)
            return 200 + base_id  # T[]的ID是T的ID加200
        
        return type_ids.get(type_name, 999)  # 未知類型返回999 