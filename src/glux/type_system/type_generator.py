"""
類型生成器模組
負責生成LLVM類型並管理類型系統
"""

from typing import Dict, List, Optional, Union, Any
import logging
from llvmlite import ir

from .type_defs import GluxType, TypeKind, NumericType


class TypeGenerator:
    """
    類型生成器類
    負責生成LLVM類型並管理類型系統
    """
    
    def __init__(self, module: ir.Module, logger: Optional[logging.Logger] = None):
        """
        初始化類型生成器
        
        Args:
            module: LLVM模組
            logger: 日誌記錄器
        """
        self.module = module
        self.logger = logger or logging.getLogger("TypeGenerator")
        self.type_cache: Dict[str, GluxType] = {}
        
        # 初始化基本類型
        self._initialize_primitive_types()
    
    def _initialize_primitive_types(self):
        """初始化基本類型"""
        # 整數類型
        self.int8_type = self._create_primitive_type("int8", ir.IntType(8), NumericType.INT8, is_signed=True)
        self.int16_type = self._create_primitive_type("int16", ir.IntType(16), NumericType.INT16, is_signed=True)
        self.int32_type = self._create_primitive_type("int32", ir.IntType(32), NumericType.INT32, is_signed=True)
        self.int64_type = self._create_primitive_type("int64", ir.IntType(64), NumericType.INT64, is_signed=True)
        
        # 無符號整數類型
        self.uint8_type = self._create_primitive_type("uint8", ir.IntType(8), NumericType.UINT8, is_signed=False)
        self.uint16_type = self._create_primitive_type("uint16", ir.IntType(16), NumericType.UINT16, is_signed=False)
        self.uint32_type = self._create_primitive_type("uint32", ir.IntType(32), NumericType.UINT32, is_signed=False)
        self.uint64_type = self._create_primitive_type("uint64", ir.IntType(64), NumericType.UINT64, is_signed=False)
        
        # 浮點類型
        self.float32_type = self._create_primitive_type("float32", ir.FloatType(), NumericType.FLOAT32)
        self.float64_type = self._create_primitive_type("float64", ir.DoubleType(), NumericType.FLOAT64)
        
        # 其他基本類型
        self.bool_type = self._create_primitive_type("bool", ir.IntType(1), None)
        self.void_type = GluxType("void", TypeKind.VOID)
        self.void_type.llvm_type = ir.VoidType()
        self.type_cache["void"] = self.void_type
        
        # 字符類型
        self.char_type = self._create_primitive_type("char", ir.IntType(8), None)
        
        # 字符串類型 (實際上是字符指針)
        self.string_type = self.create_pointer_type(self.char_type)
        self.string_type.name = "string"  # 重新命名
        self.type_cache["string"] = self.string_type
        
        # 通用類型
        self.any_type = GluxType("any", TypeKind.ANY)
        self.any_type.llvm_type = ir.IntType(8).as_pointer()  # void*
        self.type_cache["any"] = self.any_type
        
        # 錯誤類型
        self.error_type = GluxType("error", TypeKind.ERROR)
        self.error_type.llvm_type = ir.IntType(8).as_pointer()  # 錯誤使用指針表示
        self.type_cache["error"] = self.error_type
        
        # null 類型
        self.null_type = GluxType("null", TypeKind.NULL)
        self.null_type.llvm_type = ir.IntType(8).as_pointer()  # null 使用指針表示
        self.type_cache["null"] = self.null_type
    
    def _create_primitive_type(self, name: str, llvm_type: ir.Type, 
                              numeric_type: Optional[NumericType] = None, is_signed: bool = True) -> GluxType:
        """
        創建基本類型
        
        Args:
            name: 類型名稱
            llvm_type: LLVM類型
            numeric_type: 數值類型（對於數值類型）
            is_signed: 是否有符號（對於整數類型）
            
        Returns:
            創建的基本類型
        """
        type_obj = GluxType(name, TypeKind.PRIMITIVE)
        type_obj.llvm_type = llvm_type
        type_obj.numeric_type = numeric_type
        type_obj.is_signed = is_signed
        self.type_cache[name] = type_obj
        return type_obj
    
    def create_pointer_type(self, element_type: GluxType) -> GluxType:
        """
        創建指針類型
        
        Args:
            element_type: 元素類型
            
        Returns:
            指針類型
        """
        name = f"*{element_type.name}"
        
        # 檢查緩存
        if name in self.type_cache:
            return self.type_cache[name]
        
        type_obj = GluxType(name, TypeKind.POINTER)
        type_obj.element_type = element_type
        type_obj.llvm_type = element_type.llvm_type.as_pointer()
        self.type_cache[name] = type_obj
        return type_obj
    
    def create_array_type(self, element_type: GluxType, size: int) -> GluxType:
        """
        創建數組類型
        
        Args:
            element_type: 元素類型
            size: 數組大小
            
        Returns:
            數組類型
        """
        name = f"[{size}]{element_type.name}"
        
        # 檢查緩存
        if name in self.type_cache:
            return self.type_cache[name]
        
        type_obj = GluxType(name, TypeKind.ARRAY)
        type_obj.element_type = element_type
        type_obj.size = size
        type_obj.llvm_type = ir.ArrayType(element_type.llvm_type, size)
        self.type_cache[name] = type_obj
        return type_obj
    
    def create_list_type(self, element_type: GluxType) -> GluxType:
        """
        創建列表類型
        
        Args:
            element_type: 元素類型
            
        Returns:
            列表類型
        """
        name = f"list<{element_type.name}>"
        
        # 檢查緩存
        if name in self.type_cache:
            return self.type_cache[name]
        
        # 列表實際上是一個結構體，包含容量、大小和元素指針
        list_struct_type = ir.LiteralStructType([
            ir.IntType(64),  # 容量
            ir.IntType(64),  # 大小
            element_type.llvm_type.as_pointer()  # 元素指針
        ])
        
        type_obj = GluxType(name, TypeKind.LIST)
        type_obj.element_type = element_type
        type_obj.llvm_type = list_struct_type
        self.type_cache[name] = type_obj
        return type_obj
    
    def create_tuple_type(self, element_types: List[GluxType]) -> GluxType:
        """
        創建元組類型
        
        Args:
            element_types: 元素類型列表
            
        Returns:
            元組類型
        """
        name = f"({', '.join(t.name for t in element_types)})"
        
        # 檢查緩存
        if name in self.type_cache:
            return self.type_cache[name]
        
        # 創建LLVM元組類型
        llvm_types = [t.llvm_type for t in element_types]
        llvm_struct_type = ir.LiteralStructType(llvm_types)
        
        type_obj = GluxType(name, TypeKind.TUPLE)
        type_obj.element_types = element_types
        type_obj.llvm_type = llvm_struct_type
        self.type_cache[name] = type_obj
        return type_obj
    
    def create_map_type(self, key_type: GluxType, value_type: GluxType) -> GluxType:
        """
        創建映射類型
        
        Args:
            key_type: 鍵類型
            value_type: 值類型
            
        Returns:
            映射類型
        """
        name = f"map<{key_type.name}, {value_type.name}>"
        
        # 檢查緩存
        if name in self.type_cache:
            return self.type_cache[name]
        
        # 映射實際上是一個指針，指向內部實現
        # 這裡簡化為通用指針
        type_obj = GluxType(name, TypeKind.MAP)
        type_obj.key_type = key_type
        type_obj.value_type = value_type
        type_obj.llvm_type = ir.IntType(8).as_pointer()
        self.type_cache[name] = type_obj
        return type_obj
    
    def create_struct_type(self, struct_name: str, field_types: List[GluxType], 
                         field_names: List[str]) -> GluxType:
        """
        創建結構體類型
        
        Args:
            struct_name: 結構體名稱
            field_types: 欄位類型列表
            field_names: 欄位名稱列表
            
        Returns:
            結構體類型
        """
        # 檢查緩存
        if struct_name in self.type_cache:
            return self.type_cache[struct_name]
        
        # 創建LLVM結構體類型
        llvm_struct_type = ir.LiteralStructType([t.llvm_type for t in field_types])
        
        type_obj = GluxType(struct_name, TypeKind.STRUCT)
        type_obj.field_types = field_types
        type_obj.field_names = field_names
        type_obj.llvm_type = llvm_struct_type
        self.type_cache[struct_name] = type_obj
        return type_obj
    
    def create_union_type(self, union_types: List[GluxType]) -> GluxType:
        """
        創建聯合類型
        
        Args:
            union_types: 聯合類型列表
            
        Returns:
            聯合類型
        """
        name = " | ".join(t.name for t in union_types)
        
        # 檢查緩存
        if name in self.type_cache:
            return self.type_cache[name]
        
        # 聯合類型使用標記聯合實現
        # 包含類型標記和所有可能類型的內存（使用聯合體）
        type_obj = GluxType(name, TypeKind.UNION)
        type_obj.union_types = union_types
        
        # 簡化為通用指針
        type_obj.llvm_type = ir.IntType(8).as_pointer()
        self.type_cache[name] = type_obj
        return type_obj
    
    def create_function_type(self, return_type: GluxType, param_types: List[GluxType], 
                           param_names: List[str]) -> GluxType:
        """
        創建函數類型
        
        Args:
            return_type: 返回類型
            param_types: 參數類型列表
            param_names: 參數名稱列表
            
        Returns:
            函數類型
        """
        name = f"fn({', '.join(t.name for t in param_types)}) -> {return_type.name}"
        
        # 檢查緩存
        if name in self.type_cache:
            return self.type_cache[name]
        
        # 創建LLVM函數類型
        llvm_func_type = ir.FunctionType(
            return_type.llvm_type,
            [t.llvm_type for t in param_types]
        )
        
        type_obj = GluxType(name, TypeKind.FUNCTION)
        type_obj.return_type = return_type
        type_obj.param_types = param_types
        type_obj.param_names = param_names
        type_obj.llvm_type = llvm_func_type
        self.type_cache[name] = type_obj
        return type_obj
    
    def create_interface_type(self, interface_name: str, methods: Dict[str, GluxType]) -> GluxType:
        """
        創建接口類型
        
        Args:
            interface_name: 接口名稱
            methods: 方法字典，鍵為方法名，值為函數類型
            
        Returns:
            接口類型
        """
        # 檢查緩存
        if interface_name in self.type_cache:
            return self.type_cache[interface_name]
        
        # 接口實際上是一個虛擬表結構
        type_obj = GluxType(interface_name, TypeKind.INTERFACE)
        type_obj.methods = methods
        
        # 簡化為通用指針
        type_obj.llvm_type = ir.IntType(8).as_pointer()
        self.type_cache[interface_name] = type_obj
        return type_obj
    
    def create_optional_type(self, element_type: GluxType) -> GluxType:
        """
        創建可選類型
        
        Args:
            element_type: 元素類型
            
        Returns:
            可選類型
        """
        name = f"?{element_type.name}"
        
        # 檢查緩存
        if name in self.type_cache:
            return self.type_cache[name]
        
        # 可選類型使用標記聯合實現
        # 包含一個布爾標記和值
        llvm_opt_type = ir.LiteralStructType([
            ir.IntType(1),  # 是否有值
            element_type.llvm_type  # 值
        ])
        
        type_obj = GluxType(name, TypeKind.OPTIONAL)
        type_obj.element_type = element_type
        type_obj.llvm_type = llvm_opt_type
        self.type_cache[name] = type_obj
        return type_obj
    
    def deduce_numeric_type(self, value: Union[int, float]) -> GluxType:
        """
        推導數值類型
        
        Args:
            value: 數值
            
        Returns:
            數值類型
        """
        if isinstance(value, int):
            # 整數類型推導
            if -128 <= value <= 127:
                return self.int8_type
            elif -32768 <= value <= 32767:
                return self.int16_type
            elif -2147483648 <= value <= 2147483647:
                return self.int32_type
            else:
                return self.int64_type
        else:
            # 浮點類型推導
            # 科學計數法或較大數值使用float64
            if abs(value) > 3.4e38 or abs(value) < 1.17e-38 or 'e' in str(value).lower():
                return self.float64_type
            else:
                return self.float32_type
    
    def get_widest_numeric_type(self, type1: GluxType, type2: GluxType) -> GluxType:
        """
        獲取兩個類型中較寬的數值類型
        
        Args:
            type1: 第一個類型
            type2: 第二個類型
            
        Returns:
            較寬的類型
        """
        # 浮點類型比整數類型寬
        if hasattr(type1, 'numeric_type') and hasattr(type2, 'numeric_type'):
            if type1.numeric_type in [NumericType.FLOAT32, NumericType.FLOAT64]:
                if type2.numeric_type in [NumericType.FLOAT32, NumericType.FLOAT64]:
                    # 兩個都是浮點類型，取較高精度
                    if type1.numeric_type == NumericType.FLOAT64 or type2.numeric_type == NumericType.FLOAT64:
                        return self.float64_type
                    else:
                        return self.float32_type
                else:
                    # type1 是浮點，type2 是整數
                    return type1
            elif type2.numeric_type in [NumericType.FLOAT32, NumericType.FLOAT64]:
                # type2 是浮點，type1 是整數
                return type2
            else:
                # 兩個都是整數類型
                type_order = [
                    NumericType.INT8, NumericType.UINT8,
                    NumericType.INT16, NumericType.UINT16,
                    NumericType.INT32, NumericType.UINT32,
                    NumericType.INT64, NumericType.UINT64
                ]
                if type_order.index(type1.numeric_type) > type_order.index(type2.numeric_type):
                    return type1
                else:
                    return type2
        
        # 如果不是數值類型，返回任意一個（通常不應該進入這種情況）
        return type1
    
    def can_convert(self, from_type: GluxType, to_type: GluxType) -> bool:
        """
        檢查類型轉換是否可行
        
        Args:
            from_type: 源類型
            to_type: 目標類型
            
        Returns:
            是否可以轉換
        """
        # 相同類型可以轉換
        if from_type.name == to_type.name:
            return True
        
        # 任何類型都可以轉換為 any
        if to_type.kind == TypeKind.ANY:
            return True
        
        # null 可以轉換為指針或可選類型
        if from_type.kind == TypeKind.NULL:
            return (to_type.kind == TypeKind.POINTER or
                    to_type.kind == TypeKind.OPTIONAL)
        
        # 數值類型轉換
        if hasattr(from_type, 'numeric_type') and hasattr(to_type, 'numeric_type'):
            # 整數到浮點
            if from_type.numeric_type in [NumericType.INT8, NumericType.INT16, NumericType.INT32, NumericType.INT64,
                                        NumericType.UINT8, NumericType.UINT16, NumericType.UINT32, NumericType.UINT64]:
                if to_type.numeric_type in [NumericType.FLOAT32, NumericType.FLOAT64]:
                    return True
            
            # 小寬度到大寬度
            type_order = [
                NumericType.INT8, NumericType.UINT8,
                NumericType.INT16, NumericType.UINT16,
                NumericType.INT32, NumericType.UINT32,
                NumericType.INT64, NumericType.UINT64,
                NumericType.FLOAT32, NumericType.FLOAT64
            ]
            if (from_type.numeric_type in type_order and to_type.numeric_type in type_order and
                type_order.index(from_type.numeric_type) <= type_order.index(to_type.numeric_type)):
                return True
        
        # 普通類型到可選類型
        if to_type.kind == TypeKind.OPTIONAL:
            if hasattr(to_type, 'element_type') and from_type.name == to_type.element_type.name:
                return True
        
        # 默認情況下，轉換不可行
        return False 