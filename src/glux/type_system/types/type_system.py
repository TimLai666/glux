"""
Glux 類型系統
提供類型註冊、查詢、檢查和轉換功能
"""

from llvmlite import ir
from typing import Dict, List, Optional, Set, Tuple, Union, Any
import logging
import re

from .type_defs import TypeKind, GluxType

logger = logging.getLogger(__name__)


class TypeSystem:
    """
    Glux 類型系統
    管理所有類型的註冊、查詢和類型檢查
    """
    
    # 類型註冊表
    _types: Dict[str, GluxType] = {}
    
    # LLVM 類型快取
    _llvm_type_cache: Dict[str, ir.Type] = {}
    
    # 基本類型映射
    _primitive_types: Dict[str, ir.Type] = {
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
    
    # 有符號整數類型集合
    _signed_int_types: Set[str] = {"i8", "i16", "i32", "i64", "int"}
    
    # 無符號整數類型集合
    _unsigned_int_types: Set[str] = {"u8", "u16", "u32", "u64", "char"}
    
    # 浮點類型集合 
    _float_types: Set[str] = {"f32", "f64", "float", "double"}
    
    # 結構體欄位信息
    _struct_fields: Dict[str, Tuple[List[ir.Type], Optional[List[str]]]] = {}
    
    # 枚舉成員信息
    _enum_members: Dict[str, Dict[str, int]] = {}
    
    # 聯合類型欄位信息
    _union_fields: Dict[str, List[Tuple[str, ir.Type]]] = {}
    
    # 類型相容性映射
    _type_compat: Dict[str, Set[str]] = {}
    
    @classmethod
    def initialize(cls):
        """初始化類型系統"""
        cls.clear()
        cls._initialize_primitive_types()
        cls._initialize_type_compatibility()
    
    @classmethod
    def _initialize_primitive_types(cls):
        """註冊所有基本類型"""
        for type_name, llvm_type in cls._primitive_types.items():
            cls.register_type(GluxType(type_name, TypeKind.PRIMITIVE, llvm_type))
    
    @classmethod
    def _initialize_type_compatibility(cls):
        """初始化類型相容性規則"""
        # 整數類型的相容性規則
        for int_type in cls._signed_int_types:
            cls._type_compat[int_type] = set()
            bit_width = int(re.search(r'(\d+)', int_type).group(1)) if re.search(r'(\d+)', int_type) else 32
            # 更大位寬的有符號整數類型相容
            for target in cls._signed_int_types:
                target_width = int(re.search(r'(\d+)', target).group(1)) if re.search(r'(\d+)', target) else 32
                if target_width >= bit_width:
                    cls._type_compat[int_type].add(target)
            # 浮點類型相容
            cls._type_compat[int_type].update(cls._float_types)
        
        # 無符號整數類型的相容性規則
        for uint_type in cls._unsigned_int_types:
            cls._type_compat[uint_type] = set()
            bit_width = int(re.search(r'(\d+)', uint_type).group(1)) if re.search(r'(\d+)', uint_type) else 8
            # 更大位寬的無符號整數類型相容
            for target in cls._unsigned_int_types:
                target_width = int(re.search(r'(\d+)', target).group(1)) if re.search(r'(\d+)', target) else 8
                if target_width >= bit_width:
                    cls._type_compat[uint_type].add(target)
            # 足夠大的有符號整數和浮點類型相容
            for target in cls._signed_int_types:
                target_width = int(re.search(r'(\d+)', target).group(1)) if re.search(r'(\d+)', target) else 32
                if target_width > bit_width:  # 需要更大的有符號整數以保證安全轉換
                    cls._type_compat[uint_type].add(target)
            # 浮點類型相容
            cls._type_compat[uint_type].update(cls._float_types)
        
        # 浮點類型的相容性規則
        for float_type in cls._float_types:
            cls._type_compat[float_type] = set()
            is_double = float_type in {"f64", "double"}
            
            # 相同或更高精度的浮點類型相容
            for target in cls._float_types:
                target_is_double = target in {"f64", "double"}
                if not is_double or target_is_double:
                    cls._type_compat[float_type].add(target)
    
    @classmethod
    def register_type(cls, glux_type: GluxType) -> GluxType:
        """
        註冊類型
        
        Args:
            glux_type: Glux 類型
            
        Returns:
            註冊的類型
        """
        cls._types[glux_type.name] = glux_type
        if glux_type.llvm_type is not None:
            cls._llvm_type_cache[glux_type.name] = glux_type.llvm_type
        return glux_type
    
    @classmethod
    def get_type(cls, name: str) -> Optional[GluxType]:
        """
        獲取類型
        
        Args:
            name: 類型名稱
            
        Returns:
            Glux 類型或 None（如果未找到）
        """
        # 檢查已註冊類型
        if name in cls._types:
            return cls._types[name]
        
        # 嘗試解析類型
        try:
            return cls._parse_type(name)
        except:
            return None
    
    @classmethod
    def get_llvm_type(cls, type_name: str, allow_default: bool = True) -> ir.Type:
        """
        獲取 LLVM 類型
        
        Args:
            type_name: 類型名稱
            allow_default: 允許返回默認類型
            
        Returns:
            LLVM 類型
            
        Raises:
            TypeError: 如果無法解析類型且不允許默認類型
        """
        # 檢查類型快取
        if type_name in cls._llvm_type_cache:
            return cls._llvm_type_cache[type_name]
        
        # 嘗試獲取類型
        glux_type = cls.get_type(type_name)
        if glux_type is not None and glux_type.llvm_type is not None:
            return glux_type.llvm_type
        
        # 嘗試解析類型
        try:
            parsed_type = cls._parse_type(type_name)
            if parsed_type is not None and parsed_type.llvm_type is not None:
                return parsed_type.llvm_type
        except Exception as e:
            if not allow_default:
                raise TypeError(f"無法解析類型 '{type_name}': {str(e)}")
        
        # 返回默認類型
        if not allow_default:
            raise TypeError(f"未知的類型: {type_name}")
        
        logger.warning(f"未知類型 '{type_name}' 使用通用指針類型代替")
        default_type = ir.IntType(8).as_pointer()
        cls._llvm_type_cache[type_name] = default_type
        cls.register_type(GluxType(type_name, TypeKind.UNKNOWN, default_type))
        return default_type
    
    @classmethod
    def _parse_type(cls, type_name: str) -> GluxType:
        """
        解析類型名稱
        
        Args:
            type_name: 類型名稱
            
        Returns:
            解析後的 Glux 類型
            
        Raises:
            TypeError: 如果類型無法解析
        """
        # 處理基本類型
        if type_name in cls._primitive_types:
            llvm_type = cls._primitive_types[type_name]
            return cls.register_type(GluxType(type_name, TypeKind.PRIMITIVE, llvm_type))
        
        # 處理指針類型
        if type_name.endswith('*'):
            base_type_name = type_name[:-1].strip()
            base_type = cls.get_type(base_type_name)
            if base_type is None:
                base_type = cls._parse_type(base_type_name)
            
            llvm_type = base_type.llvm_type.as_pointer()
            ptr_type = GluxType(
                type_name, 
                TypeKind.POINTER, 
                llvm_type,
                element_type=base_type
            )
            return cls.register_type(ptr_type)
        
        # 處理數組類型 (e.g., i32[10])
        array_match = re.match(r'^([a-zA-Z0-9_]+)\s*\[\s*(\d+)\s*\]$', type_name)
        if array_match:
            base_type_name = array_match.group(1).strip()
            size = int(array_match.group(2))
            
            if size <= 0:
                raise ValueError(f"數組大小必須為正數: {size}")
                
            base_type = cls.get_type(base_type_name)
            if base_type is None:
                base_type = cls._parse_type(base_type_name)
            
            llvm_type = ir.ArrayType(base_type.llvm_type, size)
            array_type = GluxType(
                type_name, 
                TypeKind.ARRAY, 
                llvm_type,
                element_type=base_type,
                size=size
            )
            return cls.register_type(array_type)
        
        # 處理元組類型 (e.g., (i32, f32))
        if type_name.startswith('(') and type_name.endswith(')'):
            type_elements = cls._parse_tuple_elements(type_name[1:-1])
            element_types = []
            llvm_element_types = []
            
            for elem_type_name in type_elements:
                elem_type = cls.get_type(elem_type_name.strip())
                if elem_type is None:
                    elem_type = cls._parse_type(elem_type_name.strip())
                element_types.append(elem_type)
                llvm_element_types.append(elem_type.llvm_type)
            
            llvm_type = ir.LiteralStructType(llvm_element_types, name=f"tuple_{len(element_types)}")
            tuple_type = GluxType(
                type_name, 
                TypeKind.TUPLE, 
                llvm_type
            )
            return cls.register_type(tuple_type)
        
        # 處理泛型類型
        generic_match = re.match(r'^([a-zA-Z0-9_]+)<(.+)>$', type_name)
        if generic_match:
            base_type_name = generic_match.group(1).strip()
            param_types_str = generic_match.group(2)
            param_type_names = [t.strip() for t in cls._parse_tuple_elements(param_types_str)]
            
            # 目前支持 Option<T> 和 Result<T, E> 兩種泛型類型
            if base_type_name == "Option":
                if len(param_type_names) != 1:
                    raise ValueError(f"Option 泛型類型需要一個參數，但提供了 {len(param_type_names)} 個")
                
                value_type = cls.get_type(param_type_names[0])
                if value_type is None:
                    value_type = cls._parse_type(param_type_names[0])
                
                # Option<T> 實現為 { bool present; T value; }
                llvm_type = ir.LiteralStructType([ir.IntType(1), value_type.llvm_type], name=f"Option_{param_type_names[0]}")
                option_type = GluxType(
                    type_name, 
                    TypeKind.GENERIC, 
                    llvm_type
                )
                return cls.register_type(option_type)
                
            elif base_type_name == "Result":
                if len(param_type_names) != 2:
                    raise ValueError(f"Result 泛型類型需要兩個參數，但提供了 {len(param_type_names)} 個")
                
                ok_type = cls.get_type(param_type_names[0])
                if ok_type is None:
                    ok_type = cls._parse_type(param_type_names[0])
                
                err_type = cls.get_type(param_type_names[1])
                if err_type is None:
                    err_type = cls._parse_type(param_type_names[1])
                
                # Result<T, E> 實現為 { bool is_ok; union { T ok; E err; } data; }
                union_type = cls._create_union_type([("ok", ok_type.llvm_type), ("err", err_type.llvm_type)], f"ResultUnion_{param_type_names[0]}_{param_type_names[1]}")
                llvm_type = ir.LiteralStructType([ir.IntType(1), union_type], name=f"Result_{param_type_names[0]}_{param_type_names[1]}")
                result_type = GluxType(
                    type_name, 
                    TypeKind.GENERIC, 
                    llvm_type
                )
                return cls.register_type(result_type)
        
        # 未能解析類型
        raise TypeError(f"無法解析類型: {type_name}")
    
    @classmethod
    def _parse_tuple_elements(cls, elements_str: str) -> List[str]:
        """
        解析元組元素
        處理嵌套元組和泛型類型
        
        Args:
            elements_str: 元組元素字符串
            
        Returns:
            元素類型列表
        """
        elements = []
        current = ""
        depth = 0
        angle_depth = 0
        
        for char in elements_str:
            if char == ',' and depth == 0 and angle_depth == 0:
                elements.append(current.strip())
                current = ""
            else:
                if char == '(':
                    depth += 1
                elif char == ')':
                    depth -= 1
                elif char == '<':
                    angle_depth += 1
                elif char == '>':
                    angle_depth -= 1
                current += char
        
        if current.strip():
            elements.append(current.strip())
            
        return elements
    
    @classmethod
    def _create_union_type(cls, fields: List[Tuple[str, ir.Type]], name: str) -> ir.Type:
        """
        創建聯合類型
        
        Args:
            fields: 字段列表 (名稱, 類型)
            name: 聯合類型名稱
            
        Returns:
            LLVM 聯合類型 (使用最大字段的結構體實現)
        """
        # 計算最大字段大小
        max_size = 0
        max_type = None
        
        # 儲存聯合類型欄位信息
        cls._union_fields[name] = fields
        
        # 目前的實現只是使用最大的字段類型
        # 未來應該改進為更準確的聯合類型表示
        for field_name, field_type in fields:
            # 這是一個簡化的計算方式，實際上應該使用 data_layout 計算
            # 暫時使用類型字符串長度作為大小近似值
            size = len(str(field_type))
            if size > max_size:
                max_size = size
                max_type = field_type
        
        if max_type is None:
            # 空聯合類型，返回 i8
            return ir.IntType(8)
            
        return max_type
    
    @classmethod
    def register_struct_type(cls, name: str, field_types: List[ir.Type], field_names: Optional[List[str]] = None) -> GluxType:
        """
        註冊結構體類型
        
        Args:
            name: 結構體名稱
            field_types: 欄位類型列表
            field_names: 欄位名稱列表 (可選)
            
        Returns:
            結構體類型
            
        Raises:
            ValueError: 如果欄位名稱和欄位類型數量不匹配
        """
        if field_names and len(field_names) != len(field_types):
            raise ValueError(f"結構體 '{name}' 的欄位名稱數量 ({len(field_names)}) 與欄位類型數量 ({len(field_types)}) 不符")
        
        # 創建結構體類型
        struct_type = ir.LiteralStructType(field_types, name=name)
        
        # 儲存結構體欄位信息
        cls._struct_fields[name] = (field_types, field_names)
        
        # 註冊類型
        glux_type = GluxType(name, TypeKind.STRUCT, struct_type)
        cls.register_type(glux_type)
        
        return glux_type
    
    @classmethod
    def register_enum_type(cls, name: str, members: Dict[str, int], base_type: ir.IntType = None) -> GluxType:
        """
        註冊枚舉類型
        
        Args:
            name: 枚舉名稱
            members: 枚舉成員及其值
            base_type: 枚舉的基礎類型 (默認為 i32)
            
        Returns:
            枚舉類型
        """
        if base_type is None:
            base_type = ir.IntType(32)  # 默認使用 i32
            
        # 儲存枚舉成員信息
        cls._enum_members[name] = members
        
        # 註冊類型
        glux_type = GluxType(name, TypeKind.ENUM, base_type)
        cls.register_type(glux_type)
        
        return glux_type
    
    @classmethod
    def register_union_type(cls, name: str, fields: List[Tuple[str, ir.Type]]) -> GluxType:
        """
        註冊聯合類型
        
        Args:
            name: 聯合類型名稱
            fields: 欄位列表 (名稱, 類型)
            
        Returns:
            聯合類型
        """
        union_type = cls._create_union_type(fields, name)
        
        # 註冊類型
        glux_type = GluxType(name, TypeKind.UNION, union_type)
        cls.register_type(glux_type)
        
        return glux_type
    
    @classmethod
    def register_function_type(cls, name: str, return_type: ir.Type, param_types: List[ir.Type], param_names: Optional[List[str]] = None) -> GluxType:
        """
        註冊函數類型
        
        Args:
            name: 函數類型名稱
            return_type: 返回類型
            param_types: 參數類型列表
            param_names: 參數名稱列表 (可選)
            
        Returns:
            函數類型
        """
        # 創建函數類型
        func_type = ir.FunctionType(return_type, param_types)
        
        # 註冊類型
        glux_type = GluxType(name, TypeKind.FUNCTION, func_type)
        cls.register_type(glux_type)
        
        return glux_type
    
    @classmethod
    def is_type_compatible(cls, source_type: str, target_type: str) -> bool:
        """
        檢查類型相容性
        
        Args:
            source_type: 源類型名稱
            target_type: 目標類型名稱
            
        Returns:
            是否相容
        """
        # 相同類型當然相容
        if source_type == target_type:
            return True
            
        # 檢查相容性映射
        if source_type in cls._type_compat:
            return target_type in cls._type_compat[source_type]
        
        # 處理指針相容性
        if source_type.endswith('*') and target_type.endswith('*'):
            # void* 可以與任何指針相容
            if source_type == "void*" or target_type == "void*":
                return True
                
            # 指向相容類型的指針相容
            source_base = source_type[:-1].strip()
            target_base = target_type[:-1].strip()
            return cls.is_type_compatible(source_base, target_base)
        
        # 獲取類型信息
        source_glux_type = cls.get_type(source_type)
        target_glux_type = cls.get_type(target_type)
        
        # 處理 Option<T> 和 T 的相容性
        if source_glux_type and source_glux_type.is_generic():
            if source_type.startswith("Option<") and source_type[7:-1] == target_type:
                return True
        
        # 處理 T 和 Option<T> 的相容性 (T 可以賦值給 Option<T>)
        if target_glux_type and target_glux_type.is_generic():
            if target_type.startswith("Option<") and target_type[7:-1] == source_type:
                return True
        
        return False
    
    @classmethod
    def get_common_type(cls, type1: str, type2: str) -> Optional[str]:
        """
        獲取兩個類型的共同類型
        
        Args:
            type1: 第一個類型名稱
            type2: 第二個類型名稱
            
        Returns:
            共同類型名稱，如果沒有共同類型則返回 None
        """
        # 相同類型直接返回
        if type1 == type2:
            return type1
            
        # 如果其中一個類型是 void，返回另一個
        if type1 == "void":
            return type2
        if type2 == "void":
            return type1
            
        # 檢查相容性
        if cls.is_type_compatible(type1, type2):
            return type2
        if cls.is_type_compatible(type2, type1):
            return type1
            
        # 對於數字類型，找出最高精度的類型
        if cls._is_numeric_type(type1) and cls._is_numeric_type(type2):
            return cls._get_highest_precision_type(type1, type2)
            
        # 處理指針類型
        if type1.endswith('*') and type2.endswith('*'):
            # 如果目標類型不同，返回 void*
            return "void*"
            
        # 沒有共同類型
        return None
    
    @classmethod
    def _is_numeric_type(cls, type_name: str) -> bool:
        """
        檢查類型是否為數字類型
        
        Args:
            type_name: 類型名稱
            
        Returns:
            是否為數字類型
        """
        return (type_name in cls._signed_int_types or 
                type_name in cls._unsigned_int_types or 
                type_name in cls._float_types)
    
    @classmethod
    def _get_highest_precision_type(cls, type1: str, type2: str) -> str:
        """
        獲取兩個數字類型中精度最高的類型
        
        Args:
            type1: 第一個類型名稱
            type2: 第二個類型名稱
            
        Returns:
            精度最高的類型名稱
        """
        # 如果有浮點類型，優先選擇浮點
        if type1 in cls._float_types and type2 not in cls._float_types:
            return type1
        if type2 in cls._float_types and type1 not in cls._float_types:
            return type2
            
        # 如果都是浮點類型，選擇精度高的
        if type1 in cls._float_types and type2 in cls._float_types:
            double_types = {"f64", "double"}
            if type1 in double_types:
                return type1
            if type2 in double_types:
                return type2
            return type1  # 兩者精度相同
            
        # 如果都是整數類型，選擇位寬更大的
        # 對於有符號和無符號混合的情況，選擇有符號且位寬更大的
        if type1 in cls._signed_int_types and type2 in cls._unsigned_int_types:
            t1_width = int(re.search(r'(\d+)', type1).group(1)) if re.search(r'(\d+)', type1) else 32
            t2_width = int(re.search(r'(\d+)', type2).group(1)) if re.search(r'(\d+)', type2) else 8
            if t1_width > t2_width:
                return type1
            return f"i{max(t1_width * 2, 32)}"  # 位寬加倍以安全容納無符號值
        
        if type2 in cls._signed_int_types and type1 in cls._unsigned_int_types:
            t2_width = int(re.search(r'(\d+)', type2).group(1)) if re.search(r'(\d+)', type2) else 32
            t1_width = int(re.search(r'(\d+)', type1).group(1)) if re.search(r'(\d+)', type1) else 8
            if t2_width > t1_width:
                return type2
            return f"i{max(t2_width * 2, 32)}"  # 位寬加倍以安全容納無符號值
            
        # 同為有符號或同為無符號的情況
        t1_width = int(re.search(r'(\d+)', type1).group(1)) if re.search(r'(\d+)', type1) else (32 if type1 in cls._signed_int_types else 8)
        t2_width = int(re.search(r'(\d+)', type2).group(1)) if re.search(r'(\d+)', type2) else (32 if type2 in cls._signed_int_types else 8)
        
        if t1_width >= t2_width:
            return type1
        return type2
    
    @classmethod
    def get_struct_fields(cls, struct_name: str) -> Optional[Tuple[List[ir.Type], Optional[List[str]]]]:
        """
        獲取結構體欄位信息
        
        Args:
            struct_name: 結構體名稱
            
        Returns:
            欄位類型和欄位名稱的元組，如果結構體不存在則返回 None
        """
        return cls._struct_fields.get(struct_name)
    
    @classmethod
    def get_enum_members(cls, enum_name: str) -> Optional[Dict[str, int]]:
        """
        獲取枚舉成員信息
        
        Args:
            enum_name: 枚舉名稱
            
        Returns:
            枚舉成員字典，如果枚舉不存在則返回 None
        """
        return cls._enum_members.get(enum_name)
    
    @classmethod
    def get_union_fields(cls, union_name: str) -> Optional[List[Tuple[str, ir.Type]]]:
        """
        獲取聯合類型欄位信息
        
        Args:
            union_name: 聯合類型名稱
            
        Returns:
            聯合類型欄位列表，如果聯合類型不存在則返回 None
        """
        return cls._union_fields.get(union_name)
    
    @classmethod
    def clear(cls):
        """
        清除類型系統狀態
        """
        cls._types.clear()
        cls._llvm_type_cache.clear()
        cls._struct_fields.clear()
        cls._enum_members.clear()
        cls._union_fields.clear()
        cls._type_compat.clear()


# 初始化類型系統
TypeSystem.initialize() 