"""
LLVM 類型系統生成器
負責 Glux 類型系統的 LLVM IR 生成

警告: 這是一個兼容層，用於支援現有代碼。
新代碼應直接使用 types 模塊中的 TypeSystem 類。
"""

from llvmlite import ir
from typing import Dict, Any, List, Optional, Union, Tuple, Set
import logging
import re

from glux.types import TypeSystem, TypeKind, GluxType

logger = logging.getLogger(__name__)


class TypeGenerator:
    """
    處理 Glux 類型系統的 LLVM IR 生成
    
    該類現在是對 TypeSystem 類的兼容封裝。
    新代碼應直接使用 TypeSystem 類。
    """
    
    # 類型快取 (保留用於兼容)
    _type_cache: Dict[str, ir.Type] = {}
    
    # 基本類型映射 (保留用於兼容)
    _primitive_types = {
        "void": ir.VoidType(),
        "bool": ir.IntType(1),
        "char": ir.IntType(8),
        "i8": ir.IntType(8),
        "i16": ir.IntType(16),
        "i32": ir.IntType(32),
        "i64": ir.IntType(64),
        "u8": ir.IntType(8),
        "u16": ir.IntType(16),
        "u32": ir.IntType(32),
        "u64": ir.IntType(64),
        "f32": ir.FloatType(),
        "f64": ir.DoubleType(),
        "int": ir.IntType(32),  # 默認整數為 i32
        "float": ir.FloatType(),  # 默認浮點為 f32
        "double": ir.DoubleType(),
        "string": ir.IntType(8).as_pointer()  # 暫時用 char* 表示字符串
    }
    
    # 跟踪已註冊結構體的欄位資訊 (保留用於兼容)
    _struct_fields: Dict[str, Tuple[List[ir.Type], Optional[List[str]]]] = {}
    
    # 跟踪已註冊枚舉的成員 (保留用於兼容)
    _enum_members: Dict[str, Dict[str, int]] = {}
    
    # 跟踪已註冊聯合類型的成員 (保留用於兼容)
    _union_fields: Dict[str, List[Tuple[str, ir.Type]]] = {}
    
    @classmethod
    def initialize(cls):
        """
        初始化類型系統
        (兼容方法，實際調用 TypeSystem.initialize)
        """
        # 確保 TypeSystem 已初始化
        TypeSystem.initialize()
        
        # 清除本地快取
        cls.clear_cache()
    
    @classmethod
    def get_llvm_type(cls, type_name: str, allow_default: bool = True) -> ir.Type:
        """
        獲取 LLVM 類型
        (兼容方法，轉發到 TypeSystem.get_llvm_type)
        
        Args:
            type_name: Glux 類型名稱
            allow_default: 允許對未知類型返回默認類型
            
        Returns:
            LLVM 類型
            
        Raises:
            TypeError: 如果類型無法解析且不允許默認類型
        """
        # 先檢查本地快取
        if type_name in cls._type_cache:
            return cls._type_cache[type_name]
        
        # 從 TypeSystem 獲取類型
        llvm_type = TypeSystem.get_llvm_type(type_name, allow_default)
        
        # 更新本地快取
        cls._type_cache[type_name] = llvm_type
        
        return llvm_type
    
    @classmethod
    def register_struct_type(cls, name: str, field_types: List[ir.Type], field_names: Optional[List[str]] = None) -> ir.LiteralStructType:
        """
        註冊結構體類型
        (兼容方法，轉發到 TypeSystem.register_struct_type)
        
        Args:
            name: 結構體名稱
            field_types: 欄位類型列表
            field_names: 欄位名稱列表 (可選)
            
        Returns:
            LLVM 結構體類型
            
        Raises:
            ValueError: 如果欄位名稱和欄位類型數量不匹配
        """
        # 註冊到 TypeSystem
        glux_type = TypeSystem.register_struct_type(name, field_types, field_names)
        
        # 更新本地快取
        cls._type_cache[name] = glux_type.llvm_type
        cls._struct_fields[name] = (field_types, field_names)
        
        return glux_type.llvm_type
    
    @classmethod
    def get_struct_fields(cls, struct_name: str) -> Optional[Tuple[List[ir.Type], Optional[List[str]]]]:
        """
        獲取結構體欄位信息
        (兼容方法，轉發到 TypeSystem.get_struct_fields)
        
        Args:
            struct_name: 結構體名稱
            
        Returns:
            欄位類型和欄位名稱的元組，如果結構體不存在則返回 None
        """
        # 先檢查本地快取
        if struct_name in cls._struct_fields:
            return cls._struct_fields[struct_name]
        
        # 從 TypeSystem 獲取
        fields = TypeSystem.get_struct_fields(struct_name)
        
        # 更新本地快取
        if fields:
            cls._struct_fields[struct_name] = fields
        
        return fields
    
    @classmethod
    def register_enum_type(cls, name: str, members: Dict[str, int], base_type: ir.IntType = None) -> ir.IntType:
        """
        註冊枚舉類型
        (兼容方法，轉發到 TypeSystem.register_enum_type)
        
        Args:
            name: 枚舉名稱
            members: 枚舉成員及其值
            base_type: 枚舉的基礎類型 (默認為 i32)
            
        Returns:
            LLVM 枚舉類型 (整數類型)
        """
        # 註冊到 TypeSystem
        glux_type = TypeSystem.register_enum_type(name, members, base_type)
        
        # 更新本地快取
        cls._type_cache[name] = glux_type.llvm_type
        cls._enum_members[name] = members
        
        return glux_type.llvm_type
    
    @classmethod
    def get_enum_members(cls, enum_name: str) -> Optional[Dict[str, int]]:
        """
        獲取枚舉成員信息
        (兼容方法，轉發到 TypeSystem.get_enum_members)
        
        Args:
            enum_name: 枚舉名稱
            
        Returns:
            枚舉成員字典，如果枚舉不存在則返回 None
        """
        # 先檢查本地快取
        if enum_name in cls._enum_members:
            return cls._enum_members[enum_name]
        
        # 從 TypeSystem 獲取
        members = TypeSystem.get_enum_members(enum_name)
        
        # 更新本地快取
        if members:
            cls._enum_members[enum_name] = members
        
        return members
    
    @classmethod
    def register_union_type(cls, name: str, fields: List[Tuple[str, ir.Type]]) -> ir.Type:
        """
        註冊聯合類型
        (兼容方法，轉發到 TypeSystem.register_union_type)
        
        Args:
            name: 聯合類型名稱
            fields: 欄位列表 (名稱, 類型)
            
        Returns:
            LLVM 聯合類型
        """
        # 註冊到 TypeSystem
        glux_type = TypeSystem.register_union_type(name, fields)
        
        # 更新本地快取
        cls._type_cache[name] = glux_type.llvm_type
        cls._union_fields[name] = fields
        
        return glux_type.llvm_type
    
    @classmethod
    def get_union_fields(cls, union_name: str) -> Optional[List[Tuple[str, ir.Type]]]:
        """
        獲取聯合類型欄位信息
        (兼容方法，轉發到 TypeSystem.get_union_fields)
        
        Args:
            union_name: 聯合類型名稱
            
        Returns:
            聯合類型欄位列表，如果聯合類型不存在則返回 None
        """
        # 先檢查本地快取
        if union_name in cls._union_fields:
            return cls._union_fields[union_name]
        
        # 從 TypeSystem 獲取
        fields = TypeSystem.get_union_fields(union_name)
        
        # 更新本地快取
        if fields:
            cls._union_fields[union_name] = fields
        
        return fields
    
    @classmethod
    def register_function_type(cls, return_type: ir.Type, param_types: List[ir.Type], param_names: Optional[List[str]] = None) -> ir.FunctionType:
        """
        註冊函數類型
        (兼容方法，轉發到 TypeSystem.register_function_type)
        
        Args:
            return_type: 返回類型
            param_types: 參數類型列表
            param_names: 參數名稱列表 (可選)
            
        Returns:
            LLVM 函數類型
        """
        # 生成函數類型名稱
        param_type_str = ",".join(str(pt) for pt in param_types)
        name = f"func_({return_type})_({param_type_str})"
        
        # 註冊到 TypeSystem
        glux_type = TypeSystem.register_function_type(name, return_type, param_types, param_names)
        
        # 更新本地快取
        cls._type_cache[name] = glux_type.llvm_type
        
        return glux_type.llvm_type
    
    @classmethod
    def is_type_compatible(cls, source_type: str, target_type: str) -> bool:
        """
        檢查類型相容性
        (兼容方法，轉發到 TypeSystem.is_type_compatible)
        
        Args:
            source_type: 源類型名稱
            target_type: 目標類型名稱
            
        Returns:
            是否相容
        """
        return TypeSystem.is_type_compatible(source_type, target_type)
    
    @classmethod
    def get_common_type(cls, type1: str, type2: str) -> Optional[str]:
        """
        獲取兩個類型的共同類型
        (兼容方法，轉發到 TypeSystem.get_common_type)
        
        Args:
            type1: 第一個類型名稱
            type2: 第二個類型名稱
            
        Returns:
            共同類型名稱，如果沒有共同類型則返回 None
        """
        return TypeSystem.get_common_type(type1, type2)
    
    @classmethod
    def is_integer_type(cls, type_obj: ir.Type) -> bool:
        """
        判斷類型是否為整數類型
        
        Args:
            type_obj: LLVM 類型
            
        Returns:
            是否為整數類型
        """
        return isinstance(type_obj, ir.IntType)
    
    @classmethod
    def is_float_type(cls, type_obj: ir.Type) -> bool:
        """
        判斷類型是否為浮點類型
        
        Args:
            type_obj: LLVM 類型
            
        Returns:
            是否為浮點類型
        """
        return isinstance(type_obj, (ir.FloatType, ir.DoubleType))
    
    @classmethod
    def is_pointer_type(cls, type_obj: ir.Type) -> bool:
        """
        判斷類型是否為指針類型
        
        Args:
            type_obj: LLVM 類型
            
        Returns:
            是否為指針類型
        """
        return isinstance(type_obj, ir.PointerType)
    
    @classmethod
    def is_array_type(cls, type_obj: ir.Type) -> bool:
        """
        判斷類型是否為數組類型
        
        Args:
            type_obj: LLVM 類型
            
        Returns:
            是否為數組類型
        """
        return isinstance(type_obj, ir.ArrayType)
    
    @classmethod
    def is_struct_type(cls, type_obj: ir.Type) -> bool:
        """
        判斷類型是否為結構體類型
        
        Args:
            type_obj: LLVM 類型
            
        Returns:
            是否為結構體類型
        """
        return isinstance(type_obj, ir.LiteralStructType)
    
    @classmethod
    def get_pointer_element_type(cls, ptr_type: ir.PointerType) -> ir.Type:
        """
        獲取指針的元素類型
        
        Args:
            ptr_type: 指針類型
            
        Returns:
            指針所指向的元素類型
        """
        return ptr_type.pointee
    
    @classmethod
    def get_array_element_type(cls, array_type: ir.ArrayType) -> ir.Type:
        """
        獲取數組的元素類型
        
        Args:
            array_type: 數組類型
            
        Returns:
            數組元素類型
        """
        return array_type.element
    
    @classmethod
    def get_array_size(cls, array_type: ir.ArrayType) -> int:
        """
        獲取數組大小
        
        Args:
            array_type: 數組類型
            
        Returns:
            數組大小
        """
        return array_type.count
    
    @classmethod
    def get_struct_element_type(cls, struct_type: ir.LiteralStructType, index: int) -> ir.Type:
        """
        獲取結構體元素類型
        
        Args:
            struct_type: 結構體類型
            index: 元素索引
            
        Returns:
            結構體元素類型
        """
        if index >= len(struct_type.elements):
            raise IndexError(f"結構體索引 {index} 超出範圍 (0-{len(struct_type.elements)-1})")
        return struct_type.elements[index]
    
    @classmethod
    def clear_cache(cls):
        """
        清除類型快取和結構體欄位信息
        (兼容方法)
        """
        cls._type_cache.clear()
        cls._struct_fields.clear()
        cls._enum_members.clear()
        cls._union_fields.clear()
        
        # 重新添加基本類型
        for name, type_obj in cls._primitive_types.items():
            cls._type_cache[name] = type_obj

    def generate_heterogeneous_collections(self, collection_node):
        """生成支援異質性的集合類型代碼"""
        elements = []
        element_types = []
        
        # 收集所有元素和類型
        for item in collection_node.elements:
            element = self.generate_expr(item)
            elements.append(element)
            element_types.append(element.type)
        
        # 創建通用類型集合
        if isinstance(collection_node, ListExpr):
            # 對於 list，我們使用 void* 數組
            void_ptr = ir.IntType(8).as_pointer()
            list_struct = self._create_heterogeneous_list_type(len(elements))
            
            # 分配 list 結構
            list_ptr = self.builder.alloca(list_struct)
            
            # 設置長度
            length_ptr = self.builder.gep(list_ptr, [
                ir.Constant(ir.IntType(32), 0),
                ir.Constant(ir.IntType(32), 0)
            ])
            self.builder.store(ir.Constant(ir.IntType(32), len(elements)), length_ptr)
            
            # 設置元素
            for i, (element, element_type) in enumerate(zip(elements, element_types)):
                # 創建暫存變數
                temp = self.builder.alloca(element_type)
                self.builder.store(element, temp)
                
                # 轉換為 void*
                element_ptr = self.builder.bitcast(temp, void_ptr)
                
                # 存入 list
                element_ptr_addr = self.builder.gep(list_ptr, [
                    ir.Constant(ir.IntType(32), 0),
                    ir.Constant(ir.IntType(32), 1),
                    ir.Constant(ir.IntType(32), i)
                ])
                self.builder.store(element_ptr, element_ptr_addr)
            
            return list_ptr
        
        elif isinstance(collection_node, TupleExpr):
            # 對於 tuple，我們創建一個結構
            tuple_type = ir.LiteralStructType(element_types)
            tuple_ptr = self.builder.alloca(tuple_type)
            
            # 設置元素
            for i, element in enumerate(elements):
                element_ptr = self.builder.gep(tuple_ptr, [
                    ir.Constant(ir.IntType(32), 0),
                    ir.Constant(ir.IntType(32), i)
                ])
                self.builder.store(element, element_ptr)
            
            return tuple_ptr

    def generate_union_type(self, union_node):
        """生成 union 類型代碼，支援錯誤處理模式"""
        # 檢查是否是 error union
        is_error_union = False
        type_a = None
        type_b = None
        
        for type_expr in union_node.types:
            if isinstance(type_expr, NameExpr) and type_expr.name == "error":
                is_error_union = True
            elif type_a is None:
                type_a = self.get_type_from_expr(type_expr)
            else:
                type_b = self.get_type_from_expr(type_expr)
        
        # 對於錯誤 union，我們使用特殊結構
        if is_error_union:
            value_type = type_a or type_b
            error_union_type = self._create_error_union_type(value_type)
            
            # 分配 union 結構
            union_ptr = self.builder.alloca(error_union_type)
            
            # 設置初始值（無錯誤）
            tag_ptr = self.builder.gep(union_ptr, [
                ir.Constant(ir.IntType(32), 0),
                ir.Constant(ir.IntType(32), 0)
            ])
            self.builder.store(ir.Constant(ir.IntType(8), 0), tag_ptr)
            
            return union_ptr
        
        # 對於一般 union，我們使用最大類型加標記
        else:
            # 計算類型大小
            type_a_size = self.get_type_size(type_a)
            type_b_size = self.get_type_size(type_b)
            max_type = type_a if type_a_size >= type_b_size else type_b
            
            # 創建 union 結構
            union_type = ir.LiteralStructType([
                ir.IntType(8),  # tag
                max_type        # value
            ])
            
            union_ptr = self.builder.alloca(union_type)
            
            # 設置初始標記
            tag_ptr = self.builder.gep(union_ptr, [
                ir.Constant(ir.IntType(32), 0),
                ir.Constant(ir.IntType(32), 0)
            ])
            self.builder.store(ir.Constant(ir.IntType(8), 0), tag_ptr)
            
            return union_ptr

    def _create_error_union_type(self, value_type):
        """創建錯誤 union 類型"""
        return ir.LiteralStructType([
            ir.IntType(8),              # 0 = 正常值, 1 = 錯誤
            value_type,                 # 正常值
            ir.IntType(8).as_pointer()  # 錯誤訊息（字串）
        ])

    def _create_heterogeneous_list_type(self, size):
        """創建異質 list 類型"""
        void_ptr = ir.IntType(8).as_pointer()
        return ir.LiteralStructType([
            ir.IntType(32),                      # 長度
            ir.ArrayType(void_ptr, size)         # 元素（void*）
        ])


# 初始化類型生成器
TypeGenerator.initialize() 