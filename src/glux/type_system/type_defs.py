"""
Glux 類型系統的基本定義
包含類型種類和Glux類型的資料結構
"""

from enum import Enum, auto
from typing import List, Dict, Optional, Union, Any


class TypeKind(Enum):
    """類型種類枚舉"""
    VOID = auto()       # 空類型
    PRIMITIVE = auto()  # 基本類型（整數、浮點數、布爾等）
    STRING = auto()     # 字串類型
    ARRAY = auto()      # 陣列類型
    MAP = auto()        # 映射類型
    STRUCT = auto()     # 結構體類型
    UNION = auto()      # 聯合類型
    FUNCTION = auto()   # 函數類型
    INTERFACE = auto()  # 介面類型
    GENERIC = auto()    # 泛型類型
    ERROR = auto()      # 錯誤類型
    ANY = auto()        # 任意類型
    TUPLE = auto()      # 元組類型
    POINTER = auto()    # 指標類型
    NULL = auto()       # 空值類型
    LIST = auto()       # 列表類型
    OPTIONAL = auto()   # 可選類型
    TASK = auto()       # 並發任務類型


class NumericType(Enum):
    """數值類型枚舉"""
    INT8 = auto()      # 8位有符號整數
    INT16 = auto()     # 16位有符號整數
    INT32 = auto()     # 32位有符號整數
    INT64 = auto()     # 64位有符號整數
    UINT8 = auto()     # 8位無符號整數
    UINT16 = auto()    # 16位無符號整數
    UINT32 = auto()    # 32位無符號整數
    UINT64 = auto()    # 64位無符號整數
    FLOAT32 = auto()   # 32位浮點數
    FLOAT64 = auto()   # 64位浮點數


class GluxType:
    """Glux語言類型類別"""
    
    def __init__(self, name: str, kind: TypeKind):
        """
        初始化類型
        
        Args:
            name: 類型名稱
            kind: 類型種類
        """
        self.name = name
        self.kind = kind
        self.subtypes: List[GluxType] = []
        self.fields: Dict[str, 'GluxType'] = {}
        self.methods: Dict[str, 'GluxType'] = {}
        self.params: List['GluxType'] = []
        self.param_names: List[str] = []
        self.return_type: Optional['GluxType'] = None
        self.is_mutable: bool = False
        
        # 以下屬性根據類型種類可能存在或不存在
        self.numeric_type = None  # 針對數值類型
        self.element_type = None  # 針對陣列、列表、指標、可選類型
        self.key_type = None      # 針對映射類型
        self.value_type = None    # 針對映射類型
        self.fields = {}          # 針對結構體類型
        self.methods = {}         # 針對結構體、介面類型
        self.param_types = None   # 針對函數類型
        self.return_type = None   # 針對函數類型
        self.variant_types = None # 針對聯合類型
        self.element_types = None # 針對元組類型
        self.base_type = None     # 針對指標類型
        self.parent_interfaces = None # 針對介面類型
    
    def __str__(self) -> str:
        """
        將類型轉換為字串表示
        
        Returns:
            類型的字串表示
        """
        if self.kind == TypeKind.ARRAY:
            return f"[]{self.subtypes[0]}"
        elif self.kind == TypeKind.MAP:
            return f"map<{self.subtypes[0]}, {self.subtypes[1]}>"
        elif self.kind == TypeKind.FUNCTION:
            params_str = ", ".join(str(param) for param in self.params)
            return f"fn({params_str}) -> {self.return_type}"
        elif self.kind == TypeKind.UNION:
            types_str = " | ".join(str(t) for t in self.subtypes)
            return f"({types_str})"
        elif self.kind == TypeKind.TUPLE:
            return f"({', '.join(str(t) for t in self.subtypes)})"
        elif self.kind == TypeKind.POINTER:
            return f"*{self.subtypes[0]}"
        else:
            return self.name
    
    def __eq__(self, other: object) -> bool:
        """
        比較兩個類型是否相等
        
        Args:
            other: 另一個類型
            
        Returns:
            是否相等
        """
        if not isinstance(other, GluxType):
            return False
        
        # 基本比較
        if self.kind != other.kind or self.name != other.name:
            return False
        
        # 比較子類型
        if len(self.subtypes) != len(other.subtypes):
            return False
        
        for i, subtype in enumerate(self.subtypes):
            if subtype != other.subtypes[i]:
                return False
        
        # 如果是函數類型，還需要比較參數和返回類型
        if self.kind == TypeKind.FUNCTION:
            if len(self.params) != len(other.params):
                return False
            
            for i, param in enumerate(self.params):
                if param != other.params[i]:
                    return False
            
            if self.return_type != other.return_type:
                return False
        
        return True
    
    def is_function(self) -> bool:
        """
        檢查類型是否為函數類型
        
        Returns:
            是否為函數類型
        """
        return self.kind == TypeKind.FUNCTION 