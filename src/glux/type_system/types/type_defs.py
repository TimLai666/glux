"""
Glux 類型定義
提供類型系統的基本數據結構
"""

from enum import Enum, auto
from typing import Optional, List, Dict, Any, Union
from llvmlite import ir


class TypeKind(Enum):
    """類型種類枚舉"""
    PRIMITIVE = auto()    # 基本類型
    POINTER = auto()      # 指針類型
    ARRAY = auto()        # 數組類型
    TUPLE = auto()        # 元組類型
    LIST = auto()         # 列表類型
    MAP = auto()          # 映射類型
    STRUCT = auto()       # 結構體類型
    ENUM = auto()         # 枚舉類型
    UNION = auto()        # 聯合類型
    FUNCTION = auto()     # 函數類型
    GENERIC = auto()      # 泛型類型
    INTERFACE = auto()    # 接口類型
    ERROR = auto()        # 錯誤類型
    ANY = auto()          # 任意類型
    OPTIONAL = auto()     # 可選類型
    UNKNOWN = auto()      # 未知類型


class NumericType(Enum):
    """數值類型種類枚舉"""
    INT8 = 8
    INT16 = 16
    INT32 = 32
    INT64 = 64
    UINT8 = 8
    UINT16 = 16
    UINT32 = 32
    UINT64 = 64
    FLOAT32 = 32
    FLOAT64 = 64


class GluxType:
    """
    Glux 類型表示
    提供類型系統的抽象表示，便於類型檢查和轉換
    """
    
    def __init__(self, 
                 name: str, 
                 kind: TypeKind, 
                 llvm_type: Optional[ir.Type] = None,
                 element_type: Optional['GluxType'] = None,
                 element_types: Optional[List['GluxType']] = None,
                 key_type: Optional['GluxType'] = None,
                 value_type: Optional['GluxType'] = None,
                 size: Optional[int] = None,
                 numeric_type: Optional[NumericType] = None,
                 is_signed: bool = True):
        """
        初始化 Glux 類型
        
        Args:
            name: 類型名稱
            kind: 類型種類
            llvm_type: LLVM 類型對象
            element_type: 元素類型 (用於指針、數組等)
            element_types: 元素類型列表 (用於元組等)
            key_type: 鍵類型 (用於映射)
            value_type: 值類型 (用於映射)
            size: 大小 (用於數組等)
            numeric_type: 數值類型 (INT8, FLOAT32 等)
            is_signed: 對於整數類型，是否有符號
        """
        self.name = name
        self.kind = kind
        self.llvm_type = llvm_type
        self.element_type = element_type
        self.element_types = element_types or []
        self.key_type = key_type
        self.value_type = value_type
        self.size = size
        self.numeric_type = numeric_type
        self.is_signed = is_signed
        
        # 額外屬性
        self.field_names: Optional[List[str]] = None  # 結構體欄位名稱
        self.field_types: Optional[List['GluxType']] = None  # 結構體欄位類型
        self.enum_values: Optional[Dict[str, int]] = None  # 枚舉值
        self.methods: Dict[str, 'GluxType'] = {}  # 接口方法
        self.union_types: List['GluxType'] = []  # 聯合類型成員
        self.return_type: Optional['GluxType'] = None  # 函數返回類型
        self.param_types: Optional[List['GluxType']] = None  # 函數參數類型
        self.param_names: Optional[List[str]] = None  # 函數參數名稱
        
    def __eq__(self, other):
        """檢查類型相等性"""
        if not isinstance(other, GluxType):
            return False
        return self.name == other.name and self.kind == other.kind
    
    def __hash__(self):
        """計算類型哈希值"""
        return hash((self.name, self.kind))
    
    def __str__(self):
        """返回類型的字符串表示"""
        return self.name
    
    def is_primitive(self) -> bool:
        """判斷是否為基本類型"""
        return self.kind == TypeKind.PRIMITIVE
    
    def is_pointer(self) -> bool:
        """判斷是否為指針類型"""
        return self.kind == TypeKind.POINTER
    
    def is_array(self) -> bool:
        """判斷是否為數組類型"""
        return self.kind == TypeKind.ARRAY
    
    def is_tuple(self) -> bool:
        """判斷是否為元組類型"""
        return self.kind == TypeKind.TUPLE
    
    def is_list(self) -> bool:
        """判斷是否為列表類型"""
        return self.kind == TypeKind.LIST
    
    def is_map(self) -> bool:
        """判斷是否為映射類型"""
        return self.kind == TypeKind.MAP
    
    def is_struct(self) -> bool:
        """判斷是否為結構體類型"""
        return self.kind == TypeKind.STRUCT
    
    def is_enum(self) -> bool:
        """判斷是否為枚舉類型"""
        return self.kind == TypeKind.ENUM
    
    def is_union(self) -> bool:
        """判斷是否為聯合類型"""
        return self.kind == TypeKind.UNION
    
    def is_function(self) -> bool:
        """判斷是否為函數類型"""
        return self.kind == TypeKind.FUNCTION
    
    def is_generic(self) -> bool:
        """判斷是否為泛型類型"""
        return self.kind == TypeKind.GENERIC
        
    def is_interface(self) -> bool:
        """判斷是否為接口類型"""
        return self.kind == TypeKind.INTERFACE
    
    def is_error(self) -> bool:
        """判斷是否為錯誤類型"""
        return self.kind == TypeKind.ERROR
    
    def is_any(self) -> bool:
        """判斷是否為任意類型"""
        return self.kind == TypeKind.ANY
    
    def is_optional(self) -> bool:
        """判斷是否為可選類型"""
        return self.kind == TypeKind.OPTIONAL
    
    def is_integer(self) -> bool:
        """判斷是否為整數類型"""
        return (self.is_primitive() and 
                self.numeric_type in (NumericType.INT8, NumericType.INT16, 
                                      NumericType.INT32, NumericType.INT64,
                                      NumericType.UINT8, NumericType.UINT16, 
                                      NumericType.UINT32, NumericType.UINT64))
    
    def is_float(self) -> bool:
        """判斷是否為浮點類型"""
        return (self.is_primitive() and 
                self.numeric_type in (NumericType.FLOAT32, NumericType.FLOAT64))
    
    def is_numeric(self) -> bool:
        """判斷是否為數值類型"""
        return self.is_integer() or self.is_float()
    
    def is_signed_integer(self) -> bool:
        """判斷是否為有符號整數類型"""
        return self.is_integer() and self.is_signed
    
    def is_unsigned_integer(self) -> bool:
        """判斷是否為無符號整數類型"""
        return self.is_integer() and not self.is_signed
    
    def get_bit_width(self) -> int:
        """獲取數值類型的位寬"""
        if self.numeric_type:
            return self.numeric_type.value
        return 0
    
    def clone(self) -> 'GluxType':
        """創建類型的副本"""
        new_type = GluxType(
            name=self.name,
            kind=self.kind,
            llvm_type=self.llvm_type,
            element_type=self.element_type,
            element_types=self.element_types.copy() if self.element_types else None,
            key_type=self.key_type,
            value_type=self.value_type,
            size=self.size,
            numeric_type=self.numeric_type,
            is_signed=self.is_signed
        )
        
        new_type.field_names = self.field_names.copy() if self.field_names else None
        new_type.field_types = self.field_types.copy() if self.field_types else None
        new_type.enum_values = self.enum_values.copy() if self.enum_values else None
        new_type.methods = self.methods.copy()
        new_type.union_types = self.union_types.copy()
        new_type.return_type = self.return_type
        new_type.param_types = self.param_types.copy() if self.param_types else None
        new_type.param_names = self.param_names.copy() if self.param_names else None
        
        return new_type 