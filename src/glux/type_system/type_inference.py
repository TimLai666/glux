"""
類型推導模塊
專門處理自動類型推導邏輯，如根據整數和浮點數的範圍自動選擇合適類型
"""

from typing import Optional, Union, List, Tuple
from ..parser import ast_nodes
from ..utils.symbol_table import SymbolTable
from .type_system import TypeSystem
from .type_defs import GluxType, TypeKind


class TypeInferenceEngine:
    """
    類型推導引擎
    負責根據表達式和字面量值自動推導最適合的類型
    """
    
    def __init__(self, symbol_table: SymbolTable):
        """
        初始化類型推導引擎
        
        Args:
            symbol_table: 符號表
        """
        self.symbol_table = symbol_table
    
    def infer_type(self, expr) -> Optional[GluxType]:
        """
        推導表達式的類型
        
        Args:
            expr: 表達式節點
            
        Returns:
            推導的類型或None
        """
        if isinstance(expr, ast_nodes.IntLiteral):
            return self.infer_int_type(expr.value)
        elif isinstance(expr, ast_nodes.FloatLiteral):
            return self.infer_float_type(expr.value)
        elif isinstance(expr, ast_nodes.StringLiteral):
            return TypeSystem.get_type("string")
        elif isinstance(expr, ast_nodes.BooleanLiteral):
            return TypeSystem.get_type("bool")
        elif isinstance(expr, ast_nodes.ListLiteral):
            return self.infer_list_type(expr.elements)
        elif isinstance(expr, ast_nodes.MapLiteral):
            return self.infer_map_type(expr.pairs)
        
        # 對於其他類型的表達式，返回None表示無法自動推導
        return None
    
    def infer_int_type(self, value: int) -> GluxType:
        """
        根據整數值範圍推導最適合的整數類型
        
        Args:
            value: 整數值
            
        Returns:
            推導的整數類型
        """
        if -128 <= value <= 127:
            return TypeSystem.get_type("i8")
        elif -32768 <= value <= 32767:
            return TypeSystem.get_type("i16")
        elif -2147483648 <= value <= 2147483647:
            return TypeSystem.get_type("i32")
        else:
            return TypeSystem.get_type("i64")
    
    def infer_float_type(self, value: float) -> GluxType:
        """
        根據浮點數值的精度推導最適合的浮點數類型
        
        Args:
            value: 浮點數值
            
        Returns:
            推導的浮點數類型
        """
        # 轉換為字串檢查精度
        value_str = str(value)
        
        # 檢查是否有科學計數法
        if 'e' in value_str.lower():
            # 科學計數法通常需要更高精度
            return TypeSystem.get_type("f64")
        
        # 根據小數部分的位數決定
        if '.' in value_str:
            decimal_part = value_str.split('.')[-1]
            if len(decimal_part) > 7:
                # 超過7位小數精度，使用f64
                return TypeSystem.get_type("f64")
        
        # 預設使用f32
        return TypeSystem.get_type("f32")
    
    def infer_list_type(self, elements: List[ast_nodes.Expression]) -> GluxType:
        """
        推導列表的類型
        
        Args:
            elements: 列表元素
            
        Returns:
            推導的列表類型
        """
        # 對於空列表，預設為任意類型的列表
        if not elements:
            return TypeSystem.create_list_type(TypeSystem.get_type("any"))
        
        # 推導第一個元素的類型
        first_type = self.infer_type(elements[0])
        if not first_type:
            return TypeSystem.create_list_type(TypeSystem.get_type("any"))
        
        # 檢查所有元素是否都是相同類型
        for element in elements[1:]:
            element_type = self.infer_type(element)
            if not element_type or not TypeSystem.is_type_compatible(element_type.name, first_type.name):
                # 如果有不同類型的元素，則使用any類型
                return TypeSystem.create_list_type(TypeSystem.get_type("any"))
        
        # 所有元素都是相同類型
        return TypeSystem.create_list_type(first_type)
    
    def infer_map_type(self, pairs: List[Tuple[ast_nodes.Expression, ast_nodes.Expression]]) -> GluxType:
        """
        推導映射的類型
        
        Args:
            pairs: 鍵值對列表
            
        Returns:
            推導的映射類型
        """
        # 對於空映射，預設為任意類型
        if not pairs:
            return TypeSystem.create_map_type(
                TypeSystem.get_type("any"),
                TypeSystem.get_type("any")
            )
        
        # 嘗試推導鍵和值的類型
        first_key_type = self.infer_type(pairs[0][0])
        first_value_type = self.infer_type(pairs[0][1])
        
        if not first_key_type or not first_value_type:
            return TypeSystem.create_map_type(
                TypeSystem.get_type("any"),
                TypeSystem.get_type("any")
            )
        
        # 檢查所有鍵和值是否都是相同類型
        key_types_compatible = True
        value_types_compatible = True
        
        for key, value in pairs[1:]:
            key_type = self.infer_type(key)
            value_type = self.infer_type(value)
            
            if not key_type or not TypeSystem.is_type_compatible(key_type.name, first_key_type.name):
                key_types_compatible = False
            
            if not value_type or not TypeSystem.is_type_compatible(value_type.name, first_value_type.name):
                value_types_compatible = False
        
        key_type = first_key_type if key_types_compatible else TypeSystem.get_type("any")
        value_type = first_value_type if value_types_compatible else TypeSystem.get_type("any")
        
        return TypeSystem.create_map_type(key_type, value_type)
    
    def infer_binary_expression_type(self, left_type: GluxType, operator: str, right_type: GluxType) -> Optional[GluxType]:
        """
        推導二元表達式的結果類型
        
        Args:
            left_type: 左操作數類型
            operator: 運算符
            right_type: 右操作數類型
            
        Returns:
            推導的結果類型
        """
        # 比較運算符
        if operator in ['==', '!=', '<', '<=', '>', '>=']:
            return TypeSystem.get_type("bool")
        
        # 特殊處理字串連接
        if operator == '+' and (left_type.name == 'string' or right_type.name == 'string'):
            return TypeSystem.get_type("string")
        
        # 算術運算
        if operator in ['+', '-', '*', '/', '%']:
            # 檢查是否為數值類型
            if not self._is_numeric_type(left_type.name) or not self._is_numeric_type(right_type.name):
                return None
            
            # 獲取共同類型
            common_type_name = TypeSystem.get_common_type(left_type.name, right_type.name)
            if not common_type_name:
                return None
            
            return TypeSystem.get_type(common_type_name)
        
        # 邏輯運算
        if operator in ['and', 'or']:
            if left_type.name == 'bool' and right_type.name == 'bool':
                return TypeSystem.get_type("bool")
            return None
        
        # 位元運算
        if operator in ['&', '|', '^', '<<', '>>']:
            # 檢查是否為整數類型
            if not self._is_integer_type(left_type.name) or not self._is_integer_type(right_type.name):
                return None
            
            # 獲取共同類型
            common_type_name = TypeSystem.get_common_type(left_type.name, right_type.name)
            if not common_type_name:
                return None
            
            return TypeSystem.get_type(common_type_name)
        
        return None
    
    def _is_numeric_type(self, type_name: str) -> bool:
        """檢查類型是否為數值類型"""
        return type_name in TypeSystem.get_numeric_types()
    
    def _is_integer_type(self, type_name: str) -> bool:
        """檢查類型是否為整數類型"""
        return type_name in TypeSystem.get_integer_types() 