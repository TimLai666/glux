"""
Glux 類型系統模組
提供類型註冊、查詢和處理的功能
"""

from typing import Dict, List, Optional, Tuple, Union
from .type_defs import TypeKind, GluxType


class TypeSystem:
    """
    類型系統管理類
    單例模式實現，管理所有已知類型
    """
    # 類型註冊表
    _types: Dict[str, GluxType] = {}
    
    @classmethod
    def register_type(cls, type_obj: GluxType) -> None:
        """
        註冊類型
        
        Args:
            type_obj: 要註冊的類型對象
        """
        cls._types[type_obj.name] = type_obj
    
    @classmethod
    def get_type(cls, name: str) -> Optional[GluxType]:
        """
        通過名稱獲取類型
        
        Args:
            name: 類型名稱
            
        Returns:
            對應的類型對象或None（如果未找到）
        """
        return cls._types.get(name)
    
    @classmethod
    def create_array_type(cls, element_type: GluxType) -> GluxType:
        """
        創建陣列類型
        
        Args:
            element_type: 元素類型
            
        Returns:
            陣列類型
        """
        type_name = f"[]{element_type.name}"
        # 檢查是否已存在
        if type_name in cls._types:
            return cls._types[type_name]
        
        array_type = GluxType(type_name, TypeKind.ARRAY)
        array_type.subtypes.append(element_type)
        cls.register_type(array_type)
        return array_type
    
    @classmethod
    def create_map_type(cls, key_type: GluxType, value_type: GluxType) -> GluxType:
        """
        創建映射類型
        
        Args:
            key_type: 鍵類型
            value_type: 值類型
            
        Returns:
            映射類型
        """
        type_name = f"map<{key_type.name},{value_type.name}>"
        # 檢查是否已存在
        if type_name in cls._types:
            return cls._types[type_name]
        
        map_type = GluxType(type_name, TypeKind.MAP)
        map_type.subtypes.append(key_type)
        map_type.subtypes.append(value_type)
        cls.register_type(map_type)
        return map_type
    
    @classmethod
    def create_function_type(cls, return_type: Optional[GluxType], param_types: List[GluxType], 
                            param_names: Optional[List[str]] = None) -> GluxType:
        """
        創建函數類型
        
        Args:
            return_type: 返回值類型，若為None則表示void
            param_types: 參數類型列表
            param_names: 參數名稱列表（可選）
            
        Returns:
            函數類型
        """
        # 處理None返回類型（視為void）
        if return_type is None:
            return_type = cls.get_type("void")
            if return_type is None:
                # 如果void類型未註冊，則創建一個
                return_type = GluxType("void", TypeKind.VOID)
                cls.register_type(return_type)
        
        # 生成函數類型名稱
        params_str = ",".join(p.name for p in param_types if p is not None)
        type_name = f"fn({params_str})->{return_type.name}"
        
        # 檢查是否已存在
        if type_name in cls._types:
            return cls._types[type_name]
        
        fn_type = GluxType(type_name, TypeKind.FUNCTION)
        fn_type.return_type = return_type
        fn_type.params = param_types
        fn_type.param_types = param_types  # 同時設置param_types屬性，以確保兼容性
        
        if param_names:
            fn_type.param_names = param_names
        else:
            fn_type.param_names = [f"param{i}" for i in range(len(param_types))]
        
        cls.register_type(fn_type)
        return fn_type
    
    @classmethod
    def create_union_type(cls, types: List[GluxType]) -> GluxType:
        """
        創建聯合類型
        
        Args:
            types: 聯合的類型列表
            
        Returns:
            聯合類型
        """
        # 排序並合併相同名稱的類型
        type_names = sorted(set(t.name for t in types))
        type_name = f"union<{','.join(type_names)}>"
        
        # 檢查是否已存在
        if type_name in cls._types:
            return cls._types[type_name]
        
        union_type = GluxType(type_name, TypeKind.UNION)
        # 確保只包含唯一的類型
        seen_names = set()
        unique_types = []
        
        for t in types:
            if t.name not in seen_names:
                unique_types.append(t)
                seen_names.add(t.name)
        
        union_type.subtypes = unique_types
        cls.register_type(union_type)
        return union_type
    
    @classmethod
    def create_tuple_type(cls, types: List[GluxType]) -> GluxType:
        """
        創建元組類型
        
        Args:
            types: 元組元素類型列表
            
        Returns:
            元組類型
        """
        type_name = f"tuple<{','.join(t.name for t in types)}>"
        
        # 檢查是否已存在
        if type_name in cls._types:
            return cls._types[type_name]
        
        tuple_type = GluxType(type_name, TypeKind.TUPLE)
        tuple_type.subtypes = types
        cls.register_type(tuple_type)
        return tuple_type
    
    @classmethod
    def create_pointer_type(cls, base_type: GluxType) -> GluxType:
        """
        創建指針類型
        
        Args:
            base_type: 基礎類型
            
        Returns:
            指針類型
        """
        type_name = f"*{base_type.name}"
        
        # 檢查是否已存在
        if type_name in cls._types:
            return cls._types[type_name]
        
        ptr_type = GluxType(type_name, TypeKind.POINTER)
        ptr_type.subtypes.append(base_type)
        cls.register_type(ptr_type)
        return ptr_type
    
    @classmethod
    def is_type_compatible(cls, source_type: str, target_type: str) -> bool:
        """
        檢查源類型是否與目標類型兼容
        
        Args:
            source_type: 源類型名稱
            target_type: 目標類型名稱
            
        Returns:
            是否兼容
        """
        # 獲取類型
        source = cls.get_type(source_type)
        target = cls.get_type(target_type)
        
        if not source or not target:
            return False
        
        # 相同類型一定兼容
        if source == target:
            return True
        
        # 任何類型都可以賦值給 any
        if target.name == "any":
            return True
        
        # 數值類型之間的兼容性
        if cls.is_numeric_type(source.name) and cls.is_numeric_type(target.name):
            # 允許精度提升
            if cls.is_integer_type(source.name) and cls.is_integer_type(target.name):
                # 整型之間根據大小判斷兼容性
                return cls.get_integer_size(source.name) <= cls.get_integer_size(target.name)
            
            if cls.is_float_type(source.name) and cls.is_float_type(target.name):
                # 浮點型之間根據精度判斷兼容性
                return cls.get_float_precision(source.name) <= cls.get_float_precision(target.name)
            
            # 整型可以提升為浮點型
            if cls.is_integer_type(source.name) and cls.is_float_type(target.name):
                return True
        
        # 聯合類型的兼容性
        if target.kind == TypeKind.UNION:
            # 源類型與聯合類型中的任一類型兼容，則源類型與聯合類型兼容
            return any(cls.is_type_compatible(source.name, t.name) for t in target.subtypes)
        
        # 指針類型的兼容性
        if source.kind == TypeKind.POINTER and target.kind == TypeKind.POINTER:
            # 指針基礎類型兼容即可
            return cls.is_type_compatible(source.subtypes[0].name, target.subtypes[0].name)
        
        # 函數類型的兼容性
        if source.kind == TypeKind.FUNCTION and target.kind == TypeKind.FUNCTION:
            # 參數數量必須相同
            if len(source.params) != len(target.params):
                return False
            
            # 返回值類型必須兼容
            if not cls.is_type_compatible(source.return_type.name, target.return_type.name):
                return False
            
            # 參數類型必須兼容（逆變）
            for i in range(len(source.params)):
                if not cls.is_type_compatible(target.params[i].name, source.params[i].name):
                    return False
            
            return True
        
        # 針對 null 類型的特殊處理
        if source.name == "null":
            # null 可以賦值給指針類型
            if target.kind == TypeKind.POINTER:
                return True
            
            # null 可以賦值給聯合類型（如果聯合類型包含 null）
            if target.kind == TypeKind.UNION:
                return any(t.name == "null" for t in target.subtypes)
        
        # 默認情況下，類型不兼容
        return False
    
    @classmethod
    def get_common_type(cls, type1: str, type2: str) -> Optional[str]:
        """
        獲取兩個類型的共同類型
        
        Args:
            type1: 第一個類型名稱
            type2: 第二個類型名稱
            
        Returns:
            共同類型名稱或None（如果不存在共同類型）
        """
        # 相同類型
        if type1 == type2:
            return type1
        
        # 如果任一類型是 any，則結果是 any
        if type1 == "any" or type2 == "any":
            return "any"
        
        # 數值類型的共同類型
        if cls.is_numeric_type(type1) and cls.is_numeric_type(type2):
            # 處理整數類型
            if cls.is_integer_type(type1) and cls.is_integer_type(type2):
                # 取較大的整數類型
                size1 = cls.get_integer_size(type1)
                size2 = cls.get_integer_size(type2)
                if size1 >= size2:
                    return type1
                else:
                    return type2
            
            # 處理浮點類型
            if cls.is_float_type(type1) and cls.is_float_type(type2):
                # 取較高精度的浮點類型
                prec1 = cls.get_float_precision(type1)
                prec2 = cls.get_float_precision(type2)
                if prec1 >= prec2:
                    return type1
                else:
                    return type2
            
            # 混合整數和浮點數，結果是浮點數
            if cls.is_float_type(type1):
                return type1
            if cls.is_float_type(type2):
                return type2
        
        # 無共同類型
        return None
    
    @classmethod
    def is_numeric_type(cls, type_name: str) -> bool:
        """檢查是否為數值類型"""
        return type_name in cls.get_numeric_types()
    
    @classmethod
    def is_integer_type(cls, type_name: str) -> bool:
        """檢查是否為整數類型"""
        return type_name in cls.get_integer_types()
    
    @classmethod
    def is_float_type(cls, type_name: str) -> bool:
        """檢查是否為浮點數類型"""
        return type_name in cls.get_float_types()
    
    @classmethod
    def get_numeric_types(cls) -> List[str]:
        """獲取所有數值類型名稱"""
        return cls.get_integer_types() + cls.get_float_types()
    
    @classmethod
    def get_integer_types(cls) -> List[str]:
        """獲取所有整數類型名稱"""
        return ["i8", "i16", "i32", "i64", "u8", "u16", "u32", "u64", "int", "uint", "byte"]
    
    @classmethod
    def get_float_types(cls) -> List[str]:
        """獲取所有浮點數類型名稱"""
        return ["f32", "f64", "float", "double"]
    
    @classmethod
    def get_integer_size(cls, type_name: str) -> int:
        """獲取整數類型的大小（位元數）"""
        size_map = {
            "i8": 8, "u8": 8, "byte": 8,
            "i16": 16, "u16": 16,
            "i32": 32, "u32": 32, "int": 32, "uint": 32,
            "i64": 64, "u64": 64
        }
        return size_map.get(type_name, 0)
    
    @classmethod
    def get_float_precision(cls, type_name: str) -> int:
        """獲取浮點數類型的精度"""
        precision_map = {
            "f32": 32, "float": 32,
            "f64": 64, "double": 64
        }
        return precision_map.get(type_name, 0)
    
    @classmethod
    def initialize_built_in_types(cls) -> None:
        """初始化所有內建類型"""
        # 基本類型
        cls.register_type(GluxType("void", TypeKind.VOID))
        cls.register_type(GluxType("bool", TypeKind.PRIMITIVE))
        
        # 整數類型
        cls.register_type(GluxType("i8", TypeKind.PRIMITIVE))
        cls.register_type(GluxType("i16", TypeKind.PRIMITIVE))
        cls.register_type(GluxType("i32", TypeKind.PRIMITIVE))
        cls.register_type(GluxType("i64", TypeKind.PRIMITIVE))
        cls.register_type(GluxType("u8", TypeKind.PRIMITIVE))
        cls.register_type(GluxType("u16", TypeKind.PRIMITIVE))
        cls.register_type(GluxType("u32", TypeKind.PRIMITIVE))
        cls.register_type(GluxType("u64", TypeKind.PRIMITIVE))
        
        # 別名
        cls.register_type(GluxType("int", TypeKind.PRIMITIVE))
        cls.register_type(GluxType("uint", TypeKind.PRIMITIVE))
        cls.register_type(GluxType("byte", TypeKind.PRIMITIVE))
        
        # 浮點數類型
        cls.register_type(GluxType("f32", TypeKind.PRIMITIVE))
        cls.register_type(GluxType("f64", TypeKind.PRIMITIVE))
        
        # 別名
        cls.register_type(GluxType("float", TypeKind.PRIMITIVE))
        cls.register_type(GluxType("double", TypeKind.PRIMITIVE))
        
        # 字符和字符串
        cls.register_type(GluxType("char", TypeKind.PRIMITIVE))
        cls.register_type(GluxType("string", TypeKind.STRING))
        
        # 通用類型
        cls.register_type(GluxType("any", TypeKind.ANY))
        cls.register_type(GluxType("null", TypeKind.NULL))
        cls.register_type(GluxType("error", TypeKind.ERROR))

    @classmethod
    def initialize_built_in_functions(cls) -> None:
        """初始化所有內建函數"""
        # toString - 轉換任意類型為字符串
        to_string_func = GluxType("toString", TypeKind.FUNCTION)
        to_string_func.params = [TypeSystem.get_type("any")]
        to_string_func.param_names = ["value"]
        to_string_func.return_type = TypeSystem.get_type("string")
        cls.register_type(to_string_func)
        
        # println - 輸出並換行
        println_func = GluxType("println", TypeKind.FUNCTION)
        println_func.params = [TypeSystem.get_type("any")]
        println_func.param_names = ["value"]
        println_func.return_type = TypeSystem.get_type("void")
        cls.register_type(println_func)
        
        # print - 輸出不換行
        print_func = GluxType("print", TypeKind.FUNCTION)
        print_func.params = [TypeSystem.get_type("any")]
        print_func.param_names = ["value"]
        print_func.return_type = TypeSystem.get_type("void")
        cls.register_type(print_func)
        
        # len - 獲取容器長度
        len_func = GluxType("len", TypeKind.FUNCTION)
        len_func.params = [TypeSystem.get_type("any")]
        len_func.param_names = ["container"]
        len_func.return_type = TypeSystem.get_type("i32")
        cls.register_type(len_func)
        
        # is_error - 檢查是否為錯誤
        is_error_func = GluxType("is_error", TypeKind.FUNCTION)
        is_error_func.params = [TypeSystem.get_type("any")]
        is_error_func.param_names = ["value"]
        is_error_func.return_type = TypeSystem.get_type("bool")
        cls.register_type(is_error_func)
        
        # sleep - 暫停執行
        sleep_func = GluxType("sleep", TypeKind.FUNCTION)
        sleep_func.params = [TypeSystem.get_type("i32")]
        sleep_func.param_names = ["milliseconds"]
        sleep_func.return_type = TypeSystem.get_type("void")
        cls.register_type(sleep_func)

    @classmethod
    def infer_numeric_type(cls, value: Union[int, float]) -> str:
        """
        根據數值範圍推導整數或浮點數類型
        
        Args:
            value: 數值
            
        Returns:
            推導出的類型名稱
        """
        if isinstance(value, int):
            # 根據範圍選擇適當的整數型別
            if -128 <= value <= 127:
                return "i8"
            elif -32768 <= value <= 32767:
                return "i16"
            elif -2147483648 <= value <= 2147483647:
                return "i32"
            else:
                return "i64"
        elif isinstance(value, float):
            # 檢查精度決定使用 f32 還是 f64
            value_str = str(value)
            decimal_part = value_str.split('.')[-1]
            
            # 如果小數部分超過7位或使用科學計數法，使用 f64
            if 'e' in value_str.lower() or len(decimal_part) > 7:
                return "f64"
            else:
                return "f32"
        else:
            # 非數值型別
            return "unknown"


# 初始化內建類型
TypeSystem.initialize_built_in_types()
# 初始化內建函數
TypeSystem.initialize_built_in_functions() 